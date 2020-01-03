from flask import render_template

from ...models import Shoppoint, ProductCategory, Product
from .. import pos
from ..auth import login_required

@pos.route('/<shoppoint>')
#login_required
def index(shoppoint):
    sp = Shoppoint.query.filter_by(code=shoppoint).first_or_404()
    categories = ProductCategory.query.all()
    products = Product.query.all()
    return render_template('pos/index.html', shoppoint=sp, categories=categories, products=products)