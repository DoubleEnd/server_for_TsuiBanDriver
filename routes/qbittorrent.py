# qBittorrent 相关路由
import json
import logging

from flask import Blueprint, request

from api.api_qBittorrent import (
    get_everything, post_everything, set_rule, get_version, get_webapiVersion,
    addFeed, get_rss_items, get_rss_rules, add_torrents, get_torrents_info,
    remove_item, refresh_item, move_item, mark_as_read,
    delete_torrents, matching_articles, remove_rule, set_location,
    get_sync_maindata
)
from api.api_dandanPlay import welcome
from utils.fun_config import get_app_info
from utils.fun_response import success, error

logger = logging.getLogger(__name__)
qbittorrent_bp = Blueprint('qbittorrent', __name__)


def _simple_post_response(result):
    """统一处理 POST 请求的响应：返回 status_code 和结果文本"""
    try:
        if result.status_code == 200:
            return success(result.text)
        return error("qBittorrent 操作失败", result.status_code or 500, msg=result.text)
    except Exception:
        return error("qBittorrent 操作失败", 500)


def _simple_get_response(result):
    """统一处理 GET 请求的响应：返回 status_code 和 JSON 数据"""
    try:
        data = result.json()
        if result.status_code == 200:
            return success(data)
        return error("qBittorrent 请求失败", result.status_code or 500, msg=result.text)
    except ValueError:
        return error("qBittorrent 无返回值", result.status_code or 500)
    except Exception:
        return error("qBittorrent 请求失败", 500)


# qBittorrent通用接口（保留兼容）
@qbittorrent_bp.route("/everything", methods=["GET", "POST"])
def submit_everything():
    if request.method == "POST":
        config = request.json
        result = post_everything(config)
    elif request.method == "GET":
        config = request.args.to_dict()
        result = get_everything(config)
    else:
        return error("请求方法不被允许", 405)

    try:
        data = result.json()
    except ValueError:
        return error("qBittorrent 无返回值", result.status_code or 500)

    if data:
        if result.status_code == 200:
            return success(data.get("data") if request.method == "POST" else data)
        return error("qBittorrent 请求失败", result.status_code or 500, msg=result.text)
    else:
        return error("qBittorrent 无返回值", result.status_code or 500)


# RSS 订阅
@qbittorrent_bp.route("/addFeed", methods=["POST"])
def submit_addfeed():
    data = request.json
    result = addFeed(data)
    return _simple_post_response(result)


# RSS 条目列表
@qbittorrent_bp.route("/rssItems", methods=["GET"])
def submit_rssitems():
    params = request.args.to_dict()
    result = get_rss_items(params)
    return _simple_get_response(result)


# RSS 规则列表
@qbittorrent_bp.route("/rssRules", methods=["GET"])
def submit_rssrules():
    params = request.args.to_dict()
    result = get_rss_rules(params)
    return _simple_get_response(result)


# 删除 RSS 条目
@qbittorrent_bp.route("/removeItem", methods=["POST"])
def submit_removeitem():
    data = request.json
    result = remove_item(data)
    return _simple_post_response(result)


# 刷新 RSS 条目
@qbittorrent_bp.route("/refreshItem", methods=["POST"])
def submit_refreshitem():
    data = request.json
    result = refresh_item(data)
    return _simple_post_response(result)


# 移动 RSS 条目
@qbittorrent_bp.route("/moveItem", methods=["POST"])
def submit_moveitem():
    data = request.json
    result = move_item(data)
    return _simple_post_response(result)


# 标记 RSS 条目已读
@qbittorrent_bp.route("/markAsRead", methods=["POST"])
def submit_markasread():
    data = request.json
    result = mark_as_read(data)
    return _simple_post_response(result)


# 添加下载任务
@qbittorrent_bp.route("/addTorrents", methods=["POST"])
def submit_addtorrents():
    data = request.json
    result = add_torrents(data)
    return _simple_post_response(result)


# 删除下载任务
@qbittorrent_bp.route("/deleteTorrents", methods=["POST"])
def submit_deletetorrents():
    data = request.json
    result = delete_torrents(data)
    return _simple_post_response(result)


# 获取种子列表
@qbittorrent_bp.route("/torrentsInfo", methods=["GET"])
def submit_torrentsinfo():
    params = request.args.to_dict()
    result = get_torrents_info(params)
    return _simple_get_response(result)


# 匹配 RSS 文章
@qbittorrent_bp.route("/matchingArticles", methods=["GET"])
def submit_matchingarticles():
    params = request.args.to_dict()
    result = matching_articles(params)
    return _simple_get_response(result)


# 删除 RSS 规则
@qbittorrent_bp.route("/removeRule", methods=["POST"])
def submit_removerule():
    data = request.json
    result = remove_rule(data)
    return _simple_post_response(result)


# 设置种子保存位置
@qbittorrent_bp.route("/setLocation", methods=["POST"])
def submit_setlocation():
    data = request.json
    result = set_location(data)
    return _simple_post_response(result)


# 获取下载列表 (sync/maindata)
@qbittorrent_bp.route("/downloadList", methods=["GET"])
def submit_downloadlist():
    params = request.args.to_dict()
    result = get_sync_maindata(params)
    return _simple_get_response(result)


# qBittorrent保存下载规则
@qbittorrent_bp.route("/setRule", methods=["GET", "POST"])
def submit_setrule():
    if request.method == "POST":
        data_dict = request.json
        data_dict['ruleDef'] = json.dumps(data_dict['ruleDef'])
        result = set_rule(data_dict)
        if result.status_code == 200:
            return success()
        return error("保存规则失败", result.status_code or 500, msg=result.text)
    elif request.method == "GET":
        return error("请使用 POST 方法提交数据", 400)


# 版本信息
@qbittorrent_bp.route("/allVersion", methods=["GET", "POST"])
def submit_allversion():
    if request.method == "GET":
        qb_version = get_version(data='').text
        webapi_version = get_webapiVersion(data='').text
        dandan_play_version = welcome(params='').json()['version']
        app_info = get_app_info()
        for info in app_info:
            if info["name"] == "qbittorrent版本":
                info["value"] = qb_version
            if info["name"] == "qbittorrentWebApi版本":
                info["value"] = webapi_version
            if info["name"] == "dandanPlay版本":
                info["value"] = dandan_play_version
        data = {"app_info": app_info}
        return success(data)
    elif request.method == "POST":
        return error("请使用 GET 方法提交数据", 400)


@qbittorrent_bp.route("/getBackendVersions", methods=["GET"])
def submit_getbackendversions():
    try:
        versions = {"qBittorrent": "", "qBittorrentWebApi": "", "dandanPlay": ""}
        try:
            qb_res = get_version(data='')
            if qb_res.status_code == 200:
                versions["qBittorrent"] = qb_res.text
        except Exception as e:
            logger.warning(f"[getBackendVersions] 获取qBittorrent版本失败: {str(e)}")
        try:
            webapi_res = get_webapiVersion(data='')
            if webapi_res.status_code == 200:
                versions["qBittorrentWebApi"] = webapi_res.text
        except Exception as e:
            logger.warning(f"[getBackendVersions] 获取WebAPI版本失败: {str(e)}")
        try:
            dandan_res = welcome(params='')
            if dandan_res.status_code == 200:
                versions["dandanPlay"] = dandan_res.json().get('version', '')
        except Exception as e:
            logger.warning(f"[getBackendVersions] 获取dandanPlay版本失败: {str(e)}")
        return success(versions)
    except Exception as e:
        logger.error(f"[getBackendVersions] 异常错误: {str(e)}", exc_info=True)
        return error("获取版本信息失败", 500, msg=str(e))
