# dandanPlay 相关路由
import logging
import requests

from flask import Blueprint, Response, request, jsonify, stream_with_context

from api.api_dandanPlay import bangumi, bangumiList, getSubtitle, library, getStreamUrl, getComment, getImage, search_library
from crawler.get_subtitle import get_subtitle_list
from utils import fun_request
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
            return success(data)
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
            return result.text
        else:
            return error("获取番剧详情失败", 500)
    elif request.method == "POST":
        return error("请使用 GET 方法提交数据", 400)


@dandanplay_bp.route("/getSubtitle", methods=["GET", "POST"])
def submit_getSubtitle():
    if request.method == "GET":
        params = request.args.to_dict()
        data = getSubtitle(params=params['videoId'])
        return data
    elif request.method == "POST":
        return error("请使用 GET 方法提交数据", 400)


# 视频流相关辅助函数
# 视频不再由前端直连 dandanPlay，而是统一走本后端的 /yzr/video/<videoId> 代理，
# 这样无论局域网还是外网访问，前端拿到的都是同一个相对地址。
_PROXY_PATH_PREFIX = "/yzr/video"

# 转发给 dandanPlay 的响应头
_STREAM_PASS_HEADERS = (
    "Content-Type",
    "Content-Length",
    "Content-Range",
    "Accept-Ranges",
    "Last-Modified",
    "ETag",
)


def _build_stream_proxy_url(video_id):
    """构造对外的视频流代理地址（相对路径，前端自动带上当前访问的 host）"""
    return f"{_PROXY_PATH_PREFIX}/{video_id}"


@dandanplay_bp.route("/stream", methods=["GET"])
def submit_stream():
    """返回视频流地址，不再依赖客户端 IP 判断"""
    video_id = request.args.get('videoId')
    if not video_id:
        return error("缺少videoId参数", 400)
    stream_url = _build_stream_proxy_url(video_id)
    logger.info(f"[stream] 视频流代理地址: {stream_url}")
    return jsonify({"url": stream_url}), 200


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
        logger.info(f"[comment] 获取弹幕: {video_id}")
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
        logger.info(f"[image] 获取海报图片: {video_id}")
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


@dandanplay_bp.route("/getSubtitleList", methods=["GET", "POST"])
def submit_getSubtitleList():
    if request.method == "GET":
        params = request.args.to_dict()
        if 'videoId' not in params:
            return error("缺少videoId参数", 400)
        video_id = params['videoId']
        titles = []
        try:
            resp = fun_request.api_dandanPlay_request({
                "url": f"/api/v1/subtitle/info/{video_id}",
                "method": "get"
            })
            if resp and resp.status_code == 200:
                data = resp.json()
                if data and data.get('subtitles'):
                    subtitles = data['subtitles']
                    titles = [item.get('fileName') for item in subtitles if item.get('fileName')]
        except Exception as e:
            print(f"API获取字幕列表失败: {e}")

        if not titles:
            result = get_subtitle_list(videoId=video_id)
            if result is not None:
                titles = [item.get('title') for item in result if item.get('title')]

        if not titles:
            return error("未找到字幕", 404)
        return success(titles)
    elif request.method == "POST":
        return error("请使用 GET 方法提交数据", 400)


@dandanplay_bp.route("/setSubtitle", methods=["GET", "POST"])
def submit_setSubtitle():
    if request.method == "GET":
        params = request.args.to_dict()
        if 'videoId' not in params or 'subtitle' not in params:
            return error("缺少videoId或subtitle参数", 400)
        try:
            resp = fun_request.api_dandanPlay_request({
                "url": "/web1/video.html",
                "method": "get",
                "params": {"id": params['videoId'], "subtitle": params['subtitle']}
            })
            ok = resp is not None and resp.status_code == 200
            if ok:
                return success(True)
            return error("设置字幕失败", 500, data=False)
        except Exception as e:
            print(f"setSubtitle 请求出错: {e}")
            return error("设置字幕失败", 500, data=False)
    elif request.method == "POST":
        return error("请使用 GET 方法提交数据", 400)
