from flask import Blueprint

payment = Blueprint('payment', __name__)

from . import views
from .pay import unified_order, generate_pay_sign
