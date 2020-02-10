from datetime import datetime

from flask import request

from flask_restful import abort
from flask_restful import fields, marshal_with
from flask_restful.reqparse import RequestParser

from ..status import STATUS_NO_REQUIRED_ARGS, STATUS_NO_RESOURCE, MESSAGES

from ..models import db
from ..models import Shoppoint, Product, ProductCategory, Member
from ..models import Size, Image, ProductImage, ProductSize

from .base import BaseResource
from .image import image_fields
from .category import category_fields

from .field import WebAllowedField, POSAllowedField, PromoteAllowedField, DateTimeField, InPromoteField 

product_image_fields = {
    'index': fields.Integer,
    'type': fields.Integer,
    'note': fields.String,
    'image': fields.Nested(image_fields)
}

size_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'value': fields.Integer,
    'spec': fields.String,
    'shared_min': fields.Integer,
    'shared_max': fields.Integer,
    'utensils': fields.Integer,
    'pre_order_hours': fields.Integer,
    'banner': fields.String,
    'price_plus': fields.Integer,
    'member_price_plus': fields.Integer,
    'promote_price_plus': fields.Integer,
}

product_size_fields = {
#    'product': field.Nested(product_fields),
    'size': fields.Nested(size_fields),
    'index': fields.Integer,
    'price_plus': fields.Integer,
    'member_price_plus': fields.Integer,
    'promote_price_plus': fields.Integer,
    'stock': fields.Integer,
    'promote_stock': fields.Integer,
    'sold': fields.Integer,
    'member_sold': fields.Integer,
    'promote_sold': fields.Integer,
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
    'in_promote': InPromoteField(attribute='promote_type'),
    'stock': fields.Integer,
    'promote_stock': fields.Integer,
    'summary': fields.String,
    'note': fields.String,
    'web_allowed': WebAllowedField(attribute='show_allowed'),
    'pos_allowed': POSAllowedField(attribute='show_allowed'),
    'promote_type': fields.Integer,
    'promote_allowed': PromoteAllowedField(attribute='show_allowed'),
    'promote_begin_time': DateTimeField(dt_format='%Y-%m-%d %H:%M:%S'),
    'promote_end_time': DateTimeField(dt_format='%Y-%m-%d %H:%M:%S'),
    'is_deleted': fields.Boolean,
    'category': fields.Nested(category_fields),
    'images': fields.List(fields.Nested(product_image_fields)),
    'sizes': fields.List(fields.Nested(product_size_fields))
}

class ProductResource(BaseResource):
    @marshal_with(product_fields)
    def get(self):
        parser = RequestParser()
        parser.add_argument('X-SHOPPOINT', type=str, location='headers', required=True, help='shoppoint code must be required')
        parser.add_argument('code', type=str, location="args", help='product code should be required')
        args = parser.parse_args()
        print('GET request args: %s', args)
        if not args['code']:
            print('no code argument in request')
            abort(400, status=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'product code')

        shop = Shoppoint.query.filter_by(code=args['X-SHOPPOINT']).first_or_404()
        product = Product.query.filter_by(shoppoint_id=shop.id, code=args['code'], is_deleted=False).first()
        if not product:
            print(MESSAGES[STATUS_NO_RESOURCE])
            abort(404, status=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE])

        return product


    @marshal_with(product_fields)
    def post(self):
        is_new_product = False
        parser = RequestParser()
        parser.add_argument('X-SHOPPOINT', type=str, location='headers', required=True, help='shoppoint code must be required')
        parser.add_argument('code', type=str)
        parser.add_argument('name', type=str, required=True, help='product name should be required')
        parser.add_argument('english_name', type=str)
        parser.add_argument('category', type=int)
        parser.add_argument('price', type=int, required=True, help='product price should be required')
        parser.add_argument('member_price', type=int, required=True, help='product member price should be required')
        parser.add_argument('promote_price', type=int, required=True, help='product promote should be required')
        parser.add_argument('web_allowed', type=bool)
        parser.add_argument('promote_allowed', type=bool)
        parser.add_argument('stock', type=int)
        parser.add_argument('promote_stock')
        parser.add_argument('summary', type=str)
        parser.add_argument('note', type=str)
        #parser.add_argument('banner', type=int)
        parser.add_argument('images', type=dict, action="append")
        parser.add_argument('to_remove_images', type=dict, action="append")
        #parser.add_argument('sizes', type=dict, action="append")
        parser.add_argument('sizes', type=dict, action="append")

        data = parser.parse_args()
        print(data)

        shop = Shoppoint.query.filter_by(code=data['X-SHOPPOINT']).first_or_404()
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
        product.show_allowed = 2 # TODO POS allowed is default just now
        if data['web_allowed']:
            product.show_allowed |= 1
        if data['promote_allowed']:
            product.show_allowed |= 4
        #product.web_allowed = data['web_allowed']
        #product.promote_allowed = data['promote_allowed']
        product.summary =  data['summary']
        product.note = data['note']
        product.stock = data['stock']

        product.shoppoint_id = shop.id
        product.shoppoint = shop

        category = ProductCategory.query.get_or_404(data['category'])
        product.category_id = category.id
        product.category = category

        print(data)
        # remove image not needed
        if data['to_remove_images']:
          for photo in data['to_remove_images']:
            image = Image.query.get(photo['id'])
            if image:
              pi = ProductImage.query.get((product.id, image.id))
              if pi.type & photo['type'] == photo['type'] or pi.type == 0:
                if pi.type > photo['type']:
                  pi.type &= ~photo['type']
                else:
                  db.session.delete(pi)

        #photos = [{'code': data['banner'], 'index': 0}]
        #photos.extend(data['images'])
        photo_ids = []
        if data['images']:
          base_banner_index = db.session.query(db.func.max(ProductImage.index)).filter_by(product_id=product.id, type=1).scalar()
          base_detail_index = db.session.query(db.func.max(ProductImage.index)).filter_by(product_id=product.id, type=2).scalar()
          if base_banner_index is None: base_banner_index = 0
          if base_detail_index is None: base_detail_index = 0
          for photo in data['images']:
            photo_ids.append(photo['id'])
            image = Image.query.get_or_404(photo['id'])
            #pi = None
            #if not is_new_product:
            #    pi = ProductImage.query.get((product.id, image.id))
            #if not pi:
            pi = ProductImage.query.get((product.id, image.id))
            if not pi:
              pi = ProductImage()
              pi.type = photo['type']
              db.session.add(pi)
            pi.product_id = product.id
            pi.image_id = image.id
            pi.product = product
            pi.image = image

            if photo['type'] == 1:
              pi.index = photo['index'] + base_banner_index
            elif photo['type'] == 2:
              pi.index = photo['index'] + base_detail_index
            product.images.append(pi)

        # sizes
        if category.extra_info and category.extra_info & 1: # size info
            for ps in product.sizes:
                db.session.delete(ps)
            product.sizes = []
            for s in data['sizes']:
                size = Size.query.get_or_404(s['id'])
                ps = ProductSize()
                ps.product = product
                ps.product_id = product.id
                ps.size = size
                ps.size_id = size.id
                ps.price_plus = size.price_plus if s['price'] - product.price < 0 else s['price'] - product.price
                ps.member_price_plus = size.member_price_plus if s['member_price'] - product.member_price < 0 else s['member_price'] - product.member_price
                ps.promote_price_plus = size.promote_price_plus if s['promote_price'] - product.promote_price < 0 else s['promote_price'] - product.promote_price
                #ps.stock = spec['stock']
                #ps.promote_stock = spec['promote_stock']
                product.sizes.append(ps)

        db.session.commit()

        return product

    @marshal_with(product_fields)
    def delete(self):
        parser = RequestParser()
        parser.add_argument('X-SHOPPOINT', type=str, location='headers', required=True, help='shoppoint code must be required')
        parser.add_argument('code', type=str, help='product code should be required')
        args = parser.parse_args()
        print('GET request args: %s', args)
        if not args['code']:
            print('no code argument in request')
            abort(400, status=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'product code')
        shop = Shoppoint.query.filter_by(code=args['X-SHOPPOINT']).first_or_404()
        product = Product.query.filter_by(shoppoint_id=shop.id, code=args['code'], is_deleted=False).first()
        if not product:
            print(MESSAGES[STATUS_NO_RESOURCE])
            abort(404, status=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE])

        product.is_deleted = True
        # TODO push a task into task queue to delete the related information of the product
        db.session.commit()

        return product

class ProductsResource(BaseResource):
    @marshal_with(product_fields)
    def get(self):
        parser = RequestParser()
        parser.add_argument('X-SHOPPOINT', type=str, location='headers', required=True, help='shoppoint code must be required')
        parser.add_argument('show_type', type=int, location='args', required=True, help='terminal type should be required')
        parser.add_argument('promote_type', type=int, location='args')
        parser.add_argument('sort', type=str, location='args')
        parser.add_argument('limit', type=int, location='args')
        parser.add_argument('category', type=int, location='args')
        parser.add_argument('manage', type=int, location='args')
        data = parser.parse_args()

        print('GET request args: %s', data)
        shop = Shoppoint.query.filter_by(code=data['X-SHOPPOINT']).first_or_404()
        if data['promote_type']:
            now = str(datetime.now())
            products = Product.query.filter(Product.shoppoint_id==shop.id,
                                            Product.promote_type.op('&')(data['promote_type'])>0,
                                            Product.show_allowed.op('&')(data['show_type'])>0,
                                            db.cast(Product.promote_begin_time, db.Time) <= now,
                                            db.cast(Product.promote_end_time, db.Time) >= now,
                                            Product.is_deleted==False).order_by(Product.promote_index)
            if products.count() == 0 and data['promote_type'] == 0x10: # 没有本周推荐，就随机选在一些商品
                products = Product.query.filter(Product.shoppoint_id==shop.id,
                                            Product.show_allowed.op('&')(data['show_type'])>0,
                                            #Product.stock > 0,
                                            Product.is_deleted==False).order_by(Product.promote_index)
        elif data['category']:
            category = ProductCategory.query.get_or_404(data['category'])
            products = Product.query.filter(Product.shoppoint_id==shop.id,
                                            Product.category_id==category.id,
                                            Product.show_allowed.op('&')(data['show_type'])>0,
                                            Product.is_deleted==False)
            if not data['manage']:
                products.filter(Product.stock > 0)

        else:
          if data['sort'] == 'popular':
            products = Product.query.filter(Product.shoppoint_id==shop.id,
                                            Product.stock > 0,
                                            Product.show_allowed.op('&')(data['show_type'])>0,
                                            Product.is_deleted==False)
          else:
            products = Product.query.filter(Product.shoppoint_id==shop.id,
                                            Product.stock > 0,
                                            Product.show_allowed.op('&')(data['show_type'])>0,
                                            Product.is_deleted==False)


        if data['sort'] == 'popular':
          products = products.order_by(Product.sold.desc())
        if data['limit']:
          products = products.limit(data['limit']).all()
        else:
          products = products.all()

        return products

class SizesResource(BaseResource):
    @marshal_with(size_fields)
    def get(self):
        parser = RequestParser()
        parser.add_argument('X-SHOPPOINT', type=str, location='headers', required=True, help='shoppoint code must be required')
        data = parser.parse_args()
        shop = Shoppoint.query.filter_by(code=data['X-SHOPPOINT']).first_or_404()
        sizes = Size.query.filter(Size.shoppoint_id==shop.id).order_by(Size.index.asc()).all()

        return sizes
