import requests
from lxml import etree

from utils.fun_config import match_rule
from utils.fun_request import get_request_config


def get_subgroup_info(bangumiId):
    rule = match_rule()
    try:
        base_url = rule["base_url"]
        home_path = rule["home_path"]
        bangumi_path = rule["bangumi_path"]
        xpath_subgroup_list = rule["xpath_subgroup_list"]
        xpath_subgroup_id = rule["xpath_subgroup_id"]
        xpath_subgroup_name = rule["xpath_subgroup_name"]

        url = f"{base_url}{home_path}{bangumi_path}{bangumiId}"

        # 使用搜索配置中的请求头和代理
        request_config = get_request_config(use_proxy=True)
        response = requests.get(url, headers=request_config['headers'], proxies=request_config['proxies'])
        response.raise_for_status()

        # 使用 lxml 解析网页内容
        html = etree.HTML(response.content)
        subgroup_list = html.xpath(xpath_subgroup_list)

        data = []

        for i in subgroup_list :
            subgroup_id = i.xpath(xpath_subgroup_id)
            subgroup_name = i.xpath(xpath_subgroup_name)

            data.append({
                "subgroupId": subgroup_id[0],
                "subgroupname": subgroup_name[0]
            })

        return data

    except requests.exceptions.RequestException as e:
        print(f"请求出错: {e}")
        return None  # 在请求出错时返回 None
    except Exception as e:
        print(f"解析出错: {e}")
        return None  # 在解析出错时返回 None