# 配置相关路由（规则、搜索、URL、代理）
import logging
import time

from flask import Blueprint, request, jsonify

from utils import fun_request
from utils.fun_config import (
    update_used_rule, request_rule_msg, get_rule_config, get_rule_info,
    add_edit_rule, delete_rule, get_search_config, save_search_config,
    get_url_config_all, save_url_config
)
from utils.fun_response import success, error

logger = logging.getLogger(__name__)
config_bp = Blueprint('config', __name__)


# ============ 规则管理 ============

@config_bp.route("/getRuleList", methods=["GET", "POST"])
def submit_getrulelist():
    if request.method == "GET":
        data = get_rule_config()
        return success(data)
    elif request.method == "POST    ":
        return error("请使用 GET 方法提交数据", 400)


@config_bp.route("/getRuleInfoList", methods=["GET", "POST"])
def submit_getruleinfolist():
    if request.method == "GET":
        data = get_rule_info()
        return success(data)
    elif request.method == "POST    ":
        return error("请使用 GET 方法提交数据", 400)


@config_bp.route("/matchRule", methods=["GET", "POST"])
def submit_matchrule():
    if request.method == "POST":
        data = request.json
        if 'rule_name' not in data:
            return error("缺少必要的参数 rule_name", 400)
        rule_name = data['rule_name']
        if update_used_rule(rule_name):
            return success(request_rule_msg(rule_name))
        else:
            return error("无效的规则名称", 404, data={"无效的规则名称": rule_name})
    elif request.method == "GET":
        return error("请使用 POST 方法提交数据", 400)


@config_bp.route("/addEditRule", methods=["GET", "POST"])
def submit_addeditrule():
    if request.method == "POST":
        data = request.json
        add_edit_rule(data)
        if add_edit_rule(data):
            return success()
        else:
            return error("新增或修改规则失败", 404)
    elif request.method == "GET":
        return error("请使用 POST 方法提交数据", 400)


@config_bp.route("/deleteRule", methods=["GET", "POST"])
def submit_deleterule():
    if request.method == "POST":
        data = request.json
        if 'name' not in data:
            return error("缺少规则名称", 400)
        rule_name = data['name']
        if delete_rule(rule_name):
            return success()
        else:
            return error("规则不存在", 404)
    elif request.method == "GET":
        return error("请使用 POST 方法提交数据", 400)


# ============ 搜索配置 ============

@config_bp.route("/getSearchConfig", methods=["GET"])
def submit_getsearchconfig():
    if request.method == "GET":
        data = get_search_config()
        return success(data)
    else:
        return error("请求方法不被允许", 405)


@config_bp.route("/saveSearchConfig", methods=["POST"])
def submit_savesearchconfig():
    if request.method == "POST":
        data = request.json
        if save_search_config(data):
            return success()
        else:
            return error("保存配置失败", 500)
    else:
        return error("请求方法不被允许", 405)


# ============ 代理测试 ============

@config_bp.route("/testProxy", methods=["POST"])
def submit_testproxy():
    if request.method == "POST":
        data = request.json
        proxy_host = data.get("proxy_host", "").strip()
        proxy_port = data.get("proxy_port", "").strip()
        if not proxy_host or not proxy_port:
            return error("代理主机和端口不能为空", 400)

        logger.info(f"[testProxy] 开始测试代理服务器 - 主机: {proxy_host}, 端口: {proxy_port}")
        try:
            import requests
            proxy_protocol = data.get("proxy_protocol", "http").lower()
            proxy_url = f"socks5h://{proxy_host}:{proxy_port}" if proxy_protocol == 'socks5' else f"http://{proxy_host}:{proxy_port}"
            logger.info(f"[testProxy] 使用协议: {proxy_protocol}, 代理URL: {proxy_url}")
            proxies = {'http': proxy_url, 'https': proxy_url}
            test_url = "http://httpbin.org/delay/0"
            start_time = time.time()

            try:
                response = requests.get(test_url, proxies=proxies, timeout=10)
                elapsed_time = time.time() - start_time
                latency = int(elapsed_time * 1000)
                logger.info(f"[testProxy] 代理连接成功 - 延迟: {latency}ms")
                return jsonify({"code": 200, "msg": "success", "data": {"success": True, "latency": latency, "status_code": response.status_code}})
            except requests.exceptions.Timeout:
                return jsonify({"code": 200, "msg": "failed", "data": {"success": False, "error": "请求超时（10秒）"}})
            except requests.exceptions.ConnectionError as e:
                return jsonify({"code": 200, "msg": "failed", "data": {"success": False, "error": f"无法连接到代理服务器: {str(e)}"}})
            except requests.exceptions.RequestException as e:
                return jsonify({"code": 200, "msg": "failed", "data": {"success": False, "error": f"请求异常: {str(e)}"}})
        except Exception as e:
            logger.error(f"[testProxy] 异常错误: {str(e)}", exc_info=True)
            return error("测试代理失败", 500, msg=str(e))
    else:
        return error("请求方法不被允许", 405)


# ============ URL 配置 ============

@config_bp.route("/getUrlConfig", methods=["GET"])
def submit_geturlconfig():
    try:
        config = get_url_config_all()
        return success(config)
    except Exception as e:
        logger.error(f"[getUrlConfig] 异常错误: {str(e)}", exc_info=True)
        return error("获取URL配置失败", 500, msg=str(e))


@config_bp.route("/saveUrlConfig", methods=["POST"])
def submit_saveurlconfig():
    if request.method == "POST":
        try:
            data = request.json
            if save_url_config(data):
                fun_request.clear_qb_cookie_cache()
                logger.info(f"[saveUrlConfig] 成功保存URL配置")
                return success()
            else:
                return error("保存URL配置失败", 500)
        except Exception as e:
            logger.error(f"[saveUrlConfig] 异常错误: {str(e)}", exc_info=True)
            return error("保存URL配置失败", 500, msg=str(e))
    else:
        return error("请求方法不被允许", 405)


# ============ 后端连接测试 ============

@config_bp.route("/testBackendConnection", methods=["POST"])
def test_backend_connection():
    if request.method == "POST":
        try:
            data = request.json
            service_type = data.get('type')

            if service_type == 'qBittorrent':
                host = data.get('host', '')
                port = data.get('port', '')
                username = data.get('username', 'admin')
                password = data.get('password', '123456')
                if not host or not port:
                    return error("缺少必要参数", 400)

                import requests
                try:
                    response = requests.post(
                        f"http://{host}:{port}/api/v2/auth/login",
                        data={'username': username, 'password': password},
                        timeout=10
                    )
                    if response.status_code == 200 and response.text == 'Ok.':
                        logger.info(f"[testBackendConnection] qBittorrent 连接测试成功: {host}:{port}")
                        return success(None, msg="连接成功")
                    else:
                        return error("qBittorrent登录失败", 500, msg="请检查用户名和密码")
                except requests.exceptions.RequestException as e:
                    return error("连接失败", 500, msg=str(e))

            elif service_type == 'dandanPlay':
                host = data.get('host', '')
                port = data.get('port', '')
                if not host or not port:
                    return error("缺少必要参数", 400)

                import requests
                try:
                    response = requests.get(f"http://{host}:{port}/api/v1/welcome", timeout=10)
                    if response.status_code == 200:
                        logger.info(f"[testBackendConnection] dandanPlay 连接测试成功: {host}:{port}")
                        return success(None, msg="连接成功")
                    else:
                        return error("连接失败", 500, msg=f"HTTP {response.status_code}")
                except requests.exceptions.RequestException as e:
                    return error("连接失败", 500, msg=str(e))
            else:
                return error("未知的服务类型", 400)

        except Exception as e:
            logger.error(f"[testBackendConnection] 异常错误: {str(e)}", exc_info=True)
            return error("测试连接失败", 500, msg=str(e))
