from flask import request, current_app, json

from flask_restful import Resource
from flask_restful import fields, marshal_with, abort
from flask_restful.reqparse import RequestParser

from ..status import STATUS_NO_REQUIRED_ARGS, STATUS_NO_RESOURCE, MESSAGES

from ..models import db
from ..models import Shoppoint, Partment

from .base import BaseResource

shoppoint_fields = {
    'name': fields.String,
    'code': fields.String,
    'english_name': fields.String,
    'contact': fields.String,
    'phone': fields.String,
    'mobile': fields.String,
    'address': fields.String,
    'banner': fields.String,
    'note': fields.String,
}

partment_fields = {
    'name': fields.String,
    'code': fields.String,
    'shop': fields.Nested(shoppoint_fields)
}

class ShoppointResource(BaseResource):
    @marshal_with(shoppoint_fields)
    def get(self):
        parser = RequestParser()
        parser.add_argument('X-SHOPPOINT', type=str, location='headers', required=True, help='shoppoint code must be required')
        #parser.add_argument('X-PARTMENT', type=str, required=True, location='headers', help='partment code must be required')
        args = parser.parse_args()

        #if not args['X-PARTMENT']:
        #    print('no shoppoint partment argument in request')
        #    abort(400, status=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'partment code')

        shop = Shoppoint.query.filter_by(code=args['X-SHOPPOINT']).first_or_404()

        return shop

    @marshal_with(shoppoint_fields)
    def post(self):
        parser = RequestParser()
        parser.add_argument('X-SHOPPOINT', type=str, location='headers', required=True, help='shoppoint code must be required')
        #parser.add_argument('X-PARTMENT', type=str, required=True, location='headers', help='partment code must be required')
        parser.add_argument('name', type=str, required=True, help='partment code must be required')
        parser.add_argument('contact', type=str, required=True, help='partment code must be required')
        parser.add_argument('mobile', type=str, required=True, help='partment code must be required')
        parser.add_argument('address', type=str, required=True, help='partment code must be required')
        parser.add_argument('note', type=str)
        args = parser.parse_args()

        print('shopinfo commit info', args)

        #if not args['X-PARTMENT']:
        #    print('no shoppoint partment argument in request')
        #    abort(400, status=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'partment code')

        shop = Shoppoint.query.filter_by(code=args['X-SHOPPOINT']).first_or_404()
        shop.name = args['name']
        shop.contact = args['contact']
        shop.mobile = args['mobile']
        shop.address = args['address']
        shop.note = args['note']

        db.session.commit()
        #partment = Partment.query.filter_by(shoppoint_id=shop.id, code=args['X-PARTMENT']).first_or_404()

        return shop
