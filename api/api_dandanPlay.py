# 弹弹play 开放 API 封装（签名模式）
from utils.fun_request import api_dandanPlay_request


def match(file_name, file_hash, match_mode="hashAndFileName"):
    """文件识别：按文件名 + 前 16MB 的 MD5 匹配番剧与剧集"""
    return api_dandanPlay_request({
        "url": "/api/v2/match",
        "method": "post",
        "json": {
            "fileName": file_name,
            "fileHash": file_hash,
            "matchMode": match_mode,
        },
        "timeout": 20,
    })


def bangumi(anime_id):
    """番剧详情：名称、封面、评分、放送日期与剧集列表"""
    return api_dandanPlay_request({
        "url": f"/api/v2/bangumi/{anime_id}",
        "method": "get",
        "timeout": 20,
    })


def bangumi_by_bgmtv(subject_id):
    """按 Bangumi.tv 的 subjectId 获取番剧详情（时间表数据来自 bgm.tv）"""
    return api_dandanPlay_request({
        "url": f"/api/v2/bangumi/bgmtv/{subject_id}",
        "method": "get",
        "timeout": 20,
    })


def search_anime(keyword):
    """按关键字搜索番剧"""
    return api_dandanPlay_request({
        "url": "/api/v2/search/anime",
        "method": "get",
        "params": {"keyword": keyword},
        "timeout": 20,
    })


def comments(episode_id, with_related=True, ch_convert=0):
    """剧集弹幕：episodeId 为弹幕库编号

    withRelated 为 true 时同时获取关联的第三方弹幕源（弹幕更全）；
    该接口会 302 跳转到弹幕加速服务，requests 默认跟随跳转。
    """
    params = {"chConvert": ch_convert}
    if with_related:
        params["withRelated"] = "true"
    return api_dandanPlay_request({
        "url": f"/api/v2/comment/{episode_id}",
        "method": "get",
        "params": params,
        "timeout": 30,
    })
