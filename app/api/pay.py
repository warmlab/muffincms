from uuid import uuid4
from time import time
from datetime import datetime

from flask import url_for, abort, jsonify, request


from ..models import db
from ..models import Shoppoint, Partment, MemberOpenid, Order

from ..payment import unified_order, generate_pay_sign
#from ..weixin.notify import notify_admins, notify_customer
from ..status import STATUS_NO_VALUE_CARD_INFO, MESSAGES

from . import api
from .base import UserView, login_required
#from .order import order_fields

from server import notify_admins, notify_customer

@api.route('/pay', methods=['POST'])
@login_required
def pay():
    shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
    partment = Partment.query.filter_by(shoppoint_id=shop.id, code=request.headers.get('X-PARTMENT')).first_or_404()

    mo = MemberOpenid.query.filter_by(access_token=request.headers.get('X-ACCESS-TOKEN')).first_or_404()
    order = Order.query.get_or_404(request.json.get('code'))
    if order.payment_code is not None and order.pay_time is not None:
        return {
            'payment': order.payment,
            'cost': order.cost,
            'delivery_fee': order.delivery_fee
        }, 200 # TODO already paid formerly

    order.payment = request.json.get('payment')

    # TODO for op in order.products:
    #    if not (op.product.payment & 2): # not support value card payment
    #        weixin_pay += op.price * op.amount

    if order.payment == 2:
        payment_info = {
            'payment': order.payment,
            'cost': order.cost,
            'delivery_fee': order.delivery_fee
        }
        if not mo.name or not mo.phone:
            abort(make_response(jsonify(errcode=STATUS_NO_VALUE_CARD_INFO, message=MESSAGES[STATUS_NO_VALUE_CARD_INFO]), 400))
        else:
            order.next_index()
            order.payment_code = order.code
            order.pay_time = datetime.now()
            order.status = 2 # paid
            order.commit_amount()
            db.session.commit()
            notify_admins.delay(order.code, shop.id)
            notify_customer.delay(order.code, partment.code, shop.id, request.json.get('formId'))
    else: # default pay is wechat
        if not order.prepay_id or not order.prepay_id_expires or order.prepay_id_expires < int(time()):
            # invoke the unified order interface of WeChat
            result = unified_order(order, partment.appid, partment.mchid, partment.paysecret, order.openid, url_for('payment.notify', shopcode=shop.code, partcode=partment.code, _external=True), shop.code)
            if result['return_code'] == 'SUCCESS' and result['result_code'] == 'SUCCESS':
                order.prepay_id = result['prepay_id']
                order.prepay_id_expires = int(time()) + 7200 - 10 # prepay_id的过期时间是2小时
                #order.next_index()
                #if order.delivery_way == 1:
                #    if not order.member_openid.phone: # 自提模式下的非会员
                #        order.address.name = request.json.get('contact')
                #        order.address.phone = request.json.get('mobile')
                #    else:
                #        order.address.name = order.member_openid.name
                #        order.address.phone = order.member_openid.phone

        # to generate parameters for wx.requestPayment
        print("The order was paid by[", order.openid, "], and order info: ", order.code, order.prepay_id)
        payment_info = {
            'appId': partment.appid,
            'timeStamp': str(int(time())),
            'nonceStr': uuid4().hex,
            'package': '='.join(['prepay_id', order.prepay_id]),
            'signType': 'MD5',
        }
        payment_info['paySign'], signType = generate_pay_sign(payment_info, partment.paysecret)
        payment_info['payment'] = order.payment
        payment_info['cost'] = order.cost
    # TODO cannot notify in here
    # notify_admins(order, partment.get_access_token(), request.json.get('formId'))
    payment_info['access_token'] = partment.get_access_token()

    # modify the sold/stock amount of the promotion
    #for pp in order.promotion.products:
    #    for op in orders.products:
    #        if pp.product_id == op.product_id:
    #            pp.sold += op.amount
    #            pp.stock -= op.amount

    return jsonify({'order': order.to_json(), 'payment': payment_info}), 201
