from flask import Flask, request, jsonify
from get_info import get_info_list
from api_qBittorrent import get_all_rss_items
from get_subgroupinfo import get_subgroup_info
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # 允许所有跨域请求

@app.route("/searchAllInfo", methods=["GET", "POST"])
def submit_info():
    if request.method == "POST":
        data = request.json
        moviename = data.get("name")
        result = get_info_list(moviename)
        return jsonify({"code": 200, "msg": "success", "data": result})

    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400


@app.route("/getSubgroupInfo", methods=["GET", "POST"])  # 定义一个路由，支持GET和POST方法，路径为/getSubgroupInfo
def submit_subgroupinfo():  # 定义一个处理该路由的函数
    if request.method == "POST":  # 检查请求方法是否为POST
        data = request.json  # 从请求中获取JSON数据
        bangumiId = data.get("bangumiId")  # 从JSON数据中获取bangumiId字段
        result = get_subgroup_info(bangumiId=bangumiId)  # 调用get_subgroup_info函数，传入bangumiId，获取结果
        return jsonify({"code": 200, "msg": "success", "data": result})  # 返回JSON格式的响应，包含状态码、消息和数据

    elif request.method == "GET":  # 检查请求方法是否为GET
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400  # 返回JSON格式的错误响应，状态码为400

@app.route("/addRssLink", methods=["GET", "POST"])
def submit_addrsslink():
    if request.method == "POST":
        data = request.json
        bangumiId = data.get("bangumiId")
        result = get_subgroup_info(bangumiId=bangumiId)
        return jsonify({"code": 200, "msg": "success", "data": result})

    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
