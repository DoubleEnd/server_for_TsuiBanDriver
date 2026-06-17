import json
import logging

import requests

from utils.fun_config import get_ai_chat_config

logger = logging.getLogger(__name__)

# ---------- API 配置（从 ai_chat_config.json 读取） ----------
def _get_chat_config():
    return get_ai_chat_config()
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
    },
    {
        "type": "function",
        "function": {
            "name": "add_rss_subscription",
            "description": "添加RSS订阅源到qBittorrent，输入RSS链接和保存路径",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "RSS订阅链接"
                    },
                    "path": {
                        "type": "string",
                        "description": "保存目录路径，默认为空字符串表示默认路径"
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_rss_feeds",
            "description": "获取qBittorrent中当前的RSS订阅源列表和RSS条目",
            "parameters": {
                "type": "object",
                "properties": {
                    "withData": {
                        "type": "boolean",
                        "description": "是否附带条目的详细数据，默认为false"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_rss_download_rule",
            "description": "为qBittorrent的RSS订阅设置自动下载规则。需要规则名称和规则定义(JSON格式)",
            "parameters": {
                "type": "object",
                "properties": {
                    "rule_name": {
                        "type": "string",
                        "description": "规则名称"
                    },
                    "rule_def": {
                        "type": "object",
                        "description": "规则定义，包含enabled(true/false)、mustContain(必须包含的文本)、mustNotContain(不得包含的文本)、useRegex(true/false)、episodeFilter(剧集过滤)、smartFilter(true/false)、previouslyMatchedEpisodes(之前匹配的剧集列表)、affectedFeeds(受影响的RSS源URL列表)、enabled(是否启用)等字段"
                    }
                },
                "required": ["rule_name", "rule_def"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_rss_rules",
            "description": "获取qBittorrent中已有的RSS下载器规则列表",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_download_task",
            "description": "添加下载任务到qBittorrent，可以传入磁力链接、种子URL或直接下载链接",
            "parameters": {
                "type": "object",
                "properties": {
                    "urls": {
                        "type": "string",
                        "description": "下载链接，支持磁力链接或HTTP下载链接，多个链接用换行分隔"
                    },
                    "savepath": {
                        "type": "string",
                        "description": "保存目录路径，留空则使用默认路径"
                    }
                },
                "required": ["urls"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_download_status",
            "description": "获取qBittorrent当前下载任务列表和状态",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "match_download_rule",
            "description": "切换使用现有的搜索规则（如mikan_project、acg_rip等），切换后搜索番剧时将使用该规则",
            "parameters": {
                "type": "object",
                "properties": {
                    "rule_name": {
                        "type": "string",
                        "description": "规则名称，如：mikan_project、acg_rip、bangumi_moe、mio_bt"
                    }
                },
                "required": ["rule_name"]
            }
        }
    }
]


# ---------- 工具 → 前端组件映射 ----------
# 每种工具返回：(ai_text, component, data)
#   ai_text   — 发给 AI 的文字描述（裁剪后）
#   component — 前端要渲染的组件名
#   data      — 前端组件的 props 数据

# ---------- RSS / 下载状态辅助函数 ----------
def _count_rss_items(feeds_data):
    """统计 RSS 条目总数"""
    if not isinstance(feeds_data, dict):
        return 0
    total = 0
    for feed_key, feed_val in feeds_data.items():
        if isinstance(feed_val, dict):
            for key, val in feed_val.items():
                if isinstance(val, list):
                    total += len(val)
                elif isinstance(val, dict) and "item" in val:
                    items = val.get("item", [])
                    total += len(items) if isinstance(items, list) else 1
    return total


def _summarize_torrents(torrents):
    """汇总种子下载状态"""
    if not isinstance(torrents, list):
        return json.dumps(torrents, ensure_ascii=False)
    summaries = []
    for t in torrents:
        name = t.get("name", "未知")
        progress = t.get("progress", 0)
        state = t.get("state", "unknown")
        size = t.get("size", 0)
        summaries.append(f"{name} | 进度: {progress*100:.1f}% | 状态: {state} | 大小: {size/(1024**3):.2f}GB")
    return "\n".join(summaries[:20])  # 最多返回20条


def _summarize_rss_rules(rules):
    """汇总 RSS 下载规则"""
    if not isinstance(rules, dict):
        return json.dumps(rules, ensure_ascii=False)
    summaries = []
    for name, rule in rules.items():
        enabled = rule.get("enabled", False)
        must_contain = rule.get("mustContain", "")
        must_not = rule.get("mustNotContain", "")
        feeds = rule.get("affectedFeeds", [])
        status = "启用" if enabled else "禁用"
        line = f"[{status}] {name} | 必须包含: {must_contain or '无'} | 排除: {must_not or '无'}"
        if feeds:
            line += f" | 订阅源: {', '.join(feeds[:3])}"
        summaries.append(line)
    return "\n".join(summaries) if summaries else "暂无RSS下载规则"


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

        # ---------- qBittorrent 工具 ----------
        elif name == "add_rss_subscription":
            from api.api_qBittorrent import addFeed
            url = arguments.get("url", "")
            path = arguments.get("path", "")
            result = addFeed({"url": url, "path": path})
            if result.status_code == 200:
                return f"已成功添加RSS订阅: {url}", None, {"message": f"已添加RSS订阅: {url}"}
            return f"添加RSS订阅失败 (HTTP {result.status_code})", None, {"message": f"添加失败: HTTP {result.status_code}"}

        elif name == "get_rss_feeds":
            from api.api_qBittorrent import get_rss_items
            with_data = arguments.get("withData", False)
            params = {"withData": with_data} if with_data else {}
            items_result = get_rss_items(params)
            feeds_data = {}
            try:
                feeds_data = items_result.json() if items_result.status_code == 200 else {}
            except Exception:
                pass
            if not isinstance(feeds_data, dict) or not feeds_data:
                return "当前没有RSS订阅源", None, {"message": "当前没有RSS订阅源"}
            item_count = _count_rss_items(feeds_data)
            ai_text = json.dumps({
                "feeds": list(feeds_data.keys()),
                "total_items": item_count
            }, ensure_ascii=False)
            return ai_text, "SubscribeTable", feeds_data

        elif name == "set_rss_download_rule":
            from api.api_qBittorrent import set_rule
            import json as _json
            rule_name = arguments.get("rule_name", "")
            rule_def = arguments.get("rule_def", {})
            if not rule_name or not rule_def:
                return "规则名称和规则定义不能为空", None, {"message": "规则名称和规则定义不能为空"}

            data = {
                "ruleName": rule_name,
                "ruleDef": _json.dumps(rule_def, ensure_ascii=False)
            }
            result = set_rule(data)
            if result.status_code == 200:
                return f"已成功设置RSS下载规则: {rule_name}", None, {"message": f"已设置RSS下载规则: {rule_name}"}
            return f"设置RSS规则失败 (HTTP {result.status_code})", None, {"message": f"设置失败: HTTP {result.status_code}"}

        elif name == "get_rss_rules":
            from api.api_qBittorrent import get_rss_rules
            result = get_rss_rules()
            if result.status_code == 200:
                try:
                    rules = result.json()
                    ai_text = json.dumps(rules, ensure_ascii=False)
                    summary = _summarize_rss_rules(rules)
                    return ai_text, None, {"message": summary}
                except Exception:
                    return "获取RSS规则失败，无法解析返回数据", None, {"message": "获取RSS规则失败"}
            return f"获取RSS规则失败 (HTTP {result.status_code})", None, {"message": f"获取失败: HTTP {result.status_code}"}

        elif name == "add_download_task":
            from api.api_qBittorrent import add_torrents
            urls = arguments.get("urls", "")
            savepath = arguments.get("savepath", "")
            data = {"urls": urls}
            if savepath:
                data["savepath"] = savepath
            result = add_torrents(data)
            if result.status_code == 200:
                return f"已成功添加下载任务", None, {"message": "下载任务已添加"}
            return f"添加下载任务失败 (HTTP {result.status_code})", None, {"message": f"添加失败: HTTP {result.status_code}"}

        elif name == "get_download_status":
            from api.api_qBittorrent import get_torrents_info
            result = get_torrents_info()
            if result.status_code == 200:
                try:
                    torrents = result.json()
                    summary = _summarize_torrents(torrents)
                    return summary, None, {"message": summary}
                except Exception:
                    return "获取下载状态失败，无法解析返回数据", None, {"message": "获取下载状态失败"}
            return f"获取下载状态失败 (HTTP {result.status_code})", None, {"message": f"获取失败: HTTP {result.status_code}"}

        elif name == "match_download_rule":
            from utils.fun_config import update_used_rule, get_rule_config
            rule_name = arguments.get("rule_name", "")
            if not rule_name:
                return "请提供规则名称", None, {"message": "请提供规则名称"}
            available_rules = [r["name"] for r in get_rule_config().get("rule_list", [])]
            if rule_name not in available_rules:
                return f"规则 '{rule_name}' 不存在，可用规则: {', '.join(available_rules)}", None, {"message": f"规则不存在，可用: {', '.join(available_rules)}"}
            if update_used_rule(rule_name):
                return f"已切换到搜索规则: {rule_name}", None, {"message": f"已切换到搜索规则: {rule_name}"}
            return f"切换规则失败", None, {"message": "切换规则失败"}

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
    """返回生成器，逐个产出 SSE 事件。"""
    if not message:
        yield {"type": "error", "content": "请输入消息内容"}
        yield {"type": "done"}
        return

    config = _get_chat_config()
    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "").rstrip("/")
    model = config.get("model", "")

    if not api_key:
        yield {"type": "error", "content": "AI 服务未配置，请在 ai_chat_config.json 中设置 api_key"}
        yield {"type": "done"}
        return

    logger.info(f"[aiChat] 收到消息: {message}, 历史条数: {len(history)}")

    messages = [
        {"role": "system",
         "content": (
            "你是一个智能助手，可以帮用户完成以下操作：\n"
            "1. 搜索番剧信息（search_bangumi）\n"
            "2. 查询番剧的字幕组（get_subgroup_info）\n"
            "3. 查询视频字幕列表（get_subtitle_list）\n"
            "4. 添加RSS订阅源（add_rss_subscription）\n"
            "5. 查看RSS订阅状态（get_rss_feeds）\n"
            "6. 查看已有RSS下载器规则（get_rss_rules）\n"
            "7. 设置RSS自动下载规则（set_rss_download_rule）\n"
            "8. 添加下载任务（add_download_task）\n"
            "9. 查看下载任务状态（get_download_status）\n"
            "10. 切换搜索规则（match_download_rule）\n"
            "当用户询问番剧、订阅、下载相关内容时，请主动使用工具查询，不要编造结果。"
          )}
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
                f"{base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
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
