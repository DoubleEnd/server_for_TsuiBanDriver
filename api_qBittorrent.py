import fun_request
from fun_request import request

def get_all_rss_items(data):
    return request({
        "url": "rss/items",
        "method": "get",
        "data": data
    })

def login(data):
    return request({
        "url": "auth/login",
        "method": "post",
        "data": data
    },).cookies

def addFeed(data):
    return request({
        "url": "rss/addFeed",
        "method": "post",
        "data": data
    })


if __name__ == '__main__':
    fun_request.global_cookie = login({
        'username': 'admin',
        'password': '123456'
    },)
    # print(get_all_rss_items({}).json())

