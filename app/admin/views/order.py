from flask import request, abort
from flask import render_template

from .. import admin
from ...models import Order, Shoppoint

from ...logging import logger


@admin.route('/<shopcode>/order/info', methods=['GET'])
def order_info(shopcode):
  #logger.debug(request.headers)
  logger.debug(request.args)

  shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
  code = request.args['code']
  order = Order.query.get_or_404(code)
  print(order.openid)

  return render_template('admin/order/detail.html', order=order)
