from time import time
from datetime import datetime
from uuid import uuid4
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.request import Request

from flask import request, jsonify, url_for, json

from ..status import STATUS_NO_REQUIRED_ARGS, STATUS_NO_RESOURCE, STATUS_SOLD_OUT, STATUS_NO_ORDER_STATUS, MESSAGES

from ..models import db
from ..models import Shoppoint, Partment, Order, Promotion, Product, MemberOpenid, Size
from ..models import OrderProduct, OrderAddress
from ..models import PromotionProduct, MemberOpenidAddress, PickupAddress, ProductSize

#from .member import openid_fields
#from .product import product_fields
#from .address import address_fields as pickup_address_fields

from . import api
from .base import UserView, login_required


#order_fields = {
#    'code': fields.String,
#    'index': fields.Integer,
#    'original_cost': fields.Integer,
#    'cost': fields.Integer,
#    'refund': fields.Integer,
#    'delivery_way': fields.Integer,
#    'delivery_fee': fields.Integer,
#    'refund_delivery_fee': fields.Integer,
#    'mode': fields.Integer,
#    'payment': fields.Integer,
#    #'valuecard_allowed': fields.Boolean,
#    'bonus_balance': fields.Integer,
#    'prepay_id': fields.String,
#    'order_time': DateTimeField(dt_format='%Y-%m-%d %H:%M:%S'),
#    'pay_time': DateTimeField(dt_format='%Y-%m-%d %H:%M:%S'),
#    'note': fields.String,
#    'member_openid': fields.Nested(openid_fields),
#    'promotion_id': fields.Integer,
#    'products': fields.List(fields.Nested(order_product_fields)),
#    'address': fields.Nested(order_address_fields),
#    'pickup_address': fields.Nested(pickup_address_fields)
#}

#order_promotion_fields = order_fields
#order_promotion_fields['promotion'] = fields.Nested(promotion_fields)

@api.route('/orders', methods=['GET'])
@login_required
def orders():
    shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
    mo = MemberOpenid.query.filter_by(access_token=request.headers.get('X-ACCESS-TOKEN')).first_or_404()

    status = request.args.get('status')
    if status == 'wait':
        orders = Order.query.filter(Order.shoppoint_id==shop.id, Order.openid==mo.openid, Order.mode==0, Order.payment_code==None, Order.pay_time==None).order_by(Order.code.desc()).all()
    elif status == 'paid':
        orders = Order.query.filter(Order.shoppoint_id==shop.id, Order.openid==mo.openid, Order.mode==0, Order.payment_code!=None, Order.pay_time!=None, Order.finished_time==None).order_by(Order.code.desc()).all()
    elif status == 'finished':
        orders = Order.query.filter(Order.shoppoint_id==shop.id, Order.openid==mo.openid, Order.mode==0, Order.payment_code!=None, Order.pay_time!=None, Order.finished_time!=None).order_by(Order.code.desc()).all()
    else:
        abort(make_response(jsonify(errcode=STATUS_NO_ORDER_STATUS, message=MESSAGES[STATUS_NO_ORDER_STATUS]), 400))

    return jsonify([o.to_json() for o in orders])


class OrderView(UserView):
    def get(self):
        shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
        # customer info
        mo = MemberOpenid.query.filter_by(access_token=request.headers.get('X-ACCESS-TOKEN')).first_or_404()
        order = Order.query.get_or_404(request.args.get('code'))

        return jsonify(order.to_json())

    def post(self):
        shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
        partment = Partment.query.filter_by(shoppoint_id=shop.id, code=request.headers.get('X-PARTMENT')).first_or_404()

        # customer info
        mo = MemberOpenid.query.filter_by(access_token=request.headers.get('X-ACCESS-TOKEN')).first_or_404()
        mo.nickname = request.json.get('nickname')
        mo.avatarUrl = request.json.get('avatarUrl')
        print('put order user: %s', mo)

        #promotion = Promotion.query.get(data['promotion_id'])
        #if promotion:
        #    order = Order.query.filter_by(promotion_id=promotion.id, openid=mo.openid, payment_code=None, pay_time=None).first()
        #    if not order:
        #        order = Order()
        #        order.promotion_id = promotion.id
        #        order.openid = mo.openid
        #        order.member_openid = mo
        #        order.payment = promotion.payment
        #        db.session.add(order)
        #    else:
        #        # delete order address and order products
        #        OrderAddress.query.filter_by(order_code=order.code).delete()
        #        #db.session.delete(order.address)
        #        for p in order.products:
        #            db.session.delete(p) 
        #        order.address = None
        #        order.payment = promotion.payment
        #        db.session.commit()
        #else:
        order = Order()
        order.openid = mo.openid
        order.payment = 14
        order.member_openid = mo
        db.session.add(order)

        order.products = []
        order.code = datetime.now().strftime('%Y%m%d%%04d%H%M%S%f') % shop.id
        order.prepay_id=None
        #if request.json.get('payment') == 2:
        #    mo.name = request.json.get('member_name')
        #    mo.phone = request.json.get('member_phone')
        #order.member_openid = mo
        #order.openid = mo.openid
        #order.payment = request.json.get('payment')
        order.mode = 0
        #order.valuecard_allowed = promotion.valuecard_allowed if promotion else True
        order.note = request.json.get('note')
        order.delivery_way = request.json.get('delivery_way')
        order.shoppoint_id = shop.id
        order.shoppoint = shop
        order.partment_id = partment.id
        order.partment = partment

        # product info
        order.original_cost = 0
        order.cost = 0
        order.delivery_fee = 0 if request.json.get('delivery_way') == 1 else 1000
        soldouts = []
        for p in request.json.get('products'): # TODO if the products code in data['products') are duplicated, a db error will be occurred
            product = Product.query.get_or_404(p['id']) # filter_by(code=p['code']).first_or_404()
            if product.stock < p['want_amount']:
                soldouts.append(product.to_json())
                continue

            op = OrderProduct()
            if p['want_size'] > 0:
                size = Size.query.get_or_404(p['want_size'])
                op.size = size
            print('the product in order: %s', product)
            op.order = order
            op.product = product
            op.amount = p['want_amount']
            product.sold = p['want_amount'] if not product.sold else product.sold+p['want_amount']
            product.stock -= p['want_amount']

            #if promotion:
            #    if p['want_size'] > 0:
            #        pp = PromotionProduct.query.filter_by(promotion_id=promotion.id, product_id=product.id, size_id=size.id).first_or_404()
            #        print('the product in promotion: %s', pp)
            #        ps = ProductSize.query.get_or_404((product.id, size.id))
            #        op.size_id = size.id
            #        op.size = size
            #        op.price = pp.price if pp.price else product.promote_price
            #        op.price += ps.promote_price_plus
            #        order.original_cost += op.amount * (product.price+ps.price_plus)
            #    else:
            #        pp = PromotionProduct.query.filter_by(promotion_id=promotion.id, product_id=product.id).first_or_404()
            #        print('the product in promotion: %s', pp)
            #        op.price = pp.price if pp.price else product.promote_price
            #        order.original_cost += op.amount * product.price
            #else:
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
        if soldouts:
            abort(make_response(jsonify(errcode=STATUS_SOLD_OUT, message=MESSAGES[STATUS_NO_RESOURCE], data=json.dumps(soldouts)), 406))

        # address info
        if order.delivery_way == 1: # 自提模式
            addr = PickupAddress.query.get(request.json.get('pickup_address'))
            if not addr:
                abort(make_response(jsonify(errcode=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE]), 400))
            order.pickup_address = addr
        # user address info
        delivery_addr = MemberOpenidAddress.query.get(request.json.get('delivery_address'))
        oa = OrderAddress()
        oa.name = delivery_addr.contact
        oa.phone = delivery_addr.phone
        oa.province = delivery_addr.province
        oa.city = delivery_addr.city
        oa.district = delivery_addr.district
        oa.address = delivery_addr.address
        order.address = oa
        db.session.add(oa)

        db.session.add(order)
        db.session.commit()

        return jsonify(order.to_json())

api.add_url_rule('/order', view_func=OrderView.as_view('order'))
