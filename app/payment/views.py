from datetime import datetime
from uuid import uuid4

from flask import json, jsonify, abort
from flask import request, url_for
from flask.json import jsonify

from ..models import db
from ..models import Product, Shoppoint, Order, Partment
from ..models import MemberOpenid

from . import payment
from ..weixin import Message

from server import notify_admins, notify_customer

@payment.route('/notify', methods=['GET', 'POST'])
def notify(shopcode, partcode):
    # TODO no need to verify signature
    #if not signature_verify():
    #    return

    print('request body', request.data.decode('utf-8'))
    shoppoint = Shoppoint.query.filter_by(code=shopcode).first_or_404()
    partment = Partment.query.filter_by(code=partcode).first_or_404()
    if not shoppoint or not partment:
        return "<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[BAD REQUEST]]></return_msg></xml>", 400

    message = Message.parse_message(request.data.decode('utf-8'))
    if not message:
        return "<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[BAD REQUEST]]></return_msg></xml>", 400

    if message.get_value('result_code') != 'SUCCESS' or message.get_value('return_code') != 'SUCCESS':
        return "<xml><return_code><![CDATA[{0}]]></return_code><return_msg><![CDATA[{1}]]></return_msg></xml>".format(
                                                     message.get_value('result_code'), message.get_value('return_code')), 400

    # verify the signature of message
    if not message.check_signature(partment.appsecret):
        return "<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[签名不正确]]></return_msg></xml>", 400

    order = Order.query.get(message.get_value('out_trade_no'))
    if not order:
        return "<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[out trade no error]]></return_msg></xml>", 400
    elif order.payment_code and order.pay_time:
        return "<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>", 201

    order.payment_code = message.get_value('transaction_id')
    if order.cost+order.delivery_fee == int(message.get_value('cash_fee')):
        order.pay_time = datetime.strptime(message.get_value('time_end'), '%Y%m%d%H%M%S')
        order.status = 2
        #if order.promotion:
        #    order.commit_amount()
        #    order.next_index()

    #db.session.add(order)
    db.session.commit()
    notify_admins.delay(order.code, shoppoint.id)
    notify_customer.delay(order.code, partment.code, shoppoint.id, order.prepay_id)

    return "<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>"
