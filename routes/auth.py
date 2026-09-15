# 密码保护相关路由
import logging

from flask import Blueprint, request

from utils.fun_config import (
    get_auth_config, save_auth_config, get_auth_token, check_auth_token
)
from utils.fun_response import success, error

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)


def _get_request_token():
    """从前端请求中取出访问令牌"""
    return request.args.get("access_token") or request.headers.get("Authorization", "")


@auth_bp.route("/authStatus", methods=["GET"])
def auth_status():
    """查询是否开启密码保护以及当前请求是否已通过验证"""
    config = get_auth_config()
    return success({
        "enabled": config["auth_enabled"],
        "authenticated": check_auth_token(_get_request_token())
    })


@auth_bp.route("/authLogin", methods=["POST"])
def auth_login():
    """校验访问密码，通过后返回访问令牌"""
    data = request.json or {}
    password = data.get("password", "")
    config = get_auth_config()
    if not config["auth_enabled"]:
        return success({"token": None}, msg="未开启密码保护")
    if password != config["auth_password"]:
        logger.info("[authLogin] 密码错误，拒绝访问")
        return error("密码错误", 401)
    logger.info("[authLogin] 密码验证通过")
    return success({"token": get_auth_token()}, msg="验证通过")


@auth_bp.route("/getAuthConfig", methods=["GET"])
def get_auth_config_route():
    """获取密码保护配置（设置页使用）"""
    config = get_auth_config()
    return success({
        "auth_enabled": config["auth_enabled"],
        "auth_password": config["auth_password"]
    })


@auth_bp.route("/saveAuthConfig", methods=["POST"])
def save_auth_config_route():
    """保存密码保护配置（设置页使用）"""
    data = request.json or {}
    save_auth_config(data)
    config = get_auth_config()
    logger.info(f"[saveAuthConfig] 密码保护已{'开启' if config['auth_enabled'] else '关闭'}")
    # 返回新令牌，便于前端修改密码后继续保持登录状态
    token = get_auth_token() if config["auth_enabled"] else None
    return success({"token": token}, msg="保存成功")
