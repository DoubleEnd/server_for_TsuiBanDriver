# 搜索相关路由
import logging

from flask import Blueprint, request

from crawler.get_info import get_info_list
from crawler.get_rsslink import get_rss_link
from crawler.get_subgroupinfo import get_subgroup_info
from utils.fun_config import get_search_config
from utils.fun_response import success, error

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

            if code == 200:
                logger.info(f"[searchAllInfo] 成功搜索到番剧: {banguminame}")
                return success(result)
            elif code == 404:
                logger.warning(f"[searchAllInfo] 未找到番剧: {banguminame}")
                return error("未找到该番剧", 404, data=result)
            else:
                logger.warning(f"[searchAllInfo] 搜索失败 - 代码: {code}")
                return error("搜索番剧失败", 500, data=result)
        except Exception as e:
            logger.error(f"[searchAllInfo] 异常错误: {str(e)}", exc_info=True)
            return error("搜索番剧失败", 500, msg=str(e))

    elif request.method == "GET":
        return error("请使用 POST 方法提交数据", 400)

    else:
        return error("请求方法不被允许", 405)


@search_bp.route("/getSubgroupInfo", methods=["GET", "POST"])
def submit_subgroupinfo():
    if request.method == "POST":
        data = request.json
        bangumiId = data.get("bangumiId")
        result = get_subgroup_info(bangumiId=bangumiId)
        code = 500 if result is None else 404 if result == [] else 200
        if code == 200:
            return success(result)
        elif code == 404:
            return error("未找到字幕组信息", 404, data=result)
        else:
            return error("获取字幕组信息失败", 500)

    elif request.method == "GET":
        return error("请使用 POST 方法提交数据", 400)

    else:
        return error("请求方法不被允许", 405)


@search_bp.route("/addRssLink", methods=["GET", "POST"])
def submit_addrsslink():
    if request.method == "POST":
        data = request.json
        bangumiId = data.get("bangumiId")
        subgroupId = data.get("subgroupId")
        result = get_rss_link(bangumiId=bangumiId, subgroupid=subgroupId)
        if result.status_code == 200:
            return success(None)
        return error("添加RSS订阅失败", result.status_code or 500, msg=result.text)

    elif request.method == "GET":
        return error("请使用 POST 方法提交数据", 400)

    else:
        return error("请求方法不被允许", 405)
