import hashlib
from decimal import Decimal
from datetime import datetime

from flask import render_template, abort
from flask import request, current_app, make_response, url_for
from flask import json

from flask_login import login_required, current_user

from . import weixin
from .. import db
from .message import Message

from ..models import Shoppoint

def check_signature(code, signature, timestamp, nonce):
    #token = current_app.config['WEIXIN_TOKEN']
    shoppoint = Shoppoint.query.first()
    token = shoppoint.weixin_token
    if signature and timestamp and nonce:
        array = [token, timestamp, nonce]
        print(array)
        array.sort()
        joined = "".join(array)

        joined_sha1 = hashlib.sha1(bytes(joined, 'ascii')).hexdigest()
        if joined_sha1 == signature:
            return True

        return False

@weixin.route('/access', methods=['POST'])
def access():
    shoppoint = Shoppoint.query.first()
    signature = request.args.get("signature")
    timestamp = request.args.get("timestamp")
    nonce = request.args.get("nonce")

    openid = request.args.get('openid')
    body = request.data.decode('utf-8')
    message = Message.parse_message(body)
    if message.type == 'event':
        return message.process_event()
    else:
        body = message.generate_response_body()
        response = make_response()
        response.headers['Content-type'] = 'application/xml'
        response.data = body.encode('utf-8')

        return response
