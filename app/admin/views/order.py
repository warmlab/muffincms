from flask import request, abort
from flask import render_template

from .. import admin
from ...models import Order, Shoppoint, Promotion

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


@admin.route('/<shopcode>/order/list', methods=['GET'])
def order_list(shopcode):
  shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
  #code = request.args['code']
  id = request.args['promotion']
  if id:
      promotion = Promotion.query.get_or_404(id)

      return render_template('admin/order/list.html', promotion=promotion)
  else:
      abort(400)
