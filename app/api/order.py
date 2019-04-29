from time import time
from datetime import datetime
from uuid import uuid4
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.request import Request

from flask import request, jsonify, url_for

from flask_restful import abort
from flask_restful import fields, marshal_with
from flask_restful.reqparse import RequestParser

from ..logging import logger
from ..status import STATUS_NO_REQUIRED_ARGS, STATUS_NO_RESOURCE, STATUS_NO_ORDER_STATUS, MESSAGES

from ..models import db
from ..models import Shoppoint, Partment, Order, Promotion, Product, MemberOpenid, Size
from ..models import OrderProduct, OrderAddress
from ..models import PromotionProduct, MemberOpenidAddress, PickupAddress, ProductSize

from .member import openid_fields
from .product import product_fields

from .base import BaseResource
from .field import DateTimeField


order_address_fields = {
    'name': fields.String,
    'phone': fields.String,
    'address': fields.String,
    'delivery_way': fields.Integer,
    'delivery_time': fields.DateTime,
}

order_product_fields = {
    'price': fields.Integer,
    'amount': fields.Integer,
    'refund': fields.Integer,
    'product': fields.Nested(product_fields)
}

#payment_fields = {
#    'appId': fields.String,
#    'timeStamp': fields.String,
#    'nonceStr': fields.String,
#    'package': fields.String,
#    'signType': fields.String
#}

order_fields = {
    'code': fields.String,
    'index': fields.Integer,
    'original_cost': fields.Integer,
    'cost': fields.Integer,
    'refund': fields.Integer,
    'delivery_fee': fields.Integer,
    'refund_delivery_fee': fields.Integer,
    'mode': fields.Integer,
    'payment': fields.Integer,
    #'valuecard_allowed': fields.Boolean,
    'bonus_balance': fields.Integer,
    'prepay_id': fields.String,
    'order_time': DateTimeField(dt_format='%Y-%m-%d %H:%M:%S'),
    'pay_time': DateTimeField(dt_format='%Y-%m-%d %H:%M:%S'),
    'note': fields.String,
    'member_openid': fields.Nested(openid_fields),
    'promotion_id': fields.Integer,
    'products': fields.List(fields.Nested(order_product_fields)),
    'address': fields.Nested(order_address_fields),
}

#order_promotion_fields = order_fields
#order_promotion_fields['promotion'] = fields.Nested(promotion_fields)

class OrderResource(BaseResource):
    @marshal_with(order_fields)
    def get(self, shopcode):
        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        parser = RequestParser()
        parser.add_argument('X-ACCESS-TOKEN', type=str, location='headers', required=True, help='access token must be required')
        parser.add_argument('X-VERSION', type=str, location='headers')
        parser.add_argument('code', type=str, location='args', required=True, help='order code must be required')

        data = parser.parse_args()
        logger.debug('get order parameter: %s', data)

        # customer info
        mo = MemberOpenid.query.filter_by(access_token=data['X-ACCESS-TOKEN']).first_or_404()

        order = Order.query.get_or_404(data['code'])

        return order

    @marshal_with(order_fields)
    def post(self, shopcode):
        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        parser = RequestParser()
        parser.add_argument('X-ACCESS-TOKEN', type=str, location='headers', required=True, help='access token must be required')
        parser.add_argument('X-PARTMENT', type=str, location='headers', required=True, help='access token must be required')
        parser.add_argument('X-VERSION', type=str, location='headers')
        parser.add_argument('promotion_id', type=int, required=True, help='promotion id must be required')
        parser.add_argument('products', type=dict, action='append', required=True, help='product information must be required')
        parser.add_argument('delivery_way', type=int, required=True, help='delivery way must be required')
        parser.add_argument('address', type=int, required=True, help='address must be required')

        parser.add_argument('nickname', type=str)
        parser.add_argument('avatarUrl', type=str)
        parser.add_argument('note', type=str)

        data = parser.parse_args()

        print(data['products'])

        partment = Partment.query.filter_by(shoppoint_id=shop.id, code=data['X-PARTMENT']).first_or_404()

        # customer info
        mo = MemberOpenid.query.filter_by(access_token=data['X-ACCESS-TOKEN']).first_or_404()
        mo.nickname = data['nickname']
        mo.avatarUrl = data['avatarUrl']
        logger.debug('put order user: %s', mo)

        promotion = Promotion.query.get(data['promotion_id'])
        if promotion:
            order = Order.query.filter_by(promotion_id=promotion.id, openid=mo.openid, payment_code=None, pay_time=None).first()
            if not order:
                order = Order()
                order.promotion_id = promotion.id
                order.openid = mo.openid
                order.member_openid = mo
                order.payment = promotion.payment
                db.session.add(order)
            else:
                # delete order address and order products
                OrderAddress.query.filter_by(order_code=order.code).delete()
                #db.session.delete(order.address)
                for p in order.products:
                    db.session.delete(p) 
                order.address = None
                order.payment = promotion.payment
                db.session.commit()
        else:
            order = Order()
            order.openid = mo.openid
            order.payment = 14
            order.member_openid = mo
            db.session.add(order)

        order.products = []
        order.code = datetime.now().strftime('%Y%m%d%%04d%H%M%S%f') % shop.id
        order.prepay_id=None
        #if data['payment'] == 2:
        #    mo.name = data['member_name']
        #    mo.phone = data['member_phone']
        #order.member_openid = mo
        #order.openid = mo.openid
        #order.payment = data['payment']
        order.mode = 0
        #order.valuecard_allowed = promotion.valuecard_allowed if promotion else True
        order.note = data['note']
        order.shoppoint_id = shop.id
        order.shoppoint = shop
        order.partment_id = partment.id
        order.partment = partment

        # product info
        order.original_cost = 0
        order.cost = 0
        order.delivery_fee = 0 if data['delivery_way'] == 1 else 1000
        for p in data['products']: # TODO if the products code in data['products'] are duplicated, a db error will be occurred
            product = Product.query.get_or_404(p['id']) # filter_by(code=p['code']).first_or_404()
            op = OrderProduct()
            if p['want_size'] > 0:
                size = Size.query.get_or_404(p['want_size'])
                op.size = size
            logger.debug('the product in order: %s', product)
            op.order = order
            op.product = product
            op.amount = p['want_amount']

            if promotion:
                if p['want_size'] > 0:
                    pp = PromotionProduct.query.filter_by(promotion_id=promotion.id, product_id=product.id, size_id=size.id).first_or_404()
                    logger.debug('the product in promotion: %s', pp)
                    ps = ProductSize.query.get_or_404((product.id, size.id))
                    op.size_id = size.id
                    op.size = size
                    op.price = pp.price if pp.price else product.promote_price
                    op.price += ps.promote_price_plus
                    order.original_cost += op.amount * (product.price+ps.price_plus)
                else:
                    pp = PromotionProduct.query.filter_by(promotion_id=promotion.id, product_id=product.id).first_or_404()
                    logger.debug('the product in promotion: %s', pp)
                    op.price = pp.price if pp.price else product.promote_price
                    order.original_cost += op.amount * product.price
            else:
                pp = None
                if p['want_size']:
                    ps = ProductSize.query.get_or_404((product.id, size.id))
                    op.price = product.price + ps.price_plus
                else:
                    op.price = product.price
                order.original_cost += op.amount * op.price

            #pp.sold += op.amount
            #pp.stock -= op.amount

            #product.promote_sold = op.amount if not product.promote_sold else product.promote_sold + op.amount
            #product.sold = op.amount if not product.sold else product.sold + op.amount
            #product.promote_stock = -op.amount if not product.promote_stock else product.promote_stock - op.amount
            #product.stock = -op.amount if not product.stock else product.stock - op.amount

            order.cost += op.price * op.amount
            order.products.append(op)
            db.session.add(op)

        # address info
        oa = OrderAddress()
        oa.delivery_way = data['delivery_way']
        if oa.delivery_way == 1: # 自提模式
            addr = PickupAddress.query.get(data['address'])
        else: # 快递模式
            addr = MemberOpenidAddress.query.get(data['address'])
        oa.name = addr.contact
        oa.phone = addr.phone
        oa.address = addr.address
        order.address = oa
        db.session.add(oa)

        db.session.add(order)
        db.session.commit()

        return order

class OrdersResource(BaseResource):
    @marshal_with(order_fields)
    def get(self, shopcode):
        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        parser = RequestParser()
        parser.add_argument('status', type=str, location='args', required=True, help='order status must be required')
        parser.add_argument('X-ACCESS-TOKEN', type=str, location='headers', required=True, help='access token must be required')
        data = parser.parse_args()

        mo = MemberOpenid.query.filter_by(access_token=data['X-ACCESS-TOKEN']).first()

        status = data['status']
        if status == 'wait':
            orders = Order.query.filter(Order.shoppoint_id==shop.id, Order.openid==mo.openid, Order.mode==0, Order.payment_code==None, Order.pay_time==None).order_by(Order.code.desc()).all()
        elif status == 'paid':
            orders = Order.query.filter(Order.shoppoint_id==shop.id, Order.openid==mo.openid, Order.mode==0, Order.payment_code!=None, Order.pay_time!=None, Order.finished_time==None).order_by(Order.code.desc()).all()
        elif status == 'finished':
            orders = Order.query.filter(Order.shoppoint_id==shop.id, Order.openid==mo.openid, Order.mode==0, Order.payment_code!=None, Order.pay_time!=None, Order.finished_time!=None).order_by(Order.code.desc()).all()
        else:
            abort(400, status=STATUS_NO_ORDER_STATUS, message=MESSAGES[STATUS_NO_ORDER_STATUS])

        return orders
