import hashlib

from uuid import uuid4
from time import time
from urllib.request import Request
from urllib.request import urlopen

from flask import json

from xml.etree import ElementTree as etree


def generate_pay_sign(params, key):
    """
    签名生成函数
       
    :param params: 参数，dict 对象
    :param key: API 密钥
    :return: sign string
    """
    param_list = []
    for k,v in params.items():
        if v:
            param_list.append('='.join([k, str(v)]))

    param_list.sort()
    if key:
        param_list.append('='.join(['key', key]))
    print(param_list)

    print('&'.join(param_list))
    return hashlib.md5('&'.join(param_list).encode('utf8')).hexdigest().upper(), 'MD5' # TODO 考虑HMAC-SHA256

def generate_sign(params, key=None):
    """
    签名生成函数
       
    :param params: 参数，dict 对象
    :param key: API 密钥
    :return: sign string
    """
    param_list = []
    for k,v in params.items():
        if v:
            param_list.append('='.join([k.lower(), str(v)]))

    param_list.sort()
    #if key:
    #    param_list.append('='.join(['key', key]))
    print(param_list)

    print('&'.join(param_list))
    return hashlib.sha1('&'.join(param_list).encode('utf8')).hexdigest().upper(), 'SHA1' # TODO 考虑HMAC-SHA256

def parse_xml_to_dict(xmlbody):
    root = etree.fromstring(xmlbody)

    data = {}
    for e in root:
        data[e.tag] = e.text

    return data

def parse_dict_to_xml(dic):
    items = []
    for k,v in dic.items():
        if k == 'total_fee' or k == 'mch_id':
            items.append('<{key}>{value}</{key}>'.format(key=k, value=v))
        else:
            items.append('<{key}>{value}</{key}>'.format(key=k, value=v.join(['<![CDATA[',']]>'])))

    return ''.join(items).join(['<xml>','</xml>'])

# 统一下单，WxPayUnifiedOrder中out_trade_no、body、total_fee、trade_type必填
# appid、mchid、spbill_create_ip、nonce_str不需要填入
# @return 成功时返回，其他抛异常
def unified_order(order, appid, mch_id, key, openid, notify_url, device_info='WEB', trade_type='JSAPI', time_out=6):
    url = "https://api.mch.weixin.qq.com/pay/unifiedorder"
    data = {}

    if not order or not appid or not mch_id or not key:
        return

    data['out_trade_no'] = order.code
    print(order.products)
    data['body'] = order.promotion.name if order.promotion and order.promotion.name else '小麦芬烘焙小店'
    data['detail'] = ' '.join([p.product.name + 'x' + str(p.amount) for p in order.products]) # 商品简单描述
    data['attach'] = '小麦芬烘焙'
    data['total_fee'] = order.cost + order.delivery_fee
    data['trade_type'] = trade_type
    data['openid'] = openid
    data['device_info'] = device_info

    # 异步通知url未设置，则使用配置文件中的url
    data['notify_url'] = notify_url

    data['appid'] = appid #小程序账号ID
    data['mch_id'] = mch_id #商户号
    data['nonce_str'] = uuid4().hex #随机字符串
    data['spbill_create_ip'] = '121.42.139.198'
    #data['attach'] = '卡诺烘焙-微信小店'
    #data['detail'] = _make_goods_info(order.products)

    # 签名
    data['sign'], sign_type = generate_pay_sign(data, key)
    print(data['sign'])
    xml = parse_dict_to_xml(data)

    #startTimeStamp = int(time())
    req = Request(url=url, data=xml.encode('utf-8'), method='POST')
    req.add_header('Accept', 'application/xml')
    req.add_header('Content-Type', 'application/xml')
    with urlopen(req) as f:
        result = f.read().decode('utf8')

        return parse_xml_to_dict(result)
