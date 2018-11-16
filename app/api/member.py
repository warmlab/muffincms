import base64
from Crypto.Cipher import AES
from time import time

from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.request import Request as UrlRequest

from flask import request, current_app, json

from flask_restful import Resource
from flask_restful import fields, marshal_with, abort
from flask_restful.reqparse import RequestParser

from ..logging import logger
from ..status import STATUS_NO_REQUIRED_ARGS, STATUS_NO_RESOURCE, STATUS_CANNOT_DECRYPT, MESSAGES

from ..models import db
from ..models import MemberOpenid, Shoppoint, Partment, MemberOpenidAddress

from .base import BaseResource

address_fields = {
    'id': fields.Integer,
    'contact': fields.String,
    'phone': fields.String,
    'address': fields.String,
    'is_default': fields.Boolean
}

openid_fields = {
    'openid': fields.String,
    'nickname': fields.String,
    'avatarUrl': fields.String,
    'name': fields.String,
    'phone': fields.String,
    'contact': fields.String,
    'mobile': fields.String,
    'access_token': fields.String,
    'privilege': fields.Integer,
    'addresses': fields.List(fields.Nested(address_fields))
}

class LoginResource(Resource):
    @marshal_with(openid_fields)
    def post(self, shopcode):
        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        parser = RequestParser()
        parser.add_argument('X-PARTMENT', type=str, required=True, location='headers', help='partment code must be required')
        parser.add_argument('code', type=str, required=True, help='member login code must be required')
        #parser.add_argument('session_key', type=str, help='member session_key must be required')
        args = parser.parse_args(strict=True)

        if not args['code'] or not args['X-PARTMENT']:
            logger.error('no code and partment argument in request')
            abort(400, status=STATUS_NO_REQUIRED_ARGS, message=MESSAGES[STATUS_NO_REQUIRED_ARGS] % 'member login code or partment code')

        logger.debug('partment: %s', args['X-PARTMENT'])
        partment = Partment.query.filter_by(shoppoint_id=shop.id, code=args['X-PARTMENT']).first_or_404()

        data = (
            ('appid', partment.appid),
            ('secret', partment.appsecret),
            ('js_code', args['code']),
            ('grant_type', 'authorization_code')
        )

        logger.debug('request weixin data: %s', data)
        r = UrlRequest('https://api.weixin.qq.com/sns/jscode2session?'+urlencode(data), method='GET')
        with urlopen(r) as s:
            result = s.read().decode('utf-8')
            info = json.loads(result)
            logger.debug('result from weixin jscode2session: %s', info)
            if 'errcode' in info:
                logger.debug('request weixin jscode2session failed: %s', info)
                abort(400, status=info['errcode'], message=info['errmsg'])

            mo = MemberOpenid.query.filter_by(openid=info['openid']).first()
            if not mo:
                mo = MemberOpenid()
                mo.openid = info['openid']

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
            db.session.add(mo)
            db.session.commit()

            return mo

        abort(405, status=STATUS_CANNOT_LOGIN, message=MESSAGES[STATUS_CANNOT_LOGIN] % args['code']) 


class TokenCheckerResource(BaseResource):
    @marshal_with(openid_fields)
    def post(self, shopcode):
        parser = RequestParser()
        parser.add_argument('X-ACCESS-TOKEN', type=str, location='headers', required=True, help='access token must be required')
        parser.add_argument('X-PARTMENT', type=str, location='headers', required=True, help='partment code must be required')
        data = parser.parse_args()

        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        partment = Partment.query.filter_by(shoppoint_id=shop.id, code=data['X-PARTMENT']).first_or_404()
        mo = MemberOpenid.query.filter_by(shoppoint_id=shop.id, access_token=data['X-ACCESS-TOKEN']).first()
        if not mo or not mo.verify_access_token(partment.secret_key):
            abort(403, status=STATUS_TOKEN_INVALID, message=MESSAGES[STATUS_TOKEN_INVALID])

        return mo

class DecryptResource(BaseResource):
    def post(self, shopcode):
        parser = RequestParser()
        parser.add_argument('X-ACCESS-TOKEN', type=str, location='headers', required=True, help='access token must be required')
        parser.add_argument('X-PARTMENT', type=str, location='headers', required=True, help='partment code must be required')
        parser.add_argument('encryptedData', type=str, required=True, help='encrypted data must be required')
        parser.add_argument('iv', type=str, required=True, help='iv must be required')
        parser.add_argument('errMsg', type=str)
        data = parser.parse_args()

        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        partment = Partment.query.filter_by(shoppoint_id=shop.id, code=data['X-PARTMENT']).first_or_404()
        mo = MemberOpenid.query.filter_by(shoppoint_id=shop.id, access_token=data['X-ACCESS-TOKEN']).first()
        if not mo or not mo.verify_access_token(partment.secret_key):
            abort(403, status=STATUS_TOKEN_INVALID, message=MESSAGES[STATUS_TOKEN_INVALID])

        # decrypt procedure
        # base64 decode
        sessionKey = base64.b64decode(mo.session_key)
        encryptedData = base64.b64decode(data['encryptedData'])
        iv = base64.b64decode(data['iv'])

        print('ccccccccccccc', sessionKey, iv)

        cipher = AES.new(sessionKey, AES.MODE_CBC, iv)

        s = cipher.decrypt(encryptedData)
        print('aaaaaaaaaaaaa', s)
        s = s[:(-s[-1])]
        print('aaaaaaaaaaaaa', s)
        decrypted = json.loads(s)

        logger.debug('decrypted after: %s', decrypted)

        if decrypted['watermark']['appid'] != partment.appid:
            abort(400, STATUS_CANNOT_DECRYPT, MESSAGES[STATUS_CANNOT_DECRYPT])

        return decrypted

class OpenidResource(BaseResource):
    @marshal_with(openid_fields)
    def get(self, shopcode):
        parser = RequestParser()
        parser.add_argument('X-ACCESS-TOKEN', type=str, required=True, location='headers', help='access token must be required')
        args = parser.parse_args()
        logger.debug('GET request args: %s', args)

        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        mo = MemberOpenid.query.filter_by(shoppoint_id=shop.id, access_token=args['X-ACCESS-TOKEN']).first_or_404()

        return mo

    @marshal_with(openid_fields)
    def post(self, shopcode):
        parser = RequestParser()
        parser.add_argument('X-ACCESS-TOKEN', type=str, required=True, location='headers', help='access token must be required')
        parser.add_argument('name', type=str, required=True, help='member name must be required')
        parser.add_argument('phone', type=str, required=True, help='member phone number must be required')
        args = parser.parse_args()
        logger.debug('GET request args: %s', args)

        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        mo = MemberOpenid.query.filter_by(shoppoint_id=shop.id, access_token=args['X-ACCESS-TOKEN']).first_or_404()

        mo.name = args['name']
        mo.phone = args['phone']

        return mo, 201
        

class OpenidAddressResource(BaseResource):
    @marshal_with(address_fields)
    def get(self, shopcode):
        parser = RequestParser()
        #parser.add_argument('openid', type=str, required=True, location='args', help='openid should be required')
        parser.add_argument('X-ACCESS-TOKEN', type=str, location='headers', required=True, help='access token must be required')
        parser.add_argument('id', type=int, required=True, location='args', help='address id should be required')
        # parser.add_argument('date', type=lambda x: datetime.strptime(x,'%Y-%m-%dT%H:%M:%S'))
        args = parser.parse_args()
        logger.debug('GET request args: %s', args)

        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        mo = MemberOpenid.query.filter_by(shoppoint_id=shop.id, access_token=args['X-ACCESS-TOKEN']).first_or_404()
        address = MemberOpenidAddress.query.get_or_404(args['id'])
        if address.openid != mo.openid:
            abort(404, status=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE])
        return address

    @marshal_with(address_fields)
    def post(self, shopcode):
        parser = RequestParser()
        #parser.add_argument('openid', type=str, required=True, help='openid should be required')
        parser.add_argument('X-ACCESS-TOKEN', type=str, location='headers', required=True, help='access token must be required')
        parser.add_argument('id', type=int)
        parser.add_argument('contact', type=str, required=True, help='contact name should be required')
        parser.add_argument('phone', type=str, required=True, help='phone should be required')
        parser.add_argument('address', type=str, required=True, help='address should be required')
        parser.add_argument('is_default', type=bool, required=True, help='default setting should be required')
        # parser.add_argument('date', type=lambda x: datetime.strptime(x,'%Y-%m-%dT%H:%M:%S'))
        data = parser.parse_args()
        logger.debug('GET request args: %s', data)

        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        mo = MemberOpenid.query.filter_by(shoppoint_id=shop.id, access_token=data['X-ACCESS-TOKEN']).first_or_404()
        if data['id']:
            address = MemberOpenidAddress.query.get_or_404(data['id'])
        else:
            address = MemberOpenidAddress()
        address.contact = data['contact']
        address.phone = data['phone']
        address.address = data['address']
        address.openid = mo.openid
        if data['is_default']:
            MemberOpenidAddress.query.filter_by(openid=mo.openid).update({'is_default': False})

        address.is_default = data['is_default']
        db.session.add(address)
        db.session.commit()

        return address, 201

    def delete(self, shopcode):
        parser = RequestParser()
        parser.add_argument('openid', type=str, required=True, help='openid should be required')
        parser.add_argument('id', type=int, required=True, help='address id should be required')
        # parser.add_argument('date', type=lambda x: datetime.strptime(x,'%Y-%m-%dT%H:%M:%S'))
        args = parser.parse_args()
        logger.debug('GET request args: %s', args)

        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        address = MemberOpenidAddress.query.get_or_404(args['id'])
        db.session.delete(address)
        db.session.commit()
        return {}, 201

class OpenidAddressesResource(BaseResource):
    @marshal_with(address_fields)
    def get(self, shopcode):
        parser = RequestParser()
        parser.add_argument('openid', type=str, required=True, location='args', help='openid should be required')
        # parser.add_argument('date', type=lambda x: datetime.strptime(x,'%Y-%m-%dT%H:%M:%S'))
        args = parser.parse_args()
        logger.debug('GET request args: %s', args)

        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        addresses = MemberOpenidAddress.query.filter_by(openid=args['openid']).all()

        return addresses
