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
