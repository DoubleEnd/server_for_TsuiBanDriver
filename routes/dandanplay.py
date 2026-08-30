# dandanPlay 相关路由
import logging
import requests

from flask import Blueprint, request, jsonify

from api.api_dandanPlay import bangumi, bangumiList, getSubtitle, library, getStreamUrl, getComment, getImage
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
            result = bangumi(params=nav_type)
            if not result:
                return error("获取番剧列表失败", 500, data=[])
            try:
                data = result.json()
            except Exception:
                data = []
            if not isinstance(data, list):
                data = []
            keyword_lower = keyword.strip().lower()
            if keyword_lower:
                data = [item for item in data
                        if keyword_lower in str(item.get('Title', '')).lower()]
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
def _is_same_network(ip1, ip2, netmask='255.255.255.0'):
    import ipaddress
    try:
        ip1 = ip1.strip()
        ip2 = ip2.strip()
        if ip1 == ip2:
            return True
        addr1 = ipaddress.ip_address(ip1)
        addr2 = ipaddress.ip_address(ip2)
        network = ipaddress.ip_network(f"{ip1}/{netmask}", strict=False)
        return addr2 in network
    except Exception as e:
        logger.warning(f"[is_same_network] IP网段检查失败: {e}")
        return False


def _get_local_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        logger.warning(f"[stream] 获取本机IP失败: {e}")
        return "127.0.0.1"


@dandanplay_bp.route("/stream", methods=["GET"])
def submit_stream():
    if request.method == "GET":
        params = request.args.to_dict()
        if 'videoId' not in params:
            return error("缺少videoId参数", 400)

        video_id = params['videoId']
        client_ip = request.headers.get('X-Real-IP') or request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        logger.info(f"[stream] 获取视频流URL: {video_id}, 客户端IP: {client_ip}")

        try:
            from utils.fun_config import get_url_config
            url_config = get_url_config()
            dandan_play_base_url = url_config.get('dandanPlay_BASE_URL', 'http://127.0.0.1:8888')
            backend_ip = _get_local_ip()

            stream_url = f"{dandan_play_base_url}/api/v1/stream/id/{video_id}"

            from urllib.parse import urlparse
            parsed_url = urlparse(stream_url)
            video_server_ip = parsed_url.hostname
            logger.info(f"[stream] 原始视频流URL: {stream_url}")
            logger.info(f"[stream] 视频服务器IP: {video_server_ip}")
            logger.info(f"[stream] Python后端主机IP: {backend_ip}")

            if _is_same_network(client_ip, video_server_ip):
                logger.info(f"[stream] 客户端IP {client_ip} 与视频服务器IP {video_server_ip} 在同一网段，使用原始URL")
            else:
                logger.info(f"[stream] 客户端IP {client_ip} 与视频服务器IP {video_server_ip} 不在同一网段")
                if _is_same_network(client_ip, backend_ip):
                    logger.info(f"[stream] 客户端IP {client_ip} 与后端IP {backend_ip} 在同一网段，替换视频URL的IP")
                    stream_url = stream_url.replace(video_server_ip, backend_ip)
                    logger.info(f"[stream] 已替换IP为: {stream_url}")
                else:
                    logger.warning(f"[stream] 客户端IP {client_ip} 与后端IP {backend_ip} 也不在同一网段，保持原始URL")

            return jsonify({"url": stream_url}), 200
        except Exception as e:
            logger.error(f"[stream] 异常错误: {str(e)}", exc_info=True)
            return error("获取视频流失败", 500, msg=str(e))
    else:
        return error("请求方法不被允许", 405)


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
