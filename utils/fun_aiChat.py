import json
import logging

import requests

from utils.fun_config import get_ai_chat_config

logger = logging.getLogger(__name__)

# 单个工具返回给 AI 的 RSS 条目标题上限，避免多轮搜索把上下文撑爆
MAX_RSS_TITLES = 60
# 单个搜索工具返回给 AI 的条目上限
MAX_SEARCH_ITEMS = 20
# 本地番剧库只把必要字段交给 AI，过滤掉封面、时间戳、收藏状态等无关数据
LOCAL_BANGUMI_FIELDS = ("AnimeId", "Title", "EpisodeTotal", "EpisodeWatched", "Rating", "TypeDescription", "LastPlay")

# ---------- API 配置（从 ai_chat_config.json 读取） ----------
def _get_chat_config():
    return get_ai_chat_config()


# ---------- 工具定义 ----------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_local_bangumi",
            "description": (
                "【本地番剧库搜索】搜索本机 dandanplay 媒体库中已有的番剧，即网页主页「番剧」页的数据源。"
                "每条只返回必要信息：标题、本地ID(AnimeId)、总集数、已看集数、评分、类型、最近播放时间，"
                "不含封面、简介等无关数据。"
                "只能查到本地已存在的番剧，查不到任何可下载的网络资源；"
                "返回的 AnimeId 是 dandanplay 本地ID，与 RSS 搜索返回的番剧ID、Bangumi 条目ID 都不同，不能传给其他工具。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "番剧名称关键词，留空表示列出全部本地番剧"
                    },
                    "nav": {
                        "type": "string",
                        "description": "列表方式，可选 lastplay/season/lastupdate/lastadd/name/category/rating，默认 name"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_rss_bangumi",
            "description": (
                "【RSS 资源搜索】在网页「设置」中当前启用的 RSS 站点（蜜柑计划/MioBT/ACG.RIP/萌番组，可用 match_download_rule 切换）"
                "搜索可下载的番剧与剧集资源，返回番剧匹配项、RSS 搜索链接以及 RSS 条目标题。"
                "这是唯一能查到可下载/可订阅资源（单集、合集、字幕组）的搜索工具。"
                "keyword 支持用空格拼接多个筛选关键词，站点会按空格拆词同时匹配，"
                "例如「葬送的芙莉莲 樱都字幕组 1080p 简日」，用于把结果限定到指定字幕组/分辨率/语言，避免同一集出现多个重复版本。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词，可用空格拼接多个筛选词，例如「葬送的芙莉莲 樱都字幕组 1080p」"
                    }
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_bangumi_api",
            "description": (
                "【Bangumi 条目搜索】调用 Bangumi(bgm.tv) 公共接口搜索番剧条目元数据，"
                "返回条目ID、原名、中文名、放送日期、平台、集数、评分、简介。"
                "用于查询番剧的官方资料（原名、共几集、哪年放送、评分多少），不返回任何下载资源；"
                "返回的 id 是 bgm.tv 条目ID，不能用于订阅或字幕组查询。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "番剧名称关键词，建议用原名或中文名"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "最多返回多少条，默认 10"
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
            "description": "获取指定番剧在 RSS 站点上的所有字幕组信息，bangumi_id 需取自 search_rss_bangumi 的返回结果",
            "parameters": {
                "type": "object",
                "properties": {
                    "bangumi_id": {
                        "type": "string",
                        "description": "番剧ID，从 search_rss_bangumi 结果中获取"
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
            "name": "subscribe_rss_search",
            "description": (
                "【通过 RSS 搜索链接订阅】把空格拼接的关键词拼成当前 RSS 站点的搜索链接，作为订阅源加入 qBittorrent。"
                "关键词必须先用 search_rss_bangumi 验证过，确认结果中每一集都唯一且符合要求（指定字幕组/分辨率/语言）后再调用；"
                "只写番剧名会导致同时订阅到多个字幕组，同一集出现重复版本，"
                "应写成「番剧名 字幕组 分辨率 语言」这样的组合。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "空格拼接的筛选关键词，例如「葬送的芙莉莲 樱都字幕组 1080p 简日」"
                    },
                    "path": {
                        "type": "string",
                        "description": "保存目录路径，留空使用默认路径"
                    }
                },
                "required": ["keyword"]
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
def _extract_rss_titles(rss_json):
    """从 RSS 搜索结果里取出条目标题列表"""
    try:
        data = json.loads(rss_json) if isinstance(rss_json, str) else rss_json
        items = data["rss"]["channel"].get("item") or []
        if isinstance(items, dict):
            items = [items]
        return [str(item.get("title", "")) for item in items if isinstance(item, dict)]
    except Exception:
        return []


def _summarize_rss_search(raw):
    """把 RSS 搜索结果整理成便于 AI 判断的文本（番剧匹配项 + 条目标题）"""
    bangumi_items = raw.get("bangumiItem") or []
    lines = [f"番剧匹配数: {len(bangumi_items)}"]
    for item in bangumi_items[:MAX_SEARCH_ITEMS]:
        lines.append(
            f"- {item.get('title', '')} | bangumiId: {item.get('bangumiId', '')} | 订阅源: {item.get('rss_url', '')}"
        )

    titles = _extract_rss_titles(raw.get("rss"))
    lines.append(f"RSS 条目数: {len(titles)}")
    for title in titles[:MAX_RSS_TITLES]:
        lines.append(f"- {title}")
    if len(titles) > MAX_RSS_TITLES:
        lines.append(f"...（其余 {len(titles) - MAX_RSS_TITLES} 条已省略）")
    return "\n".join(lines)


def _summarize_local_bangumi(data):
    """本地番剧库结果只把前若干条交给 AI，避免条目过多"""
    if not data:
        return None
    ai_text = json.dumps(data[:MAX_SEARCH_ITEMS], ensure_ascii=False)
    if len(data) > MAX_SEARCH_ITEMS:
        ai_text += f"\n（共 {len(data)} 条，仅列出前 {MAX_SEARCH_ITEMS} 条）"
    return ai_text


def _search_bangumi_api(keyword, limit=10):
    """调用 Bangumi 公共接口搜索番剧条目，复用 routes/bangumi.py 的请求实现

    返回整理后的条目列表；请求失败返回 None。
    """
    from routes.bangumi import request_bangumi_api, BangumiApiError

    try:
        payload = request_bangumi_api(
            "v0/search/subjects",
            method="POST",
            data=json.dumps({"keyword": keyword, "filter": {"type": [2]}}, ensure_ascii=False),
            headers={"Content-Type": "application/json"},
        )
    except BangumiApiError as e:
        logger.error(f"[aiChat] Bangumi 搜索失败: {str(e)}")
        return None

    subjects = (payload or {}).get("data") or []
    return [
        {
            "bgmId": s.get("id"),
            "name": s.get("name", ""),
            "name_cn": s.get("name_cn", ""),
            "放送日期": s.get("date", ""),
            "平台": s.get("platform", ""),
            "集数": s.get("eps"),
            "评分": (s.get("rating") or {}).get("score"),
            "简介": (s.get("summary") or "")[:80],
        }
        for s in subjects[:limit]
    ]


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
        if name == "search_local_bangumi":
            from api.api_dandanPlay import search_library
            keyword = arguments.get("keyword", "")
            nav = arguments.get("nav") or "name"
            data = search_library(keyword=keyword, nav=nav, fields=LOCAL_BANGUMI_FIELDS)
            if data is None:
                return "本地番剧库查询失败，请检查 dandanPlay 是否可用", None, {"message": "本地番剧库查询失败"}
            if not data:
                tip = f"本地番剧库中没有找到与「{keyword}」相关的番剧" if keyword else "本地番剧库为空"
                return tip, None, {"message": tip}
            ai_text = _summarize_local_bangumi(data)
            return ai_text, None, {"message": ai_text}

        elif name == "search_rss_bangumi":
            from crawler.get_info import get_info_list
            keyword = arguments.get("keyword", "")
            raw = get_info_list(banguminame=keyword)
            if not raw:
                return "RSS 搜索失败或未找到相关资源，请检查网络与代理设置", None, {"message": "RSS 搜索失败或未找到相关资源"}
            ai_text = _summarize_rss_search(raw)
            # 前端用完整数据渲染搜索结果卡片，AI 只看整理后的文本
            return ai_text, "SearchResult", raw

        elif name == "search_bangumi_api":
            keyword = arguments.get("keyword", "")
            try:
                limit = int(arguments.get("limit") or 10)
            except (TypeError, ValueError):
                limit = 10
            if not keyword:
                return "请提供番剧名称关键词", None, {"message": "请提供番剧名称关键词"}
            subjects = _search_bangumi_api(keyword, limit=limit)
            if subjects is None:
                return "Bangumi 接口请求失败，请检查网络或代理设置", None, {"message": "Bangumi 接口请求失败"}
            if not subjects:
                return f"Bangumi 上没有找到与「{keyword}」相关的番剧条目", None, {"message": "未找到相关番剧条目"}
            ai_text = json.dumps(subjects, ensure_ascii=False)
            return ai_text, None, {"message": ai_text}

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
        elif name == "subscribe_rss_search":
            from crawler.get_info import build_rss_search_url
            from api.api_qBittorrent import addFeed
            keyword = (arguments.get("keyword") or "").strip()
            if not keyword:
                return "订阅关键词不能为空", None, {"message": "订阅关键词不能为空"}
            url = build_rss_search_url(keyword, url_encode=True)
            result = addFeed({"url": url, "path": arguments.get("path", "")})
            if result.status_code == 200:
                return f"已通过 RSS 搜索链接订阅: {url}", None, {"message": f"已订阅: {url}"}
            return f"订阅失败 (HTTP {result.status_code})", None, {"message": f"订阅失败: HTTP {result.status_code}"}

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


# ---------- AI 系统描述 ----------
SYSTEM_PROMPT = (
    "你是一个番剧搜索、订阅与下载管理助手，通过调用工具完成任务。\n"
    "\n"
    "【三个搜索工具的区别，务必按需选择】\n"
    "1. search_local_bangumi —— 本地番剧库搜索：查的是本机 dandanplay 媒体库里已经下载的番剧"
    "（即网页主页「番剧」页的内容），能看到本地有哪些番、共几集、已看到第几集、评分、类型，"
    "只返回这些必要字段，不含封面等无关数据。它查不到任何可下载的网络资源。\n"
    "2. search_rss_bangumi —— RSS 资源搜索：查的是网页「设置」里当前启用的 RSS 站点"
    "（蜜柑计划/MioBT/ACG.RIP/萌番组等，可用 match_download_rule 切换）上的可下载资源，"
    "能看到番剧匹配项、字幕组、以及每条 RSS 的剧集标题（单集/合集/分辨率/语言）。"
    "这是唯一能查到可下载、可订阅资源的搜索工具。\n"
    "3. search_bangumi_api —— Bangumi 条目搜索：查的是 Bangumi(bgm.tv) 的番剧资料，"
    "包括原名、中文名、放送日期、平台、总集数、评分、简介，属于元数据，不含任何下载资源。\n"
    "注意：三者返回的 ID 互不相同（dandanplay 本地ID / RSS 站点番剧ID / bgm.tv 条目ID），"
    "只有 RSS 站点番剧ID 能用于 get_subgroup_info，禁止混用。\n"
    "\n"
    "【搜索订阅流程，必须按此执行】\n"
    "1. 用户要订阅番剧时，先用 search_rss_bangumi 搜索，keyword 用空格拼接多个筛选关键词，"
    "站点会按空格拆词同时匹配，例如「葬送的芙莉莲 樱都字幕组 1080p 简日」。\n"
    "2. 检查返回的 RSS 条目：若同一集出现多个版本（不同字幕组/不同分辨率/不同语言）、"
    "或缺少目标集数，就调整筛选词重新搜索，直到每一集都唯一且符合要求。\n"
    "3. 确认无误后，再用 subscribe_rss_search 传入同一组关键词完成订阅。\n"
    "4. 订阅后可用 get_rss_rules 查看规则，用 set_rss_download_rule 配置 mustContain / mustNotContain，"
    "并开启 smartFilter 与 previouslyMatchedEpisodes，避免同一集重复下载。\n"
    "只写番剧名作为关键词会同时订阅到多个字幕组、同一集重复下载，因此订阅关键词必须带上"
    "字幕组、分辨率、语言等限定词；如果用户没有指定，先询问用户或根据搜索结果显示的常见版本给出建议。\n"
    "\n"
    "【其他工具】\n"
    "- get_subgroup_info：查看某番剧在某 RSS 站点上的字幕组（bangumi_id 取自 search_rss_bangumi）\n"
    "- get_subtitle_list：查看某个视频可用的字幕（需视频ID）\n"
    "- add_rss_subscription：添加一个已知的 RSS 链接\n"
    "- get_rss_feeds：查看已订阅的 RSS 源与条目\n"
    "- add_download_task：添加磁力/种子下载任务\n"
    "- get_download_status：查看下载进度\n"
    "- match_download_rule：切换使用的 RSS 站点\n"
    "\n"
    "涉及番剧、订阅、下载的问题必须先用工具查询，不要凭记忆编造结果；"
    "每次调用工具前用一句话说明你的判断依据；回答使用与用户相同的语言。"
)


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
    max_tool_rounds = int(config.get("max_tool_rounds") or 50)

    if not api_key:
        yield {"type": "error", "content": "AI 服务未配置，请在 ai_chat_config.json 中设置 api_key"}
        yield {"type": "done"}
        return

    logger.info(f"[aiChat] 收到消息: {message}, 历史条数: {len(history)}, 最大工具轮次: {max_tool_rounds}")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in (history or []):
        role = item.get("role", "")
        content = item.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    yield {"type": "thinking", "content": "正在分析你的需求..."}

    full_reply_parts = []

    for round_num in range(max_tool_rounds):
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

    yield {"type": "error", "content": f"工具调用轮次已达上限（{max_tool_rounds} 轮），请简化问题后重试"}
    yield {"type": "done"}
