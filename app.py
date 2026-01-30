import json
import logging
import time

from flask import Flask, request, jsonify
from flask_cors import CORS

from ai.ai import transcribe_audio_to_srt, get_ai_config
from api.api_dandanPlay import welcome, bangumi, bangumiList, getSubtitle, library
from api.api_qBittorrent import get_everything, post_everything, set_rule, get_version, get_webapiVersion
from crawler.get_info import get_info_list
from crawler.get_rsslink import get_rss_link
from crawler.get_subgroupinfo import get_subgroup_info
from crawler.get_subtitle import get_subtitle_list
from utils import fun_request
from utils.fun_config import update_used_rule, request_rule_msg, get_rule_config, get_rule_info, add_edit_rule, \
    delete_rule, load_json, add_edit_ai_config, delete_ai_config, get_search_config, save_search_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允许所有跨域请求


# 提供动漫信息，返回选定的动漫id
@app.route("/searchAllInfo", methods=["GET", "POST"])
def submit_info():
    if request.method == "POST":
        data = request.json
        banguminame = data.get("name")
        search_config = get_search_config()

        # 记录请求信息和代理配置
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


# 提供字幕组信息，返回选定的字幕组id
@app.route("/getSubgroupInfo", methods=["GET", "POST"])
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


# 添加RSS订阅链接到订阅列表
@app.route("/addRssLink", methods=["GET", "POST"])
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


# qBittorrent通用接口
@app.route("/everything", methods=["GET", "POST"])
# def submit_everything():
#     if request.method == "POST":
#         config = request.json
#         result = post_everything(config)
#         try:
#             data = result.json()
#         except ValueError:
#             return jsonify({"code": result.status_code, "msg": "无返回值", "data": None})
#
#         if data:
#             return jsonify({"code": result.status_code,
#                             "msg": "success" if result.status_code == 200 else "error",
#                             "data": data.get("data")})
#         else:
#             pass
#
#
#     elif request.method == "GET":
#         config = request.args.to_dict()
#         result = get_everything(config)
#         # print(config)
#         try:
#             data = result.json()
#             # print(data)
#         except ValueError:
#             return jsonify({"code": result.status_code, "msg": "无返回值", "data": None})
#         if data:
#             return jsonify({"code": result.status_code,
#                             "msg": "success" if result.status_code == 200 else "error",
#                             "data": data})
#         else:
#             pass
def submit_everything():
    if request.method == "POST":
        config = request.json
        result = post_everything(config)

    elif request.method == "GET":
        config = request.args.to_dict()
        result = get_everything(config)

    else:
        return jsonify({"code": 405, "msg": "请求方法不被允许", "data": None}), 405

    try:
        data = result.json()

    except ValueError:
        return jsonify({"code": result.status_code, "msg": "无返回值", "data": None})

    if data:
        return jsonify({"code": result.status_code,
                        "msg": "success" if result.status_code == 200 else "error",
                        "data": data.get("data") if request.method == "POST" else data})

    else:
        return jsonify({"code": result.status_code, "msg": "无返回值", "data": None})


# 发送qBittorrent版本信息和个人信息
@app.route("/allVersion", methods=["GET", "POST"])
def submit_allversion():
    if request.method == "GET":
        qb_version = get_version(data='').text
        webapi_version = get_webapiVersion(data='').text
        dandan_play_version = welcome(params='').json()['version']
        # print(dandan_play_version)
        app_info = load_json("assets/app_info.json")
        for info in app_info:
            if info["name"] == "qbittorrent版本":
                info["value"] = qb_version
            if info["name"] == "qbittorrentWebApi版本":
                info["value"] = webapi_version
            if info["name"] == "dandanPlay版本":
                info["value"] = dandan_play_version
        data = {
            "app_info": app_info,
        }
        return jsonify({"code": get_version('').status_code and get_webapiVersion('').status_code,
                        "msg": "success" if get_version('').status_code and get_webapiVersion(
                            '').status_code == 200 else "error",
                        "data": data})

    elif request.method == "POST":
        return jsonify({"error": "请使用 GET 方法提交数据"}), 400


# qBittorrent保存下载规则
@app.route("/setRule", methods=["GET", "POST"])
def submit_setrule():
    if request.method == "POST":
        data_dict = request.json
        data_dict['ruleDef'] = json.dumps(data_dict['ruleDef'])
        result = set_rule(data_dict)
        return jsonify(
            {"code": result.status_code, "msg": "success" if result.status_code == 200 else "error", "data": None})

    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400


# 获取规则配置列表
@app.route("/getRuleList", methods=["GET", "POST"])
def submit_getrulelist():
    if request.method == "GET":
        data = get_rule_config()
        return jsonify({"code": 200, "msg": "success", "data": data})

    elif request.method == "POST    ":
        return jsonify({"error": "请使用 GET 方法提交数据"}), 400


# 获取规则信息列表
@app.route("/getRuleInfoList", methods=["GET", "POST"])
def submit_getruleinfolist():
    if request.method == "GET":
        data = get_rule_info()
        return jsonify({"code": 200, "msg": "success", "data": data})

    elif request.method == "POST    ":
        return jsonify({"error": "请使用 GET 方法提交数据"}), 400


# 匹配下载规则
@app.route("/matchRule", methods=["GET", "POST"])
def submit_matchrule():
    if request.method == "POST":
        data = request.json
        if 'rule_name' not in data:
            return jsonify({"error": "缺少必要的参数 rule_name"}), 400
        rule_name = data['rule_name']
        if update_used_rule(rule_name):
            return jsonify({"code": 200, "msg": "success", "data": request_rule_msg(rule_name)})
        else:
            return jsonify({"code": 404, "msg": "error", "data": {"无效的规则名称": rule_name}})

    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400


# 新增或编辑下载规则
@app.route("/addEditRule", methods=["GET", "POST"])
def submit_addeditrule():
    if request.method == "POST":
        data = request.json
        add_edit_rule(data)
        if add_edit_rule(data):
            return jsonify({"code": 200, "msg": "success", "data": None})
        else:
            return jsonify({"code": 404, "msg": "error", "data": "新增或修改失败"})

    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400


# 删除下载规则
@app.route("/deleteRule", methods=["GET", "POST"])
def submit_deleterule():
    if request.method == "POST":
        data = request.json
        if 'name' not in data:
            return jsonify({"code": 400, "msg": "error", "data": "缺少规则名称"}), 400

        rule_name = data['name']
        if delete_rule(rule_name):
            return jsonify({"code": 200, "msg": "success", "data": None})
        else:
            return jsonify({"code": 404, "msg": "error", "data": "规则不存在"})
    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400


# # 获取dandanPlay欢迎信息
# @app.route("/welcome", methods=["GET", "POST"])
# def submit_welcome():
#     if request.method == "GET":
#         data = welcome(params='')
#         if data:
#             return data.text
#         else:
#             return jsonify({"code": 500, "msg": "error", "data": "访问失败"}),500
#     elif request.method == "POST":
#         return jsonify({"error": "请使用 GET 方法提交数据"}), 400
#

# 获取dandanPlay媒体库中的所有内容
@app.route("/library", methods=["GET", "POST"])
def submit_library():
    if request.method == "GET":
        data = library(params='')
        if data:
            return data.text
        else:
            return jsonify({"code": 500, "msg": "error", "data": "访问失败"}), 500
    elif request.method == "POST":
        return jsonify({"error": "请使用 GET 方法提交数据"}), 400


# 获取剧集分类
@app.route("/bangumi", methods=["GET", "POST"])
def submit_bangumi():
    if request.method == "GET":
        # 获取 URL 查询参数并转换为字典
        params = request.args.to_dict()
        result = bangumi(params=params['params'])
        if result:
            return result.text
        else:
            return jsonify({"code": 500, "msg": "error", "data": "访问失败"}), 500
    elif request.method == "POST":
        return jsonify({"error": "请使用 GET 方法提交数据"}), 400


# 获取单部番的所有分集
@app.route("/bangumiList", methods=["GET", "POST"])
def submit_bangumiList():
    if request.method == "GET":
        params = request.args.to_dict()
        result = bangumiList(params=params['params'])
        if result:
            return result.text
        else:
            return jsonify({"code": 500, "msg": "error", "data": "访问失败"}), 500
    elif request.method == "POST":
        return jsonify({"error": "请使用 GET 方法提交数据"}), 400


# 获取字幕
@app.route("/getSubtitle", methods=["GET", "POST"])
def submit_getSubtitle():
    if request.method == "GET":
        params = request.args.to_dict()
        # print(params)
        data = getSubtitle(params=params['videoId'])
        # print(data)
        return data
    elif request.method == "POST":
        return jsonify({"error": "请使用 GET 方法提交数据"}), 400


# 获取字幕列表
@app.route("/getSubtitleList", methods=["GET", "POST"])
def submit_getSubtitleList():
    if request.method == "GET":
        params = request.args.to_dict()
        if 'videoId' not in params:
            return jsonify({"error": "缺少videoId参数"}), 400
        result = get_subtitle_list(videoId=params['videoId'])
        if result is None:
            return jsonify({"code": 500, "msg": "error", "data": None})

        # 提取最多两个字幕的 title 列表，仅返回标题（不包含 href）
        titles = [item.get('title') for item in result if item.get('title')]
        titles = titles[:2]
        code = 200 if titles else 404
        msg = "success" if code == 200 else "error"
        return jsonify({"code": code, "msg": msg, "data": titles})
    elif request.method == "POST":
        return jsonify({"error": "请使用 GET 方法提交数据"}), 400


# 设置字幕（访问 video 页面并带上 subtitle 参数），返回布尔结果
@app.route("/setSubtitle", methods=["GET", "POST"])
def submit_setSubtitle():
    if request.method == "GET":
        params = request.args.to_dict()
        if 'videoId' not in params or 'subtitle' not in params:
            return jsonify({"error": "缺少videoId或subtitle参数"}), 400
        try:
            # 传入的 subtitle 仅为文件名字符串，直接放到 subtitle 参数中（无需中间赋值）
            resp = fun_request.api_dandanPlay_request({
                "url": "/web1/video.html",
                "method": "get",
                "params": {"id": params['videoId'], "subtitle": params['subtitle']}
            })
            success = resp is not None and resp.status_code == 200
            return jsonify({"code": 200 if success else 500, "msg": "success" if success else "error", "data": success})
        except Exception as e:
            print(f"setSubtitle 请求出错: {e}")
            return jsonify({"code": 500, "msg": "error", "data": False})

    elif request.method == "POST":
        return jsonify({"error": "请使用 GET 方法提交数据"}), 400


# 获取ai模型和设备配置
@app.route("/aiConfig", methods=["GET"])
def get_ai_configuration():
    try:
        ai_config = get_ai_config()
        return jsonify({
            "valid_models": ai_config.get("valid_models", []),
            "valid_devices": ai_config.get("valid_devices", []),
            "default_model": ai_config.get("default_model"),
            "default_device": ai_config.get("default_device")
        })
    except Exception as e:
        return jsonify({
            "error": "获取配置失败",
            "detail": str(e)
        }), 500


# AI生成字幕
@app.route("/aiSubtitle", methods=["GET"])
def submit_aiSubtitle():
    try:
        params = request.args.to_dict()
        if 'video_path' not in params:
            return jsonify({"error": "缺少video_path参数"}), 400

        # 从配置获取默认值
        ai_config = get_ai_config()
        model_type = params.get('model_type',
                                ai_config.get("default_model", "medium"))
        device = params.get('device',
                            ai_config.get("default_device", "cpu")).lower()
        srt_path = transcribe_audio_to_srt(
            video_path=params['video_path'],
            model_type=model_type,
            device=device
        )
        return jsonify({
            "srt_path": srt_path,
            "model_used": model_type,
            "device_used": device
        })
    except Exception as e:
        return jsonify({
            "error": "处理请求时发生错误",
            "detail": str(e)
        }), 500


# 新增或修改 AI 配置
@app.route("/addEditAiConfig", methods=["POST"])
def submit_addeditaiconfig():
    if request.method == "POST":
        data = request.json
        if add_edit_ai_config(data):
            return jsonify({"code": 200, "msg": "success", "data": None})
        else:
            return jsonify({"code": 400, "msg": "error", "data": "缺少关键信息或配置项无效"})
    else:
        return jsonify({"code": 405, "msg": "请求方法不被允许", "data": None}), 405


# 删除 AI 配置
@app.route("/deleteAiConfig", methods=["POST"])
def submit_deleteaiconfig():
    if request.method == "POST":
        data = request.json
        key = data.get("key")
        if key:
            if delete_ai_config(key):
                return jsonify({"code": 200, "msg": "success", "data": None})
            else:
                return jsonify({"code": 404, "msg": "error", "data": "配置项不存在"})
        else:
            return jsonify({"code": 400, "msg": "error", "data": "缺少配置项名称"})
    else:
        return jsonify({"code": 405, "msg": "请求方法不被允许", "data": None}), 405


# 获取搜索配置
@app.route("/getSearchConfig", methods=["GET"])
def submit_getsearchconfig():
    if request.method == "GET":
        data = get_search_config()
        return jsonify({"code": 200, "msg": "success", "data": data})
    else:
        return jsonify({"code": 405, "msg": "请求方法不被允许", "data": None}), 405


# 保存搜索配置
@app.route("/saveSearchConfig", methods=["POST"])
def submit_savesearchconfig():
    if request.method == "POST":
        data = request.json
        if save_search_config(data):
            return jsonify({"code": 200, "msg": "success", "data": None})
        else:
            return jsonify({"code": 500, "msg": "error", "data": "保存失败"})
    else:
        return jsonify({"code": 405, "msg": "请求方法不被允许", "data": None}), 405


# 测试代理服务器
@app.route("/testProxy", methods=["POST"])
def submit_testproxy():
    if request.method == "POST":
        data = request.json
        proxy_host = data.get("proxy_host", "").strip()
        proxy_port = data.get("proxy_port", "").strip()

        if not proxy_host or not proxy_port:
            return jsonify({"code": 400, "msg": "error", "data": "代理主机和端口不能为空"}), 400

        logger.info(f"[testProxy] 开始测试代理服务器 - 主机: {proxy_host}, 端口: {proxy_port}")

        try:
            import requests

            # 获取代理协议（默认为 http）
            proxy_protocol = data.get("proxy_protocol", "http").lower()

            # 构建代理URL
            if proxy_protocol == "socks5":
                proxy_url = f"socks5://{proxy_host}:{proxy_port}"
            else:
                proxy_url = f"http://{proxy_host}:{proxy_port}"

            logger.info(f"[testProxy] 使用协议: {proxy_protocol}, 代理URL: {proxy_url}")

            # 构建代理URL
            if proxy_protocol == "socks5":
                proxy_url = f"socks5://{proxy_host}:{proxy_port}"
            else:
                proxy_url = f"http://{proxy_host}:{proxy_port}"

            logger.info(f"[testProxy] 使用协议: {proxy_protocol}, 代理URL: {proxy_url}")

            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }

            # 测试代理连接，使用一个简单的 GET 请求
            test_url = "http://httpbin.org/delay/0"
            start_time = time.time()

            try:
                response = requests.get(test_url, proxies=proxies, timeout=10)
                elapsed_time = time.time() - start_time
                latency = int(elapsed_time * 1000)  # 转换为毫秒

                logger.info(f"[testProxy] 代理连接成功 - 延迟: {latency}ms")
                return jsonify({
                    "code": 200,
                    "msg": "success",
                    "data": {
                        "success": True,
                        "latency": latency,
                        "status_code": response.status_code
                    }
                })
            except requests.exceptions.Timeout:
                error_msg = "请求超时（10秒）"
                logger.warning(f"[testProxy] 代理连接超时 - {error_msg}")
                return jsonify({
                    "code": 200,
                    "msg": "failed",
                    "data": {
                        "success": False,
                        "error": error_msg
                    }
                })
            except requests.exceptions.ConnectionError as e:
                error_msg = f"无法连接到代理服务器: {str(e)}"
                logger.warning(f"[testProxy] 代理连接失败 - {error_msg}")
                return jsonify({
                    "code": 200,
                    "msg": "failed",
                    "data": {
                        "success": False,
                        "error": error_msg
                    }
                })
            except requests.exceptions.RequestException as e:
                error_msg = f"请求异常: {str(e)}"
                logger.warning(f"[testProxy] 请求异常 - {error_msg}")
                return jsonify({
                    "code": 200,
                    "msg": "failed",
                    "data": {
                        "success": False,
                        "error": error_msg
                    }
                })
        except Exception as e:
            error_msg = f"测试出错: {str(e)}"
            logger.error(f"[testProxy] 异常错误: {error_msg}", exc_info=True)
            return jsonify({
                "code": 500,
                "msg": "error",
                "data": {
                    "success": False,
                    "error": error_msg
                }
            }), 500
    else:
        return jsonify({"code": 405, "msg": "请求方法不被允许", "data": None}), 405


# 获取后端版本信息
@app.route("/getBackendVersions", methods=["GET"])
def submit_getbackendversions():
    try:
        versions = {
            "qBittorrent": "",
            "qBittorrentWebApi": "",
            "dandanPlay": "",
        }

        # 获取 qBittorrent 版本
        try:
            qb_res = get_version(data='')
            if qb_res.status_code == 200:
                versions["qBittorrent"] = qb_res.text
        except Exception as e:
            logger.warning(f"[getBackendVersions] 获取qBittorrent版本失败: {str(e)}")

        # 获取 qBittorrent WebAPI 版本
        try:
            webapi_res = get_webapiVersion(data='')
            if webapi_res.status_code == 200:
                versions["qBittorrentWebApi"] = webapi_res.text
        except Exception as e:
            logger.warning(f"[getBackendVersions] 获取WebAPI版本失败: {str(e)}")

        # 获取 dandanPlay 版本
        try:
            dandan_res = welcome(params='')
            if dandan_res.status_code == 200:
                versions["dandanPlay"] = dandan_res.json().get('version', '')
        except Exception as e:
            logger.warning(f"[getBackendVersions] 获取dandanPlay版本失败: {str(e)}")

        return jsonify({"code": 200, "msg": "success", "data": versions})
    except Exception as e:
        logger.error(f"[getBackendVersions] 异常错误: {str(e)}", exc_info=True)
        return jsonify({"code": 500, "msg": "error", "data": None}), 500


# 获取URL配置
@app.route("/getUrlConfig", methods=["GET"])
def submit_geturlconfig():
    from utils.fun_config import get_url_config_all
    try:
        config = get_url_config_all()
        return jsonify({"code": 200, "msg": "success", "data": config})
    except Exception as e:
        logger.error(f"[getUrlConfig] 异常错误: {str(e)}", exc_info=True)
        return jsonify({"code": 500, "msg": "error", "data": None}), 500


# 测试后端服务连接
@app.route("/testBackendConnection", methods=["POST"])
def test_backend_connection():
    if request.method == "POST":
        try:
            data = request.json
            service_type = data.get('type')  # 'qBittorrent' 或 'dandanPlay'

            if service_type == 'qBittorrent':
                # 测试 qBittorrent 连接
                from api.api_qBittorrent import login
                host = data.get('host', '')
                port = data.get('port', '')
                username = data.get('username', 'admin')
                password = data.get('password', '123456')

                if not host or not port:
                    return jsonify({"code": 400, "msg": "缺少必要参数"}), 400

                # 构造临时URL
                temp_base_url = f"http://{host}:{port}/api/v2/"

                # 尝试登录
                import requests
                try:
                    response = requests.post(
                        f"{temp_base_url}auth/login",
                        data={'username': username, 'password': password},
                        timeout=10
                    )
                    if response.status_code == 200 and response.text == 'Ok.':
                        logger.info(f"[testBackendConnection] qBittorrent 连接测试成功: {host}:{port}")
                        return jsonify({"code": 200, "msg": "连接成功"})
                    else:
                        logger.warning(f"[testBackendConnection] qBittorrent 登录失败: {response.text}")
                        return jsonify({"code": 500, "msg": "登录失败，请检查用户名和密码"}), 500
                except requests.exceptions.RequestException as e:
                    logger.error(f"[testBackendConnection] qBittorrent 连接失败: {str(e)}")
                    return jsonify({"code": 500, "msg": f"连接失败: {str(e)}"}), 500

            elif service_type == 'dandanPlay':
                # 测试 dandanPlay 连接
                from api.api_dandanPlay import welcome
                host = data.get('host', '')
                port = data.get('port', '')

                if not host or not port:
                    return jsonify({"code": 400, "msg": "缺少必要参数"}), 400

                # 构造临时URL
                temp_base_url = f"http://{host}:{port}"

                # 尝试连接
                import requests
                try:
                    response = requests.get(f"{temp_base_url}/api/v1/welcome", timeout=10)
                    if response.status_code == 200:
                        logger.info(f"[testBackendConnection] dandanPlay 连接测试成功: {host}:{port}")
                        return jsonify({"code": 200, "msg": "连接成功"})
                    else:
                        logger.warning(f"[testBackendConnection] dandanPlay 连接失败: status={response.status_code}")
                        return jsonify({"code": 500, "msg": f"连接失败: HTTP {response.status_code}"}), 500
                except requests.exceptions.RequestException as e:
                    logger.error(f"[testBackendConnection] dandanPlay 连接失败: {str(e)}")
                    return jsonify({"code": 500, "msg": f"连接失败: {str(e)}"}), 500
            else:
                return jsonify({"code": 400, "msg": "未知的服务类型"}), 400

        except Exception as e:
            logger.error(f"[testBackendConnection] 异常错误: {str(e)}", exc_info=True)
            return jsonify({"code": 500, "msg": f"测试失败: {str(e)}"}), 500


# 保存URL配置
@app.route("/saveUrlConfig", methods=["POST"])
def submit_saveurlconfig():
    from utils.fun_config import save_url_config
    if request.method == "POST":
        try:
            data = request.json
            if save_url_config(data):
                # 清除 qBittorrent cookie 缓存，下次访问时会用新的账号密码登录
                fun_request.clear_qb_cookie_cache()
                logger.info(f"[saveUrlConfig] 成功保存URL配置")
                return jsonify({"code": 200, "msg": "success"})
            else:
                logger.warning(f"[saveUrlConfig] 保存失败")
                return jsonify({"code": 500, "msg": "error"}), 500
        except Exception as e:
            logger.error(f"[saveUrlConfig] 异常错误: {str(e)}", exc_info=True)
            return jsonify({"code": 500, "msg": "error"}), 500
    else:
        return jsonify({"code": 405, "msg": "请求方法不被允许"}), 405


if __name__ == "__main__":
    logger.info("[启动] 启动应用服务器...")
    app.run(host="0.0.0.0", debug=True)
