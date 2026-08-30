# 统一响应格式工具
# 成功: {"code": 200, "msg": "success", "data": ...}
# 失败: {"code": <错误代码>, "type": <错误类型>, "title": <中文标题>, "msg": <详细错误>, "data": None}
from flask import jsonify

# 错误代码 -> 错误类型映射
_ERROR_TYPES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    500: "server_error",
    502: "bad_gateway",
}


def success(data=None, msg="success", code=200):
    """统一成功响应"""
    return jsonify({"code": code, "msg": msg, "data": data})


def error(title, code=500, msg=None, data=None):
    """
    统一错误响应，title 必须为中文，用于前端 toast 显示。
    code: 错误代码（HTTP 风格），type 根据 code 自动推导
    """
    body = {
        "code": code,
        "type": _ERROR_TYPES.get(code, "unknown"),
        "title": title,
        "msg": msg if msg is not None else title,
        "data": data,
    }
    return jsonify(body), code
