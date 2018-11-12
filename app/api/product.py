from datetime import datetime

from flask import request

from flask_restful import abort
from flask_restful import fields, marshal_with
from flask_restful.reqparse import RequestParser

from ..logging import logger
from ..status import STATUS_NO_REQUIRED_ARGS, STATUS_NO_RESOURCE, MESSAGES

from ..models import db
from ..models import Shoppoint, Product
from ..models import Image, ProductImage, ProductSpec

from .base import BaseResource
from .image import image_fields
from .category import category_fields

product_image_fields = {
    'index': fields.Integer,
    'note': fields.String,
    'image': fields.Nested(image_fields)
}

product_spec_fields = {
    'id': fields.Integer,
    'name': fields.String
}

product_fields = {
    'id': fields.Integer,
    'code': fields.String,
    'name': fields.String,
    'english_name': fields.String,
    'pinyin': fields.String,
    'price': fields.Integer,
    'member_price': fields.Integer,
    'promote_price': fields.Integer,
    'stock': fields.Integer,
    'promote_stock': fields.Integer,
    'summary': fields.String,
    'note': fields.String,
    'web_allowed': fields.Boolean,
    'pos_allowed': fields.Boolean,
    'promote_allowed': fields.Boolean,
    'is_deleted': fields.Boolean,
    'category': fields.Nested(category_fields),
    'images': fields.List(fields.Nested(product_image_fields)),
    'specs': fields.List(fields.Nested(product_spec_fields))
}

class ProductResource(BaseResource):
    @marshal_with(product_fields)
    def get(self, shopcode):
        parser = RequestParser()
        parser.add_argument('code', type=str, location="args", help='product code should be required')
        args = parser.parse_args()
        logger.debug('GET request args: %s', args)
        if not args['code']:
            logger.error('no code argument in request')
            abort(400, status=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'product code')

        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        product = Product.query.filter_by(shoppoint_id=shop.id, code=args['code'], is_deleted=False).first()
        if not product:
            logger.warning(MESSAGES[STATUS_NO_RESOURCE])
            abort(404, status=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE])

        return product


    @marshal_with(product_fields)
    def post(self, shopcode):
        is_new_product = False
        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        parser = RequestParser()
        parser.add_argument('code', type=str)
        parser.add_argument('name', type=str, required=True, help='product name should be required')
        parser.add_argument('english_name', type=str)
        parser.add_argument('price', type=int, required=True, help='product price should be required')
        parser.add_argument('member_price', type=int, required=True, help='product member price should be required')
        parser.add_argument('promote_price', type=int, required=True, help='product promote should be required')
        parser.add_argument('stock', type=int)
        parser.add_argument('promote_stock')
        parser.add_argument('summary', type=str)
        parser.add_argument('note', type=str)
        #parser.add_argument('banner', type=int)
        parser.add_argument('images', type=dict, action="append")
        parser.add_argument('specs', type=dict, action="append")

        data = parser.parse_args()

        product = Product.query.filter_by(code=data['code'], is_deleted=False).first()
        if not product:
            is_new_product = True
            product = Product()
            product.code = datetime.now().strftime('%Y%m%d%H%M%S%f')
            db.session.add(product)

        product.name = data['name']
        product.price = data['price']
        product.member_price = data['member_price']
        product.promote_price = data['promote_price']
        product.english_name = data['english_name']
        product.promote_allowed = True
        product.summary =  data['summary']
        product.note = data['note']

        product.shoppoint_id = shop.id
        product.shoppoint = shop

        logger.debug(data)

        print(data['images'])
        for i in product.images:
            db.session.delete(i)
        product.images = []

        #photos = [{'code': data['banner'], 'index': 0}]
        #photos.extend(data['images'])
        for photo in data['images']:
            image = Image.query.get_or_404(photo['id'])
            #pi = None
            #if not is_new_product:
            #    pi = ProductImage.query.get((product.id, image.id))
            #if not pi:
            pi = ProductImage()
            pi.product_id = product.id
            pi.image_id = image.id
            pi.product = product
            pi.image = image
            db.session.add(pi)

            pi.index = photo['index']
            product.images.append(pi)

        """
        #specifications
        for s in product.specs:
            db.session.delete(s)
        product.specs = []
        for spec in data['specs']:
            ps = ProductSpec()
            ps.product = product
            #ps.product_id = product.id
            ps.name = spec['name']
            ps.price_plus = spec['price_plus']
            ps.promote_price_plus = spec['promote_price_plus']
            ps.stock = spec['stock']
            ps.promote_stock = spec['promote_stock']
            product.specs.append(ps)
        """

        db.session.commit()

        return product

    @marshal_with(product_fields)
    def delete(self, shopcode):
        parser = RequestParser()
        parser.add_argument('code', type=str, help='product code should be required')
        args = parser.parse_args(strict=True)
        logger.debug('GET request args: %s', args)
        if not args['code']:
            logger.error('no code argument in request')
            abort(400, status=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'product code')
        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        product = Product.query.filter_by(shoppoint_id=shop.id, code=args['code'], is_deleted=False).first()
        if not product:
            logger.warning(MESSAGES[STATUS_NO_RESOURCE])
            abort(404, status=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE])

        product.is_deleted = True
        # TODO push a task into task queue to delete the related information of the product
        db.session.commit()

        return product

class ProductsResource(BaseResource):
    @marshal_with(product_fields)
    def get(self, shopcode):
        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        products = Product.query.filter_by(shoppoint_id=shop.id, promote_allowed=True, is_deleted=False).all()

        return products
