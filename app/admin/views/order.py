from datetime import datetime, timedelta

from flask import request, abort
from flask import render_template

from .. import admin
from ...models import Order, Shoppoint


@admin.route('/<shopcode>/order/info', methods=['GET'])
def order_info(shopcode):
  print(request.args)

  shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
  code = request.args['code']
  order = Order.query.get_or_404(code)
  print(order.openid)

  return render_template('admin/order/detail.html', order=order)


@admin.route('/<shopcode>/order/list', methods=['GET'])
def order_list(shopcode):
  shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
  #code = request.args['code']
  #id = request.args['promotion']
  #if id:
      #promotion = Promotion.query.get_or_404(id)

  now = datetime.now()+timedelta(days=-2)
  orders = Order.query.filter(Order.shoppoint_id==shop.id)#, Order.pay_time>now)
  dic = {}
  for o in orders:
      for p in o.products:
          if p.product_id in dic:
              dic[p.product_id].amount += p.amount
          else:
              p.product.amount = p.amount
              dic[p.product_id] = p.product

  return render_template('admin/order/list.html', orders=orders, products=dic)
