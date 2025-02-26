import requests
from lxml import etree

def get_rss_link(backbangumiId,backsubgroupid):
    try:
        http = "https://mikanani.me"  # 修正了 URL 的定义
        search = f"/RSS/Bangumi?bangumiId={backbangumiId}&subgroupid={backsubgroupid}"
        url = f"{http}{search}"

        response = requests.get(url)
        response.raise_for_status()

        # 使用 lxml 解析网页内容
        html = etree.HTML(response.content)

        data = []

        return data

    except requests.exceptions.RequestException as e:
        print(f"请求出错: {e}")
    except Exception as e:
        print(f"解析出错: {e}")

