import requests
from lxml import etree

dandanPlay_BASE_URL = 'http://100.65.133.102:8888'
def is_subtitle(videoId):
    try:
        url = f"{dandanPlay_BASE_URL}/web1/video.html?id={videoId}"

        xpath_subtitle_card_head = "(//div[@class='card-header'])[1]"

        response = requests.get(url)
        response.raise_for_status()

        html = etree.HTML(response.content)
        # print(html.xpath(xpath_subtitle_card_head)[0].text.strip())

        if html.xpath(xpath_subtitle_card_head)[0].text.strip() != '字幕列表':
            return False

        return True

    except requests.exceptions.RequestException as e:
        print(f"请求出错: {e}")
        return None  # 在请求出错时返回 None
    except Exception as e:
        print(f"解析出错: {e}")
        return None  # 在解析出错时返回 None
