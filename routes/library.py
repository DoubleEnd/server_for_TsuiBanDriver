# 本地媒体库路由：扫描触发、番剧库读取、首页番剧列表与详情
import logging

from flask import Blueprint, jsonify, request

from utils import fun_dandan, fun_scan, fun_user
from utils.fun_response import success, error

logger = logging.getLogger(__name__)
library_bp = Blueprint('library', __name__)


@library_bp.route("/scanLibrary", methods=["POST"])
def submit_scanlibrary():
    """立刻触发一次媒体库扫描，结果写入 data/library.json，返回扫描摘要

    mode 为 fast 时执行快速扫描（只识别从未扫描过的文件并合并进已有番剧库），
    其余取值执行完全扫描（重建整个番剧库）。
    """
    mode = (request.json or {}).get("mode", "full")
    try:
        return success(fun_scan.scan_library(mode=mode))
    except Exception as e:
        logger.error(f"[scanLibrary] 异常错误: {str(e)}", exc_info=True)
        return error("扫描媒体库失败", 500, msg=str(e))


@library_bp.route("/getLibrary", methods=["GET"])
def submit_getlibrary():
    """读取最近一次扫描生成的番剧库（不含视频磁盘路径）"""
    try:
        return success(fun_scan.load_library_public())
    except Exception as e:
        logger.error(f"[getLibrary] 异常错误: {str(e)}", exc_info=True)
        return error("获取媒体库失败", 500, msg=str(e))


@library_bp.route("/bangumi/search", methods=["GET"])
def submit_bangumi_search():
    """首页番剧列表：从本地番剧库检索（params 为导航方式，keyword 为搜索关键字）

    带 username 时回填该用户的「已看集数」，并按最近播放排序。
    """
    nav = request.args.get("params", "name")
    keyword = request.args.get("keyword", "")
    username = request.args.get("username", "")
    logger.info(f"[bangumi/search] 导航: {nav}, 关键字: {keyword}, 用户: {username}")
    try:
        history = fun_user.get_history(username)
        return success(fun_scan.search_bangumi(keyword=keyword, nav=nav, history=history))
    except Exception as e:
        logger.error(f"[bangumi/search] 异常错误: {str(e)}", exc_info=True)
        return error("获取番剧列表失败", 500, msg=str(e), data=[])


@library_bp.route("/localBangumi", methods=["GET"])
def submit_local_bangumi():
    """本地番剧库中已识别的作品（手动重新识别时选择作品用）"""
    keyword = request.args.get("keyword", "").strip()
    try:
        return success(fun_scan.search_local_bangumi(keyword))
    except Exception as e:
        logger.error(f"[localBangumi] 异常错误: {str(e)}", exc_info=True)
        return error("获取本地作品列表失败", 500, msg=str(e), data=[])


@library_bp.route("/searchAnime", methods=["GET"])
def submit_search_anime():
    """在弹弹play 上按关键字搜索番剧（手动重新识别用）"""
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return success([])
    return success(fun_dandan.search_anime(keyword))


@library_bp.route("/animeEpisodes", methods=["GET"])
def submit_anime_episodes():
    """在线番剧的剧集列表（手动重新识别时选择剧集用）"""
    anime_id = request.args.get("animeId", "").strip()
    if not anime_id:
        return error("缺少animeId参数", 400)
    try:
        episodes = fun_scan.list_bangumi_episodes(anime_id)
    except Exception as e:
        logger.error(f"[animeEpisodes] 异常错误: {str(e)}", exc_info=True)
        return error("获取剧集列表失败", 500, msg=str(e))
    if episodes is None:
        return error("未获取到该作品的剧集信息", 404)
    return success(episodes)


@library_bp.route("/rematchFile", methods=["POST"])
def submit_rematch_file():
    """手动把某个视频文件改判到指定作品与剧集，并写入本地识别记录"""
    data = request.json or {}
    video_id = str(data.get("videoId") or "").strip()
    anime_id = str(data.get("animeId") or "").strip()
    episode_id = str(data.get("episodeId") or "").strip()
    if not video_id or not anime_id or not episode_id:
        return error("缺少videoId、animeId或episodeId参数", 400)
    try:
        result = fun_scan.rematch_file(video_id, anime_id, episode_id)
    except ValueError as e:
        logger.warning(f"[rematchFile] 参数或数据不合法: {str(e)}")
        return error(str(e), 400)
    except Exception as e:
        logger.error(f"[rematchFile] 异常错误: {str(e)}", exc_info=True)
        return error("重新识别失败", 500, msg=str(e))
    return success(result)


@library_bp.route("/bangumiDetail", methods=["GET"])
def submit_bangumi_detail():
    """番剧详情页：在线元信息（封面/名称/简介/评分/标签/评论）+ 本地剧集

    animeId（首页/播放页）与 bgmId（时间表）二选一。
    """
    anime_id = request.args.get("animeId", "").strip()
    bgm_id = request.args.get("bgmId", "").strip()
    if not anime_id and not bgm_id:
        return error("缺少animeId或bgmId参数", 400)
    username = request.args.get("username", "")
    try:
        history = fun_user.get_history(username)
        info = fun_scan.get_bangumi_info(anime_id=anime_id, bgm_id=bgm_id, history=history)
    except Exception as e:
        logger.error(f"[bangumiDetail] 异常错误: {str(e)}", exc_info=True)
        return error("获取番剧详情失败", 500, msg=str(e))
    if info is None:
        logger.warning(f"[bangumiDetail] 未找到番剧: animeId={anime_id} bgmId={bgm_id}")
        return error("番剧不存在", 404)
    logger.info(f"[bangumiDetail] {info['Title']}（本地剧集 {len(info['Episodes'])} 集）")
    return success(info)


@library_bp.route("/bangumiList", methods=["GET"])
def submit_bangumi_list():
    """番剧详情：按本地番剧 ID（params）返回剧集与本地文件

    沿用前端历史约定，直接返回原始对象（不做 code/msg/data 包装）。
    """
    anime_id = request.args.get("params", "")
    if not anime_id:
        return error("缺少params参数", 400)
    username = request.args.get("username", "")
    try:
        history = fun_user.get_history(username)
        detail = fun_scan.get_bangumi_detail(anime_id, history=history)
    except Exception as e:
        logger.error(f"[bangumiList] 异常错误: {str(e)}", exc_info=True)
        return error("获取番剧详情失败", 500, msg=str(e))
    if detail is None:
        logger.warning(f"[bangumiList] 未找到番剧: {anime_id}")
        return error("番剧不存在", 404)
    logger.info(f"[bangumiList] {detail['Title']} -> {len(detail['Episodes'])} 集")
    return jsonify(detail)
