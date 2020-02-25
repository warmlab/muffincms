from datetime import datetime

from flask import request, jsonify, render_template, abort, make_response

from flask_mail import Message

from ..status import STATUS_NO_REQUIRED_ARGS, STATUS_NO_RESOURCE, MESSAGES

from ..models import db
from ..models import Promotion, PromotionProduct
from ..models import Product, Shoppoint, PickupAddress
from ..models import Order, Size

from . import api
from .base import UserView, login_required

from .. import mail


@api.route('/promotions', methods=['GET'])
@login_required
def promotions():
    shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
    if 'limit' not in request.args:
        limit = 10
    else:
        limit = request.args.get('limit')

    if 'manage' in request.args:
        promotions = Promotion.query.filter_by(shoppoint_id=shop.id, is_deleted=False).order_by(Promotion.to_time.desc()).limit(limit).all()
    else:
        promotions = Promotion.query.filter(Promotion.shoppoint_id==shop.id, Promotion.is_deleted==False, Promotion.to_time>datetime.now()).order_by(Promotion.to_time.desc()).all()

    return jsonify([p.to_json() for p in promotions])


@api.route('/promotion/products', methods=['GET'])
@login_required
def promotion_products():
    shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
    promotions = PromotionProduct.query.filter(PromotionProduct.shoppoint_id==shop.id, PromotionProduct.is_deleted==False,
                                                  ).order_by(Promotion.to_time.desc()).limit(limit).all()
    #else:
    #    promotions = Promotion.query.filter(Promotion.shoppoint_id==shop.id, Promotion.is_deleted==False, Promotion.to_time>datetime.now()).order_by(Promotion.to_time.desc()).all()

    return jsonify([p.to_json() for p in promotions])

@api.route('/promotion/orders', methods=['GET'])
@login_required
def promotion_orders():
    shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
    try:
        promotion_id = int(request.args.get('id'))
    except Exception as e:
        promotion_id = 0
    orders = Order.query.filter(Order.shoppoint_id==shop.id, Order.promotion_id==promotion_id, Order.index>0).order_by(Order.index.desc()).all()

    return jsonify([o.to_json() for o in orders])


class PromotionView(UserView):
    methods = ['GET', 'POST', 'DELETE', 'PUT']

    def get(self):
        if 'id' not in request.args:
            abort(make_response(jsonify(errcode=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'promotion id'), 400))

        shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()

        try:
            promotion_id = int(request.args.get('id'))
        except Exception as e:
            promotion_id = 0

        promotion = Promotion.query.get(promotion_id)
        if promotion and promotion.shoppoint_id == shop.id and not promotion.is_deleted:
            return jsonify(promotion.to_json())
        else:
            print(MESSAGES[STATUS_NO_RESOURCE])
            abort(make_response(jsonify(errcode=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE]), 404))

    def post(self):
        shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()

        print('request.json', request.json)
        if request.json.get('id'):
            try:
                promotion_id = int(request.json.get('id'))
            except Exception as e:
                promotion_id = 0
            promotion = Promotion.query.get(promotion_id)
            if not promotion:
                promotion = Promotion()
                db.session.add(promotion)
        else:
            promotion = Promotion()
            db.session.add(promotion)

        #promotion.name = request.json.get('name')
        #promotion.binding = request.json.get('binding')
        #promotion.paymode = request.json.get('paymode')
        #promotion.payment = request.json.get('payment')
        #promotion.valuecard_allowed = request.json.get('valuecard_allowed')
        #promotion.delivery_way = request.json.get('delivery_way')
        #promotion.delivery_fee = 0 if promotion.delivery_way == 1 else request.json.get('delivery_fee')
        #promotion.last_order_time = datetime.strptime(' '.join([request.json.get('last_order_date'], data['last_order_time'])), '%Y-%m-%d %H:%M')
        promotion.type = int(request.json.get('promote_type'))
        promotion.from_time = datetime.strptime(' '.join([request.json.get('from_date'), request.json.get('from_time')]), '%Y-%m-%d %H:%M')
        promotion.to_time = datetime.strptime(' '.join([request.json.get('to_date'), request.json.get('to_time')]), '%Y-%m-%d %H:%M')
        promotion.shoppoint_id = shop.id
        promotion.shoppoint = shop
        promotion.is_deleted = False
        promotion.note = request.json.get('note')
        #if request.json.get('publish') == 0:
        #    promotion.publish_time = datetime.now()
        #else:
        #    promotion.publish_time = datetime.strptime(' '.join([request.json.get('publish_date'], data['publish_time'])), '%Y-%m-%d %H:%M')
        if promotion.products:
            PromotionProduct.query.filter_by(promotion_id=promotion.id).update({'is_deleted': True})
        # get max index from db
        max_index = db.session.query(db.func.max(PromotionProduct.index)).filter_by(promotion_id=promotion.id).scalar()
        if max_index is None: max_index = 0
        if request.json.get('to_remove'):
          for p in request.json.get('to_remove'):
            product = Product.query.get_or_404(p['id'])
            product.promote_type = product.promote_type & ~promotion.type
            if promotion.type == 4: # 特价
                product.promote_begin_time = None
                product.promote_end_time = None
            pp = PromotionProduct.query.filter_by(promotion_id=promotion.id, product_id=product.id).first()
            if pp:
              pp.is_deleted = True
        for index, p in enumerate(request.json.get('products')):
            product = Product.query.get_or_404(p['id'])
            if not product.promote_type:
                product.promote_type = request.json.get('promote_type')
            else:
                product.promote_type |= request.json.get('promote_type')
            product.promote_begin_time = datetime.strptime(' '.join([request.json.get('from_date'), request.json.get('from_time')]), '%Y-%m-%d %H:%M')
            product.promote_end_time = datetime.strptime(' '.join([request.json.get('to_date'), request.json.get('to_time')]), '%Y-%m-%d %H:%M')
            if product.category and product.category.extra_info and product.category.extra_info & 1 == 1:
                size = Size.query.get_or_404(p['size'])
                pp = PromotionProduct.query.filter_by(promotion_id=promotion.id, product_id=product.id, size_id=size.id).first()
                if not pp:
                    pp = PromotionProduct()
                    pp.size = size
                    pp.size_id = size.id
                else:
                  pp.is_deleted = False
            else:
                pp = PromotionProduct.query.filter_by(promotion_id=promotion.id, product_id=product.id).first()
                if not pp:
                    pp = PromotionProduct()
                else:
                  pp.is_deleted = False

            pp.product = product
            pp.promotion = promotion
            promotion.products.append(pp)
            #db.session.add(pp)
            pp.index = max_index + index + 1
            #if p['size'] > 0:
            #    pp.size_id = pp.size.id
            pp.is_deleted = False
            #if p['price']:
            #    pp.price = p['price']
            #else:
            pp.price = product.promote_price + (size.promote_price_plus if p['size'] else 0)
            if p['stock']:
                pp.stock = p['stock']
                product.stock = p['stock']
            else:
                product.promote_stock = p['stock']
                pp.stock = product.promote_stock

        #promotion.addresses = []
        #to_delete_addresses = [pa.address_id for pa in promotion.addresses]
        #for aid in request.json.get('addresses'):
        #    addr = PickupAddress.query.get_or_404(aid)
        #    pa = PromotionAddress.query.get((promotion.id, addr.id))
        #    if not pa:
        #        pa = PromotionAddress()
        #        pa.promotion_id = promotion.id
        #        pa.promotion = promotion
        #        pa.address = addr
        #        #db.session.add(pa)
        #        promotion.addresses.append(pa)
        #    if aid in to_delete_addresses:
        #        to_delete_addresses.remove(aid)
        #for aid in to_delete_addresses:
        #    pa = PromotionAddress.query.get((promotion.id, aid))
        #    if pa:
        #        promotion.addresses.remove(pa)
        #        db.session.delete(pa)

        db.session.commit()

        return jsonify(promotion.to_json()), 201

    def delete(self):
        if 'id' not in request.args:
            abort(make_response(jsonify(errcode=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'promotion id'), 400))

        shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
        promotion = Promotion.query.get(request.args.get('id'))
        if promotion and promotion.shoppoint_id == shop.id:
            promotion.is_deleted = True
            return jsonify({}), 201
        else:
            print(MESSAGES[STATUS_NO_RESOURCE])
            abort(make_response(jsonify(errcode=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE]), 404))

    # TODO used for sending emails
    def put(self):
        shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
        promotion = Promotion.query.get(request.json.get('id'))
        if not promotion or promotion.shoppoint_id != shop.id:
            print(MESSAGES[STATUS_NO_RESOURCE])
            abort(make_response(jsonify(errcode=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE]), 404))

        orders = Order.query.filter(Order.promotion_id==promotion.id, Order.index>0).order_by(Order.index).all()

        msg = Message('小麦芬团购-' + promotion.name, recipients=["bzip@qq.com", "nzip@qq.com"])
        msg.html = render_template('mail/promotion_orders.html', orders=orders, promotion=promotion)

        with mail.connect() as conn:
            conn.send(msg)

        return jsonify({})

api.add_url_rule('/promotion', view_func=PromotionView.as_view('promotion'))
