from flask import Blueprint

api = Blueprint('api', __name__)

from . import shoppoint, address, product, image, member, order, pay, promotion, qrcode
