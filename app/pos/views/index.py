from flask import render_template, request

from ...models import Shoppoint, ProductCategory, Product
from .. import pos
from ..auth import login_required

@pos.route('/')
#login_required
def index(shoppoint):
    sp = Shoppoint.query.filter_by(code=shoppoint).first_or_404()
    categories = ProductCategory.query.all()
    products = Product.query.limit(40)
    return render_template('pos/index.html', shoppoint=sp, categories=categories, products=products)

@pos.route('/products')
def products(shoppoint):
    sp = Shoppoint.query.filter_by(code=shoppoint).first_or_404()
    print(request.headers)
    print(request.args)

    category_id = request.args.get('category')
    products = Product.query.filter_by(shoppoint_id=sp.id, category_id=category_id)
    return products.to
