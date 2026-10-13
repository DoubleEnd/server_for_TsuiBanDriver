# AI 对话持久化管理（按账号存储：data/users/<username>/conversations.json）
import logging
import os
import time
import uuid

from utils import fun_user
from utils.config_manager import get_config_path, load_json_safe, save_json_safe

logger = logging.getLogger(__name__)

_FILE_NAME = "conversations.json"


def _path(username):
    return fun_user.get_user_file(username, _FILE_NAME)


def _load_conversations(username):
    data = load_json_safe(_path(username))
    if data is None or not isinstance(data, dict):
        return {"conversations": []}
    if not isinstance(data.get("conversations"), list):
        data["conversations"] = []
    return data


def _save_conversations(username, data):
    return save_json_safe(_path(username), data)


def migrate_legacy_conversations():
    """旧版全局对话（config/ai_conversations.json）归属到主账号

    对话原先不分账号存储，迁移时归入旧用户数据里的第一个账号；完成后把旧文件改名，
    避免重复执行。目标账号已有对话文件时不覆盖。
    """
    legacy = get_config_path("ai_conversations.json")
    if not os.path.isfile(legacy):
        return
    data = load_json_safe(legacy)
    owner = fun_user.primary_username()
    if owner and isinstance(data, dict) and data.get("conversations") and not os.path.isfile(_path(owner)):
        save_json_safe(_path(owner), data)
        logger.info(f"[conversation] 旧对话记录已归属到账号: {owner}")
    try:
        os.replace(legacy, legacy + ".migrated")
    except OSError as e:
        logger.warning(f"[conversation] 旧对话文件改名失败: {e}")


def list_conversations(username):
    """返回该账号的对话摘要列表（不含消息内容），按更新时间倒序。
    过滤掉尚无任何消息的对话（如流式生成失败后残留的空对话），避免点击后无内容可显示。
    """
    if not username:
        return []
    data = _load_conversations(username)
    result = []
    for conv in data["conversations"]:
        if not conv.get("display_messages"):
            continue
        result.append({
            "id": conv["id"],
            "title": conv.get("title", "新对话"),
            "created_at": conv.get("created_at", 0),
            "updated_at": conv.get("updated_at", 0),
        })
    result.sort(key=lambda x: x["updated_at"], reverse=True)
    return result


def get_conversation(username, conv_id):
    """获取该账号下某对话的完整内容（含 display_messages，不含 context_messages）"""
    if not username:
        return None
    data = _load_conversations(username)
    for conv in data["conversations"]:
        if conv["id"] == conv_id:
            return {
                "id": conv["id"],
                "title": conv.get("title", "新对话"),
                "created_at": conv.get("created_at", 0),
                "updated_at": conv.get("updated_at", 0),
                "display_messages": conv.get("display_messages", []),
            }
    return None


def get_context_messages(username, conv_id):
    """获取该账号下某对话的 LLM 上下文消息（含 tool_calls / tool 结果）"""
    if not username:
        return []
    data = _load_conversations(username)
    for conv in data["conversations"]:
        if conv["id"] == conv_id:
            return conv.get("context_messages", [])
    return []


def create_conversation(username):
    """为该账号创建新对话，返回对话 ID；账号为空时返回空串"""
    if not username:
        return ""
    data = _load_conversations(username)
    conv_id = uuid.uuid4().hex[:12]
    now = time.time()
    data["conversations"].append({
        "id": conv_id,
        "title": "新对话",
        "created_at": now,
        "updated_at": now,
        "context_messages": [],
        "display_messages": [],
    })
    _save_conversations(username, data)
    logger.info(f"[conversation] 创建对话: {username} / {conv_id}")
    return conv_id


def save_conversation_turn(username, conv_id, user_message, context_messages, display_items, title=None):
    """保存一个对话轮次：追加用户消息和 AI 回复的展示项，更新完整上下文"""
    if not username:
        return False
    data = _load_conversations(username)
    for conv in data["conversations"]:
        if conv["id"] == conv_id:
            conv["context_messages"] = context_messages
            conv["display_messages"].append({"role": "user", "content": user_message})
            if display_items:
                conv["display_messages"].append({"role": "assistant", "items": display_items})
            conv["updated_at"] = time.time()
            if title:
                conv["title"] = title
            _save_conversations(username, data)
            logger.info(f"[conversation] 保存对话轮次: {username} / {conv_id}, 上下文消息数: {len(context_messages)}")
            return True
    logger.warning(f"[conversation] 对话不存在: {username} / {conv_id}")
    return False


def delete_conversation(username, conv_id):
    """删除该账号下的对话"""
    if not username:
        return False
    data = _load_conversations(username)
    before = len(data["conversations"])
    data["conversations"] = [c for c in data["conversations"] if c["id"] != conv_id]
    if len(data["conversations"]) < before:
        _save_conversations(username, data)
        logger.info(f"[conversation] 删除对话: {username} / {conv_id}")
        return True
    return False


def rename_conversation(username, conv_id, title):
    """重命名该账号下的对话"""
    if not username:
        return False
    data = _load_conversations(username)
    for conv in data["conversations"]:
        if conv["id"] == conv_id:
            conv["title"] = title
            conv["updated_at"] = time.time()
            _save_conversations(username, data)
            return True
    return False


migrate_legacy_conversations()
