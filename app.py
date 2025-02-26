from flask import Flask, request, jsonify
from get_info import get_info_list
from get_rsslink import get_rss_link
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允许所有跨域请求

@app.route("/searchAllInfo", methods=["GET", "POST"])
def submit_info():
    if request.method == "POST":
        data = request.json  # 获取 JSON 数据
        moviename = data.get("name")
        result = get_info_list(moviename)

        return jsonify({"code": 200, "msg": "success", "data": result})


    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400


@app.route("/getRSSLink", methods=["GET", "POST"])
def submit_rsslink():
    if request.method == "POST":
        data = request.json  # 获取 JSON 数据
        id = data.get("id")
        result = get_rss_link(id)

        return jsonify({"code": 200, "msg": "success", "data": result})


    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)