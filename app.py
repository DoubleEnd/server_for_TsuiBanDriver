from flask import Flask, request, jsonify
from get_info import get_info_list
from get_rsslink import get_rss_link
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


@app.route("/getSubgroupInfo", methods=["GET", "POST"])
def submit_subgroupinfo():
    if request.method == "POST":
        data = request.json
        bangumiId = data.get("bangumiId")
        result = get_subgroup_info(bangumiId=bangumiId)
        return jsonify({"code": 200, "msg": "success", "data": result})

    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
