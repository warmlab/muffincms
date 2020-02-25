from datetime import datetime, timedelta

from flask import request, abort
from flask import render_template

from .. import admin
from ...models import Order, Shoppoint, Promotion


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


  #from_date = request.args.get('from_date')
  #from_time = request.args.get('from_time')
  #to_date = request.args.get('to_date')
  #to_time = request.args.get('to_time')

  promotion = Promotion.query.order_by(Promotion.id.desc()).first()
  promote_time = promotion.publish_time

  #try:
  #    from_date = datetime.strptime(from_date, '%Y-%m-%d')
  #except Exception as e:
  #    from_date = datetime.now() + timedelta(days=-1)

  #now = datetime.now()+timedelta(days=-9)
  orders = Order.query.filter(Order.shoppoint_id==shop.id, Order.order_time>promote_time).order_by(Order.order_time.asc())
  dic = {}
  for o in orders:
      for p in o.products:
          if p.product_id in dic:
              dic[p.product_id].amount += p.amount
          else:
              p.product.amount = p.amount
              dic[p.product_id] = p.product

  return render_template('admin/order/list.html', orders=orders, products=dic)
