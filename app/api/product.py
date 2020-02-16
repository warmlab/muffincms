from datetime import datetime

from flask import request, jsonify, abort

from ..status import STATUS_NO_REQUIRED_ARGS, STATUS_NO_RESOURCE, MESSAGES

from ..models import db
from ..models import Shoppoint, Product, ProductCategory, Member
from ..models import Size, Image, ProductImage, ProductSize

from . import api
from .base import UserView, login_required

@api.route('/categories', methods=['GET'])
@login_required
def category_list():
    shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
    categories = ProductCategory.query.filter_by(shoppoint_id=shop.id).order_by(ProductCategory.index).all()
    if not categories:
        abort(make_response(jsonify(errcode=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE]), 404))

    return jsonify([c.to_json() for c in categories])

@api.route('/products', methods=['GET'])
@login_required
def products():
    print('args', request.args)
    shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
    try:
        show_type = int(request.args['show_type'])
    except Exception as e:
        show_type = 0
    try:
        promote_type = int(request.args['promote_type'])
    except Exception as e:
        promote_type = 0
    if 'promote_type' in request.args:
        now = datetime.now()
        products = Product.query.filter(Product.shoppoint_id==shop.id,
                                        Product.promote_type.op('&')(promote_type)>0,
                                        Product.show_allowed.op('&')(show_type)>0,
                                        Product.promote_begin_time <= now,
                                        Product.promote_end_time >= now,
                                        Product.stock > 0,
                                        Product.is_deleted==False).order_by(Product.promote_index)
        if products.count() == 0 and int(request.args.get('promote_type')) == 0x10: # 没有本周推荐，就随机选一些商品
            products = Product.query.filter(Product.shoppoint_id==shop.id,
                                        Product.show_allowed.op('&')(show_type)>0,
                                        Product.stock > 0,
                                        Product.is_deleted==False).order_by(Product.promote_index)
    elif 'category' in request.args:
        category = ProductCategory.query.get_or_404(request.args.get('category'))
        products = Product.query.filter(Product.shoppoint_id==shop.id,
                                        Product.category_id==category.id,
                                        Product.show_allowed.op('&')(show_type)>0,
                                        Product.is_deleted==False)
        if not request.args.get('manage'):
            products.filter(Product.stock > 0)

    else:
        products = Product.query.filter(Product.shoppoint_id==shop.id,
                                        Product.stock > 0,
                                        Product.show_allowed.op('&')(show_type)>0,
                                        Product.is_deleted==False)


    if request.args.get('sort') == 'popular':
      products = products.order_by(Product.sold.desc())

    if request.args.get('limit'):
      products = products.limit(request.args.get('limit')).all()
    else:
      products = products.all()

    return jsonify([p.to_json() for p in products])

@api.route('/product/sizes', methods=['GET'])
@login_required
def sizes():
    shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
    sizes = Size.query.filter(Size.shoppoint_id==shop.id).order_by(Size.index.asc()).all()

    return jsonify([s.to_json() for s in sizes])

class ProductView(UserView):
    methods = ['GET', 'POST', 'DELETE']

    def get(self):
        if 'code' not in request.args:
            abort(make_response(jsonify(errcode=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'product code'), 400))

        shop = Shoppoint.query.filter_by(code=request.headers['X-SHOPPOINT']).first_or_404()
        product = Product.query.filter_by(shoppoint_id=shop.id, code=request.args['code'], is_deleted=False).first_or_404()
        #if not product:
        #    abort(make_response(jsonify(errcode=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE]), 404))

        r = product.to_json()
        r['category'] = product.category.to_json()
        return jsonify(r)

    def post(self):
        shop = Shoppoint.query.filter_by(code=request.header['X-SHOPPOINT']).first_or_404()
        product = Product.query.filter_by(code=request.json.get('code'), is_deleted=False).first()
        if not product:
            product = Product()
            product.code = datetime.now().strftime('%Y%m%d%H%M%S%f')
            db.session.add(product)

        product.name = request.json.get('name')
        product.price = request.json.get('price')
        product.member_price = request.json.get('member_price')
        product.promote_price = request.json.get('promote_price')
        product.english_name = request.json.get('english_name')
        product.show_allowed = 2 # TODO POS allowed is default just now
        if request.json.get('web_allowed'):
            product.show_allowed |= 1
        if request.json.get('promote_allowed'):
            product.show_allowed |= 4
        #product.web_allowed = request.json.get('web_allowed')
        #product.promote_allowed = request.json.get('promote_allowed')
        product.summary =  request.json.get('summary')
        product.note = request.json.get('note')
        product.stock = request.json.get('stock')

        product.shoppoint_id = shop.id
        product.shoppoint = shop

        category = ProductCategory.query.get_or_404(request.json.get('category'))
        product.category_id = category.id
        product.category = category

        print(data)
        # remove image not needed
        if request.json.get('to_remove_images'):
          for photo in request.json.get('to_remove_images'):
            image = Image.query.get(photo['id'])
            if image:
              pi = ProductImage.query.get((product.id, image.id))
              if pi.type & photo['type'] == photo['type'] or pi.type == 0:
                if pi.type > photo['type']:
                  pi.type &= ~photo['type']
                else:
                  db.session.delete(pi)

        #photos = [{'code': request.json.get('banner'], 'index': 0})
        #photos.extend(request.json.get('images'))
        photo_ids = []
        if request.json.get('images'):
          base_banner_index = db.session.query(db.func.max(ProductImage.index)).filter_by(product_id=product.id, type=1).scalar()
          base_detail_index = db.session.query(db.func.max(ProductImage.index)).filter_by(product_id=product.id, type=2).scalar()
          if base_banner_index is None: base_banner_index = 0
          if base_detail_index is None: base_detail_index = 0
          for photo in request.json.get('images'):
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
            for s in request.json.get('sizes'):
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

        return jsonify(product.to_json()), 201

    def delete(self):
        if 'code' not in request.args:
            abort(make_response(jsonify(errcode=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'product code'), 400))
        shop = Shoppoint.query.filter_by(code=request.headers['X-SHOPPOINT']).first_or_404()
        product = Product.query.filter_by(shoppoint_id=shop.id, code=request.args['code'], is_deleted=False).first()
        if not product:
            abort(make_response(jsonify(errcode=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE]), 404))

        product.is_deleted = True
        # TODO push a task into task queue to delete the related information of the product
        db.session.commit()

        return jsonify(product.to_json())

api.add_url_rule('/product', view_func=ProductView.as_view('product'))
