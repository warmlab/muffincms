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
    for i in range(3):
        r = do_notify_customer(order_code, partment_code, shoppoint_id, form_id)
        if r['errcode'] == 43101: # user refuse to accept the msg, try another time
            from time import sleep
            sleep(10) # sleep 10 seconds
        else:
            break

def do_notify_customer(order_code, partment_code, shoppoint_id, form_id):
    # 获取订单信息
    order = Order.query.get_or_404(order_code)
    # 获取公众号的partment
    partment = Partment.query.filter_by(shoppoint_id=shoppoint_id, code=partment_code).first()
    thing1 = ' '.join(['x'.join([p.product.name + ('' if not p.size else '['+p.size.name+']'), str(p.amount)]) for p in order.products])
    if len(thing1)> 20:
        thing1 = thing1[:17] + '...'

    if order.note:
        if len(order.note) > 20:
            thing17 = order.note[:17] + '...'
        else:
            thing17 = order.note
    else:
        thing17 = '-'
    # 提醒顾客订单已经付款
    data = {
        "thing1":{
            #"value": ' '.join(["x".join([p.product.name, str(p.amount)]) for p in order.products])
            "value": thing1
            },
        "amount7":{
            "value": '￥' + str((order.cost+order.delivery_fee)/100)
            },
        "thing17":{
            "value": thing17
            },
        "thing9":{
            "value": '纯手工现场制作，请及时取货'
            },
    }

    if order.delivery_way == 2:
        template_id = 'BmAwxIPTXz1p5ymj3g04NxChpWWI4sbgdy1RPyXphnU'
        data['thing8'] = {'value': order.address.name[:7] + '[' + order.address.phone + ']'}
    else:
        template_id = 'BmAwxIPTXz1p5ymj3g04NwrfuwnEl-ySpeaHrv7kxss'
        data['thing21'] = {'value': order.pickup_address.address[:20]}

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
    r = access_weixin_api('https://api.weixin.qq.com/cgi-bin/message/subscribe/send', body, access_token=partment.get_access_token())
    print('subscribe send result', r)
    return r
    #if r['errcode'] == 43101: # user refuse to accept the msg
    #    return 1 # to try again
        # try another way send uniform message
        # 提醒顾客订单已经付款
        #weapp_data = {
        #        "keyword1": {
        #            "value": order.code
        #            },
        #        "keyword2": {
        #            "value": order.pay_time.strftime('%Y-%m-%d %H:%M:%S') if order.pay_time else ''
        #            },
        #        "keyword3":{
        #            #"value": ' '.join(["x".join([p.product.name, str(p.amount)]) for p in order.products])
        #            "value": ' '.join(['x'.join([p.product.name + ('' if not p.size else '['+p.size.name+']'), str(p.amount)]) for p in order.products])
        #            },
        #        "keyword4":{
        #            "value": '￥' + str((order.cost+order.delivery_fee)/100)
        #            },
        #        "keyword5":{
        #            "value": "自提" if order.delivery_way == 1 else "快递 -- 运费:￥" + str(order.delivery_fee/100)
        #            },
        #        "keyword6":{
        #            "value": '-'.join([order.address.name, order.address.phone, order.address.address])
        #            },
        #        "keyword7":{
        #            "value": '如有疑问，可以拨打客服电话: 13370836021，服务时间：9:00~19:00'
        #            },
        #        "keyword8":{
        #            "value": order.note
        #            },
        #        }
        #j = {
        #     'touser': order.openid,
        #     #'url':  url_for('shop.payresult', _external=True, ticket_code=order.code),
        #     'weapp_template_msg': {
        #        'template_id': 'x61QivvlgTGlNGuKDX8lYprf1EbgLw8Vv6MneCHSEmw',
        #        'form_id': form_id,
        #        'data': weapp_data,
        #        'emphasis_keyword': 'keyword4.DATA',
        #        'page': '/pages/my/order/detail?code=' + order.code
        #     }
        # },
        #print('body', j)
        #body = json.dumps(j)
        #access_weixin_api('https://api.weixin.qq.com/cgi-bin/message/wxopen/template/uniform_send', body, access_token=partment.get_access_token())
