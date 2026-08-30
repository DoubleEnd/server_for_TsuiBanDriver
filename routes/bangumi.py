# Bangumi 相关路由
import logging

import requests
from flask import Blueprint, request

from utils.fun_request import request as fun_request
from utils.fun_response import success, error

logger = logging.getLogger(__name__)
bangumi_bp = Blueprint('bangumi', __name__)

BGMI_API = "https://api.bgm.tv"
BGMI_MIRROR_API = "https://bgmapi.anibt.net"

ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD", "PATCH", "OPTIONS"]


def _build_attempts(use_mirror):
    sources = [("mirror", BGMI_MIRROR_API), ("official", BGMI_API)] if use_mirror else [("official", BGMI_API), ("mirror", BGMI_MIRROR_API)]
    attempts = []
    for source_name, base_url in sources:
        attempts.append((source_name, base_url, True))
    for source_name, base_url in sources:
        attempts.append((source_name, base_url, False))
    return attempts


def _proxy_bangumi_request(rel_path):
    use_mirror = request.args.get("useMirror", "false").lower() == "true"
    method = request.method.upper()
    if method not in ALLOWED_METHODS:
        return error("请求方法不被允许", 405)

    upstream_params = {k: v for k, v in request.args.items() if k.lower() != "usemirror"}
    upstream_headers = {k: v for k, v in request.headers.items()
                        if k.lower() not in ("host", "content-length", "cookie", "authorization")}
    upstream_data = request.get_data()
    content_type = request.headers.get("Content-Type", "")

    logger.info(f"[bangumi/proxy] {method} {rel_path} 镜像优先: {use_mirror}")

    try:
        if content_type.startswith("application/json") or request.is_json:
            try:
                json_data = request.get_json(silent=True)
            except Exception:
                json_data = None
            data_arg = json_data if json_data is not None else upstream_data
        else:
            data_arg = upstream_data

        last_error = None
        for source_name, base_url, use_proxy in _build_attempts(use_mirror):
            upstream_url = f"{base_url}/{rel_path}"
            try:
                logger.info(f"[bangumi/proxy] 尝试 {method} {upstream_url} source={source_name} proxy={use_proxy}")
                response = fun_request(
                    config={
                        "method": method,
                        "params": upstream_params,
                        "data": data_arg,
                        "headers": upstream_headers,
                        "timeout": 30,
                    },
                    url=upstream_url,
                    use_proxy=use_proxy,
                )

                if 200 <= response.status_code < 300:
                    content_type_res = response.headers.get("Content-Type", "")
                    try:
                        if "application/json" in content_type_res.lower():
                            body = response.json()
                        else:
                            body = response.text
                        logger.info(f"[bangumi/proxy] 成功 {method} {upstream_url} -> {response.status_code}")
                        return success(body)
                    except Exception as e:
                        logger.warning(f"[bangumi/proxy] 解析响应失败, 返回原文: {str(e)}")
                        return success(response.text)

                last_error = f"HTTP {response.status_code}: {response.text}"
                logger.warning(f"[bangumi/proxy] 上游失败 {method} {upstream_url} -> {last_error}")
            except requests.RequestException as e:
                last_error = str(e)
                logger.warning(
                    f"[bangumi/proxy] 请求异常 {method} {upstream_url} "
                    f"source={source_name} proxy={use_proxy}: {last_error}"
                )

        return error("请求 Bangumi API 失败", 502, msg=last_error)

    except Exception as e:
        logger.error(f"[bangumi/proxy] 异常错误 {method} {rel_path}: {str(e)}", exc_info=True)
        return error("请求 Bangumi API 失败", 500, msg=str(e))


@bangumi_bp.route("/proxy/<path:subpath>", methods=ALLOWED_METHODS)
def bangumi_proxy(subpath):
    return _proxy_bangumi_request(subpath)
