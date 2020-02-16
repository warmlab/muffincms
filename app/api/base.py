from functools import wraps

from flask import request, jsonify, abort, make_response
from flask.views import View

from ..models import Shoppoint, Partment, MemberOpenid
from ..status import STATUS_NO_REQUIRED_HEADERS, STATUS_TOKEN_INVALID, STATUS_METHOD_NOT_ALLOWED, MESSAGES


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not getattr(func, 'authenticated', True):
            return func(*args, **kwargs)

        #print('the function args: %s - %s', args, kwargs)
        #shop = Shoppoint.query.filter_by(code=kwargs['shopcode']).first_or_404()
        #acct = basic_authentication()  # custom account lookup function
        print('login_required')
        if not request.headers.get('X-ACCESS-TOKEN') or \
           not request.headers.get('X-VERSION') or \
           not request.headers.get('X-SHOPPOINT'):
            abort(make_response(jsonify(errcode=STATUS_NO_REQUIRED_HEADERS, message=MESSAGES[STATUS_NO_REQUIRED_HEADERS]), 400))


        shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
        partment = Partment.query.filter_by(shoppoint_id=shop.id, code=request.headers.get('X-PARTMENT')).first_or_404()
        mo = MemberOpenid.query.filter_by(access_token=request.headers.get('X-ACCESS-TOKEN')).first()
        if not mo or not mo.verify_access_token(partment.secret_key):
            abort(make_response(jsonify(errcode=STATUS_TOKEN_INVALID, message=MESSAGES[STATUS_TOKEN_INVALID]), 406))

        return func(*args, **kwargs)
    return wrapper


class UserView(View):
    methods = ['GET', 'POST']
    decorators = [login_required]

    def dispatch_request(self):
        print('method name', request.method)
        method_name = request.method
        if method_name in self.__class__.methods and method_name.lower() in self.__class__.__dict__:
            return getattr(self, method_name.lower())()
        else:
            return jsonify({"status": STATUS_METHOD_NOT_ALLOWED, "message": MESSAGES[STATUS_METHOD_NOT_ALLOWED]}), 405

class AdminView(UserView):
    decorators = [login_required]
