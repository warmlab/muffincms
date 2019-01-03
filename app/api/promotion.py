from datetime import datetime

from flask import request, jsonify, render_template

from flask_restful import abort
from flask_restful import fields, marshal_with
from flask_restful.reqparse import RequestParser

from flask_mail import Message

from ..logging import logger
from ..status import STATUS_NO_REQUIRED_ARGS, STATUS_NO_RESOURCE, MESSAGES

from ..models import db
from ..models import Promotion, PromotionProduct, PromotionAddress
from ..models import Product, Shoppoint, PickupAddress
from ..models import Order, Size

from .product import product_fields
from .address import address_fields
from .order import order_fields
from .base import BaseResource
from .field import DateTimeField

from .. import mail


promotion_product_fields = {
    'price': fields.Integer,
    'sold': fields.Integer,
    'stock': fields.Integer,
    'product': fields.Nested(product_fields),
    'is_deleted': fields.Boolean
}

promotion_address_fields = {
    'address': fields.Nested(address_fields)
}

promotion_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'binding': fields.Boolean,
    'paymode': fields.Integer,
    'valuecard_allowed': fields.Boolean,
    'delivery_way': fields.Integer,
    'delivery_fee': fields.Integer,
    'last_order_time': DateTimeField('%Y-%m-%d %H:%M'),
    'from_time': DateTimeField('%Y-%m-%d %H:%M'),
    'to_time': DateTimeField('%Y-%m-%d %H:%M'),
    'publish_time': DateTimeField('%Y-%m-%d %H:%M'),
    'note': fields.String,

    'products': fields.List(fields.Nested(promotion_product_fields)),
    'addresses': fields.List(fields.Nested(promotion_address_fields)),
    #'orders': fields.List(fields.Nested(order_fields)) # 参团数量多的话，直接影响页面加载速度
}

class PromotionResource(BaseResource):
#class PromotionResource(Resource):
    @marshal_with(promotion_fields)
    def get(self, shopcode):
        parser = RequestParser()
        parser.add_argument('id', type=int, required=True, location='args', help='promotion id should be required')
        # parser.add_argument('date', type=lambda x: datetime.strptime(x,'%Y-%m-%dT%H:%M:%S'))
        args = parser.parse_args()
        logger.debug('GET request args: %s', args)
        if not args['id']:
            logger.error('no promotion id argument in request')
            abort(400, status=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'promotion id')

        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        promotion = Promotion.query.get(args['id'])
        if promotion and promotion.shoppoint_id == shop.id and not promotion.is_deleted:
            return promotion
        else:
            logger.warning(MESSAGES[STATUS_NO_RESOURCE])
            abort(404, status=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE])

    @marshal_with(promotion_fields)
    def post(self, shopcode):
        is_new_promotion = False
        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        #request.get_json(force=True)
        parser = RequestParser()
        #parser.add_argument('X-ACCESS-TOKEN', type=str, location='headers', required=True, help='access token must be required')
        #parser.add_argument('X-VERSION', type=str, location='headers')
        parser.add_argument('id', type=int)
        parser.add_argument('name', type=str)
        parser.add_argument('binding', type=bool)
        parser.add_argument('valuecard_allowed', type=bool)
        parser.add_argument('paymode', type=int)
        parser.add_argument('delivery_fee', type=int)
        parser.add_argument('delivery_way', type=int)
        parser.add_argument('last_order_date', type=str, required=True, help='last order date should be required')
        parser.add_argument('last_order_time', type=str, required=True, help='last order time should be required')
        parser.add_argument('from_date', type=str, required=True, help='from date should be required')
        parser.add_argument('from_time', type=str, required=True, help='from time should be required')
        parser.add_argument('to_date', type=str, required=True, help='end date should be required')
        parser.add_argument('to_time', type=str, required=True, help='end time should be required')
        parser.add_argument('publish', type=int) # 发布标志
        parser.add_argument('publish_date', type=str)
        parser.add_argument('publish_time', type=str)
        parser.add_argument('note', type=str)
        parser.add_argument('products', type=dict, action='append', required=True, help='product information should be required')
        parser.add_argument('addresses', type=int, action='append', required=True, help='pickup address information should be required')

        data = parser.parse_args()

        logger.debug('promotion post data: %s', data)

        if data['id']:
            promotion = Promotion.query.get(data['id'])
            if not promotion:
                is_new_promotion = True
                promotion = Promotion()
                db.session.add(promotion)
        else:
            is_new_promotion = True
            promotion = Promotion()
            db.session.add(promotion)

        promotion.name = data['name']
        promotion.binding = data['binding']
        promotion.paymode = data['paymode']
        promotion.valuecard_allowed = data['valuecard_allowed']
        promotion.delivery_way = data['delivery_way']
        promotion.delivery_fee = 0 if promotion.delivery_way == 1 else data['delivery_fee']
        promotion.last_order_time = datetime.strptime(' '.join([data['last_order_date'], data['last_order_time']]), '%Y-%m-%d %H:%M')
        promotion.from_time = datetime.strptime(' '.join([data['from_date'], data['from_time']]), '%Y-%m-%d %H:%M')
        promotion.to_time = datetime.strptime(' '.join([data['to_date'], data['to_time']]), '%Y-%m-%d %H:%M')
        promotion.shoppoint_id = shop.id
        promotion.shoppoint = shop
        promotion.is_deleted = False
        promotion.note = data['note']
        if data['publish'] == 0:
            promotion.publish_time = datetime.now()
        else:
            promotion.publish_time = datetime.strptime(' '.join([data['publish_date'], data['publish_time']]), '%Y-%m-%d %H:%M')
        if promotion.products:
            PromotionProduct.query.filter_by(promotion_id=promotion.id).update({'is_deleted': True})
        # get max index from db
        max_index = db.session.query(db.func.max(PromotionProduct.index)).filter_by(promotion_id=promotion.id).scalar()
        if max_index is None: max_index = 0
        for index, p in enumerate(data['products']):
            product = Product.query.filter_by(code=p['code']).first_or_404()
            if product.category and product.category.extra_info and product.category.extra_info & 1 == 1 and 'size' in p:
                size = Size.query.get_or_404(p['size'])
                pp = PromotionProduct.query.filter_by(promotion_id=promotion.id, product_id=product.id, size_id=size.id).first()
                if not pp:
                    pp = PromotionProduct()
                    pp.size = size
                    pp.size_id = size.id
            else:
                pp = PromotionProduct.query.filter_by(promotion_id=promotion.id, product_id=product.id).first()
                if not pp:
                    pp = PromotionProduct()

            pp.product = product
            pp.promotion = promotion
            promotion.products.append(pp)
            #db.session.add(pp)
            pp.index = max_index + index + 1
            if 'size' in p and p['size'] > 0:
                pp.size_id = pp.size.id
            pp.is_deleted = False
            if p['price']:
                pp.price = p['price']
            else:
                pp.price = product.promote_price
            if p['stock']:
                pp.stock = p['stock']
            else:
                pp.stock = product.promote_stock

        #promotion.addresses = []
        to_delete_addresses = [pa.address_id for pa in promotion.addresses]
        for aid in data['addresses']:
            addr = PickupAddress.query.get_or_404(aid)
            pa = PromotionAddress.query.get((promotion.id, addr.id))
            if not pa:
                pa = PromotionAddress()
                pa.promotion_id = promotion.id
                pa.promotion = promotion
                pa.address = addr
                #db.session.add(pa)
                promotion.addresses.append(pa)
            if aid in to_delete_addresses:
                to_delete_addresses.remove(aid)
        for aid in to_delete_addresses:
            pa = PromotionAddress.query.get((promotion.id, aid))
            if pa:
                promotion.addresses.remove(pa)
                db.session.delete(pa)

        db.session.commit()

        return promotion, 201

    @marshal_with(promotion_fields)
    def delete(self, shopcode):
        parser = RequestParser()
        parser.add_argument('id', type=int, required=True, help='promotion id should be required')
        # parser.add_argument('date', type=lambda x: datetime.strptime(x,'%Y-%m-%dT%H:%M:%S'))
        args = parser.parse_args()
        logger.debug('GET request args: %s', args)
        if not args['id']:
            logger.error('no promotion id argument in request')
            abort(400, status=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'promotion id')

        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        promotion = Promotion.query.get(args['id'])
        if promotion and promotion.shoppoint_id == shop.id:
            promotion.is_deleted = True
            return {}, 201
        else:
            logger.warning(MESSAGES[STATUS_NO_RESOURCE])
            abort(404, status=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE])

    # TODO used for sending emails
    def put(self, shopcode):
        parser = RequestParser()
        parser.add_argument('id', type=int, required=True, help='promotion id should be required')
        # parser.add_argument('date', type=lambda x: datetime.strptime(x,'%Y-%m-%dT%H:%M:%S'))
        args = parser.parse_args()
        logger.debug('GET request args: %s', args)

        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        promotion = Promotion.query.get(args['id'])
        if not promotion or promotion.shoppoint_id != shop.id:
            logger.warning(MESSAGES[STATUS_NO_RESOURCE])
            abort(404, status=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE])

        orders = Order.query.filter(Order.promotion_id==promotion.id, Order.index>0).order_by(Order.index).all()

        msg = Message('小麦芬团购-' + promotion.name, recipients=["bzip@qq.com", "nzip@qq.com"])
        msg.html = render_template('mail/promotion_orders.html', orders=orders, promotion=promotion)

        with mail.connect() as conn:
            conn.send(msg)

        return jsonify({})


class PromotionsResource(BaseResource):
    @marshal_with(promotion_fields)
    def get(self, shopcode):
        parser = RequestParser()
        parser.add_argument('manage', type=bool, location='args')
        # parser.add_argument('date', type=lambda x: datetime.strptime(x,'%Y-%m-%dT%H:%M:%S'))
        args = parser.parse_args()
        logger.debug('GET request args: %s', args)
        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        if args['manage']:
            promotions = Promotion.query.filter_by(shoppoint_id=shop.id, is_deleted=False).order_by(Promotion.last_order_time.desc()).all()
        else:
            promotions = Promotion.query.filter(Promotion.shoppoint_id==shop.id, Promotion.is_deleted==False, Promotion.to_time>datetime.now()).order_by(Promotion.last_order_time.desc()).all()

        return promotions

class PromotionOrdersResource(BaseResource):
    @marshal_with(order_fields)
    def get(self, shopcode):
        parser = RequestParser()
        parser.add_argument('id', type=int, location='args', required=True, help='promotion id should be required')
        # parser.add_argument('date', type=lambda x: datetime.strptime(x,'%Y-%m-%dT%H:%M:%S'))
        args = parser.parse_args()
        logger.debug('GET request args: %s', args)

        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        orders = Order.query.filter(Order.shoppoint_id==shop.id, Order.promotion_id==args['id'], Order.index>0).order_by(Order.index.desc()).all()

        return orders
