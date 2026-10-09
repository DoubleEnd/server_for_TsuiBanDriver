# dandanPlay 相关路由
import logging
import mimetypes
import os
import requests
from urllib.parse import quote

from flask import Blueprint, Response, request, jsonify, send_file, stream_with_context

from api.api_dandanPlay import bangumi, bangumiList, library, getComment, getImage, search_library
from utils import fun_subtitle
from utils.fun_thumbnail import get_poster, get_sprite, get_sprite_info
from utils.fun_response import success, error

logger = logging.getLogger(__name__)
dandanplay_bp = Blueprint('dandanplay', __name__)


@dandanplay_bp.route("/library", methods=["GET", "POST"])
def submit_library():
    if request.method == "GET":
        data = library(params='')
        if data:
            return data.text
        else:
            return error("获取番剧库失败", 500)
    elif request.method == "POST":
        return error("请使用 GET 方法提交数据", 400)


@dandanplay_bp.route("/bangumi", methods=["GET", "POST"])
def submit_bangumi():
    if request.method == "GET":
        params = request.args.to_dict()
        result = bangumi(params=params['params'])
        if result:
            return result.text
        else:
            return error("获取番剧列表失败", 500)
    elif request.method == "POST":
        return error("请使用 GET 方法提交数据", 400)


@dandanplay_bp.route("/bangumi/search", methods=["GET", "POST"])
def submit_bangumi_search():
    """番剧搜索：params 为导航类型（nav），keyword 为搜索关键字，由后端完成筛选后返回"""
    if request.method == "GET":
        args = request.args.to_dict()
        nav_type = args.get('params', '')
        keyword = args.get('keyword', '')
        logger.info(f"[bangumi/search] 类型: {nav_type}, 关键字: {keyword}")
        try:
            data = search_library(keyword=keyword, nav=nav_type)
            if data is None:
                return error("获取番剧列表失败", 500, data=[])
            return success(_simplify_bangumi_list(data))
        except Exception as e:
            logger.error(f"[bangumi/search] 异常错误: {str(e)}", exc_info=True)
            return error("获取番剧列表失败", 500, msg=str(e), data=[])
    return error("请使用 GET 方法提交数据", 400)


@dandanplay_bp.route("/bangumiList", methods=["GET", "POST"])
def submit_bangumiList():
    if request.method == "GET":
        params = request.args.to_dict()
        result = bangumiList(params=params['params'])
        if result:
            try:
                data = result.json()
            except ValueError:
                return error("番剧详情数据解析失败", 500)

            simplified = _simplify_bangumi_detail(data)
            return jsonify(simplified)
        else:
            return error("获取番剧详情失败", 500)
    elif request.method == "POST":
        return error("请使用 GET 方法提交数据", 400)


@dandanplay_bp.route("/getSubtitle", methods=["GET"])
def submit_getSubtitle():
    """返回本地字幕内容：subFile 为外挂字幕文件；videoPath + stream 为视频内封字幕流"""
    sub_file = request.args.get('subFile')
    video_path = request.args.get('videoPath')
    stream_index = request.args.get('stream')

    if sub_file:
        if not os.path.isfile(sub_file):
            return error("字幕文件不存在", 404)
        text = fun_subtitle.read_external_subtitle(sub_file)
    elif video_path and stream_index is not None:
        if not os.path.isfile(video_path):
            return error("视频文件不存在", 404)
        try:
            text = fun_subtitle.extract_internal_subtitle(video_path, stream_index)
        except RuntimeError as e:
            return error("获取字幕内容失败", 500, msg=str(e))
    else:
        return error("缺少subFile或videoPath、stream参数", 400)

    if text is None:
        return error("获取字幕内容失败", 500)
    return Response(text, content_type="text/plain; charset=utf-8")


# 视频流相关辅助函数
# 视频不再由前端直连 dandanPlay，而是统一走本后端的 /yzr/video/<videoId> 代理，
# 这样无论局域网还是外网访问，前端拿到的都是同一个相对地址。
_PROXY_PATH_PREFIX = "/yzr/video"

# 本地视频文件直读地址前缀
_LOCAL_FILE_PATH = "/yzr/file"

# 进度条预览精灵图地址
_THUMBNAIL_SPRITE_PATH = "/yzr/thumbnails/sprite"

# 字幕内容地址
_SUBTITLE_PATH = "/yzr/getSubtitle"

# 转发给 dandanPlay 的响应头
_STREAM_PASS_HEADERS = (
    "Content-Type",
    "Content-Length",
    "Content-Range",
    "Accept-Ranges",
    "Last-Modified",
    "ETag",
)

# bangumiList 返回值精简：只保留前端实际使用的字段
_FILE_KEEP_KEYS = ("Id", "Name", "Path", "AnimeId", "AnimeTitle", "EpisodeTitle")
_EPISODE_KEEP_KEYS = ("EpisodeTitle", "AirDate", "AirStatus")

# bangumi/search 返回值精简：只保留前端实际使用的字段
_BANGUMI_KEEP_KEYS = ("Id", "GroupName", "Cover", "Title", "Rating", "EpisodeWatched", "EpisodeTotal", "AnimeId")


def _simplify_bangumi_detail(data):
    """精简 bangumiList 返回数据，减少传输体积"""
    episodes = []
    for ep in data.get("Episodes", []):
        simplified_ep = {k: ep.get(k) for k in _EPISODE_KEEP_KEYS}
        simplified_ep["LocalMatchedFiles"] = [
            {k: f.get(k) for k in _FILE_KEEP_KEYS}
            for f in ep.get("LocalMatchedFiles", [])
        ]
        episodes.append(simplified_ep)
    return {
        "AnimeId": data.get("AnimeId"),
        "Title": data.get("Title"),
        "Episodes": episodes,
    }


def _simplify_bangumi_list(data):
    """精简 bangumi/search 返回的番剧列表数据"""
    return [
        {k: item.get(k) for k in _BANGUMI_KEEP_KEYS}
        for item in (data or [])
    ]


def _build_stream_proxy_url(video_id):
    """构造对外的视频流代理地址（相对路径，前端自动带上当前访问的 host）"""
    return f"{_PROXY_PATH_PREFIX}/{video_id}"


def _build_local_file_url(file_path):
    """构造本地视频文件直读地址（相对路径，前端自动带上当前访问的 host）"""
    return f"{_LOCAL_FILE_PATH}?path={quote(file_path)}"


@dandanplay_bp.route("/stream", methods=["GET"])
def submit_stream():
    """返回视频播放地址：优先按前端传入的本地文件路径直读，未传路径时回退到 dandanPlay 代理"""
    video_id = request.args.get('videoId')
    file_path = request.args.get('path')
    if not video_id and not file_path:
        return error("缺少videoId或path参数", 400)

    if file_path:
        stream_url = _build_local_file_url(file_path)
    else:
        stream_url = _build_stream_proxy_url(video_id)
    return jsonify({"url": stream_url}), 200


@dandanplay_bp.route("/file", methods=["GET", "HEAD"])
def submit_local_file():
    """本地视频文件直读：直接按磁盘路径返回文件，send_file 自动处理 Range 分段（支持拖动进度）"""
    file_path = request.args.get('path')
    if not file_path:
        return error("缺少path参数", 400)
    if not os.path.isfile(file_path):
        logger.error(f"[file] 视频文件不存在: {file_path}")
        return error("视频文件不存在", 404)

    mimetype, _ = mimetypes.guess_type(file_path)
    return send_file(file_path, conditional=True, mimetype=mimetype)


@dandanplay_bp.route("/poster", methods=["GET"])
def submit_poster():
    """视频封面：用 ffmpeg 从本地视频截帧生成（带缓存）"""
    file_path = request.args.get('path')
    if not file_path:
        return error("缺少path参数", 400)
    if not os.path.isfile(file_path):
        return error("视频文件不存在", 404)

    poster_file = get_poster(file_path)
    if not poster_file:
        return error("生成视频封面失败", 500)
    return send_file(poster_file, mimetype="image/jpeg")


@dandanplay_bp.route("/thumbnails", methods=["GET"])
def submit_thumbnails():
    """进度条预览缩略图布局信息，前端用于配置播放器 thumbnails"""
    file_path = request.args.get('path')
    if not file_path:
        return error("缺少path参数", 400)
    if not os.path.isfile(file_path):
        return error("视频文件不存在", 404)

    info = get_sprite_info(file_path)
    if not info:
        return error("获取缩略图信息失败", 500)
    return success({
        "url": f"{_THUMBNAIL_SPRITE_PATH}?path={quote(file_path)}",
        "number": info["number"],
        "column": info["column"],
        "width": info["width"],
        "height": info["height"],
    })


@dandanplay_bp.route("/thumbnails/sprite", methods=["GET"])
def submit_thumbnail_sprite():
    """进度条预览精灵图：用 ffmpeg 从本地视频生成（带缓存）"""
    file_path = request.args.get('path')
    if not file_path or not os.path.isfile(file_path):
        return error("视频文件不存在", 404)

    sprite_file = get_sprite(file_path)
    if not sprite_file:
        return error("生成缩略图失败", 500)
    return send_file(sprite_file, mimetype="image/jpeg")


@dandanplay_bp.route("/video/<video_id>", methods=["GET", "HEAD"])
def submit_video(video_id):
    """视频流代理：透传 Range 请求，保证播放器可拖动进度"""
    from utils.fun_config import get_url_config
    dandan_play_base_url = get_url_config().get('dandanPlay_BASE_URL', 'http://127.0.0.1:8888')
    upstream_url = f"{dandan_play_base_url}/api/v1/stream/id/{video_id}"

    # 透传 Range，dandanPlay 才会返回 206 与对应片段
    headers = {}
    if request.headers.get('Range'):
        headers['Range'] = request.headers['Range']
    if request.headers.get('If-Range'):
        headers['If-Range'] = request.headers['If-Range']

    try:
        upstream = requests.request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            stream=True,
            timeout=(10, 60),
        )
    except requests.RequestException as e:
        logger.error(f"[video] 请求上游视频流失败: {e}")
        return error("获取视频流失败", 502, msg=str(e))

    if upstream.status_code >= 400:
        logger.error(f"[video] 上游返回错误: {upstream.status_code}")
        upstream.close()
        return error("获取视频流失败", upstream.status_code)

    resp_headers = {}
    for key in _STREAM_PASS_HEADERS:
        value = upstream.headers.get(key)
        if value:
            resp_headers[key] = value
    resp_headers.setdefault('Accept-Ranges', 'bytes')

    logger.info(
        f"[video] 代理视频流 {video_id}: "
        f"Range={request.headers.get('Range', '无')} -> {upstream.status_code}"
    )

    if request.method == "HEAD":
        upstream.close()
        return Response(status=upstream.status_code, headers=resp_headers)

    def generate():
        try:
            for chunk in upstream.iter_content(chunk_size=64 * 1024):
                if chunk:
                    yield chunk
        except requests.RequestException as e:
            # 客户端中断/上游断开属于常见情况，仅记录
            logger.warning(f"[video] 视频流传输中断 {video_id}: {e}")
        finally:
            upstream.close()

    return Response(
        stream_with_context(generate()),
        status=upstream.status_code,
        headers=resp_headers,
        direct_passthrough=True,
    )


@dandanplay_bp.route("/comment", methods=["GET"])
def submit_comment():
    if request.method == "GET":
        params = request.args.to_dict()
        if 'videoId' not in params:
            return "", 400
        video_id = params['videoId']
        try:
            resp = getComment(videoId=video_id)
            if resp.status_code == 200:
                return resp.content, 200, {'Content-Type': 'application/json'}
            else:
                logger.error(f"[comment] 获取弹幕失败: {resp.status_code}")
                return "", resp.status_code
        except Exception as e:
            logger.error(f"[comment] 异常错误: {str(e)}", exc_info=True)
            return "", 500
    else:
        return "", 405


@dandanplay_bp.route("/image", methods=["GET"])
def submit_image():
    if request.method == "GET":
        params = request.args.to_dict()
        if 'videoId' not in params:
            return error("缺少videoId参数", 400)
        video_id = params['videoId']
        try:
            resp = getImage(videoId=video_id)
            if resp.status_code == 200:
                return resp.content, 200, {'Content-Type': 'image/jpeg'}
            else:
                return resp.content, resp.status_code, {'Content-Type': 'image/jpeg'}
        except Exception as e:
            logger.error(f"[image] 异常错误: {str(e)}", exc_info=True)
            return error("获取海报图片失败", 500, msg=str(e))
    else:
        return error("请求方法不被允许", 405)


@dandanplay_bp.route("/getSubtitleList", methods=["GET"])
def submit_getSubtitleList():
    """获取本地字幕列表：同目录外挂字幕 + 视频内封文本字幕"""
    path = request.args.get('path')
    if not path:
        return error("缺少path参数", 400)
    if not os.path.isfile(path):
        return error("视频文件不存在", 404)

    data = []
    has_internal = False
    for item in fun_subtitle.list_subtitles(path):
        if item["source"] == "external":
            # .ssa 与 .ass 同属 ASS 系列，统一按 ass 交给播放器解析
            sub_type = os.path.splitext(item["path"])[1].lstrip(".").lower()
            if sub_type == "ssa":
                sub_type = "ass"
            sub_url = f"{_SUBTITLE_PATH}?subFile={quote(item['path'])}"
        else:
            has_internal = True
            # ASS/SSA 内封字幕按 ass 输出以保留样式（交给前端 libass 渲染），
            # 其余文本字幕由 ffmpeg 转成 srt（内置编码器，不依赖 libass）
            sub_type = "ass" if item.get("codec") in ("ass", "ssa") else "srt"
            sub_url = f"{_SUBTITLE_PATH}?videoPath={quote(path)}&stream={item['stream']}"
        data.append({
            "source": item["source"],
            "name": item["name"],
            "type": sub_type,
            "url": sub_url,
        })

    logger.info(f"[getSubtitleList] {path} -> {len(data)} 条字幕")
    if not data:
        return error("未找到字幕", 404)

    # 有内封字幕则后台预热：打开播放页就开始提取并缓存，切换时直接命中缓存
    if has_internal:
        fun_subtitle.start_internal_prefetch(path)

    return success(data)


@dandanplay_bp.route("/getFontList", methods=["GET"])
def submit_getFontList():
    """获取字幕组随片提供的外挂字体（视频同目录 / fonts 子目录），前端交给 ASS 渲染器加载"""
    path = request.args.get('path')
    if not path:
        return error("缺少path参数", 400)
    if not os.path.isfile(path):
        return error("视频文件不存在", 404)

    data = [
        {
            "name": item["name"],
            "url": f"{_LOCAL_FILE_PATH}?path={quote(item['path'])}",
        }
        for item in fun_subtitle.list_external_fonts(path)
    ]
    logger.info(f"[getFontList] {path} -> {len(data)} 个外挂字体")
    return success(data)
