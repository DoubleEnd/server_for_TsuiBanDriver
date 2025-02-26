import requests
from lxml import etree

def get_rss_link(id):
    try:
        http = "https://mikanani.me"  # 修正了 URL 的定义
        search = "/Home/Bangumi/"
        url = f"{http}{search}{id}"

        response = requests.get(url)
        response.raise_for_status()

        # 使用 lxml 解析网页内容
        html = etree.HTML(response.content)

        # 获取 RSS 链接
        rss_links_element = html.xpath('/html/body/div[4]/div[2]/div[5]/a[1]/@href')

        data = []

        # 提取 RSS 链接
        rss_link = rss_links_element[0].split('&')[0]
        rss_link = f"{http}{rss_link}"

        data.append({
            "rss_link" : rss_link
        })

        return data

    except requests.exceptions.RequestException as e:
        print(f"请求出错: {e}")
    except Exception as e:
        print(f"解析出错: {e}")

# if __name__ == "__main__":
#     sendInfo = {"code": 200, "msg": "success", "data": get_rss_link(id="212")}
#     print(sendInfo)