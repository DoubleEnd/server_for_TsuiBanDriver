# 本地媒体库：扫描目录、调用弹弹play 识别番剧与集数，生成番剧库并落盘 data/
import hashlib
import logging
import os
import re
import time
from datetime import datetime

from utils import fun_bangumi, fun_dandan
from utils.config_manager import get_base_path, load_json_safe, save_json_safe
from utils.fun_config import get_scan_config

logger = logging.getLogger(__name__)

# 视为视频的扩展名
_VIDEO_EXTS = (
    ".mkv", ".mp4", ".avi", ".rmvb", ".rm", ".mov", ".wmv",
    ".flv", ".ts", ".m2ts", ".webm", ".m4v", ".mpg", ".mpeg",
)

# 扫描结果落盘目录（项目根目录下 data/）
_DATA_DIR_NAME = "data"
_LIBRARY_FILE_NAME = "library.json"

# 未识别到在线番剧时的分组名
_DEFAULT_GROUP = "本地番剧"
# 无法判断分组时的名称（缺少放送日期、缺少文件时间等）
_UNKNOWN_GROUP = "未知"
# 最近播放中没有任何观看记录的番剧的分组名
_UNWATCHED_GROUP = "未观看"

# 本地视频封面地址（按视频文件 ID 取图，用于未识别番剧的封面）
_POSTER_PATH = "/yzr/poster"

# 扫描状态：running 供并发保护，last_result 供前端查询最近一次结果
_scan_state = {"running": False, "last_result": None}


def get_library_path():
    """番剧库落盘路径：data/library.json"""
    return os.path.join(get_base_path(), _DATA_DIR_NAME, _LIBRARY_FILE_NAME)


def load_library():
    """读取最近一次扫描生成的番剧库，不存在返回 None"""
    return load_json_safe(get_library_path())


def load_library_public():
    """读取番剧库并剔除视频磁盘路径（对外接口用），不存在返回 None

    视频路径只在后端内部使用，前端一律以文件 ID（videoId）引用。
    """
    library = load_library()
    if not library:
        return library
    result = dict(library)
    result["series"] = [
        {
            **series,
            "files": [
                {key: value for key, value in item.items() if key != "path"}
                for item in series.get("files") or []
            ],
        }
        for series in library.get("series") or []
    ]
    return result


def get_scan_state():
    return dict(_scan_state)


def _compile_blacklist(patterns):
    """把黑名单字符串编译为正则，路径与正则都支持

    Windows 路径里的反斜杠不是合法正则转义（如 E:\\Videos\\ACG\\shnk 中的 \\V），
    这类规则按「路径字面量」处理；其余按正则编译，便于用文件名特征（如 Sample）过滤。
    """
    compiled = []
    for pattern in patterns or []:
        text = str(pattern)
        try:
            compiled.append(re.compile(text, re.IGNORECASE))
        except re.error:
            logger.info(f"[scan] 黑名单含路径反斜杠，按路径字面量处理: {text}")
            compiled.append(re.compile(re.escape(text), re.IGNORECASE))
    return compiled


def _is_blacklisted(patterns, full_path, name):
    """黑名单对“完整路径”或“文件名”任一命中即排除"""
    for pattern in patterns:
        if pattern.search(full_path) or pattern.search(name):
            return True
    return False


def _scan_root(root, blacklist):
    """遍历单个扫描目录，返回命中的视频文件列表与命中黑名单跳过的数量"""
    files = []
    skipped = 0
    for current_dir, _dir_names, file_names in os.walk(root):
        for name in sorted(file_names):
            if os.path.splitext(name)[1].lower() not in _VIDEO_EXTS:
                continue
            full_path = os.path.join(current_dir, name)
            if _is_blacklisted(blacklist, full_path, name):
                skipped += 1
                logger.info(f"[scan] 命中黑名单，跳过: {full_path}")
                continue
            try:
                stat = os.stat(full_path)
            except OSError as e:
                logger.warning(f"[scan] 读取文件信息失败: {full_path} ({e})")
                continue
            files.append({
                "name": name,
                "path": full_path,
                "size": stat.st_size,
                "mtime": int(stat.st_mtime),
            })
    return files, skipped


def _series_of(root, file_path):
    """按“扫描目录下的一级子目录”归组；直接位于根目录的文件归到根目录名下"""
    rel = os.path.relpath(file_path, root)
    parts = rel.split(os.sep)
    if len(parts) > 1:
        return os.path.join(root, parts[0]), parts[0]
    return root, os.path.basename(os.path.normpath(root))


def _extract_episodes(detail):
    """从在线番剧信息中提取剧集列表"""
    episodes = []
    for ep in (detail or {}).get("episodes") or []:
        episodes.append({
            "episodeId": str(ep.get("episodeId", "")),
            "episodeTitle": ep.get("episodeTitle") or "",
            "episodeNumber": ep.get("episodeNumber"),
            "airDate": ep.get("airDate") or "",
        })
    return episodes


def _episode_number_value(value):
    """把集号转成数字，非数字（如 SP、OVA）返回 None"""
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _first_air_date(detail, episodes):
    """放送日期：优先详情 startDate，接口不返回时取正片首集的 airDate

    部分番剧含开播前的特别篇，直接取最早 airDate 会落到上一季度，
    因此优先取集号最小（且不小于 1）的正片集。
    """
    start = (detail or {}).get("startDate")
    if start:
        return str(start)
    numbered = [
        (_episode_number_value(ep.get("episodeNumber")), str(ep["airDate"]))
        for ep in episodes
        if ep.get("airDate")
    ]
    numbered = [(n, d) for n, d in numbered if n is not None and n >= 1]
    if numbered:
        return min(numbered)[1]
    dates = sorted(str(ep.get("airDate") or "") for ep in episodes if ep.get("airDate"))
    return dates[0] if dates else ""


def _build_series_by_anime(anime_id, group):
    """按识别结果构建一部番剧（含在线信息、剧集列表与本地文件）"""
    detail = fun_dandan.get_bangumi(anime_id) or {}
    episodes = _extract_episodes(detail)
    start_date = _first_air_date(detail, episodes)

    # 用在线剧集补全每个本地文件的集号 / 集名
    episode_by_id = {ep["episodeId"]: ep for ep in episodes if ep.get("episodeId")}
    for item in group["files"]:
        episode = episode_by_id.get(str(item.get("episodeId") or ""))
        if episode:
            item["episodeNumber"] = episode.get("episodeNumber")
            item["episodeTitle"] = episode.get("episodeTitle") or item.get("episodeTitle")

    return {
        "animeId": str(anime_id),
        "title": detail.get("animeTitle") or group.get("title") or "",
        "typeDescription": detail.get("typeDescription") or "",
        "rating": detail.get("rating") or 0,
        "startDate": start_date,
        "season": fun_dandan.season_label(start_date),
        "imageUrl": detail.get("imageUrl") or "",
        "episodeCount": len(episodes) or len(group["files"]),
        "episodes": episodes,
        "files": sorted(group["files"], key=lambda f: f["name"].lower()),
    }


def _build_local_series(series_dir, group):
    """未识别的文件按目录归组为一部本地番剧"""
    files = sorted(group["files"], key=lambda f: f["name"].lower())
    return {
        "animeId": "",
        "dir": series_dir,
        "title": group.get("title") or "",
        "rating": 0,
        "season": "",
        "episodeCount": len(files),
        "episodes": [],
        "files": files,
    }


def scan_library():
    """执行一次媒体库扫描，结果写入 data/library.json，返回扫描摘要

    流程：遍历扫描目录 → 复用已有识别记录或调用弹弹play 识别文件所属番剧与剧集
    → 按 animeId 归组 → 拉取番剧详情（名称/封面/评分/季度/剧集列表）→ 清理失效记录 → 落盘。
    已有识别记录的文件不再请求识别接口；文件已删除、被移走或命中黑名单的记录会被删除，
    作品下已无任何文件的识别记录也会一并清理，不留空白作品。
    未配置弹弹play 凭证时跳过识别，退化为按目录归组，功能仍可用。
    """
    if _scan_state["running"]:
        logger.warning("[scan] 已有扫描任务进行中，忽略本次触发")
        return {"running": True, "message": "已有扫描任务进行中"}

    config = get_scan_config()
    scan_paths = config.get("scan_paths") or []
    blacklist = _compile_blacklist(config.get("scan_blacklist"))

    if not scan_paths:
        logger.warning("[scan] 未配置任何扫描目录，已跳过")
        return {"total_files": 0, "total_series": 0, "skipped": 0, "message": "未配置扫描目录"}

    identified = fun_dandan.is_configured()
    if not identified:
        logger.warning("[scan] 未配置弹弹play AppId/AppSecret，跳过文件识别，仅按目录归组")

    _scan_state["running"] = True
    started = time.time()
    logger.info(f"[scan] 开始扫描，目录: {scan_paths}，黑名单规则: {len(blacklist)} 条，识别: {identified}")

    try:
        total_skipped = 0
        collected = []
        for root in scan_paths:
            if not os.path.isdir(root):
                logger.warning(f"[scan] 扫描目录不存在，已跳过: {root}")
                continue
            files, skipped = _scan_root(root, blacklist)
            total_skipped += skipped
            logger.info(f"[scan] 目录 {root} 扫描到 {len(files)} 个视频文件，黑名单跳过 {skipped} 个")
            for item in files:
                collected.append((root, item))

        total_files = len(collected)
        logger.info(f"[scan] 共 {total_files} 个视频文件，开始识别")

        matched_groups = {}
        local_groups = {}
        unmatched = 0
        for root, item in collected:
            info = fun_dandan.match_file(item["path"], item["name"]) if identified else None
            if info and info.get("AnimeId"):
                item["episodeId"] = info.get("EpisodeId") or ""
                item["episodeTitle"] = info.get("EpisodeTitle") or ""
                group = matched_groups.setdefault(
                    info["AnimeId"], {"title": info.get("AnimeTitle") or "", "files": []}
                )
                group["files"].append(item)
            else:
                unmatched += 1
                series_dir, series_title = _series_of(root, item["path"])
                local_groups.setdefault(
                    series_dir, {"title": series_title, "files": []}
                )["files"].append(item)

        series = [_build_series_by_anime(aid, group) for aid, group in matched_groups.items()]
        series += [_build_local_series(d, group) for d, group in local_groups.items()]
        series.sort(key=lambda s: (s.get("title") or "").lower())

        # 清理识别记录：文件已消失或命中黑名单的删除，作品下已无任何文件的记录一并删除
        pruned = fun_dandan.prune_cache(item["path"] for _root, item in collected)
        # 同步清理已不在媒体库中的剧集弹幕缓存
        pruned_danmaku = fun_dandan.prune_danmaku(
            file_item.get("episodeId")
            for series_item in series
            for file_item in series_item.get("files") or []
        )

        elapsed = round(time.time() - started, 2)
        library = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "scan_paths": scan_paths,
            "identified": identified,
            "total_files": total_files,
            "total_series": len(series),
            "skipped": total_skipped,
            "unmatched": unmatched,
            "series": series,
        }
        save_json_safe(get_library_path(), library)
        fun_dandan.save_cache()
        logger.info(
            f"[scan] 扫描完成：{len(series)} 部番剧 / {total_files} 个文件"
            f"（未识别 {unmatched} 个），黑名单跳过 {total_skipped} 个，"
            f"清理识别记录 {pruned['matches']} 条失效文件 / {pruned['bangumi']} 条无文件作品，"
            f"清理弹幕缓存 {pruned_danmaku} 份，"
            f"耗时 {elapsed}s，已写入 {get_library_path()}"
        )

        result = {
            "updated_at": library["updated_at"],
            "total_files": total_files,
            "total_series": len(series),
            "skipped": total_skipped,
            "unmatched": unmatched,
            "identified": identified,
            "elapsed": elapsed,
        }
        _scan_state["last_result"] = result
        return result
    finally:
        _scan_state["running"] = False


# ---------- 番剧库查询（首页番剧列表 / 详情） ----------


def _series_dir(series):
    """番剧所属目录：优先取库中记录的 dir，旧数据回退到首个文件所在目录"""
    if series.get("dir"):
        return series["dir"]
    files = series.get("files") or []
    if files:
        return os.path.dirname(files[0]["path"])
    return series.get("title") or ""


def _series_id(series):
    """番剧稳定 ID：已识别的用弹弹play animeId，未识别的由作品目录推导"""
    anime_id = str(series.get("animeId") or "").strip()
    if anime_id:
        return anime_id
    return hashlib.md5(_series_dir(series).encode("utf-8")).hexdigest()[:16]


def _file_id(file_path):
    """视频文件的本地稳定 ID（由文件路径推导）"""
    return hashlib.md5(str(file_path).encode("utf-8")).hexdigest()[:16]


def _episode_key(episode_number=None, episode_id=None, fallback=None):
    """历史记录中「第几集」的键：优先在线集号，其次 episodeId，最后本地序号"""
    if episode_number is not None and str(episode_number).strip() != "":
        return str(episode_number)
    episode_id = str(episode_id or "").strip()
    if episode_id:
        return episode_id
    return str(fallback) if fallback is not None else ""


def _newest_mtime(series):
    return max((f.get("mtime", 0) for f in series.get("files") or []), default=0)


def _oldest_mtime(series):
    """作品内最早文件的时间，可视为「作品首次出现」的时间（新增剧集不会改变它）"""
    return min((f.get("mtime", 0) for f in series.get("files") or []), default=0)


def _month_label_of_timestamp(timestamp):
    """文件时间戳 -> 月份分组名，如 2026年10月；时间无效返回空串"""
    try:
        value = int(timestamp or 0)
    except (TypeError, ValueError):
        return ""
    if value <= 0:
        return ""
    moment = datetime.fromtimestamp(value)
    return f"{moment.year}年{moment.month}月"


def _month_label_of_text(text):
    """历史记录时间（2026-10-12 08:30:00）-> 月份分组名，如 2026年10月；无效返回空串"""
    value = str(text or "").strip()
    if len(value) < 7:
        return ""
    try:
        return f"{int(value[0:4])}年{int(value[5:7])}月"
    except ValueError:
        return ""


def _season_group_rank(group_name):
    """季度分组排序键：季度按时间倒序（新季度在前），非季度分组（本地番剧 / 未知）排在最后

    季度名形如 2024年10月（秋季），由 fun_dandan.season_label 生成。
    """
    text = str(group_name or "")
    try:
        year, rest = text.split("年", 1)
        month = rest.split("月", 1)[0]
        return 0, -int(year), -int(month)
    except (ValueError, IndexError):
        return 1, 0, 0


def _latest_episode_number(series):
    """本地已有文件对应的最新集号：取文件集号的最大值

    未识别（文件没有集号）时退回文件数量；没有文件返回 0。
    """
    files = series.get("files") or []
    numbers = [
        value
        for value in (_episode_number_value(item.get("episodeNumber")) for item in files)
        if value is not None
    ]
    if numbers:
        return int(max(numbers))
    return len(files)


def _to_bangumi_item(series):
    """番剧列表项：优先使用在线信息（封面/评分/集数/季度分组），未识别时回退本地"""
    files = series.get("files") or []
    uid = _series_id(series)
    # 封面：在线海报优先，未识别时用首个文件的本地截帧（按文件 ID 取图）
    cover = series.get("imageUrl") or (
        f"{_POSTER_PATH}?videoId={_file_id(files[0]['path'])}" if files else ""
    )
    if series.get("animeId"):
        group_name = series.get("season") or _UNKNOWN_GROUP
    else:
        group_name = _DEFAULT_GROUP
    return {
        "AnimeId": uid,
        "Title": series.get("title") or "",
        "Cover": cover,
        "Rating": series.get("rating") or 0,
        "EpisodeWatched": 0,
        "EpisodeTotal": series.get("episodeCount") or len(files),
        # 本地已有文件对应的最新集号（首页卡片第二行展示「全 N 话」）
        "EpisodeLatest": _latest_episode_number(series),
        "GroupName": group_name,
    }


def _last_play(episodes):
    """某番剧下最新一次观看时间（可读字符串，可直接按字典序比较）"""
    return max((r.get("updatedAt") or "" for r in (episodes or {}).values()), default="")


def search_bangumi(keyword="", nav="name", history=None):
    """首页番剧列表：从本地番剧库检索，按关键字过滤并按导航方式排序

    nav 取值与前端一致（season/lastplay/lastupdate/lastadd/name/category/rating）。
    history（结构为 {animeId: {集数: 记录}}）传入后，可回填「已看集数」。
    最近播放 / 最近更新 / 最近添加 三种导航以月份为大分类，分组名直接写入 GroupName。
    """
    library = load_library() or {}
    anime_history = history or {}
    nav = nav or "season"

    entries = []
    for series in library.get("series") or []:
        item = _to_bangumi_item(series)
        episodes = anime_history.get(item["AnimeId"]) or {}
        item["EpisodeWatched"] = min(len(episodes), item["EpisodeTotal"])
        entries.append({
            "item": item,
            "newest": _newest_mtime(series),
            "oldest": _oldest_mtime(series),
            "last_play": _last_play(episodes),
        })

    keyword_lower = (keyword or "").strip().lower()
    if keyword_lower:
        entries = [e for e in entries if keyword_lower in e["item"]["Title"].lower()]

    if nav == "lastplay":
        # 观看月份为大分类、最新观看的排最前；没有观看记录的统一归到「未观看」并排在最后
        watched = [e for e in entries if e["last_play"]]
        unwatched = [e for e in entries if not e["last_play"]]
        watched.sort(key=lambda e: e["last_play"], reverse=True)
        unwatched.sort(key=lambda e: e["newest"], reverse=True)
        for entry in watched:
            entry["item"]["GroupName"] = _month_label_of_text(entry["last_play"]) or _UNKNOWN_GROUP
        for entry in unwatched:
            entry["item"]["GroupName"] = _UNWATCHED_GROUP
        entries = watched + unwatched
    elif nav == "lastupdate":
        # 按最新识别文件的识别时间排序，月份为大分类、最新的排最前
        entries.sort(key=lambda e: e["newest"], reverse=True)
        for entry in entries:
            entry["item"]["GroupName"] = _month_label_of_timestamp(entry["newest"]) or _UNKNOWN_GROUP
    elif nav == "lastadd":
        # 按作品首次出现的时间排序（新增剧集不改变它），新出现的番剧排最前
        entries.sort(key=lambda e: e["oldest"], reverse=True)
        for entry in entries:
            entry["item"]["GroupName"] = _month_label_of_timestamp(entry["oldest"]) or _UNKNOWN_GROUP
    elif nav == "rating":
        entries.sort(key=lambda e: e["item"]["Rating"] or 0, reverse=True)
    elif nav == "name":
        entries.sort(key=lambda e: e["item"]["Title"].lower())
    else:
        # 番剧季度 / 分类：先按季度时间给分组排序（新季度在前），同季度内按标题
        entries.sort(key=lambda e: (
            _season_group_rank(e["item"]["GroupName"]),
            e["item"]["Title"].lower(),
        ))

    return [entry["item"] for entry in entries]


def _find_file(file_id):
    """按视频文件 ID 在番剧库中定位（所属番剧, 文件条目, 同作品内序号）

    找不到返回 (None, None, -1)。
    """
    file_id = str(file_id or "").strip()
    if not file_id:
        return None, None, -1
    for series in (load_library() or {}).get("series") or []:
        for index, item in enumerate(series.get("files") or []):
            if _file_id(item["path"]) == file_id:
                return series, item, index
    return None, None, -1


def find_path_by_file_id(file_id):
    """按视频文件 ID 找到本地视频路径；库中不存在时返回 None"""
    _series, item, _index = _find_file(file_id)
    return item["path"] if item else None


def find_episode_by_file_id(file_id):
    """按视频文件 ID 在番剧库中定位所属番剧与集数

    返回 {AnimeId, AnimeTitle, EpisodeKey, EpisodeId, EpisodeTitle}；库中找不到时返回 None。
    EpisodeKey 为历史记录里「第几集」的键（在线集号 / episodeId / 本地序号）；
    EpisodeId 为该文件识别到的在线剧集 ID（即弹幕库 ID），未识别时为空串。
    """
    series, item, index = _find_file(file_id)
    if item is None:
        return None
    return {
        "AnimeId": _series_id(series),
        "AnimeTitle": series.get("title") or "",
        "EpisodeKey": _episode_key(
            item.get("episodeNumber"), item.get("episodeId"), index + 1
        ),
        "EpisodeId": str(item.get("episodeId") or ""),
        "EpisodeTitle": item.get("episodeTitle") or os.path.splitext(item["name"])[0],
    }


def _build_episode(anime_id, anime_title, episode_title, air_date, files, watched):
    return {
        "EpisodeTitle": episode_title,
        "AirDate": air_date,
        "AirStatus": "1" if watched else "0",
        "LocalMatchedFiles": [
            {
                "Id": _file_id(item["path"]),
                "Name": item["name"],
                "AnimeId": anime_id,
                "AnimeTitle": anime_title,
                "EpisodeTitle": episode_title,
                # 该文件当前识别到的剧集（手动重新识别时用于标记当前剧集）
                "EpisodeId": str(item.get("episodeId") or ""),
            }
            for item in files
        ],
    }


def _bgm_subject_info(bgm_id):
    """弹弹play 未收录该番剧时，退化为 Bangumi.tv 的条目信息（无本地剧集）"""
    try:
        subject = fun_bangumi.get_subject(bgm_id)
    except fun_bangumi.BangumiApiError as e:
        logger.warning(f"[scan] 获取 Bangumi 条目失败: {bgm_id} ({e})")
        return None
    if not isinstance(subject, dict):
        return None

    images = subject.get("images") or {}
    rating = subject.get("rating") or {}
    tags = [t.get("name") for t in (subject.get("tags") or []) if t.get("name")]
    return {
        "AnimeId": "",
        "Title": subject.get("name_cn") or subject.get("name") or "",
        "Cover": images.get("large") or images.get("common") or images.get("medium") or "",
        "Rating": rating.get("score") or 0,
        "TypeDescription": "",
        "Summary": subject.get("summary") or "",
        "Comment": "",
        "Tags": tags[:20],
        "Episodes": [],
    }


def _local_series_info(anime_id, history=None):
    """未识别（或在线信息不可用）的本地番剧：仅返回本地库中的名称、封面与剧集"""
    library = load_library() or {}
    for series in library.get("series") or []:
        if _series_id(series) != str(anime_id):
            continue
        item = _to_bangumi_item(series)
        detail = get_bangumi_detail(str(anime_id), history=history) or {}
        return {
            "AnimeId": str(anime_id),
            "Title": item["Title"],
            "Cover": item["Cover"],
            "Rating": item["Rating"],
            "TypeDescription": "",
            "Summary": "",
            "Comment": "",
            "Tags": [],
            "Episodes": detail.get("Episodes") or [],
        }
    return None


def get_bangumi_info(anime_id=None, bgm_id=None, history=None):
    """番剧详情页数据：在线元信息 + 本地剧集

    anime_id 为番剧库中的稳定 ID（首页/播放页用），bgm_id 为 Bangumi.tv 的 subjectId
    （时间表用）。本地剧集仅在本地番剧库命中该番剧时返回，未命中返回空列表。
    未识别的本地番剧（ID 非弹弹play 纯数字 animeId）或在线信息不可用时，退化为本地信息。
    """
    if bgm_id:
        detail = fun_dandan.get_bangumi_by_bgmtv(bgm_id)
        if not detail:
            # 弹弹play 未收录时用 Bangumi.tv 条目兜底，保证时间表能正常打开详情页
            return _bgm_subject_info(bgm_id)
    elif anime_id:
        # 只有弹弹play 的 animeId（纯数字）才值得请求在线信息，本地推导的 ID 直接走本地
        detail = fun_dandan.get_bangumi(anime_id) if str(anime_id).isdigit() else None
        if not detail:
            return _local_series_info(anime_id, history)
    else:
        return None
    if not detail:
        return None

    real_id = str(detail.get("animeId") or anime_id or "").strip()
    local = get_bangumi_detail(real_id, history=history) if real_id else None
    # 标签按接口顺序取前若干个，避免条目过多挤满页面
    tags = [t.get("name") for t in (detail.get("tags") or []) if t.get("name")]

    return {
        "AnimeId": real_id,
        "Title": detail.get("animeTitle") or "",
        "Cover": detail.get("imageUrl") or "",
        "Rating": detail.get("rating") or 0,
        "TypeDescription": detail.get("typeDescription") or "",
        "Summary": detail.get("summary") or detail.get("intro") or "",
        "Comment": detail.get("comment") or "",
        "Tags": tags[:20],
        "Episodes": (local or {}).get("Episodes") or [],
    }


def get_bangumi_detail(anime_id, history=None):
    """番剧详情：优先返回在线剧集列表（含集名/放送日期），本地文件挂在对应集下

    未识别（无在线剧集）时退化为按本地文件顺序，一个文件一集。
    AirStatus 由该用户的历史记录决定（"1" 已观看，"0" 未观看）。
    """
    history = history or {}
    library = load_library() or {}
    for series in library.get("series") or []:
        if _series_id(series) != str(anime_id):
            continue
        uid = _series_id(series)
        title = series.get("title") or ""
        watched_episodes = history.get(uid) or {}

        # 本地文件按所属剧集分组（无 episodeId 的归入空键）
        files_by_episode = {}
        for item in series.get("files") or []:
            files_by_episode.setdefault(str(item.get("episodeId") or ""), []).append(item)

        api_episodes = series.get("episodes") or []
        episodes = []
        if api_episodes:
            for ep in api_episodes:
                ep_id = str(ep.get("episodeId") or "")
                number = ep.get("episodeNumber")
                key = _episode_key(number, ep_id)
                episodes.append(_build_episode(
                    uid, title,
                    ep.get("episodeTitle") or "",
                    ep.get("airDate") or "",
                    files_by_episode.get(ep_id) or [],
                    key in watched_episodes,
                ))
        else:
            for index, item in enumerate(series.get("files") or []):
                number = index + 1
                episodes.append(_build_episode(
                    uid, title,
                    item.get("episodeTitle") or f"第{number}话",
                    "",
                    [item],
                    str(number) in watched_episodes,
                ))
        return {"AnimeId": uid, "Title": title, "Episodes": episodes}
    return None


# ---------- 单个文件的手动重新识别 ----------


def _pick_item(series):
    """重新识别弹窗里的作品条目（本地作品与在线搜索结果共用同一结构）"""
    episodes = series.get("episodes") or []
    return {
        "AnimeId": str(series.get("animeId") or ""),
        "Title": series.get("title") or "",
        "TypeDescription": series.get("typeDescription") or "",
        "ImageUrl": series.get("imageUrl") or "",
        "Rating": series.get("rating") or 0,
        "EpisodeCount": len(episodes) or series.get("episodeCount") or 0,
        "StartDate": series.get("startDate") or "",
    }


def search_local_bangumi(keyword=""):
    """本地番剧库中已识别的作品（手动重新识别时选择作品用）

    只返回有在线剧集的作品：没有剧集信息的本地作品无法指定剧集。
    结构与在线搜索结果一致，便于前端复用同一套渲染。
    """
    keyword_lower = str(keyword or "").strip().lower()
    result = []
    for series in (load_library() or {}).get("series") or []:
        anime_id = str(series.get("animeId") or "").strip()
        if not anime_id or not (series.get("episodes") or []):
            continue
        title = series.get("title") or ""
        if keyword_lower and keyword_lower not in title.lower():
            continue
        result.append(_pick_item(series))
    result.sort(key=lambda item: item["Title"].lower())
    return result


def list_bangumi_episodes(anime_id):
    """在线番剧的剧集列表（手动重新识别时选择剧集用）

    获取不到在线信息时返回 None。
    """
    detail = fun_dandan.get_bangumi(anime_id)
    if not detail:
        return None
    return [
        {
            "EpisodeId": ep["episodeId"],
            "EpisodeTitle": ep["episodeTitle"],
            "EpisodeNumber": ep["episodeNumber"],
            "AirDate": ep["airDate"],
        }
        for ep in _extract_episodes(detail)
    ]


def rematch_file(file_id, anime_id, episode_id):
    """手动把某个视频文件改判到指定作品与剧集

    同时更新识别记录（data/dandan_cache.json，后续扫描直接复用改判结果）
    与番剧库（data/library.json，把文件从原作品移到目标作品下）。
    返回改判后的 {AnimeId, AnimeTitle, EpisodeId, EpisodeTitle}。
    """
    file_id = str(file_id or "").strip()
    anime_id = str(anime_id or "").strip()
    episode_id = str(episode_id or "").strip()

    detail = fun_dandan.get_bangumi(anime_id)
    if not detail:
        raise ValueError("未获取到该作品的在线信息")
    episode = next(
        (ep for ep in _extract_episodes(detail) if ep["episodeId"] == episode_id),
        None,
    )
    if episode is None:
        raise ValueError("该作品下没有找到对应剧集")

    library = load_library() or {}
    series_list = library.get("series") or []

    # 从原作品下摘掉这个文件
    record = None
    for series in series_list:
        files = series.get("files") or []
        hit = next((f for f in files if _file_id(f.get("path")) == file_id), None)
        if hit is not None:
            record = hit
            series["files"] = [f for f in files if f is not hit]
            break
    if record is None:
        raise ValueError("番剧库中没有该文件，请先扫描媒体库")
    path = record["path"]

    anime_title = detail.get("animeTitle") or ""
    episode_title = episode["episodeTitle"] or os.path.splitext(record["name"])[0]
    record.update({
        "episodeId": episode["episodeId"],
        "episodeNumber": episode["episodeNumber"],
        "episodeTitle": episode_title,
    })

    # 原作品下已无文件时整体移除，避免留下空白作品
    series_list[:] = [s for s in series_list if s.get("files")]

    # 挂到目标作品下；库中还没有该作品时按在线信息新建
    target = next(
        (s for s in series_list if str(s.get("animeId") or "") == anime_id), None
    )
    if target is None:
        series_list.append(_build_series_by_anime(anime_id, {"files": [record], "title": ""}))
    else:
        target["files"].append(record)
        target["files"].sort(key=lambda f: f["name"].lower())

    library["series"] = series_list
    save_json_safe(get_library_path(), library)

    # 写入识别记录：后续扫描不再请求识别接口，直接用改判结果
    fun_dandan.set_match(path, {
        "AnimeId": anime_id,
        "EpisodeId": episode["episodeId"],
        "AnimeTitle": anime_title,
        "EpisodeTitle": episode_title,
    })

    logger.info(f"[rematch] {os.path.basename(path)} -> {anime_title} / {episode_title}")
    return {
        "AnimeId": anime_id,
        "AnimeTitle": anime_title,
        "EpisodeId": episode["episodeId"],
        "EpisodeTitle": episode_title,
    }
