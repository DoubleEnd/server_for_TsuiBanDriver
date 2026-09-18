from crawler.get_subtitle import is_subtitle
from utils.fun_request import api_dandanPlay_request

def welcome(params):
    return api_dandanPlay_request({
        "url": "/api/v1/welcome",
        "method": "get",
        "params": params
    })


def library(params):
    return api_dandanPlay_request({
        "url": "/api/v1/library",
        "method": "get",
        "params": params
    })


def bangumi(params):
    return api_dandanPlay_request({
        "url": f"/api/v1/library/v2/bangumi/list/nav:{params}",
        "method": "get"
    })


def bangumiList(params):
    return api_dandanPlay_request({
        "url": f"/api/v1/library/v2/bangumi/details/{params}",
        "method": "get"
    })


def search_library(keyword="", nav="name", fields=None):
    """在本地番剧库（dandanplay library）中按标题关键字搜索

    nav 为列表排序/分类方式（lastplay/season/lastupdate/lastadd/name/category/rating）。
    fields 传入字段名集合时，只保留这些字段（如给 AI 用时过滤掉封面、时间戳等无关数据）。
    返回番剧列表；请求失败返回 None，解析失败返回空列表。
    """
    result = bangumi(params=nav)
    if not result:
        return None
    try:
        data = result.json()
    except Exception:
        data = []
    if not isinstance(data, list):
        data = []
    keyword_lower = (keyword or "").strip().lower()
    if keyword_lower:
        data = [item for item in data
                if keyword_lower in str(item.get("Title", "")).lower()]
    if fields:
        data = [{key: item.get(key) for key in fields} for item in data]
    return data

# 获取字幕
def getSubtitle(params):
    # print("获取字幕")
    if is_subtitle(params):
        result = api_dandanPlay_request({
            "url": f"/web1/subtitle/{params}/ass",
            "method": "get",
        })
        if result.text:
            return result.content.decode("utf-8")
        else:
            return getSubtitle(params)
    else:
        return ""


def getStreamUrl(videoId):
    return api_dandanPlay_request({
        "url": f"/api/v1/stream/id/{videoId}",
        "method": "get",
        "timeout": 60
    })


def getComment(videoId):
    return api_dandanPlay_request({
        "url": f"/api/v1/comment/id/{videoId}",
        "method": "get",
        "timeout": 30
    })


def getImage(videoId):
    return api_dandanPlay_request({
        "url": f"/api/v1/image/id/{videoId}",
        "method": "get",
        "timeout": 30
    })
