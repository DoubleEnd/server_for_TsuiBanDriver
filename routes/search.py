# 搜索相关路由
import json
import logging

from flask import Blueprint, request, jsonify

from crawler.get_info import get_info_list
from crawler.get_rsslink import get_rss_link
from crawler.get_subgroupinfo import get_subgroup_info
from utils.fun_config import get_search_config

logger = logging.getLogger(__name__)
search_bp = Blueprint('search', __name__)


@search_bp.route("/searchAllInfo", methods=["GET", "POST"])
def submit_info():
    if request.method == "POST":
        data = request.json
        banguminame = data.get("name")
        search_config = get_search_config()

        logger.info(f"[searchAllInfo] 开始搜索番剧: {banguminame}")
        logger.info(f"[searchAllInfo] 代理设置 - 已启用: {search_config.get('proxy_enabled')}, "
                    f"协议: {search_config.get('proxy_protocol')}, "
                    f"主机: {search_config.get('proxy_host')}, 端口: {search_config.get('proxy_port')}")

        try:
            result = get_info_list(banguminame=banguminame)
            code = 500 if result is None else 404 if result == {} else 200
            msg = "success" if code == 200 else "error"

            if code == 200:
                logger.info(f"[searchAllInfo] 成功搜索到番剧: {banguminame}")
            else:
                logger.warning(f"[searchAllInfo] 搜索失败 - 代码: {code}, 消息: {msg}")

            return jsonify({"code": code, "msg": msg, "data": result})
        except Exception as e:
            logger.error(f"[searchAllInfo] 异常错误: {str(e)}", exc_info=True)
            return jsonify({"code": 500, "msg": f"error: {str(e)}", "data": None}), 500

    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400

    else:
        return jsonify({"code": 405, "msg": "请求方法不被允许", "data": None}), 405


@search_bp.route("/getSubgroupInfo", methods=["GET", "POST"])
def submit_subgroupinfo():
    if request.method == "POST":
        data = request.json
        bangumiId = data.get("bangumiId")
        result = get_subgroup_info(bangumiId=bangumiId)
        code = 500 if result is None else 404 if result == [] else 200
        msg = "success" if code == 200 else "error"
        return jsonify({"code": code, "msg": msg, "data": result})

    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400

    else:
        return jsonify({"code": 405, "msg": "请求方法不被允许", "data": None}), 405


@search_bp.route("/addRssLink", methods=["GET", "POST"])
def submit_addrsslink():
    if request.method == "POST":
        data = request.json
        bangumiId = data.get("bangumiId")
        subgroupId = data.get("subgroupId")
        result = get_rss_link(bangumiId=bangumiId, subgroupid=subgroupId)
        return jsonify({"code": result.status_code, "msg": ("success" if result.status_code == 200 else "error")})

    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400

    else:
        return jsonify({"code": 405, "msg": "请求方法不被允许", "data": None}), 405
