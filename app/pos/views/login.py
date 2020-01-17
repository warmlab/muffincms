import hashlib
from decimal import Decimal
from datetime import datetime

from flask import render_template, abort
from flask import request, current_app, make_response, url_for
from flask import json

from .. import pos
from ..auth import login_required

from ... import db

from ...models import Shoppoint