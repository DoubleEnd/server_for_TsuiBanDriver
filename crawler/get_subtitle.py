import requests
from lxml import etree
from utils.fun_config import get_url_config
from urllib.parse import urljoin

# dandanPlay_BASE_URL = 'http://100.65.133.102:8888'
dandanPlay_BASE_URL = get_url_config()['dandanPlay_BASE_URL']


def get_subtitle_list(videoId):
    """
    获取视频页面中的字幕列表，返回一个字幕字典列表：
    [ { 'title': ..., 'href': ... }, ... ]

    返回说明：
    - 成功解析但无字幕：返回空列表 []
    - 请求或解析出错：返回 None
    """
    try:
        url = f"{dandanPlay_BASE_URL}/web1/video.html?id={videoId}"
        response = requests.get(url)
        response.raise_for_status()

        html = etree.HTML(response.content)

        # 定位包含“字幕列表”卡片的区域，并在其范围内找所有链接
        anchors = html.xpath(
            "//div[contains(@class,'card')][.//div[@class='card-header' and normalize-space(text())='字幕列表']]//a"
        )

        result = []
        for a in anchors:
            href = a.get('href')
            if not href:
                continue
            title = a.xpath('string(.)').strip()
            full_href = href if href.startswith('http') else urljoin(dandanPlay_BASE_URL, href)
            result.append({'title': title, 'href': full_href})

        return result

    except requests.exceptions.RequestException as e:
        print(f"请求出错: {e}")
        return None
    except Exception as e:
        print(f"解析出错: {e}")
        return None


def is_subtitle(videoId):
    """使用 `get_subtitle_list` 判断是否存在字幕。
    返回 True/False/None：None 表示请求或解析出错。
    """
    try:
        lst = get_subtitle_list(videoId)
        if lst is None:
            return None
        return len(lst) > 0
    except Exception as e:
        print(f"is_subtitle 出错: {e}")
        return None
