from functools import wraps

from flask_restful import abort
from flask_restful import Resource

from flask_restful.reqparse import RequestParser

from ..models import Shoppoint, Partment, MemberOpenid
from ..status import STATUS_NO_REQUIRED_HEADERS, STATUS_TOKEN_INVALID, MESSAGES

def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not getattr(func, 'authenticated', True):
            return func(*args, **kwargs)

        #print('the function args: %s - %s', args, kwargs)
        #shop = Shoppoint.query.filter_by(code=kwargs['shopcode']).first_or_404()
        #acct = basic_authentication()  # custom account lookup function
        parser = RequestParser()
        parser.add_argument('X-ACCESS-TOKEN', type=str, location='headers', required=True, help='access token must be required')
        parser.add_argument('X-SHOPPOINT', type=str, location='headers', required=True, help='shoppoint code must be required')
        parser.add_argument('X-PARTMENT', type=str, location='headers', required=True, help='partment code must be required')
        parser.add_argument('X-VERSION', type=str, location='headers')

        data = parser.parse_args()
        if not data['X-ACCESS-TOKEN'] or not data['X-VERSION'] or not data['X-SHOPPOINT']:
            abort(400, status=STATUS_NO_REQUIRED_HEADERS, message=MESSAGES[STATUS_NO_REQUIRED_HEADERS])


        shop = Shoppoint.query.filter_by(code=data['X-SHOPPOINT']).first_or_404()
        partment = Partment.query.filter_by(shoppoint_id=shop.id, code=data['X-PARTMENT']).first_or_404()
        mo = MemberOpenid.query.filter_by(access_token=data['X-ACCESS-TOKEN']).first()
        if not mo or not mo.verify_access_token(partment.secret_key):
            abort(403, status=STATUS_TOKEN_INVALID, message=MESSAGES[STATUS_TOKEN_INVALID])

        return func(*args, **kwargs)
    return wrapper

class BaseResource(Resource):
    method_decorators = [authenticate]
