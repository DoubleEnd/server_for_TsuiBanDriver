# AI 对话持久化管理
import time
import uuid
import logging

from utils.config_manager import get_config_path, load_json_safe, save_json_safe

logger = logging.getLogger(__name__)

conversations_path = get_config_path('ai_conversations.json')


def _load_conversations():
    data = load_json_safe(conversations_path)
    if data is None or not isinstance(data, dict):
        return {"conversations": []}
    if "conversations" not in data:
        data["conversations"] = []
    return data


def _save_conversations(data):
    return save_json_safe(conversations_path, data)


def list_conversations():
    """返回所有对话摘要列表（不含消息内容），按更新时间倒序。
    过滤掉尚无任何消息的对话（如流式生成失败后残留的空对话），避免点击后无内容可显示。
    """
    data = _load_conversations()
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


def get_conversation(conv_id):
    """获取完整对话（含 display_messages，不含 context_messages）"""
    data = _load_conversations()
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


def get_context_messages(conv_id):
    """获取对话的 LLM 上下文消息（含 tool_calls / tool 结果）"""
    data = _load_conversations()
    for conv in data["conversations"]:
        if conv["id"] == conv_id:
            return conv.get("context_messages", [])
    return []


def create_conversation():
    """创建新对话，返回对话 ID"""
    data = _load_conversations()
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
    _save_conversations(data)
    logger.info(f"[conversation] 创建对话: {conv_id}")
    return conv_id


def save_conversation_turn(conv_id, user_message, context_messages, display_items, title=None):
    """保存一个对话轮次：追加用户消息和 AI 回复的展示项，更新完整上下文"""
    data = _load_conversations()
    for conv in data["conversations"]:
        if conv["id"] == conv_id:
            conv["context_messages"] = context_messages
            conv["display_messages"].append({"role": "user", "content": user_message})
            if display_items:
                conv["display_messages"].append({"role": "assistant", "items": display_items})
            conv["updated_at"] = time.time()
            if title:
                conv["title"] = title
            _save_conversations(data)
            logger.info(f"[conversation] 保存对话轮次: {conv_id}, 上下文消息数: {len(context_messages)}")
            return True
    logger.warning(f"[conversation] 对话不存在: {conv_id}")
    return False


def delete_conversation(conv_id):
    """删除对话"""
    data = _load_conversations()
    before = len(data["conversations"])
    data["conversations"] = [c for c in data["conversations"] if c["id"] != conv_id]
    if len(data["conversations"]) < before:
        _save_conversations(data)
        logger.info(f"[conversation] 删除对话: {conv_id}")
        return True
    return False


def rename_conversation(conv_id, title):
    """重命名对话"""
    data = _load_conversations()
    for conv in data["conversations"]:
        if conv["id"] == conv_id:
            conv["title"] = title
            conv["updated_at"] = time.time()
            _save_conversations(data)
            return True
    return False
