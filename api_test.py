from fun_request import request

def post_everything(config):
    return request({
        "url": config['url'],
        "method": 'POST',
        "data": config['data']
    })

def get_everything(config):
    #判断键值params是否存在
    return request({
        "url": config['url'],
        "method": 'GET',
        "params": config
    })