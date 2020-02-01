from flask import Blueprint

weixin = Blueprint('weixin', __name__)

from . import views
from .message import Message
