import json
import logging

import requests
import xmltodict
from lxml import etree
from utils.fun_config import match_rule
from utils.fun_request import request, get_request_config

logger = logging.getLogger(__name__)


#获取id列表
def get_info_list(banguminame):
    rule = match_rule()
    try:
        data = {}
        base_url = rule["base_url"]
        rss_path = rule["rss_path"]
        query_params_bangumi_name = rule["query_params_bangumi_name"]
        rss_suffix = rule["rss_suffix"]

        rss_url = f"{base_url}{rss_path}{query_params_bangumi_name}{banguminame}{rss_suffix}"
        logger.info(f"[get_info_list] 搜索URL: {rss_url}")
        # print(rss_url)

        if "home_path" in rule:
            home_path = rule["home_path"]
            url = f"{base_url}{home_path}{query_params_bangumi_name}{banguminame}"
            data["bangumiItem"] = getBangumiItem(url,base_url,rss_url,rule)
        else:
            data["bangumiItem"] = []

        data["rss"] = getRssList(rss_url)

        return data

    except requests.exceptions.RequestException as e:
        logger.error(f"[get_info_list] 网络请求出错: {e}")
        return None  # 在请求出错时返回 None
    except Exception as e:
        logger.error(f"[get_info_list] 解析出错: {e}")
        return None  # 在解析出错时返回 None

def getRssList(rss_url):
    logger.info(f"[getRssList] 获取RSS列表: {rss_url}")
    # 使用搜索配置中的请求头和代理
    request_config = get_request_config(use_proxy=True)
    
    try:
        response_rss = requests.get(rss_url, headers=request_config['headers'], proxies=request_config['proxies'], timeout=10)
        response_rss.raise_for_status()
        logger.info(f"[getRssList] 成功获取RSS (状态码: {response_rss.status_code})")
    except requests.exceptions.ProxyError as e:
        logger.error(f"[getRssList] 代理连接失败: {e}")
        raise
    except requests.exceptions.Timeout as e:
        logger.error(f"[getRssList] 请求超时: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"[getRssList] 网络请求出错: {e}")
        raise
    
    xml_content = response_rss.text
    # 将 XML 转换为 JSON
    convertJson = xmltodict.parse(xml_content, encoding='utf-8')
    jsonStr = json.dumps(convertJson, indent=1, ensure_ascii=False)
    return jsonStr

def getBangumiItem(url,base_url,rss_url,rule):
    logger.info(f"[getBangumiItem] 获取番剧列表: {url}")
    xpath_bangumi_list_item = rule["xpath_bangumi_list_item"]
    xpath_bangumi_id_href = rule["xpath_bangumi_id_href"]
    xpath_bangumi_img = rule["xpath_bangumi_img"]
    xpath_bangumi_title = rule["xpath_bangumi_title"]

    bangumiItem = []

    # 使用搜索配置中的请求头和代理
    request_config = get_request_config(use_proxy=True)
    try:
        response = requests.get(url, headers=request_config['headers'], proxies=request_config['proxies'], timeout=10)
        response.raise_for_status()
        logger.info(f"[getBangumiItem] 成功获取番剧列表 (状态码: {response.status_code})")
    except requests.exceptions.ProxyError as e:
        logger.error(f"[getBangumiItem] 代理连接失败: {e}")
        raise
    except requests.exceptions.Timeout as e:
        logger.error(f"[getBangumiItem] 请求超时: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"[getBangumiItem] 网络请求出错: {e}")
        raise

    html = etree.HTML(response.content)
    id_list = html.xpath(xpath_bangumi_list_item)
    logger.info(f"[getBangumiItem] 找到 {len(id_list)} 个番剧项目")
    
    for i in id_list:
        bangumiId_element = i.xpath(xpath_bangumi_id_href)
        img_element = i.xpath(xpath_bangumi_img)
        title_element = i.xpath(xpath_bangumi_title)

        url_part = img_element[0]  # 先通过 url( 分割，取第二个部分
        image_path = url_part.split('?')[0]  # 再通过 ? 分割，取第一个部分
        bangumiItem.append({
            "bangumiId": bangumiId_element[0].split('/')[-1],
            "img": base_url + image_path,
            "title": title_element[0],
            "rss_url": rss_url,
        })
    return bangumiItem

