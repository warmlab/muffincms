from flask import Blueprint

pos = Blueprint('POS', __name__)

from . import views
