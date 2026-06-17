# AI 相关路由（字幕生成、对话、配置）
import json
import logging

from flask import Blueprint, request, jsonify, Response, stream_with_context

from ai.ai import transcribe_audio_to_srt, get_ai_config
from utils.fun_config import add_edit_ai_config, delete_ai_config, get_ai_chat_config, save_ai_chat_config
from utils.fun_aiChat import chat

logger = logging.getLogger(__name__)
ai_bp = Blueprint('ai', __name__)


@ai_bp.route("/aiConfig", methods=["GET"])
def get_ai_configuration():
    try:
        ai_config = get_ai_config()
        return jsonify({
            "valid_models": ai_config.get("valid_models", []),
            "valid_devices": ai_config.get("valid_devices", []),
            "default_model": ai_config.get("default_model"),
            "default_device": ai_config.get("default_device")
        })
    except Exception as e:
        return jsonify({"error": "获取配置失败", "detail": str(e)}), 500


@ai_bp.route("/aiSubtitle", methods=["GET"])
def submit_aiSubtitle():
    try:
        params = request.args.to_dict()
        if 'video_path' not in params:
            return jsonify({"error": "缺少video_path参数"}), 400
        ai_config = get_ai_config()
        model_type = params.get('model_type', ai_config.get("default_model", "medium"))
        device = params.get('device', ai_config.get("default_device", "cpu")).lower()
        srt_path = transcribe_audio_to_srt(video_path=params['video_path'], model_type=model_type, device=device)
        return jsonify({"srt_path": srt_path, "model_used": model_type, "device_used": device})
    except Exception as e:
        return jsonify({"error": "处理请求时发生错误", "detail": str(e)}), 500


@ai_bp.route("/addEditAiConfig", methods=["POST"])
def submit_addeditaiconfig():
    if request.method == "POST":
        data = request.json
        if add_edit_ai_config(data):
            return jsonify({"code": 200, "msg": "success", "data": None})
        else:
            return jsonify({"code": 400, "msg": "error", "data": "缺少关键信息或配置项无效"})
    else:
        return jsonify({"code": 405, "msg": "请求方法不被允许", "data": None}), 405


@ai_bp.route("/deleteAiConfig", methods=["POST"])
def submit_deleteaiconfig():
    if request.method == "POST":
        data = request.json
        key = data.get("key")
        if key:
            if delete_ai_config(key):
                return jsonify({"code": 200, "msg": "success", "data": None})
            else:
                return jsonify({"code": 404, "msg": "error", "data": "配置项不存在"})
        else:
            return jsonify({"code": 400, "msg": "error", "data": "缺少配置项名称"})
    else:
        return jsonify({"code": 405, "msg": "请求方法不被允许", "data": None}), 405


@ai_bp.route("/aiChatConfig", methods=["GET"])
def get_ai_chat_configuration():
    try:
        config = get_ai_chat_config()
        return jsonify({"code": 200, "msg": "success", "data": config})
    except Exception as e:
        logger.error(f"[aiChatConfig] 获取配置失败: {str(e)}", exc_info=True)
        return jsonify({"code": 500, "msg": "error", "data": None}), 500


@ai_bp.route("/saveAiChatConfig", methods=["POST"])
def submit_saveaichatconfig():
    if request.method == "POST":
        data = request.json
        if not data:
            return jsonify({"code": 400, "msg": "请求体为空"}), 400
        try:
            save_ai_chat_config(data)
            return jsonify({"code": 200, "msg": "success", "data": None})
        except Exception as e:
            logger.error(f"[saveAiChatConfig] 保存配置失败: {str(e)}", exc_info=True)
            return jsonify({"code": 500, "msg": "error", "data": None}), 500
    else:
        return jsonify({"code": 405, "msg": "请求方法不被允许", "data": None}), 405


@ai_bp.route("/aiChat", methods=["POST"])
def submit_aiChat():
    if request.method != "POST":
        return jsonify({"code": 405, "msg": "请求方法不被允许"}), 405
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求体为空"}), 400

    def generate():
        for event in chat(message=data.get("message", ""), history=data.get("history", [])):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
