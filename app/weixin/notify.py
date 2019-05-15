from urllib.parse import urlencode
from urllib.request import urlopen

from flask import json

from ..models import Partment, Shoppoint, Staff
from ..logging import logger

def access_weixin_api(url, body, **kwargs):
    params = urlencode(kwargs)
    final_url = '?'.join([url, params])
    data = body.encode('utf-8')
    with urlopen(final_url, data=data) as f:
        result = f.read().decode('utf-8')

        info = json.loads(result)

        return info

def notify_admins(order, shoppoint_id):
    # 获取营业网点
    shoppoint = Shoppoint.query.get_or_404(shoppoint_id)
    # 获取公众号的partment
    web = Partment.query.filter_by(shoppoint_id=shoppoint_id, code='web').first()
    if not web:
        return
    # 提醒接龙发起者有新订单了
    products = ['x'.join([p.product.name + ('' if not p.size else '['+p.size.name+']'), str(p.amount)]) for p in order.products]

    promotion = order.promotion
    if promotion:
        first = promotion.name + '-拼团编号: ' + str(order.index)
        #array.extend(['&promotion=', str(promotion.id)])
    else:
        first = '商城订单: ' + order.code
    url = ''.join(['https://wecakes.com/admin/', shoppoint.code, '/order/info?code=', order.code])

    data = {
            "first": {
                "value": first
                },
            "keyword1": {
                "value": ' '.join(products)
                },
            "keyword2":{
                "value": '￥' + str((order.cost+order.delivery_fee)/100)
                },
            "keyword3":{
                "value": order.member_openid.nickname
                },
            "keyword4":{
                "value": '储值卡支付，会员: ' + order.member_openid.name + '[' + order.member_openid.phone + ']' if order.payment == 2 else "微信已支付" if order.pay_time and order.payment_code else "微信未支付"
                },
            "keyword5":{
                "value": order.note
                },
            "remark": {
                "value": '送货地址: ' + order.address.name + '[' + order.address.phone + ']' + order.address.address if order.address.delivery_way == 2 else '取货地址: ' + order.address.address
                
                }
            }

    staffs = Staff.query.filter(Staff.shoppoint_id==shoppoint_id, Staff.privilege.op('&')(1)==1).all()
    for staff in staffs:
        j = {
            'template_id': 'pkl-0GTnDHxthXtR381PPNAooBT1JwUYuuP-YK1nRSA',
            'touser': staff.openid,
            'data': data,
            'url': url
            }
        body = json.dumps(j)
        result = access_weixin_api('https://api.weixin.qq.com/cgi-bin/message/template/send', body, access_token=web.get_access_token())

        logger.debug('notify admin result: %s', result)

def notify_promotion_customer(order, form_id):
    # 提醒顾客订单已经付款
    data = {
        "keyword1": {
            "value": order.index
            },
        "keyword2": {
            "value": order.code
            },
        "keyword3":{
            "value": '￥' + str(order.cost/100)
            },
        "keyword4":{
            #"value": ' '.join(["x".join([p.product.name, str(p.amount)]) for p in order.products])
            "value": ' '.join(['x'.join([p.product.name + ('' if not p.size else '['+p.size.name+']'), str(p.amount)]) for p in order.products])
            },
        "keyword5":{
            "value": "自提" if order.address.delivery_way == 1 else "快递 -- 运费:￥" + str(order.delivery_fee/100)
            },
        "keyword6":{
            "value": '-'.join([order.address.name, order.address.phone])
            },
        "keyword7":{
            "value": order.address.address
            },
        "keyword8":{
            "value": '您已拼团成功，如需退款，请务必在截单前申请退款，截单后不予退款，谢谢理解'
            },
        "keyword9":{
            "value": order.note
            },
        "keyword10":{
            "value": '如有疑问，可以拨打客服电话: 13370836021，服务时间：9:00~19:00'
            }
    }
    return {
        'template_id': 'pRZaMpRAWQLuyFVtGXaWQBbsJ7ECHjPBKAWRCUBRfps',
        'touser': order.openid,
        'form_id': form_id,
        #'url':  url_for('shop.payresult', _external=True, ticket_code=order.code),
        'data': data,
        'emphasis_keyword': 'keyword1.DATA'
        }

def notify_shop_customer(order, form_id):
    # 提醒顾客订单已经付款
    data = {
        "keyword1": {
            "value": order.code
            },
        "keyword2": {
            "value": order.pay_time.strftime('%Y-%m-%d %H:%M:%S') if order.pay_time else ''
            },
        "keyword3":{
            #"value": ' '.join(["x".join([p.product.name, str(p.amount)]) for p in order.products])
            "value": ' '.join(['x'.join([p.product.name + ('' if not p.size else '['+p.size.name+']'), str(p.amount)]) for p in order.products])
            },
        "keyword4":{
            "value": '￥' + str((order.cost+order.delivery_fee)/100)
            },
        "keyword5":{
            "value": "自提" if order.address.delivery_way == 1 else "快递 -- 运费:￥" + str(order.delivery_fee/100)
            },
        "keyword6":{
            "value": '-'.join([order.address.name, order.address.phone, order.address.address])
            },
        "keyword7":{
            "value": '如有疑问，可以拨打客服电话: 13370836021，服务时间：9:00~19:00'
            },
        "keyword8":{
            "value": order.note
            },
    }
    return {
        'template_id': 'x61QivvlgTGlNGuKDX8lYprf1EbgLw8Vv6MneCHSEmw',
        'touser': order.openid,
        'form_id': form_id,
        #'url':  url_for('shop.payresult', _external=True, ticket_code=order.code),
        'data': data,
        'emphasis_keyword': 'keyword4.DATA'
        }


def notify_customer(order, partment, form_id):
    if order.promotion:
        j = notify_promotion_customer(order, form_id)
    else:
        j = notify_shop_customer(order, form_id)

    body = json.dumps(j)
    access_weixin_api('https://api.weixin.qq.com/cgi-bin/message/wxopen/template/send', body, access_token=partment.get_access_token())
