import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

# ---------- API 配置（通过环境变量设置） ----------
API_KEY = os.environ.get("AI_CHAT_API_KEY", "sk-5220a1b36fe749bfb078e7b62bd7128f")
BASE_URL = os.environ.get("AI_CHAT_BASE_URL", "https://api.deepseek.com").rstrip("/")
MODEL = os.environ.get("AI_CHAT_MODEL", "deepseek-v4-pro")
MAX_TOOL_ROUNDS = 5  # 工具调用最大轮次，防止死循环


# ---------- 工具定义 ----------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_bangumi",
            "description": "在番剧库中搜索番剧信息，返回匹配的番剧列表及其ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词，例如番剧名称"
                    }
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_subgroup_info",
            "description": "获取指定番剧的所有字幕组信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "bangumi_id": {
                        "type": "string",
                        "description": "番剧ID，从 search_bangumi 结果中获取"
                    }
                },
                "required": ["bangumi_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_subtitle_list",
            "description": "获取指定视频可用的字幕列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "视频ID"
                    }
                },
                "required": ["video_id"]
            }
        }
    }
]


# ---------- 工具 → 前端组件映射 ----------
# 每种工具返回：(ai_text, component, data)
#   ai_text   — 发给 AI 的文字描述（裁剪后）
#   component — 前端要渲染的组件名
#   data      — 前端组件的 props 数据

def _execute_tool(name, arguments):
    """执行工具，返回 (ai_text, component, data) 三元组。"""
    try:
        if name == "search_bangumi":
            from crawler.get_info import get_info_list
            raw = get_info_list(banguminame=arguments.get("keyword", ""))
            if not raw:
                return "未找到相关番剧", None, []

            ai_text = json.dumps(raw, ensure_ascii=False)
            frontend_data = raw
            return ai_text, "SearchResult", frontend_data

        elif name == "get_subgroup_info":
            from crawler.get_subgroupinfo import get_subgroup_info
            raw = get_subgroup_info(bangumiId=arguments.get("bangumi_id", ""))
            if not raw:
                return "未找到字幕组信息", "SubgroupList", []
            ai_text = json.dumps(raw, ensure_ascii=False)
            return ai_text, "SubgroupList", raw

        elif name == "get_subtitle_list":
            from crawler.get_subtitle import get_subtitle_list
            raw = get_subtitle_list(videoId=arguments.get("video_id", ""))
            if not raw:
                return "未找到字幕列表", "SubtitleList", []
            ai_text = json.dumps(raw, ensure_ascii=False)
            return ai_text, "SubtitleList", raw

        else:
            return f"未知工具: {name}", "ErrorCard", {"message": f"未知工具: {name}"}

    except Exception as e:
        logger.error(f"[aiChat] 工具执行失败: {name}({arguments}) - {str(e)}", exc_info=True)
        return f"工具执行出错: {str(e)}", "ErrorCard", {"message": str(e)}


# ---------- SSE 流解析 ----------
def _parse_sse_stream(response):
    """逐行解析 DeepSeek SSE 流，产出 dict 事件。"""
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("data: "):
            data_str = line[6:].strip()
            if data_str == "[DONE]":
                return
            try:
                yield json.loads(data_str)
            except json.JSONDecodeError:
                logger.warning(f"[aiChat] SSE 解析失败: {data_str[:200]}")
                continue


def _aggregate_stream_events(response):
    """聚合流式事件。

    产出:
        {"type": "reply_chunk", "content": str}
        {"type": "_tool_calls_aggregated", "tool_calls": [...]}
    """
    tool_calls_accum = {}

    for event in _parse_sse_stream(response):
        choices = event.get("choices", [])
        if not choices:
            continue

        delta = choices[0].get("delta", {})
        finish_reason = choices[0].get("finish_reason", "")

        content = delta.get("content", "")
        if content:
            yield {"type": "reply_chunk", "content": content}

        tc_list = delta.get("tool_calls", [])
        for tc in tc_list:
            idx = tc.get("index", 0)
            if idx not in tool_calls_accum:
                tool_calls_accum[idx] = {
                    "id": tc.get("id", ""),
                    "function": {"name": "", "arguments": ""}
                }
            acc = tool_calls_accum[idx]
            if tc.get("id"):
                acc["id"] = tc["id"]
            func = tc.get("function", {})
            if func.get("name"):
                acc["function"]["name"] = func["name"]
            if func.get("arguments"):
                acc["function"]["arguments"] += func["arguments"]

        if finish_reason:
            if finish_reason == "tool_calls":
                yield {"type": "_tool_calls_aggregated", "tool_calls": list(tool_calls_accum.values())}
            elif finish_reason == "stop":
                pass
            else:
                logger.warning(f"[aiChat] 未知 finish_reason: {finish_reason}")
            break


# ---------- 核心对话逻辑 ----------
def chat(message, history):
    """返回生成器，逐个产出 SSE 事件。

    完整事件类型一览：

    ┌─────────────────┬──────────────────────────────────────────────┐
    │ type            │ 额外字段                                      │
    ├─────────────────┼──────────────────────────────────────────────┤
    │ thinking        │ content: str    — 思考状态文案                 │
    │ reply_chunk     │ content: str    — 逐字推送                    │
    │ reply_complete  │ content: str    — 完整回复（流结束后）          │
    │ tool_call       │ name: str, arguments: dict — AI 决定调用工具   │
    │ tool_result     │ name: str, result: str, component: str,       │
    │                 │   data: [...]   — 工具返回 + 前端组件 + 数据    │
    │ error           │ content: str    — 错误信息                    │
    │ done            │ (无)            — 流结束                      │
    └─────────────────┴──────────────────────────────────────────────┘

    tool_result 示例：
    {
      "type": "tool_result",
      "name": "search_bangumi",
      "result": "[{\"bangumiId\":\"123\",\"title\":\"进击的巨人\"}]",
      "component": "BangumiCardRow",
      "data": [
        {"bangumiId": "123", "img": "https://...", "title": "进击的巨人", ...}
      ]
    }
    """
    if not message:
        yield {"type": "error", "content": "请输入消息内容"}
        yield {"type": "done"}
        return

    if not API_KEY:
        yield {"type": "error", "content": "AI 服务未配置，请设置 AI_CHAT_API_KEY 环境变量"}
        yield {"type": "done"}
        return

    logger.info(f"[aiChat] 收到消息: {message}, 历史条数: {len(history)}")

    messages = [
        {"role": "system",
         "content": "你是一个智能助手，可以帮助用户搜索番剧、查询字幕组信息和字幕列表。当用户询问番剧相关内容时，请主动使用工具查询。"}
    ]
    for item in (history or []):
        role = item.get("role", "")
        content = item.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    yield {"type": "thinking", "content": "正在分析你的需求..."}

    full_reply_parts = []

    for round_num in range(MAX_TOOL_ROUNDS):
        try:
            resp = requests.post(
                f"{BASE_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": messages,
                    "tools": TOOLS,
                    "stream": True
                },
                stream=True,
                timeout=60
            )

            if resp.status_code == 401:
                yield {"type": "error", "content": "认证已过期"}
                yield {"type": "done"}
                return

            if resp.status_code != 200:
                logger.error(f"[aiChat] API 错误: {resp.status_code}, body: {resp.text[:500]}")
                yield {"type": "error", "content": f"AI 服务返回错误: {resp.status_code}"}
                yield {"type": "done"}
                return

            aggregated_tool_calls = None

            for event in _aggregate_stream_events(resp):
                if event["type"] == "reply_chunk":
                    full_reply_parts.append(event["content"])
                    yield event
                elif event["type"] == "_tool_calls_aggregated":
                    aggregated_tool_calls = event["tool_calls"]

            # ---- 工具调用 ----
            if aggregated_tool_calls:
                normalized = []
                for tc in aggregated_tool_calls:
                    normalized.append({
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": tc["function"]
                    })

                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": normalized
                })

                for tc in aggregated_tool_calls:
                    func_name = tc["function"]["name"]
                    try:
                        func_args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        func_args = {}

                    yield {"type": "thinking", "content": f"调用工具: {func_name}"}
                    yield {"type": "tool_call", "name": func_name, "arguments": func_args}

                    ai_text, component, data = _execute_tool(func_name, func_args)
                    yield {
                        "type": "tool_result",
                        "name": func_name,
                        "result": ai_text,
                        "component": component,
                        "data": data
                    }

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "content": ai_text
                    })

                logger.info(f"[aiChat] 第 {round_num + 1} 轮工具调用完成，继续对话...")
                continue

            # ---- 正常结束 ----
            full_reply = "".join(full_reply_parts)
            if not full_reply:
                full_reply = "抱歉，我没有获取到有效的回复。"

            yield {"type": "reply_complete", "content": full_reply}
            logger.info(f"[aiChat] 对话完成 - 回复长度: {len(full_reply)}")
            yield {"type": "done"}
            return

        except requests.exceptions.Timeout:
            logger.error("[aiChat] API 请求超时")
            yield {"type": "error", "content": "AI 服务响应超时，请稍后重试"}
            yield {"type": "done"}
            return
        except requests.exceptions.ConnectionError:
            logger.error("[aiChat] API 连接失败")
            yield {"type": "error", "content": "无法连接 AI 服务，请检查网络"}
            yield {"type": "done"}
            return

    yield {"type": "error", "content": "工具调用轮次过多，请简化问题后重试"}
    yield {"type": "done"}
