from datetime import datetime

from flask import request

from flask_restful import abort
from flask_restful import fields, marshal_with
from flask_restful.reqparse import RequestParser

from ..status import STATUS_NO_REQUIRED_ARGS, STATUS_NO_RESOURCE, MESSAGES

from ..models import db
from ..models import Shoppoint, PickupAddress

from .base import BaseResource

address_fields = {
    'id': fields.Integer,
    'contact': fields.String,
    'phone': fields.String,
    'province': fields.String,
    'city': fields.String,
    'district': fields.String,
    'address': fields.String,
    'checked': fields.Boolean,
    'day': fields.Integer,
    'weekday': fields.Integer,
    'from_time': fields.String,
    'to_time': fields.String,
}

class AddressResource(BaseResource):
    @marshal_with(address_fields)
    def get(self):
        parser = RequestParser()
        parser.add_argument('code', type=int, location='args', help='pickup address code should be required')
        parser.add_argument('X-SHOPPOINT', type=str, location='headers', required=True, help='shoppoint code must be required')
        args = parser.parse_args()
        print('GET request args: %s', args)
        if not args['code']:
            print('no code argument in request')
            abort(400, status=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'pickup address code')
        shop = Shoppoint.query.filter_by(code=args['X-SHOPPOINT']).first_or_404()
        address = PickupAddress.query.get(args['code'])
        if not address or address.shoppoint_id != shop.id:
            print(MESSAGES[STATUS_NO_RESOURCE])
            abort(404, status=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE])

        return address

    @marshal_with(address_fields)
    def post(self):
        parser = RequestParser()
        parser.add_argument('X-SHOPPOINT', type=str, location='headers', required=True, help='shoppoint code must be required')
        parser.add_argument('code', type=int)
        parser.add_argument('contact', type=str)
        parser.add_argument('phone', type=str)
        parser.add_argument('province', type=str, required=True, help='province must be required')
        parser.add_argument('city', type=str, required=True, help='city must be required')
        parser.add_argument('district', type=str, required=True, help='district must be required')
        parser.add_argument('address', type=str, required=True, help='address must be required')
        parser.add_argument('checked', type=bool)
        parser.add_argument('day', type=int)
        parser.add_argument('weekday', type=int)
        parser.add_argument('from_time', type=str)
        parser.add_argument('to_time', type=str)
        data = parser.parse_args()
        print('POST request args: %s', data)

        shop = Shoppoint.query.filter_by(code=dat['X-SHOPPOINT']).first_or_404()

        address = None
        if data['code']:
            address = PickupAddress.query.get(data['code'])
        if not address:
            address = PickupAddress()
            db.session.add(address)

        address.contact = data['contact']
        address.phone = data['phone']
        address.address = data['address']
        address.checked = data['checked']
        address.day = data['day']
        address.weekday = data['weekday']
        address.from_time = data['from_time']
        address.to_time = data['to_time']
        address.shoppoint = shop

        db.session.commit()

        return address, 201


class AddressesResource(BaseResource):
    @marshal_with(address_fields)
    def get(self):
        parser = RequestParser()
        parser.add_argument('X-SHOPPOINT', type=str, location='headers', required=True, help='shoppoint code must be required')
        #parser.add_argument('code', type=int, help='pickup address code should be required')
        args = parser.parse_args()
        #print('GET request args: %s', args)
        #if not args['code']:
        #    print('no code argument in request')
        #    abort(400, status=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'pickup address code')
        shop = Shoppoint.query.filter_by(code=args['X-SHOPPOINT']).first_or_404()
        addresses = PickupAddress.query.filter_by(shoppoint_id=shop.id, status=1).all()

        return addresses
