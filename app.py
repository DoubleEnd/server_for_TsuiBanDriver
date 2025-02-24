from flask import Flask, request, jsonify
from get_info import get_info_list
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允许所有跨域请求

@app.route("/searchAllInfo", methods=["GET", "POST"])
def submit():
    if request.method == "POST":
        data = request.json  # 获取 JSON 数据
        moviename = data.get("name")  # 从 JSON 中提取 name 字段
        result = get_info_list(moviename)  # 调用 get_info_list 函数

        return jsonify({"code": 200, "msg": "success", "data": result})


    elif request.method == "GET":
        return jsonify({"error": "请使用 POST 方法提交数据"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)