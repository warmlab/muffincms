from datetime import datetime

from flask import request

from flask_restful import abort
from flask_restful import fields, marshal_with
from flask_restful.reqparse import RequestParser

from ..logging import logger
from ..status import STATUS_NO_REQUIRED_ARGS, STATUS_NO_RESOURCE, MESSAGES

from ..models import db
from ..models import Shoppoint, ProductCategory

from .base import BaseResource
from .image import image_fields
from .field import WebAllowedField, POSAllowedField, PromoteAllowedField

category_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'english_name': fields.String,
    'slug': fields.String,
    'extra_info': fields.Integer,
    'web_allowed': WebAllowedField(attribute='show_allowed'),
    'pos_allowed': POSAllowedField(attribute='show_allowed'),
    'promote_allowed': PromoteAllowedField(attribute='show_allowed'),
    'summary': fields.String,
    'note': fields.String,
}

class CategoriesResource(BaseResource):
    @marshal_with(category_fields)
    def get(self, shopcode):
        #parser = RequestParser()
        #parser.add_argument('code', type=str, help='product code should be required')
        #args = parser.parse_args(strict=True)
        #logger.debug('GET request args: %s', args)
        #if not args['code']:
        #    logger.error('no code argument in request')
        #    abort(400, status=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'product code')
        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        categories = ProductCategory.query.filter_by(shoppoint_id=shop.id).all()
        if not categories:
            logger.warning(MESSAGES[STATUS_NO_RESOURCE])
            abort(404, status=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE])

        return categories
