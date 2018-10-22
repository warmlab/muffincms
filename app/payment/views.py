from datetime import datetime
from time import time
from uuid import uuid4

from flask import json, jsonify, abort
from flask import request, url_for
from flask.json import jsonify

from ..models import Product, Shoppoint, Order
from ..models import MemberOpenid, Member
from ..logging import logger

from . import payment
from .message import Message

def notify_admins(order, access_token, formId=None):
    # 提醒接龙发起者有新订单了
    if order.address:
        data = {
            "keyword4":{
                "value": "自提",
                },
            "keyword5":{
                "value": order.address.address,
                },
            "keyword6":{
                "value": order.member.nickname + ' 拼团编号:' + str(order.seq),
                },
            "keyword7":{
                "value": '',
                },
            }
    else:
        data = {
            "keyword4":{
                "value": "送货",
                },
            "keyword5":{
                "value": order.delivery_address.address,
                },
            "keyword6":{
                "value": order.delivery_address.name + ' 拼团编号:' + str(order.seq),
                },
            "keyword7":{
                "value": order.delivery_address.phone,
                },
            }

    data.update({
        "keyword1": {
            "value": order.code,
            },
        "keyword2":{
            "value": ','.join(["x".join([p.product.product.name, str(p.amount)]) for p in order.products]),
            },
        "keyword3":{
            "value": '￥' + str(order.real_price),
            },
        "keyword8":{
            "value": order.note,
            },
        "keyword9":{
            "value": ("微信已支付" if order.pay_time and order.payment_code else "微信未支付") if order.payment == 4 else '请注意确认会员卡，会员: ' + order.member.name + '[' + order.member.phone + ']',
            }
    })

    mos = MemberOpenID.query.filter_by(privilege=1).all()
    for mo in mos:
        j = {
            'template_id': '2IFBivZUlocpzX-jM5etKReqveFPPn1NaHF--lwjH1A',
            'touser': mo.openid,
            #'url':  url_for('shop.payresult', _external=True, ticket_code=order.code),
            'form_id': formId if formId else order.prepay_id,
            'data': data,
            "emphasis_keyword": "keyword3.DATA"
            }
        body = json.dumps(j)
        print(body)
        result = post_weixin_api('https://api.weixin.qq.com/cgi-bin/message/wxopen/template/send', body, access_token=access_token)
        print('8888888888888888888888 result', result)

def notify_customer():
    """
    # 提醒顾客订单已经付款
    data = {
        "keyword1": {
            "value": order.code,
            "color": "orange"
            },
        "keyword2":{
            "value": ','.join(["*".join([p.product.product.name, str(p.amount)]) for p in order.products]),
            "color":"#754c24"
            },
        "keyword3":{
            "value": '￥' + str(order.real_price),
            "color":"#754c24"
            },
        "keyword4":{
            "value": "自提" if order.address else "送货",
            "color":"#754c24"
            },
        "keyword5":{
            "value": '￥' + str(order.member.address),
            "color":"#754c24"
            },
        "keyword6":{
            "value": '￥' + str(order.member.nickname),
            "color":"#754c24"
            },
        "keyword7":{
            "value": '￥' + str(order.member.phone),
            "color":"#754c24"
            },
        "keyword8":{
            "value": order.note,
            "color":"#754c24"
            },
        "keyword9":{
            "value": "已支付" if order.pay_time and order.payment_code else "未支付",
            "color":"#754c24"
            }
    }
    j = {
        'template_id': 'x61QivvlgTGlNGuKDX8lYprf1EbgLw8Vv6MneCHSEmw',
        'touser': message.get_value('openid'),
        'url':  url_for('shop.payresult', _external=True, ticket_code=order.code),
        'form_id': order.prepay_id,
        'data': data
        }
    body = json.dumps(message.generate_template_body('hes3WdAVpnWrS1VenAUM8MFJbKQmTlKnBLOr7SAuvcI',
         message.get_value('openid'), url_for('shop.payresult', _external=True, ticket_code=order.code), data))
    post_weixin_api('https://api.weixin.qq.com/cgi-bin/message/template/send', body, access_token=shoppoint.access_token)
    """
    pass


@payment.route('/<string:partcode>/notify', methods=['GET', 'POST'])
def notify(shopcode, partcode):
    if not signature_verify():
        return

    shoppoint = Shoppoint.query.filter_by(code=shoppcode).first()
    partment = Partment.query.filter_by(code=partcode).first()
    if not shoppoint or not partment:
        return "<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[BAD REQUEST]]></return_msg></xml>", 400

    message = Message.parse_message(request.data.decode('utf-8'))
    if not message:
        return "<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[BAD REQUEST]]></return_msg></xml>", 400

    if message.get_value('result_code') != 'SUCCESS' or message.get_value('return_code') != 'SUCCESS':
        return "<xml><return_code><![CDATA[{0}]]></return_code><return_msg><![CDATA[{1}]]></return_msg></xml>".format(
                                                     message.get_value('result_code'), message.get_value('return_code')), 400

    if not message.check_signature(partment.appsecret):
        return "<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[签名不正确]]></return_msg></xml>", 400

    order = Order.query.get(message.get_value('out_trade_no'))
    if not order:
        return "<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[out trade no error]]></return_msg></xml>", 400
    elif order.payment_code and order.pay_time:
        return "<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>", 201
            

    order.payment_code = message.get_value('transaction_id')
    if int(order.cost) == int(message.get_value('cash_fee')):
        order.pay_time = datetime.strptime(message.get_value('time_end'), '%Y%m%d%H%M%S')
        if order.promotion:
            order.commit_amount()

    #db.session.add(order)
    db.session.commit()

    notify_admins(order, shoppoint.get_access_token())

    notify_customer()

    return "<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>"

    if result.get('return_code') == 'SUCCESS':
        order.payment_code = result.get('prepay_id')
        #package = '='.join(['prepay_id', result.get('prepay_id')])
        #params = {
        #    'timeStamp': int(time()),
        #    'appId': sp.weixin_mini_appid,
        #    'nonceStr': result.get('nonce_str'),
        #    'package': package,
        #    'signType': 'MD5'
        #}
        #params['signature'], signType = generate_pay_sign(params, sp.weixin_appsecret)
        #params['pack'] = [package]

        order.save()

        return "<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>", 201
        #return jsonify({
        #    'order': order.to_json(),
        #    'payment': params}), 201

    elif result.get('result_code') == 'FAIL' and result.get('err_code') == 'OUT_TRADE_NO_USED':
        return "<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[out trade no error]]></return_msg></xml>", 409
