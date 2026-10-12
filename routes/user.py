# 用户路由：按用户名的观看历史与个性化设置
import logging

from flask import Blueprint, request

from utils import fun_user
from utils.fun_response import success, error

logger = logging.getLogger(__name__)
user_bp = Blueprint('user', __name__)


@user_bp.route("/getUserData", methods=["GET"])
def submit_getuserdata():
    """获取该用户的完整数据（历史记录 + 个性化设置）"""
    username = request.args.get("username", "")
    if not username.strip():
        return error("缺少username参数", 400)
    try:
        return success(fun_user.get_user_data(username))
    except Exception as e:
        logger.error(f"[getUserData] 异常错误: {str(e)}", exc_info=True)
        return error("获取用户数据失败", 500, msg=str(e))


@user_bp.route("/getHistory", methods=["GET"])
def submit_gethistory():
    """获取观看历史：带 videoId 时只返回该视频对应剧集的记录（用于续播）"""
    username = request.args.get("username", "")
    if not username.strip():
        return error("缺少username参数", 400)
    video_id = request.args.get("videoId") or None
    try:
        return success(fun_user.get_history(username, video_id=video_id))
    except Exception as e:
        logger.error(f"[getHistory] 异常错误: {str(e)}", exc_info=True)
        return error("获取观看历史失败", 500, msg=str(e))


@user_bp.route("/saveHistory", methods=["POST"])
def submit_savehistory():
    """记录观看历史：打开播放页记为已观看，并保存播放进度"""
    data = request.json or {}
    username = data.get("username", "")
    video_id = data.get("videoId", "")
    if not username.strip() or not video_id:
        return error("缺少username或videoId参数", 400)
    try:
        record = fun_user.record_history(
            username=username,
            video_id=video_id,
            position=data.get("position", 0),
            duration=data.get("duration", 0),
        )
        return success(record)
    except Exception as e:
        logger.error(f"[saveHistory] 异常错误: {str(e)}", exc_info=True)
        return error("保存观看历史失败", 500, msg=str(e))


@user_bp.route("/saveUserSettings", methods=["POST"])
def submit_saveusersettings():
    """保存该用户的个性化设置（lang/弹幕/时间表等）"""
    data = request.json or {}
    username = data.get("username", "")
    if not username.strip():
        return error("缺少username参数", 400)
    try:
        if fun_user.save_user_settings(username, data.get("settings") or {}):
            return success()
        return error("保存用户设置失败", 500)
    except Exception as e:
        logger.error(f"[saveUserSettings] 异常错误: {str(e)}", exc_info=True)
        return error("保存用户设置失败", 500, msg=str(e))
