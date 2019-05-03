from flask import Blueprint
from flask_restful import Api

from .promotion import PromotionResource, PromotionsResource, PromotionOrdersResource
from .image import ImageResource
from .product import ProductResource, ProductsResource, SizesResource
from .qrcode import QRCodeResource
from .order import OrderResource, OrdersResource
from .member import LoginResource, OpenidResource, OpenidAddressResource, OpenidAddressesResource, TokenCheckerResource, DecryptResource
from .address import AddressResource, AddressesResource
from .category import CategoriesResource
from .shoppoint import ShoppointResource
from .pay import PayResource

api_blueprint = Blueprint('api', __name__)
api = Api(api_blueprint)

api.add_resource(PromotionResource, '/promotion', endpoint='promotion_ep')
api.add_resource(PromotionOrdersResource, '/promotion/orders')
api.add_resource(PromotionsResource, '/promotions', endpoint='promotions_ep')

api.add_resource(ImageResource, '/image')
api.add_resource(CategoriesResource, '/categories')
api.add_resource(ProductResource, '/product')
api.add_resource(QRCodeResource, '/qrcode')
api.add_resource(ProductsResource, '/products')
api.add_resource(SizesResource, '/product/sizes')
api.add_resource(OrderResource, '/order')
api.add_resource(OrdersResource, '/orders')

api.add_resource(LoginResource, '/login')
api.add_resource(TokenCheckerResource, '/tokencheck')
api.add_resource(OpenidResource, '/openid')
api.add_resource(DecryptResource, '/openid/decrypt')
api.add_resource(OpenidAddressResource, '/openid/address')
api.add_resource(OpenidAddressesResource, '/openid/addresses')

api.add_resource(AddressResource, '/address')
api.add_resource(AddressesResource, '/addresses')
api.add_resource(ShoppointResource, '/info')
api.add_resource(PayResource, '/pay')
