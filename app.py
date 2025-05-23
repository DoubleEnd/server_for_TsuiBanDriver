import json

from flask import Flask, request, jsonify

from ai.ai import transcribe_audio_to_srt, get_ai_config
from api.api_dandanPlay import welcome, bangumi, bangumiList, getSubtitle, library
from utils import fun_request
from crawler.get_info import get_info_list
# from api_qBittorrent import get_all_rss_items, login, removeItem, refreshItem, moveItem
from api.api_qBittorrent import login, get_everything, post_everything, set_rule, get_version, get_webapiVersion
from crawler.get_rsslink import get_rss_link
from crawler.get_subgroupinfo import get_subgroup_info
from flask_cors import CORS
from utils.fun_config import update_used_rule, request_rule_msg, get_rule_config, get_rule_info, add_edit_rule, \
    delete_rule, load_json, add_edit_ai_config, delete_ai_config

app = Flask(__name__)
CORS(app)  # 允许所有跨域请求

# 提供动漫信息，返回选定的动漫id
@app.route("/searchAllInfo", methods=["GET", "POST"])
def submit_info():
    if request.method == "POST":
        data = request.json
        banguminame = data.get("name")
        result = get_info_list(banguminame=banguminame)
        # print(result)
        code = 500 if result is None else 404 if result == {} else 200
        msg = "success" if code == 200 else "error"
        # print({"code": code, "msg": msg, "data": result})
        return jsonify({"code": code, "msg": msg, "data": result})

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


# # 获取所有订阅列表
# @app.route("/getItems", methods=["GET", "POST"])
# def submit_getitems():
#     if request.method == "GET":
#         result = get_all_rss_items({"withData": "true"})
#         return jsonify({"code": result.status_code, "msg": "success", "data": result.json()})
#
#     elif request.method == "POST":
#         return jsonify({"error": "请使用 GET 方法提交数据"}), 400
#
#
# # 删除订阅列表或项目
# @app.route("/removeItem", methods=["GET", "POST"])
# def submit_removeitem():
#     if request.method == "POST":
#         # print(request.json)
#         data = request.json
#         result = removeItem(data)
#         # print(result.status_code)
#         return jsonify({"code": result.status_code, "msg": "success"})
#
#     elif request.method == "GET":
#         return jsonify({"error": "请使用 POST 方法提交数据"}), 400
#
#
# # 刷新订阅列表
# @app.route("/refreshItem", methods=["GET", "POST"])
# def submit_refreshItem():
#     if request.method == "POST":
#         data = request.json
#         result = refreshItem(data)
#         # print(result.status_code)
#         return jsonify({"code": result.status_code, "msg": "success" if result.status_code == 200 else "error"})
#
#     elif request.method == "GET":
#         return jsonify({"error": "请使用 POST 方法提交数据"}), 400
#
#
# # 重命名列表或项目
# @app.route("/moveItem", methods=["GET", "POST"])
# def submit_moveItem():
#     if request.method == "POST":
#         data = request.json
#         result = moveItem(data)
#         # print(result.status_code)
#         return jsonify({"code": result.status_code, "msg": "success" if result.status_code == 200 else "error"})
#
#     elif request.method == "GET":
#         return jsonify({"error": "请使用 POST 方法提交数据"}), 400


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
        webapi_version  = get_webapiVersion(data='').text
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
                        "msg": "success" if get_version('').status_code and get_webapiVersion('').status_code ==200 else "error",
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
            return jsonify({"code": 500, "msg": "error", "data": "访问失败"}),500
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
            return jsonify({"code": 500, "msg": "error", "data": "访问失败"}),500
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
            return jsonify({"code": 500, "msg": "error", "data": "访问失败"}),500
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



if __name__ == "__main__":
    fun_request.global_cookie = login({
        'username': 'admin',
        'password': '123456'
    }, )
    app.run(host="0.0.0.0", debug=True)

