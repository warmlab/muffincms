from datetime import datetime

from flask import request, jsonify
from flask.views import View

from . import api
from .base import UserView, login_required

from ..status import STATUS_NO_REQUIRED_ARGS, STATUS_NO_RESOURCE, MESSAGES

from ..models import db
from ..models import Shoppoint, PickupAddress

@api.route('/pickupaddresses', methods=['GET'])
@login_required
def pickup_addresses():
    shop = Shoppoint.query.filter_by(code=request.headers['X-SHOPPOINT']).first_or_404()
    if 'manage' in request.args:
        addresses = PickupAddress.query.filter(PickupAddress.shoppoint_id==shop.id).all()
    else:
        addresses = PickupAddress.query.filter(PickupAddress.shoppoint_id==shop.id, 
                                           PickupAddress.status.op('&')(1)==1).all()

    return jsonify([a.to_json() for a in addresses])


class PickupAddressView(UserView):
    methods = ['GET', 'POST', 'DELETE']

    def get(self):
        if 'code' not in request.args:
            abort(make_response(jsonify(errcode=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'product code'), 400))

        shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
        address = PickupAddress.query.get(request.args['code'])
        if not address or address.shoppoint_id != shop.id:
            abort(make_response(jsonify(errcode=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE]), 404))

        return jsonify(address.to_json())

    def post(self):
        shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()

        address = None
        if 'code' in request.json:
            address = PickupAddress.query.get(request.json['code'])
        if not address:
            address = PickupAddress()
            db.session.add(address)

        print('dddddd', request.json)
        address.contact = request.json.get('contact')
        address.phone = request.json.get('phone')
        address.province = request.json.get('province')
        address.city = request.json.get('city')
        address.district = request.json.get('district')
        address.address = request.json.get('address')
        address.day = request.json.get('day')
        address.weekday = request.json.get('weekday')
        address.from_time = request.json.get('from_time')
        address.to_time = request.json.get('to_time')
        address.status = request.json.get('status')
        address.shoppoint_id = shop.id

        db.session.commit()

        return jsonify(address.to_json()), 201

api.add_url_rule('/pickupaddress', view_func=PickupAddressView.as_view('pickupaddress'))
