from uuid import uuid4
from time import time
from datetime import datetime

from flask import url_for
from flask_restful import marshal_with, marshal
from flask_restful.reqparse import RequestParser

from ..models import db
from ..models import Shoppoint, Partment, MemberOpenid, Order

from ..payment import unified_order, generate_pay_sign
from ..weixin.notify import notify_admins, notify_customer
from ..status import STATUS_NO_VALUE_CARD_INFO, MESSAGES

from .base import BaseResource
from .order import order_fields

class PayResource(BaseResource):
    def post(self, shopcode):
        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        parser = RequestParser()
        parser.add_argument('X-ACCESS-TOKEN', type=str, location='headers', required=True, help='access token must be required')
        parser.add_argument('X-PARTMENT', type=str, location='headers', required=True, help='access token must be required')
        parser.add_argument('X-VERSION', type=str, location='headers')
        parser.add_argument('code', type=str, required=True, help='order code must be required')
        parser.add_argument('payment', type=int)
        parser.add_argument('contact', type=str)
        parser.add_argument('mobile', type=str)
        parser.add_argument('formId', type=str, required=True, help='form submit id must be required')

        data = parser.parse_args()

        partment = Partment.query.filter_by(shoppoint_id=shop.id, code=data['X-PARTMENT']).first_or_404()

        mo = MemberOpenid.query.filter_by(access_token=data['X-ACCESS-TOKEN']).first_or_404()
        order = Order.query.get_or_404(data['code'])
        if order.payment_code is not None and order.pay_time is not None:
            return {
                'payment': order.payment,
                'cost': order.cost,
                'delivery_fee': order.delivery_fee
            }, 200 # TODO already paid formerly

        order.payment = data['payment']
        if order.payment == 2:
            payment_info = {
                'payment': order.payment,
                'cost': order.cost,
                'delivery_fee': order.delivery_fee
            }
            if not mo.name or not mo.phone:
                abort(400, status=STATUS_NO_VALUE_CARD_INFO, message=MESSAGES[STATUS_NO_VALUE_CARD_INFO])
            else:
                order.next_index()
                order.payment_code = order.code
                order.pay_time = datetime.now()
                order.commit_amount()
                notify_admins(order, shop.id)
                notify_customer(order, partment, data['formId'])
        else: # default pay is wechat
            if not order.prepay_id or not order.prepay_id_expires or order.prepay_id_expires < int(time()):
                # invoke the unified order interface of WeChat
                result = unified_order(order, partment.appid, partment.mchid, partment.paysecret, order.openid, url_for('payment.notify', shopcode=shop.code, partcode=partment.code, _external=True), shop.code)
                print('aaaaaaa', result)
                if result['return_code'] == 'SUCCESS' and result['result_code'] == 'SUCCESS':
                    order.prepay_id = result['prepay_id']
                    order.prepay_id_expires = int(time()) + 7200 - 10 # prepay_id的过期时间是2小时
                    #order.next_index()
                    if order.address.delivery_way == 1:
                        if not order.member_openid.phone: # 自提模式下的非会员
                            order.address.name = data['contact']
                            order.address.phone = data['mobile']
                        else:
                            order.address.name = order.member_openid.name
                            order.address.phone = order.member_openid.phone

            # to generate parameters for wx.requestPayment
            print(order.code, order.prepay_id)
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
        # notify_admins(order, partment.get_access_token(), data['formId'])
        payment_info['access_token'] = partment.get_access_token()

        # modify the sold/stock amount of the promotion
        #for pp in order.promotion.products:
        #    for op in orders.products:
        #        if pp.product_id == op.product_id:
        #            pp.sold += op.amount
        #            pp.stock -= op.amount

        return {'order': marshal(order, order_fields), 'payment': payment_info}, 201
