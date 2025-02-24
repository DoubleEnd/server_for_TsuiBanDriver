import requests
from lxml import etree

#获取id列表
def get_info_list(moviename):
    try:
        http = "https://mikanani.me"
        search = "/Home/Search?searchstr="
        url = f"{http}{search}{moviename}"

        response = requests.get(url)
        response.raise_for_status()

        # 使用 lxml 解析网页内容
        html = etree.HTML(response.content)
        len_id_list = len(html.xpath(f'//*[@id="sk-container"]/div[2]/ul/li'))

        data = []

        for i in range(1,len_id_list+1):
            id_element = html.xpath(f'//*[@id="sk-container"]/div[2]/ul/li[{i}]/a/@href')
            img_element = html.xpath(f'//*[@id="sk-container"]/div[2]/ul/li[{i}]//a/span/@data-src')
            title_element = html.xpath(f'//*[@id="sk-container"]/div[2]/ul/li[{i}]/a//div[@class="an-text"]/@title')
            # print(etree.tostring(img_element[0], encoding='utf-8').decode('utf-8'))

            url_part = img_element[0] # 先通过 url( 分割，取第二个部分
            image_path = url_part.split('?')[0] # 再通过 ? 分割，取第一个部分

            data.append({
                "id": id_element[0].split('/')[-1],
                "img": image_path,
                "title": title_element[0]
            })

        return data

    except requests.exceptions.RequestException as e:
        print(f"请求出错: {e}")
    except Exception as e:
        print(f"解析出错: {e}")

if __name__ == "__main__":
    sendInfo = {"code": 200, "msg": "success", "data": get_info_list(moviename="进击的巨人")}
    print(sendInfo)
#提交测试
