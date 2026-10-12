# Bangumi 相关路由
import logging

from flask import Blueprint, request

from utils.fun_bangumi import BangumiApiError, request_bangumi_api
from utils.fun_response import success, error

logger = logging.getLogger(__name__)
bangumi_bp = Blueprint('bangumi', __name__)

ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD", "PATCH", "OPTIONS"]


@bangumi_bp.route("/proxy/<path:subpath>", methods=ALLOWED_METHODS)
def bangumi_proxy(subpath):
    use_mirror = request.args.get("useMirror", "false").lower() == "true"
    method = request.method.upper()
    if method not in ALLOWED_METHODS:
        return error("请求方法不被允许", 405)

    upstream_params = {k: v for k, v in request.args.items() if k.lower() != "usemirror"}
    upstream_headers = {k: v for k, v in request.headers.items()
                        if k.lower() not in ("host", "content-length", "cookie", "authorization")}
    content_type = request.headers.get("Content-Type", "")

    if content_type.startswith("application/json") or request.is_json:
        json_data = request.get_json(silent=True)
        upstream_data = json_data if json_data is not None else request.get_data()
    else:
        upstream_data = request.get_data()

    logger.info(f"[bangumi/proxy] {method} {subpath} 镜像优先: {use_mirror}")

    try:
        body = request_bangumi_api(
            subpath,
            method=method,
            params=upstream_params,
            data=upstream_data,
            headers=upstream_headers,
            use_mirror=use_mirror,
        )
        return success(body)
    except BangumiApiError as e:
        return error("请求 Bangumi API 失败", 502, msg=str(e))
    except Exception as e:
        logger.error(f"[bangumi/proxy] 异常错误 {method} {subpath}: {str(e)}", exc_info=True)
        return error("请求 Bangumi API 失败", 500, msg=str(e))
