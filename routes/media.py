# 本地媒体路由：本地视频直读、封面/缩略图生成、本地字幕与字体
#
# 全流程只按视频文件 ID（videoId）定位资源，视频路径不出后端：
# 前端持有 videoId，后端通过本地番剧库（data/library.json）反查磁盘路径。
import logging
import mimetypes
import os

from flask import Blueprint, Response, request, send_file

from utils import fun_dandan, fun_scan, fun_subtitle
from utils.fun_thumbnail import get_poster, get_sprite, get_sprite_info
from utils.fun_response import success, error

logger = logging.getLogger(__name__)
media_bp = Blueprint('media', __name__)

# 进度条预览精灵图地址（按视频文件 ID）
_THUMBNAIL_SPRITE_PATH = "/yzr/thumbnails/sprite"

# 字幕内容地址（按视频文件 ID + 字幕序号）
_SUBTITLE_PATH = "/yzr/getSubtitle"

# 字幕组外挂字体地址（按视频文件 ID + 字体序号）
_FONT_PATH = "/yzr/getFont"


def _resolve_video():
    """解析 videoId 参数为磁盘路径：返回 (video_id, path)

    videoId 缺失时返回 ("", None)；videoId 存在但库中找不到时 path 为 None。
    """
    video_id = request.args.get("videoId", "").strip()
    if not video_id:
        return "", None
    return video_id, fun_scan.find_path_by_file_id(video_id)


def _missing_video_error(video_id):
    """统一的视频定位失败响应：缺参数 400，文件不存在 404"""
    if not video_id:
        return error("缺少videoId参数", 400)
    return error("视频文件不存在", 404)


@media_bp.route("/videoStream", methods=["GET", "HEAD"])
def submit_video_stream():
    """本地视频流：按 videoId 定位文件并直接返回字节

    send_file(conditional=True) 自动处理 Range 分段请求，支持拖动进度。
    """
    video_id, file_path = _resolve_video()
    if not file_path or not os.path.isfile(file_path):
        logger.error(f"[videoStream] 视频文件不存在: videoId={video_id}")
        return _missing_video_error(video_id)

    mimetype, _ = mimetypes.guess_type(file_path)
    return send_file(file_path, conditional=True, mimetype=mimetype)


@media_bp.route("/poster", methods=["GET"])
def submit_poster():
    """视频封面：按 videoId 定位文件，用 ffmpeg 截帧生成（带缓存）"""
    video_id, file_path = _resolve_video()
    if not file_path or not os.path.isfile(file_path):
        return _missing_video_error(video_id)

    poster_file = get_poster(file_path)
    if not poster_file:
        return error("生成视频封面失败", 500)
    return send_file(poster_file, mimetype="image/jpeg")


@media_bp.route("/thumbnails", methods=["GET"])
def submit_thumbnails():
    """进度条预览缩略图布局信息，前端用于配置播放器 thumbnails"""
    video_id, file_path = _resolve_video()
    if not file_path or not os.path.isfile(file_path):
        return _missing_video_error(video_id)

    info = get_sprite_info(file_path)
    if not info:
        return error("获取缩略图信息失败", 500)
    return success({
        "url": f"{_THUMBNAIL_SPRITE_PATH}?videoId={video_id}",
        "number": info["number"],
        "column": info["column"],
        "width": info["width"],
        "height": info["height"],
    })


@media_bp.route("/thumbnails/sprite", methods=["GET"])
def submit_thumbnail_sprite():
    """进度条预览精灵图：按 videoId 定位文件，用 ffmpeg 生成（带缓存）"""
    video_id, file_path = _resolve_video()
    if not file_path or not os.path.isfile(file_path):
        return _missing_video_error(video_id)

    sprite_file = get_sprite(file_path)
    if not sprite_file:
        return error("生成缩略图失败", 500)
    return send_file(sprite_file, mimetype="image/jpeg")


@media_bp.route("/getSubtitle", methods=["GET"])
def submit_getSubtitle():
    """返回指定字幕内容：按 videoId + 字幕序号（与字幕列表顺序一致）

    外挂字幕读同目录字幕文件；内封字幕从视频中提取对应字幕流。
    """
    video_id, file_path = _resolve_video()
    if not file_path or not os.path.isfile(file_path):
        return _missing_video_error(video_id)

    try:
        index = int(request.args.get("index", ""))
    except (TypeError, ValueError):
        return error("缺少index参数", 400)

    items = fun_subtitle.list_subtitles(file_path)
    if index < 0 or index >= len(items):
        return error("字幕不存在", 404)

    item = items[index]
    if item["source"] == "external":
        text = fun_subtitle.read_external_subtitle(item["path"])
    else:
        try:
            text = fun_subtitle.extract_internal_subtitle(file_path, item["stream"])
        except RuntimeError as e:
            return error("获取字幕内容失败", 500, msg=str(e))

    if text is None:
        return error("获取字幕内容失败", 500)
    return Response(text, content_type="text/plain; charset=utf-8")


@media_bp.route("/getSubtitleList", methods=["GET"])
def submit_getSubtitleList():
    """获取本地字幕列表：同目录外挂字幕 + 视频内封文本字幕"""
    video_id, path = _resolve_video()
    if not path or not os.path.isfile(path):
        return _missing_video_error(video_id)

    data = []
    has_internal = False
    for index, item in enumerate(fun_subtitle.list_subtitles(path)):
        if item["source"] == "external":
            # .ssa 与 .ass 同属 ASS 系列，统一按 ass 交给播放器解析
            sub_type = os.path.splitext(item["path"])[1].lstrip(".").lower()
            if sub_type == "ssa":
                sub_type = "ass"
        else:
            has_internal = True
            # ASS/SSA 内封字幕按 ass 输出以保留样式（交给前端 libass 渲染），
            # 其余文本字幕由 ffmpeg 转成 srt（内置编码器，不依赖 libass）
            sub_type = "ass" if item.get("codec") in ("ass", "ssa") else "srt"
        data.append({
            "source": item["source"],
            "name": item["name"],
            "type": sub_type,
            "url": f"{_SUBTITLE_PATH}?videoId={video_id}&index={index}",
        })

    logger.info(f"[getSubtitleList] videoId={video_id} -> {len(data)} 条字幕")

    # 有内封字幕则后台预热：打开播放页就开始提取并缓存，切换时直接命中缓存
    if has_internal:
        fun_subtitle.start_internal_prefetch(path)

    # 没有字幕属正常情况（多数视频内嵌或无字幕），返回空列表而非报错，与字体/弹幕接口保持一致
    return success(data)


@media_bp.route("/getFontList", methods=["GET"])
def submit_getFontList():
    """获取字幕组随片提供的外挂字体（视频同目录 / fonts 子目录），前端交给 ASS 渲染器加载"""
    video_id, path = _resolve_video()
    if not path or not os.path.isfile(path):
        return _missing_video_error(video_id)

    data = [
        {
            "name": item["name"],
            "url": f"{_FONT_PATH}?videoId={video_id}&index={index}",
        }
        for index, item in enumerate(fun_subtitle.list_external_fonts(path))
    ]
    logger.info(f"[getFontList] videoId={video_id} -> {len(data)} 个外挂字体")
    return success(data)


@media_bp.route("/getFont", methods=["GET"])
def submit_getFont():
    """外挂字体文件：按 videoId + 字体序号（与字体列表顺序一致）"""
    video_id, path = _resolve_video()
    if not path or not os.path.isfile(path):
        return _missing_video_error(video_id)

    try:
        index = int(request.args.get("index", ""))
    except (TypeError, ValueError):
        return error("缺少index参数", 400)

    fonts = fun_subtitle.list_external_fonts(path)
    if index < 0 or index >= len(fonts):
        return error("字体不存在", 404)
    return send_file(fonts[index]["path"])


@media_bp.route("/comment", methods=["GET"])
def submit_comment():
    """视频文件对应的弹幕：按本地文件 ID 找到该文件所属剧集的弹幕库并返回弹幕

    播放器打开/切换视频时先用缓存立即显示（响应头 X-Danmaku-Cached 表示命中缓存），
    再带 refresh=1 重新拉取，拉取结果与缓存按 cid 合并后落盘。
    文件未识别（没有弹幕库）时返回空列表，播放器不显示弹幕。
    """
    video_id = request.args.get('videoId', '').strip()
    if not video_id:
        return error("缺少videoId参数", 400)

    episode_id = (fun_scan.find_episode_by_file_id(video_id) or {}).get("EpisodeId") or ""
    if not episode_id:
        logger.info(f"[comment] 该文件没有对应的弹幕库: {video_id}")
        return success([])

    if request.args.get('refresh'):
        return success(fun_dandan.refresh_comments(episode_id))

    cached = fun_dandan.get_cached_comments(episode_id)
    if cached is not None:
        logger.info(f"[comment] 命中弹幕缓存: {episode_id}（{len(cached)} 条）")
        response = success(cached)
        response.headers["X-Danmaku-Cached"] = "1"
        return response

    return success(fun_dandan.refresh_comments(episode_id))
