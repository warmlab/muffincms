from flask import request, current_app, json, jsonify

from . import api
from .base import UserView

from ..status import STATUS_NO_REQUIRED_ARGS, STATUS_NO_RESOURCE, MESSAGES

from ..models import db
from ..models import Shoppoint, Partment


class ShoppointView(UserView):
  def get(self):
    shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()

    return jsonify(shop.to_json())

  def post(self):
    shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
    if request.method == 'POST':
        shop.name = request.json.get('name')
        shop.contact = request.json.get('contact')
        shop.mobile = request.json.get('mobile')
        shop.address = request.json.get('address')
        shop.note = request.json.get('note')

        db.session.commit()

    return jsonify(shop.to_json())

api.add_url_rule('/shopinfo', view_func=ShoppointView.as_view('shopinfo'))
