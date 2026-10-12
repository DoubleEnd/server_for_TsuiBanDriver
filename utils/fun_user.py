# 用户数据：按用户名的观看历史与个性化设置，落盘 data/users.json
import logging
import os
from datetime import datetime

from utils.config_manager import get_base_path, load_json_safe, save_json_safe
from utils.fun_scan import find_episode_by_file_id

logger = logging.getLogger(__name__)

_DATA_DIR_NAME = "data"
_USERS_FILE_NAME = "users.json"


def get_users_path():
    """用户数据落盘路径：data/users.json"""
    return os.path.join(get_base_path(), _DATA_DIR_NAME, _USERS_FILE_NAME)


def _load_users():
    """读取用户数据；文件尚不存在时静默返回空结构（首次运行）"""
    path = get_users_path()
    if not os.path.isfile(path):
        return {}
    return load_json_safe(path) or {}


def _save_users(users):
    save_json_safe(get_users_path(), users)


def _normalize_username(username):
    return str(username or "").strip()


def _get_user(users, name):
    return users.setdefault(name, {"history": {}, "settings": {}})


def get_user_data(username):
    """返回指定用户的完整数据（history/settings），用户不存在时返回空结构"""
    name = _normalize_username(username)
    if not name:
        return {"username": "", "history": {}, "settings": {}}
    user = _load_users().get(name) or {}
    return {
        "username": name,
        "history": user.get("history") or {},
        "settings": user.get("settings") or {},
    }


def get_history(username, video_id=None):
    """观看历史：结构为 {animeId: {集数: {position, duration, updatedAt}}}

    video_id 传入时只返回该视频文件对应剧集的记录（用于续播）；否则返回整份历史。
    """
    history = get_user_data(username)["history"]
    if not video_id:
        return history
    return get_record_by_video_id(username, video_id)


def get_record_by_video_id(username, video_id):
    """按视频文件 ID 定位所属番剧与集数，返回该集的观看记录（不存在返回空字典）"""
    episode = find_episode_by_file_id(video_id)
    if not episode or not episode.get("AnimeId"):
        return {}
    history = get_user_data(username)["history"]
    return (history.get(str(episode["AnimeId"])) or {}).get(str(episode["EpisodeKey"])) or {}


def record_history(username, video_id, position=0, duration=0):
    """记录观看历史：只保存 animeId → 集数 → 播放进度 / 观看时间

    打开播放页即视为已观看（存在记录即视为看过），不保存文件名等无关数据。
    视频文件 ID 仅用于内部定位所属番剧与集数，不会被写入历史。
    """
    name = _normalize_username(username)
    if not name or not video_id:
        return None

    episode = find_episode_by_file_id(video_id)
    if not episode or not episode.get("AnimeId"):
        # 不在本地番剧库中的文件不记录
        return None

    def _to_seconds(value):
        try:
            return max(0.0, float(value or 0))
        except (TypeError, ValueError):
            return 0.0

    anime_id = str(episode["AnimeId"])
    episode_key = str(episode["EpisodeKey"])

    users = _load_users()
    user = _get_user(users, name)
    record = {
        "position": _to_seconds(position),
        "duration": _to_seconds(duration),
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    user["history"].setdefault(anime_id, {})[episode_key] = record
    _save_users(users)
    return {"animeId": anime_id, "episodeKey": episode_key, **record}


def save_user_settings(username, settings):
    """保存该用户的个性化设置（lang/弹幕/时间表等，值为浏览器里的原始字符串）"""
    name = _normalize_username(username)
    if not name:
        return False
    if not isinstance(settings, dict):
        return False

    users = _load_users()
    user = _get_user(users, name)
    user["settings"] = {str(k): str(v) for k, v in settings.items()}
    _save_users(users)
    return True
