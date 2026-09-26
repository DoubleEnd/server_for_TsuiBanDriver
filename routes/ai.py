# AI 相关路由（对话、配置）
import json
import logging

from flask import Blueprint, request, jsonify, Response, stream_with_context

from utils.fun_config import get_ai_chat_config, save_ai_chat_config
from utils.fun_aiChat import chat
from utils.fun_conversation import (
    list_conversations, get_conversation, create_conversation,
    delete_conversation, rename_conversation
)
from utils.fun_response import success, error

logger = logging.getLogger(__name__)
ai_bp = Blueprint('ai', __name__)


@ai_bp.route("/aiChatConfig", methods=["GET"])
def get_ai_chat_configuration():
    try:
        config = get_ai_chat_config()
        return success(config)
    except Exception as e:
        logger.error(f"[aiChatConfig] 获取配置失败: {str(e)}", exc_info=True)
        return error("获取AI对话配置失败", 500, msg=str(e))


@ai_bp.route("/saveAiChatConfig", methods=["POST"])
def submit_saveaichatconfig():
    if request.method == "POST":
        data = request.json
        if not data:
            return error("请求体为空", 400)
        try:
            save_ai_chat_config(data)
            return success()
        except Exception as e:
            logger.error(f"[saveAiChatConfig] 保存配置失败: {str(e)}", exc_info=True)
            return error("保存AI对话配置失败", 500, msg=str(e))
    else:
        return error("请求方法不被允许", 405)


@ai_bp.route("/aiChat", methods=["POST"])
def submit_aiChat():
    if request.method != "POST":
        return error("请求方法不被允许", 405)
    data = request.json
    if not data:
        return error("请求体为空", 400)

    def generate():
        for event in chat(message=data.get("message", ""), conversation_id=data.get("conversation_id")):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@ai_bp.route("/aiConversations", methods=["GET"])
def submit_aiConversations():
    try:
        return success(list_conversations())
    except Exception as e:
        logger.error(f"[aiConversations] 获取对话列表失败: {str(e)}", exc_info=True)
        return error("获取对话列表失败", 500, msg=str(e))


@ai_bp.route("/aiConversation", methods=["GET"])
def submit_aiConversation():
    conv_id = request.args.get("id", "")
    if not conv_id:
        return error("缺少对话ID", 400)
    try:
        conv = get_conversation(conv_id)
        if conv is None:
            return error("对话不存在", 404)
        return success(conv)
    except Exception as e:
        logger.error(f"[aiConversation] 获取对话失败: {str(e)}", exc_info=True)
        return error("获取对话失败", 500, msg=str(e))


@ai_bp.route("/newAiConversation", methods=["POST"])
def submit_newAiConversation():
    try:
        conv_id = create_conversation()
        return success({"id": conv_id})
    except Exception as e:
        logger.error(f"[newAiConversation] 创建对话失败: {str(e)}", exc_info=True)
        return error("创建对话失败", 500, msg=str(e))


@ai_bp.route("/deleteAiConversation", methods=["POST"])
def submit_deleteAiConversation():
    data = request.json
    if not data or not data.get("id"):
        return error("缺少对话ID", 400)
    try:
        if delete_conversation(data["id"]):
            return success()
        return error("对话不存在", 404)
    except Exception as e:
        logger.error(f"[deleteAiConversation] 删除对话失败: {str(e)}", exc_info=True)
        return error("删除对话失败", 500, msg=str(e))


@ai_bp.route("/renameAiConversation", methods=["POST"])
def submit_renameAiConversation():
    data = request.json
    if not data or not data.get("id") or not data.get("title"):
        return error("缺少对话ID或标题", 400)
    try:
        if rename_conversation(data["id"], data["title"]):
            return success()
        return error("对话不存在", 404)
    except Exception as e:
        logger.error(f"[renameAiConversation] 重命名对话失败: {str(e)}", exc_info=True)
        return error("重命名对话失败", 500, msg=str(e))
