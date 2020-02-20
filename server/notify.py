from urllib.parse import urlencode
from urllib.request import urlopen

from flask import json

from . import app

from app.models import Partment, Shoppoint, Staff, Order

def access_weixin_api(url, body, **kwargs):
    params = urlencode(kwargs)
    final_url = '?'.join([url, params])
    data = body.encode('utf-8')
    with urlopen(final_url, data=data) as f:
        result = f.read().decode('utf-8')

        info = json.loads(result)
        print('message sent result', info)

        return info

@app.task()
def notify_admins(code, shoppoint_id):
    # 获取营业网点
    shoppoint = Shoppoint.query.get_or_404(shoppoint_id)
    # 获取订单信息
    order = Order.query.get_or_404(code)
    # 获取公众号的partment
    web = Partment.query.filter_by(shoppoint_id=shoppoint_id, code='web').first()
    if not web:
        return
    # 提醒接龙发起者有新订单了
    products = ['x'.join([p.product.name + ('' if not p.size else '['+p.size.name+']'), str(p.amount)]) for p in order.products]

    if order.member_openid.name and order.member_openid.phone:
        first = '会员: ' + order.member_openid.name + ' [' + order.member_openid.phone + '] ' + order.address.address
    else:
        first = '顾客: ' + order.address.name + ' [' + order.address.phone + '] ' + order.address.address

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
                "value": '储值卡支付' if order.payment == 2 else "微信已支付" if order.pay_time and order.payment_code else "微信未支付"
                },
            "keyword5":{
                "value": order.note
                },
            "remark": {
                "value": '送货地址: ' + order.address.name + '[' + order.address.phone + ']' + order.address.full_address() if order.delivery_way == 2 else '取货地址: ' + order.pickup_address.address
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

        print('notify admin result: ', result)

@app.task()
def notify_customer(order_code, partment_code, shoppoint_id, form_id):
    # 获取订单信息
    order = Order.query.get_or_404(order_code)
    # 获取公众号的partment
    partment = Partment.query.filter_by(shoppoint_id=shoppoint_id, code=partment_code).first()
    # 提醒顾客订单已经付款
    data = {
        "thing1":{
            #"value": ' '.join(["x".join([p.product.name, str(p.amount)]) for p in order.products])
            "value": ' '.join(['x'.join([p.product.name + ('' if not p.size else '['+p.size.name+']'), str(p.amount)]) for p in order.products])
            },
        "amount7":{
            "value": '￥' + str((order.cost+order.delivery_fee)/100)
            },
        "thing17":{
            "value": order.note
            },
        "thing9":{
            "value": '如有疑问，可以拨打客服电话: 13370882078，服务时间：9:00~19:00'
            },
    }

    if order.delivery_way == 2:
        template_id = 'BmAwxIPTXz1p5ymj3g04NxChpWWI4sbgdy1RPyXphnU'
        data['thing8'] = order.address.name + '[' + order.address.phone + ']' + order.address.full_address()
    else:
        template_id = 'BmAwxIPTXz1p5ymj3g04NwrfuwnEl-ySpeaHrv7kxss'
        data['thing21'] = order.pickup_address.address

    j = {
        'template_id': template_id,
        'touser': order.openid,
        #'form_id': form_id,
        #"miniprogram_state": "developer",
        'page': '/pages/my/order/detail?code=' + order.code,
        'data': data
        }

    print('notify customer', j)

    body = json.dumps(j)
    access_weixin_api('https://api.weixin.qq.com/cgi-bin/message/subscribe/send', body, access_token=partment.get_access_token())
