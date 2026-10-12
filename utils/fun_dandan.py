# 弹弹play 开放 API 辅助：文件识别（前 16MB MD5）、番剧信息获取与本地缓存
import hashlib
import logging
import os
import time

from api.api_dandanPlay import bangumi as api_bangumi
from api.api_dandanPlay import bangumi_by_bgmtv as api_bangumi_by_bgmtv
from api.api_dandanPlay import comments as api_comments
from api.api_dandanPlay import match as api_match
from api.api_dandanPlay import search_anime as api_search_anime
from utils.config_manager import get_base_path, load_json_safe, save_json_safe
from utils.fun_request import is_dandanplay_configured

logger = logging.getLogger(__name__)

# 文件识别用的哈希长度：前 16MB
_HASH_SIZE = 16 * 1024 * 1024
_READ_CHUNK = 1024 * 1024

_CACHE_FILE = "dandan_cache.json"
# 番剧信息缓存有效期（秒），7 天
_BANGUMI_TTL = 7 * 24 * 3600

# 内存缓存：一次扫描内复用，避免反复读写文件
_cache = None


def get_cache_path():
    """识别/番剧信息缓存路径：data/dandan_cache.json"""
    return os.path.join(get_base_path(), "data", _CACHE_FILE)


def _migrate_match_keys(matches):
    """旧的识别记录键为「路径|修改时间|大小」，读取时统一迁移为路径键"""
    for key in list(matches.keys()):
        path = key.split("|", 1)[0]
        if path != key:
            matches.setdefault(path, matches.pop(key))


def _load_cache():
    global _cache
    if _cache is None:
        path = get_cache_path()
        data = load_json_safe(path) if os.path.isfile(path) else None
        _cache = data if isinstance(data, dict) else {}
        _cache.setdefault("matches", {})
        _cache.setdefault("bangumi", {})
        _migrate_match_keys(_cache["matches"])
    return _cache


def save_cache():
    """把内存缓存落盘（扫描流程结束时调用）"""
    if _cache is not None:
        save_json_safe(get_cache_path(), _cache)


def is_configured():
    """是否已配置弹弹play 凭证，未配置时扫描会跳过识别"""
    return is_dandanplay_configured()


def file_hash(path):
    """弹弹play 文件识别用的哈希：文件前 16MB（16x1024x1024 字节）的 MD5"""
    md5 = hashlib.md5()
    remaining = _HASH_SIZE
    with open(path, "rb") as f:
        while remaining > 0:
            chunk = f.read(min(_READ_CHUNK, remaining))
            if not chunk:
                break
            md5.update(chunk)
            remaining -= len(chunk)
    return md5.hexdigest()


def match_file(path, name=None):
    """识别视频文件对应的番剧与剧集

    已有扫描记录（按路径）时直接复用，不再请求弹弹play 接口；
    未识别也记录为 None，避免重复请求。接口异常时不写记录，便于下次重试。
    返回 {AnimeId, EpisodeId, AnimeTitle, EpisodeTitle}；未识别返回 None。
    """
    name = name or os.path.basename(path)
    cache = _load_cache()
    if path in cache["matches"]:
        return cache["matches"][path]

    try:
        digest = file_hash(path)
        response = api_match(file_name=name, file_hash=digest)
    except Exception as e:
        logger.warning(f"[dandan] 文件识别请求失败: {name} ({e})")
        return None

    if response is None or response.status_code != 200:
        status = getattr(response, "status_code", "-")
        logger.warning(f"[dandan] 文件识别失败(HTTP {status}): {name}")
        return None

    try:
        body = response.json()
    except ValueError:
        logger.warning(f"[dandan] 文件识别返回无法解析: {name}")
        return None

    if body.get("errorCode"):
        logger.warning(f"[dandan] 文件识别错误: {name} -> {body.get('errorMessage')}")
        return None

    matches = body.get("matches") or []
    result = None
    if body.get("isMatched") and matches:
        first = matches[0]
        result = {
            "AnimeId": str(first.get("animeId", "")),
            "EpisodeId": str(first.get("episodeId", "")),
            "AnimeTitle": first.get("animeTitle") or "",
            "EpisodeTitle": first.get("episodeTitle") or "",
        }
        logger.info(f"[dandan] 识别成功: {name} -> {result['AnimeTitle']} / {result['EpisodeTitle']}")

    cache["matches"][path] = result
    return result


def set_match(path, result):
    """写入/覆盖某个文件的识别记录（手动重新识别用），后续扫描直接复用该结果"""
    cache = _load_cache()
    cache["matches"][path] = result
    save_cache()


def search_anime(keyword):
    """按关键字搜索番剧（手动重新识别用，结果不做缓存）

    返回 [{AnimeId, Title, TypeDescription, ImageUrl, Rating, EpisodeCount, StartDate}]。
    """
    keyword = str(keyword or "").strip()
    if not keyword:
        return []

    try:
        response = api_search_anime(keyword)
    except Exception as e:
        logger.warning(f"[dandan] 搜索番剧失败: {keyword} ({e})")
        return []

    status = getattr(response, "status_code", "-")
    if response is None or response.status_code != 200:
        logger.warning(f"[dandan] 搜索番剧失败(HTTP {status}): {keyword}")
        return []

    try:
        body = response.json()
    except ValueError:
        logger.warning(f"[dandan] 搜索番剧返回无法解析: {keyword}")
        return []

    if body.get("errorCode"):
        logger.warning(f"[dandan] 搜索番剧错误: {keyword} -> {body.get('errorMessage')}")
        return []

    result = [
        {
            "AnimeId": str(item.get("animeId", "")),
            "Title": item.get("animeTitle") or "",
            "TypeDescription": item.get("typeDescription") or "",
            "ImageUrl": item.get("imageUrl") or "",
            "Rating": item.get("rating") or 0,
            "EpisodeCount": item.get("episodeCount") or 0,
            "StartDate": item.get("startDate") or "",
        }
        for item in (body.get("animes") or [])
    ]
    logger.info(f"[dandan] 搜索番剧 {keyword} -> {len(result)} 个结果")
    return result


def prune_cache(active_paths):
    """清理已失效的扫描记录（每次扫描结束后调用）

    - 文件记录：路径不在本次扫描结果中的（文件已删除、被移走或命中黑名单）直接删除
    - 番剧信息：其下已无任何文件记录时删除，避免本地识别里留下空白作品
      （时间表等按 bgmtv 缓存的条目不参与清理）
    返回删除的条数，供扫描日志输出。
    """
    cache = _load_cache()
    active = set(active_paths)

    removed_matches = 0
    for key in list(cache["matches"].keys()):
        if key not in active:
            del cache["matches"][key]
            removed_matches += 1

    referenced = {
        str(info["AnimeId"])
        for info in cache["matches"].values()
        if info and info.get("AnimeId")
    }
    removed_bangumi = 0
    for key in list(cache["bangumi"].keys()):
        if key.startswith("bgmtv:"):
            continue
        if key not in referenced:
            del cache["bangumi"][key]
            removed_bangumi += 1

    return {"matches": removed_matches, "bangumi": removed_bangumi}


def _cached_bangumi(key, fetch):
    """按缓存键读取番剧详情，缺失或过期时调用 fetch 重新拉取

    fetch 为无参函数，返回 requests 响应。接口异常时回退到过期缓存（若有）。
    """
    cache = _load_cache()
    entry = cache["bangumi"].get(key)
    if entry and time.time() - entry.get("cachedAt", 0) < _BANGUMI_TTL:
        return entry.get("data")

    try:
        response = fetch()
    except Exception as e:
        logger.warning(f"[dandan] 获取番剧信息失败: {key} ({e})")
        return entry.get("data") if entry else None

    if response is None or response.status_code != 200:
        status = getattr(response, "status_code", "-")
        logger.warning(f"[dandan] 获取番剧信息失败(HTTP {status}): {key}")
        return entry.get("data") if entry else None

    try:
        body = response.json()
    except ValueError:
        return entry.get("data") if entry else None

    data = body.get("bangumi")
    if not data:
        logger.warning(f"[dandan] 番剧信息为空: {key} -> {body.get('errorMessage')}")
        return entry.get("data") if entry else None

    cache["bangumi"][key] = {"cachedAt": int(time.time()), "data": data}
    logger.info(f"[dandan] 获取番剧信息成功: {data.get('animeTitle')}（{len(data.get('episodes') or [])} 集）")
    return data


def get_bangumi(anime_id):
    """获取番剧详情（含剧集列表、评分、封面），带本地缓存"""
    return _cached_bangumi(str(anime_id), lambda: api_bangumi(anime_id))


def get_bangumi_by_bgmtv(subject_id):
    """按 Bangumi.tv 的 subjectId 获取番剧详情（时间表数据来源），带本地缓存"""
    return _cached_bangumi(f"bgmtv:{subject_id}", lambda: api_bangumi_by_bgmtv(subject_id))


# 弹幕缓存：每个剧集（episodeId）一个文件，落盘 data/danmaku/<episodeId>.json
_DANMAKU_DIR_NAME = "danmaku"

# 弹幕位置：弹幕库与 B站取值一致（1 滚动 / 4 底部 / 5 顶部），
# 播放器（artplayer-plugin-danmuku）用 0 滚动 / 1 顶部 / 2 底部
_DANMAKU_MODES = {1: 0, 2: 0, 3: 0, 4: 2, 5: 1}


def get_danmaku_dir():
    """弹幕缓存目录：data/danmaku"""
    return os.path.join(get_base_path(), "data", _DANMAKU_DIR_NAME)


def _danmaku_path(episode_id):
    """某剧集的弹幕缓存文件路径"""
    return os.path.join(get_danmaku_dir(), f"{episode_id}.json")


def _parse_comment(comment):
    """单条弹幕：p 为「出现时间,模式,颜色,用户ID」，m 为弹幕文本

    cid 为弹幕库内的唯一编号，用于缓存合并去重。
    """
    text = str(comment.get("m") or "").strip()
    parts = str(comment.get("p") or "").split(",")
    if not text or len(parts) < 4:
        return None
    try:
        moment = float(parts[0])
        color = int(parts[2])
    except ValueError:
        return None
    try:
        mode = _DANMAKU_MODES.get(int(parts[1]), 0)
    except ValueError:
        mode = 0
    return {
        "cid": str(comment.get("cid") or ""),
        "text": text,
        "time": round(moment, 3),
        "mode": mode,
        "color": f"#{color & 0xFFFFFF:06x}",
    }


def get_cached_comments(episode_id):
    """读取缓存的弹幕，没有缓存返回 None"""
    path = _danmaku_path(episode_id)
    if not os.path.isfile(path):
        return None
    items = (load_json_safe(path) or {}).get("items")
    return items if isinstance(items, list) else None


def save_comments(episode_id, items):
    """写入弹幕缓存（含缓存时间）"""
    saved = save_json_safe(_danmaku_path(episode_id), {
        "cachedAt": int(time.time()),
        "items": items,
    })
    if saved:
        logger.info(f"[dandan] 弹幕缓存已写入: {episode_id}（{len(items)} 条）")
    return saved


def merge_comments(old_items, new_items):
    """合并两批弹幕：按 cid 去重取并集，并按出现时间排序

    同一 cid 以新数据为准；第三方弹幕源抖动导致某次返回变少时，
    旧缓存里的弹幕不会被丢掉。
    """
    merged = {}
    for item in list(new_items or []) + list(old_items or []):
        key = str(item.get("cid") or "")
        if not key:
            key = f"{item.get('time')}|{item.get('mode')}|{item.get('text')}"
        merged.setdefault(key, item)
    return sorted(merged.values(), key=lambda item: item.get("time") or 0)


def fetch_comments(episode_id):
    """从弹弹play 拉取某剧集的弹幕（弹幕库 + 关联的第三方弹幕源）

    返回 [{cid, text, time, mode, color}]：
    time 为出现时间（秒），mode 0 滚动 / 1 顶部 / 2 底部，color 为 #rrggbb。
    未配置凭证、剧集不存在或请求失败时返回空列表。
    """
    episode_id = str(episode_id or "").strip()
    if not episode_id or not is_configured():
        return []

    try:
        response = api_comments(episode_id)
    except Exception as e:
        logger.warning(f"[dandan] 获取弹幕失败: {episode_id} ({e})")
        return []

    status = getattr(response, "status_code", "-")
    if response is None or response.status_code != 200:
        logger.warning(f"[dandan] 获取弹幕失败(HTTP {status}): {episode_id}")
        return []

    try:
        body = response.json()
    except ValueError:
        logger.warning(f"[dandan] 弹幕返回无法解析: {episode_id}")
        return []

    if body.get("errorCode"):
        logger.warning(f"[dandan] 弹幕错误: {episode_id} -> {body.get('errorMessage')}")
        return []

    danmaku = []
    for comment in body.get("comments") or []:
        item = _parse_comment(comment)
        if item:
            danmaku.append(item)
    logger.info(f"[dandan] 拉取弹幕成功: {episode_id} -> {len(danmaku)} 条")
    return danmaku


def refresh_comments(episode_id):
    """重新拉取弹幕并与本地缓存合并落盘，返回合并后的弹幕

    拉取失败时返回旧缓存（保证有缓存就还能用），没有缓存则返回空列表。
    """
    cached = get_cached_comments(episode_id) or []
    fresh = fetch_comments(episode_id)
    if not fresh:
        return cached
    merged = merge_comments(cached, fresh)
    logger.info(
        f"[dandan] 弹幕合并: {episode_id} 缓存 {len(cached)} 条 + 拉取 {len(fresh)} 条 -> {len(merged)} 条"
    )
    save_comments(episode_id, merged)
    return merged


def prune_danmaku(active_episode_ids):
    """清理已不在媒体库中的剧集弹幕缓存，返回删除的文件数（扫描流程结束时调用）"""
    directory = get_danmaku_dir()
    if not os.path.isdir(directory):
        return 0
    active = {str(item) for item in active_episode_ids if str(item or "").strip()}
    removed = 0
    for name in os.listdir(directory):
        if not name.endswith(".json") or os.path.splitext(name)[0] in active:
            continue
        try:
            os.remove(os.path.join(directory, name))
            removed += 1
        except OSError as e:
            logger.warning(f"[dandan] 删除弹幕缓存失败: {name} ({e})")
    return removed


def season_label(start_date):
    """由放送日期推导季度分组名，如 2024-10-05 -> 2024年10月（秋季）；无法解析返回空串"""
    text = str(start_date or "")
    if len(text) < 7:
        return ""
    try:
        year = int(text[0:4])
        month = int(text[5:7])
    except ValueError:
        return ""
    if not 1 <= month <= 12:
        return ""
    quarter_months = (1, 4, 7, 10)
    seasons = ("冬季", "春季", "夏季", "秋季")
    index = (month - 1) // 3
    return f"{year}年{quarter_months[index]}月（{seasons[index]}）"
