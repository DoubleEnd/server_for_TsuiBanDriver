from flask import Flask, request, jsonify

import fun_request
from get_info import get_info_list
from api_qBittorrent import get_all_rss_items, login, addFeed, removeItem, refreshItem, moveItem
from get_rsslink import get_rss_link
from get_subgroupinfo import get_subgroup_info
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # 允许所有跨域请求

#提供动漫信息，返回选定的动漫id
@app.route("/searchAllInfo", methods=["GET", "POST"])
def submit_info():
    if request.method == "POST":
        data = request.json
        movieName = data.get("name")
        result = get_info_list(movieName)
        code = 500 if result is None else 404 if result == [] else 200
        msg = "success" if code == 200 else "error"
        return jsonify({"code": code, "msg": msg, "data": result})

    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400

#提供字幕组信息，返回选定的字幕组id
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

#添加RSS订阅链接到订阅列表
@app.route("/addRssLink", methods=["GET", "POST"])
def submit_addrsslink():
    if request.method == "POST":
        data = request.json
        bangumiId = data.get("bangumiId")
        subgroupId = data.get("subgroupId")
        result = get_rss_link(bangumiId=bangumiId, subgroupid=subgroupId)
        return jsonify({"code": result.status_code, "msg": ( "success" if result.status_code == 200 else "error")})

    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400

#获取所有订阅列表
@app.route("/getItems", methods=["GET", "POST"])
def submit_getitems():
    if request.method == "GET":
        result = get_all_rss_items({"withData":"true"})
        return jsonify({"code": result.status_code, "msg": "success", "data": result.json()})

    elif request.method == "POST":
        return jsonify({"error": "请使用 GET 方法提交数据"}), 400

#删除订阅列表或项目
@app.route("/removeItem", methods=["GET", "POST"])
def submit_removeitem():
    if request.method == "POST":
        # print(request.json)
        data = request.json
        result = removeItem(data)
        # print(result.status_code)
        return jsonify({"code": result.status_code, "msg": "success"})

    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400

#刷新订阅列表
@app.route("/refreshItem", methods=["GET", "POST"])
def submit_refreshItem():
    if request.method == "POST":
        data = request.json
        result = refreshItem(data)
        # print(result.status_code)
        return jsonify({"code": result.status_code, "msg": "success" if result.status_code == 200 else "error"})

    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400

#重命名列表或项目
@app.route("/moveItem", methods=["GET", "POST"])
def submit_moveItem():
    if request.method == "POST":
        data = request.json
        result = moveItem(data)
        # print(result.status_code)
        return jsonify({"code": result.status_code, "msg": "success" if result.status_code == 200 else "error"})

    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400

if __name__ == "__main__":
    fun_request.global_cookie = login({
        'username': 'admin',
        'password': '123456'
    }, )
    app.run(host="0.0.0.0", debug=True)
