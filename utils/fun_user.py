# 用户数据：按用户名分目录存储，落盘 data/users/<username>/{history,settings}.json
import logging
import os
import re
from datetime import datetime

from utils.config_manager import get_base_path, load_json_safe, save_json_safe
from utils.fun_scan import find_episode_by_file_id

logger = logging.getLogger(__name__)

_DATA_DIR_NAME = "data"
_USERS_DIR_NAME = "users"
# 旧版单文件用户数据（data/users.json），首次运行自动拆分到用户目录
_LEGACY_FILE_NAME = "users.json"

# 目录名里不允许出现的字符（Windows 限制与控制字符），统一替换为下划线
_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def get_users_dir():
    """用户数据根目录：data/users"""
    return os.path.join(get_base_path(), _DATA_DIR_NAME, _USERS_DIR_NAME)


def _dir_name(username):
    """用户名 -> 目录名：去掉首尾空白与非法文件名字符，避免建目录失败"""
    name = re.sub(r"\s+", " ", str(username or "").strip())
    return _ILLEGAL_CHARS.sub("_", name).strip(" .")


def get_user_dir(username):
    """某个用户的数据目录：data/users/<username>"""
    return os.path.join(get_users_dir(), _dir_name(username))


def get_user_file(username, filename):
    """某个用户的数据文件路径，如 history.json / settings.json / conversations.json

    供其他模块（如 AI 对话）复用同一套按账号分目录的存储结构。
    """
    return os.path.join(get_user_dir(username), filename)


def _normalize_username(username):
    return str(username or "").strip()


def _load_json(username, filename):
    """读取用户目录下的 json，不存在返回 None"""
    return load_json_safe(get_user_file(username, filename))


def _save_json(username, filename, data):
    return save_json_safe(get_user_file(username, filename), data)


def _legacy_users_path():
    return os.path.join(get_base_path(), _DATA_DIR_NAME, _LEGACY_FILE_NAME)


def primary_username():
    """主账号名：旧数据里的第一个用户

    用于把历史遗留的全局数据（如 AI 对话）归属到主账号。
    """
    for path in (_legacy_users_path(), _legacy_users_path() + ".migrated"):
        if not os.path.isfile(path):
            continue
        data = load_json_safe(path)
        if isinstance(data, dict):
            for name in data.keys():
                return str(name)
    return ""


def migrate_legacy_users():
    """把旧版单文件用户数据（data/users.json）拆分到 data/users/<username>/

    已存在的新文件不覆盖；迁移完成后把旧文件改名为 users.json.migrated，避免重复执行。
    """
    legacy = _legacy_users_path()
    if not os.path.isfile(legacy):
        return
    data = load_json_safe(legacy)
    if isinstance(data, dict):
        for name, user in data.items():
            if not isinstance(user, dict):
                continue
            history = user.get("history") or {}
            settings = user.get("settings") or {}
            if history and not os.path.isfile(get_user_file(name, "history.json")):
                _save_json(name, "history.json", history)
            if settings and not os.path.isfile(get_user_file(name, "settings.json")):
                _save_json(name, "settings.json", settings)
    try:
        os.replace(legacy, legacy + ".migrated")
    except OSError as e:
        logger.warning(f"[user] 旧用户数据改名失败: {e}")
    logger.info("[user] 已将旧用户数据（data/users.json）拆分到 data/users/<username>/")


def get_user_data(username):
    """返回指定用户的完整数据（history/settings），用户不存在时返回空结构"""
    name = _normalize_username(username)
    if not name:
        return {"username": "", "history": {}, "settings": {}}
    history = _load_json(name, "history.json")
    settings = _load_json(name, "settings.json")
    return {
        "username": name,
        "history": history if isinstance(history, dict) else {},
        "settings": settings if isinstance(settings, dict) else {},
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

    history = _load_json(name, "history.json")
    if not isinstance(history, dict):
        history = {}
    record = {
        "position": _to_seconds(position),
        "duration": _to_seconds(duration),
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    history.setdefault(anime_id, {})[episode_key] = record
    _save_json(name, "history.json", history)
    return {"animeId": anime_id, "episodeKey": episode_key, **record}


def save_user_settings(username, settings):
    """保存该用户的个性化设置（lang/弹幕/时间表等，值为浏览器里的原始字符串）"""
    name = _normalize_username(username)
    if not name:
        return False
    if not isinstance(settings, dict):
        return False
    return _save_json(name, "settings.json", {str(k): str(v) for k, v in settings.items()})


migrate_legacy_users()
