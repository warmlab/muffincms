import base64
from Crypto.Cipher import AES
from time import time

from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.request import Request as UrlRequest

from flask import request, current_app, json, jsonify, abort, make_response

from ..status import STATUS_NO_REQUIRED_ARGS, STATUS_NO_RESOURCE, STATUS_CANNOT_DECRYPT, STATUS_TOKEN_INVALID, MESSAGES

from ..models import db
from ..models import MemberOpenid, Shoppoint, Partment, MemberOpenidAddress

from . import api
from .base import UserView, login_required


@api.route('/login', methods=['POST'])
def login():
    shop = Shoppoint.query.filter_by(code=request.headers['X-SHOPPOINT']).first_or_404()
    if 'code' not in request.json:
        print('no code or partment argument in request')
        abort(make_response(jsonify(errcode=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'member login code or partment code'), 400))

    partment = Partment.query.filter_by(shoppoint_id=shop.id, code=request.headers.get('X-PARTMENT')).first_or_404()

    data = (
        ('appid', partment.appid),
        ('secret', partment.appsecret),
        ('js_code', request.json.get('code')),
        ('grant_type', 'authorization_code')
    )

    print('request weixin data: ', data)
    r = UrlRequest('https://api.weixin.qq.com/sns/jscode2session?'+urlencode(data), method='GET')
    with urlopen(r) as s:
        result = s.read().decode('utf-8')
        info = json.loads(result)
        print('result from weixin jscode2session: ', info)
        if 'errcode' in info:
            print('request weixin jscode2session failed: ', info)
            abort(make_response(jsonify(errcode=info['errcode'], message=info['errmsg']), 400))

        mo = MemberOpenid.query.filter_by(openid=info['openid']).first()
        if not mo:
            mo = MemberOpenid()
            mo.openid = info['openid']
            db.session.add(mo)

        mo.session_key = info['session_key']
        mo.expires_time = int(time()) + 86400
        mo.shoppoint_id = shop.id

        mo.generate_access_token(partment.secret_key)

        if 'unionid' in info and not mo.unionid:
            mo.unionid = info['unionid']
            m = Member.query.filter_by(unionid=mo.unionid).first()
            if m:
                mo.member = m
            else:
                m = Member()
                m.unionid = info['unionid']
                db.session.add(m)
        dic = mo.to_json()
        db.session.commit()
        print('member openid', dic)

        return jsonify(dic)

    abort(make_response(jsonify(errcode=STATUS_CANNOT_LOGIN, message=MESSAGES[STATUS_CANNOT_LOGIN] % args['code']), 405))


@api.route('/tokencheck', methods=['POST'])
def token_check():
    shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
    partment = Partment.query.filter_by(shoppoint_id=shop.id, code=request.headers.get('X-PARTMENT')).first_or_404()
    mo = MemberOpenid.query.filter_by(shoppoint_id=shop.id, access_token=request.headers.get('X-ACCESS-TOKEN')).first()
    if not mo or not mo.verify_access_token(partment.secret_key):
        abort(make_response(jsonify(errcode=STATUS_TOKEN_INVALID, message=MESSAGES[STATUS_TOKEN_INVALID]), 403))

    return jsonify(mo.to_json())

@api.route('/openid/decrypt', methods=['POST'])
@login_required
def descrypt():
    shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
    partment = Partment.query.filter_by(shoppoint_id=shop.id, code=request.headers.get('X-PARTMENT')).first_or_404()
    mo = MemberOpenid.query.filter_by(shoppoint_id=shop.id, access_token=request.headers.get('X-ACCESS-TOKEN')).first()
    if not mo or not mo.verify_access_token(partment.secret_key):
        abort(make_response(jsonify(errcode=STATUS_TOKEN_INVALID, message=MESSAGES[STATUS_TOKEN_INVALID]), 403))

    # decrypt procedure
    # base64 decode
    sessionKey = base64.b64decode(mo.session_key)
    encryptedData = base64.b64decode(request.headers.get('encryptedData'))
    iv = base64.b64decode(request.headers.get('iv'))

    cipher = AES.new(sessionKey, AES.MODE_CBC, iv)

    s = cipher.decrypt(encryptedData)
    s = s[:(-s[-1])]
    decrypted = json.loads(s)

    print('decrypted after: %s', decrypted)

    if decrypted['watermark']['appid'] != partment.appid:
        abort(400, STATUS_CANNOT_DECRYPT, MESSAGES[STATUS_CANNOT_DECRYPT])

    return decrypted

@api.route('/openid/addresses', methods=['GET'])
@login_required
def address_list():
    shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
    mo = MemberOpenid.query.filter_by(access_token=request.headers.get('X-ACCESS-TOKEN')).first_or_404()
    addresses = MemberOpenidAddress.query.filter_by(openid=mo.openid).all()

    return jsonify([a.to_json() for a in addresses])

class OpenidView(UserView):
    def get(self):
        shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
        mo = MemberOpenid.query.filter_by(shoppoint_id=shop.id, access_token=request.headers.get('X-ACCESS-TOKEN')).first_or_404()

        return jsonify(mo.to_json())

    def post(self):
        shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
        mo = MemberOpenid.query.filter_by(shoppoint_id=shop.id, access_token=request.headers.get('X-ACCESS-TOKEN')).first_or_404()

        mo.name = request.json.get('name')
        mo.phone = request.json.get('phone')

        return jsonify(mo.to_json()), 201


class OpenidAddressView(UserView):
    methods = ['GET', 'POST', 'DELETE']
    def get(self):
        shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
        mo = MemberOpenid.query.filter_by(shoppoint_id=shop.id, access_token=request.headers.get('X-ACCESS-TOKEN')).first_or_404()

        try:
            address_id = int(request.args.get('id'))
        except Exception as e:
            address_id = 0
        address = MemberOpenidAddress.query.get_or_404(address_id)
        if address.openid != mo.openid:
            abort(make_response(jsonify(errcode=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE]), 404))
        return jsonify(address.to_json())

    def post(self):
        shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
        mo = MemberOpenid.query.filter_by(shoppoint_id=shop.id, access_token=request.headers.get('X-ACCESS-TOKEN')).first_or_404()

        try:
            address_id = int(request.args.get('id'))
        except Exception as e:
            address_id = 0

        if address_id:
            address = MemberOpenidAddress.query.get_or_404(address_id)
        else:
            address = MemberOpenidAddress()
        address.contact = request.json.get('contact')
        address.phone = request.json.get('phone')
        address.province = request.json.get('province')
        address.city = request.json.get('city')
        address.district = request.json.get('district')
        address.address = request.json.get('address').strip()
        address.openid = mo.openid
        if request.json.get('is_default'):
            MemberOpenidAddress.query.filter_by(openid=mo.openid).update({'is_default': False})

        address.is_default = request.json.get('is_default')
        db.session.add(address)
        db.session.commit()

        return jsonify(address.to_json()), 201

    def delete(self):
        shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
        address = MemberOpenidAddress.query.get_or_404(request.json.get('id'))
        db.session.delete(address)
        db.session.commit()

        return jsonify({})

api.add_url_rule('/openid', view_func=OpenidView.as_view('openid'))
api.add_url_rule('/openid/address', view_func=OpenidAddressView.as_view('openid_address'))
