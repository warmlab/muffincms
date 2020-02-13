import json

from time import time
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.request import Request

#from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method

#from flask import current_app#, url_for
from flask_sqlalchemy import SQLAlchemy

from itsdangerous import TimedJSONWebSignatureSerializer as TimedSerializer
from itsdangerous import JSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired, BadSignature

db = SQLAlchemy()

class Shoppoint(db.Model):
    __tablename__ = 'shoppoint'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8), unique=True, index=True)
    name = db.Column(db.String(128))
    english_name = db.Column(db.String(64))
    contact = db.Column(db.String(128)) # 店长或者负责人
    phone = db.Column(db.String(12)) # 店内固定电话
    mobile = db.Column(db.String(12))
    address = db.Column(db.String(1024))
    banner = db.Column(db.String(256)) # 广告语
    note = db.Column(db.Text)

    def __repr__(self):
        return self.name

    ## mail section
    #mail = db.Column(db.String(64))
    #mail_server = db.Column(db.String(128))
    #mail_port = db.Column(db.SmallInteger, default=587)
    #mail_use_tls = db.Column(db.Boolean, default=True)
    #mail_login_name = db.Column(db.String(64))
    #mail_login_password = db.Column(db.String(128))
    #mail_subject_prefix = db.Column(db.String(64))
    #mail_sender = db.Column(db.String(64))

# 一个店通常有多个分部
class Partment(db.Model):
    __tablename__ = 'partment'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32)) # 分支名称
    code = db.Column(db.String(32)) # 分支代码
    appid = db.Column(db.String(32))
    appsecret = db.Column(db.String(64))
    paysecret = db.Column(db.String(64))
    mchid = db.Column(db.String(16))
    token = db.Column(db.String(64)) # 服务器配置中的token
    aeskey = db.Column(db.String(128)) # 服务器配置中的EncodingAESKey
    secret_key = db.Column(db.String(128)) # 每一分支一个secret key

    access_token = db.Column(db.String(256))
    expires_time = db.Column(db.BigInteger) # timestamp
    jsapi_ticket = db.Column(db.String(256))
    jsapi_expires_time = db.Column(db.BigInteger) # timestamp
    third_party = db.Column(db.SmallInteger) # 1-微信(包括公众号和小程序) 2-支付宝

    shoppoint_id = db.Column(db.Integer, db.ForeignKey('shoppoint.id'), nullable=True)
    shoppoint = db.relationship('Shoppoint',
                         backref=db.backref('parts', lazy="dynamic"))

    def get_access_token(self):
        if self.access_token and self.expires_time and self.expires_time > int(time()):
            return self.access_token

        print('Get token from weixin or cannot get access token', self.code)

        # get access token
        #params = urllib.parse.urlencode({'grant_type': 'client_credential', 'appid': app_id, 'secret': app_secret})
        #params = params.encode('ascii')
        #with urllib.request.urlopen("https://api.weixin.qq.com/cgi-bin/token?%s", params) as f:
        #    result = f.read().decode('utf-8')
        #    print (result)
        #    j = json.loads(result)
        #info = _access_weixin_api("https://api.weixin.qq.com/cgi-bin/token?%s",
        #                        grant_type='client_credential', appid=self.weixin_appid, secret=self.weixin_appsecret)
        params = {'grant_type':'client_credential', 'appid':self.appid, 'secret':self.appsecret}
        url_param = urlencode(params).encode('utf-8')
        with urlopen("https://api.weixin.qq.com/cgi-bin/token?%s", url_param) as f:
            result = f.read().decode('utf-8')
            info = json.loads(result)

            if 'errcode' in info or 'access_token' not in info or 'expires_in' not in info:
                errcode = info.get('errcode')
                errmsg = info.get('errmsg')
                return ''

            self.access_token = info.get('access_token')
            self.expires_time = int(time()) + info.get('expires_in') - 10
            db.session.commit()

            return self.access_token
        return ''

class ProductCategory(db.Model):
    __tablename__ = 'product_category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True, nullable=False)
    english_name = db.Column(db.String(128), index=True)
    slug = db.Column(db.String(128), unique=True, index=True, nullable=True)
    extra_info = db.Column(db.BigInteger, default=0) # 额外信息标志, 用位表示需要的信息，默认不需要
    index = db.Column(db.SmallInteger, default=0) # 在列表的顺序
    show_allowed = db.Column(db.Integer, default=1023) # 显示标志，0x01-web display, 0x02-pos display, 0x04-promotion display
    #web_allowed = db.Column(db.Boolean, default=True) # web端允许标志
    #pos_allowed = db.Column(db.Boolean, default=True) # POS端允许标志
    #promote_allowed = db.Column(db.Boolean, default=True) # 团购允许标志
    is_deleted = db.Column(db.Boolean, default=False) # 删除标志
    to_point = db.Column(db.Boolean, default=False) # 是否参与积分
    summary = db.Column(db.Text)
    note = db.Column(db.Text)

    shoppoint_id = db.Column(db.Integer, db.ForeignKey('shoppoint.id'))
    shoppoint = db.relationship('Shoppoint',
                         backref=db.backref('categories', lazy="dynamic"))

    def __repr__(self):
        return self.name

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
        }

class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), nullable=False, unique=True, index=True)
    name = db.Column(db.String(128), unique=True, index=True)
    english_name = db.Column(db.String(128), index=True)
    pinyin = db.Column(db.String(128), unique=True, index=True)
    price = db.Column(db.Integer, default=999900) # 现价
    member_price = db.Column(db.Integer, default=999900) # 会员价
    promote_price = db.Column(db.Integer, default=999900) # 建议的促销价, 团购价
    sold = db.Column(db.Integer, default=0) # 一共卖出的数量
    promote_sold = db.Column(db.Integer, default=0) # 促销卖了多少
    stock = db.Column(db.Integer, default=0) # 库存
    promote_stock = db.Column(db.Integer, default=0) # 建议的参与促销的库存
    promote_index = db.Column(db.Integer, default=0) # 在促销列表中的排序
    to_point = db.Column(db.Boolean, default=False) # 是否参与积分
    payment = db.Column(db.Integer, default=15) # 该商品支持的支付方式 0x01-现金支付 0x02-储值卡支付 0x04-微信支付 0x08-支付宝支付
    promote_type = db.Column(db.Integer, default=1) # 0x01-热卖 0x02-上新 0x04-特价 0x08-预售 0x10-本周推荐
    status = db.Column(db.Integer, default=0)
    summary = db.Column(db.Text)
    note = db.Column(db.Text)

    show_allowed = db.Column(db.Integer, default=1023) # 显示标志，0x01-web display, 0x02-pos display, 0x04-promotion display
    #web_allowed = db.Column(db.Boolean, default=True) # web端允许标志
    #pos_allowed = db.Column(db.Boolean, default=True) # POS端允许标志
    #promote_allowed = db.Column(db.Boolean, default=True) # 是否参与促销
    is_deleted = db.Column(db.Boolean, default=False) # 删除标志

    category_id = db.Column(db.Integer, db.ForeignKey('product_category.id'))
    category = db.relationship('ProductCategory',
                         backref=db.backref('products', lazy="dynamic"))
    shoppoint_id = db.Column(db.Integer, db.ForeignKey('shoppoint.id'))
    shoppoint = db.relationship('Shoppoint',
                         backref=db.backref('products', lazy="dynamic"))

    promote_begin_time = db.Column(db.DateTime) # 促销开始时间
    promote_end_time = db.Column(db.DateTime) # 促销结束时间
    promote_delivery_time = db.Column(db.DateTime) # 团购交付开始时间
    images = db.relationship('ProductImage', back_populates='product', order_by="asc(ProductImage.index)")
    promotions = db.relationship('PromotionProduct', back_populates='product')
    orders = db.relationship('OrderProduct', back_populates='product')
    histories = db.relationship('HistoryProduct', back_populates='product')
    sizes = db.relationship('ProductSize', back_populates='product', order_by='asc(ProductSize.product_id)')

    def __repr__(self):
        return self.name

    def to_json(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'price': self.price,
            'stock': self.stock,
            'promote_stock': self.promote_stock,
            'member_price': self.member_price,
            'promote_begin_time': self.promote_begin_time,
            'promote_end_time': self.promote_end_time
        }


class Size(db.Model):
    __tablename__ = 'size'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64)) # 尺寸名称，如‘6寸’
    value = db.Column(db.Integer) # size value used in system
    index = db.Column(db.SmallInteger, default=0) # 在列表的顺序
    # image
    spec = db.Column(db.SmallInteger, default=20) # 规格大小，如直径20cm
    shared_min = db.Column(db.SmallInteger, default=3) # 适合分享最少人数
    shared_max = db.Column(db.SmallInteger, default=4) # 适合分享最多人数
    utensils = db.Column(db.SmallInteger, default=10) # 含有餐具的数量
    pre_order_hours = db.Column(db.SmallInteger, default=24) # 须提前预定的小时数
    banner = db.Column(db.String(128)) # 该尺寸的图片

    price_plus = db.Column(db.Integer, default=0) # 在原价的基础上加上该价格
    member_price_plus = db.Column(db.Integer, default=0) # 在会员价的基础上加上该价格
    promote_price_plus = db.Column(db.Integer, default=0) # 在促销价的基础上加上该价格

    shoppoint_id = db.Column(db.Integer, db.ForeignKey('shoppoint.id'), nullable=True)
    shoppoint = db.relationship('Shoppoint', backref=db.backref('sizes', lazy="dynamic"), order_by="asc(Size.index)")

    products = db.relationship('ProductSize', back_populates='size')

class ProductSize(db.Model): # 产品尺寸，一般用于蛋糕
    __tablename__ = 'product_size'
    #id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), primary_key=True)
    size_id = db.Column(db.Integer, db.ForeignKey('size.id'), primary_key=True)
    #name = db.Column(db.String(64)) # 规格, 如：80克-巧克力味
    index = db.Column(db.SmallInteger, default=0) # 在列表的顺序
    price_plus = db.Column(db.Integer, default=0) # 在原价的基础上加上该价格
    member_price_plus = db.Column(db.Integer, default=0) # 在会员价的基础上加上该价格
    promote_price_plus = db.Column(db.Integer, default=0) # 在促销价的基础上加上该价格
    promote_stock = db.Column(db.Integer, default=0) # 参与促销的库存
    stock = db.Column(db.Integer, default=0) # 库存
    sold = db.Column(db.Integer, default=0) # 一共卖了多少（包括促销部分）
    member_sold = db.Column(db.Integer, default=0) # 会员价卖了多少（包括促销部分）
    promote_sold = db.Column(db.Integer, default=0) # 促销卖了多少

    product = db.relationship('Product', back_populates='sizes')
    size = db.relationship('Size', back_populates='products')


class Image(db.Model):
    __tablename__ = 'image'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True) # 图片存储时的名字
    #directory = db.Column(db.String(2048)) # 存储在系统上的相对路径
    hash_value = db.Column(db.String(128), index=True) # MD5 value
    title = db.Column(db.String(128)) # 图片主题
    note = db.Column(db.Text) # 图片详细描述

    type = db.Column(db.Integer, default=1) # 1-banner 2-detail 4-ad
    status = db.Column(db.Integer, default=1)

    shoppoint_id = db.Column(db.Integer, db.ForeignKey('shoppoint.id'), nullable=True)
    shoppoint = db.relationship('Shoppoint', backref=db.backref('images', lazy="dynamic"))

    products = db.relationship('ProductImage', back_populates='image')

    def __repr__(self):
        return self.name

class ProductImage(db.Model):
    __tablename__ = 'product_image'

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'), primary_key=True)
    index = db.Column(db.Integer, default=1) # 做为封面的图片，index为0, 其余为1或者排序
    type = db.Column(db.Integer, default=1) # 1-banner, 2-detail
    note = db.Column(db.Text) # 产品图片描述

    product = db.relationship("Product", back_populates="images")
    image = db.relationship('Image', back_populates='products')

class Promotion(db.Model):
    __tablename__ = 'promotion'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64)) # used in weixin
    binding = db.Column(db.Boolean, default=True) # true-捆绑销售
    paymode = db.Column(db.SmallInteger, default=0) # 0-预先支付; 1-货到付款
    #valuecard_allowed = db.Column(db.Boolean, default=True) # true-允许使用储值卡支付
    payment = db.Column(db.Integer, default=14) # 1-现金支付 2-储值卡支付 4-微信支付 8-支付宝支付
    delivery_way = db.Column(db.SmallInteger, default=1) # 交付方式(按位与)，1-自提；2-快递; 4-不允许快递
    delivery_fee = db.Column(db.Integer, default=1000) # 最低基础运费
    delivery_threshold = db.Column(db.Integer, default=9900) # 免邮金额
    last_order_time = db.Column(db.DateTime, default=datetime.now, nullable=False) # 截单时间
    from_time = db.Column(db.DateTime, default=datetime.now, nullable=False) # 取货开始时间
    to_time = db.Column(db.DateTime, default=datetime.now, nullable=False) # 取货结束时间
    publish_time = db.Column(db.DateTime, default=datetime.now) # 发布时间
    is_deleted = db.Column(db.Boolean, default=False) # 删除标志
    type = db.Column(db.Integer, default=1) # 0x01-热卖 0x02-上新 0x04-特价 0x08-预售
    status = db.Column(db.Integer, default=1) # 状态标志

    note = db.Column(db.Text) # 详细描述

    shoppoint_id = db.Column(db.Integer, db.ForeignKey('shoppoint.id'), nullable=True)
    shoppoint = db.relationship('Shoppoint', backref=db.backref('promotions', lazy="dynamic"))

    products = db.relationship('PromotionProduct', back_populates="promotion",
                               order_by="asc(PromotionProduct.index)")
    orders = db.relationship('Order', back_populates='promotion', order_by="desc(Order.index)")
    #addresses = db.relationship('PromotionAddress', back_populates='promotion')


class PromotionProduct(db.Model):
    __tablename__ = 'promotion_product'

    id = db.Column(db.Integer, primary_key=True)
    promotion_id = db.Column(db.Integer, db.ForeignKey('promotion.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    size_id = db.Column(db.Integer, db.ForeignKey('size.id'))
    index = db.Column(db.Integer, default=1)# 商品在团购中的排序
    is_deleted = db.Column(db.Boolean, default=False) # 是否删除产品

    price = db.Column(db.Integer, default=0) # 现价 通常等于商品的promote_price
    sold = db.Column(db.Integer, default=0) # 商品卖出量
    stock = db.Column(db.Integer, default=0) # 参与促销商品总数量，通常等于商品的promote_stock

    product = db.relationship("Product", back_populates="promotions")
    promotion = db.relationship("Promotion", back_populates="products")
    size = db.relationship("Size", backref=db.backref('orders', lazy='dynamic'))

#class PromotionAddress(db.Model):
#    __tablename__ = 'promotion_address'
#    promotion_id = db.Column(db.Integer, db.ForeignKey('promotion.id'), primary_key=True)
#    address_id = db.Column(db.Integer, db.ForeignKey('pickup_address.id'), primary_key=True)
#
#    promotion = db.relationship("Promotion", back_populates="addresses")
#    address = db.relationship('PickupAddress', back_populates='promotions')


class PickupAddress(db.Model):
    __tablename__ = 'pickup_address'

    id = db.Column(db.Integer, primary_key=True)
    contact = db.Column(db.String(32))
    phone = db.Column(db.String(12))
    province = db.Column(db.String(32))
    city = db.Column(db.String(32))
    district = db.Column(db.String(32))
    address = db.Column(db.String(512))
    longitude = db.Column(db.Numeric(10, 7)) # 经度
    latitude = db.Column(db.Numeric(10, 7)) # 纬度
    status = db.Column(db.Integer)
    day = db.Column(db.Integer, default=0) # 32位标示31天, 为1的位表示不营业
    weekday = db.Column(db.SmallInteger, default=0) # 用其中的7位标识一周
    from_time = db.Column(db.String(8)) # just the time no date, 每天的营业开始时间
    to_time = db.Column(db.String(8)) # just the time no date, 每天的营业结束时间

    shoppoint_id = db.Column(db.Integer, db.ForeignKey('shoppoint.id'), nullable=True)
    shoppoint = db.relationship('Shoppoint', backref=db.backref('addresses', lazy="dynamic"))

    #promotions = db.relationship('PromotionAddress', back_populates='address')
    orders = db.relationship("Order", back_populates="pickup_address")


## NO_PAY = 0
## CASH_PAY = 1
## VALUE_CARD_PAY = 2 # 储值卡
## WECHAT_PAY = 4
## ALI_PAY = 8
#class Payment(db.Model):
#    __tablename__ = 'payment'
#    id = db.Column(db.Integer, primary_key=True)
#    name = db.Column(db.String(32))
#    needs = db.Column(db.SmallInteger) # 0-no need; 1-value card input; 2-appid and other info
#
#    shoppoint_id = db.Column(db.Integer, db.ForeignKey('shoppoint.id'), nullable=True)
#    shoppoint = db.relationship('Shoppoint', backref=db.backref('payments', lazy="dynamic"))
#
#    orders = db.relationship("OrderPayment", back_populates="payment")

class Order(db.Model):
    __tablename__ = 'order'

    code = db.Column(db.String(32), primary_key=True, index=True) # 订单编号
    payment_code = db.Column(db.String(128), nullable=True) # 第三方支付平台订单编号
    index = db.Column(db.SmallInteger) # 拼团编号, 接龙编号
    #cashier = models.ForeignKey(Staff) # 收银员
    original_cost = db.Column(db.Integer, default=0) # 订单原始总价格
    cost = db.Column(db.Integer, default=0) # 订单现在总价格
    delivery_fee = db.Column(db.Integer, default=0) # 订单运费
    refund = db.Column(db.Integer, default=0) # 已退款金额
    refund_delivery_fee = db.Column(db.Integer, default=0) # 已退订单运费

    mode = db.Column(db.SmallInteger, default=0) # 0-消费, 1-充值, 2-退货, 3-反结账, 4-退卡
    #valuecard_allowed = db.Column(db.Boolean, default=True) # true-允许使用储值卡支付
    payment = db.Column(db.Integer, default=0) # 支付方式
    bonus_balance = db.Column(db.Integer, default=0) # 赠送金额，充值的时候会产生赠送金额

    prepay_id = db.Column(db.String(128), nullable=True) # 微信预支付ID
    prepay_id_expires = db.Column(db.BigInteger) # 微信预支付ID过期时间

    order_time = db.Column(db.DateTime, default=datetime.now) # 订单时间
    pay_time = db.Column(db.DateTime) # 支付时间
    # 遇到现成订蛋糕，然后有买面包，生成2个订单
    delivery_way = db.Column(db.SmallInteger, default=0) # 交付方式(按位与)，1-自提；2-快递
    delivery_time = db.Column(db.DateTime, default=datetime.now) # 交付时间
    finished_time = db.Column(db.DateTime) # 收货时间

    note = db.Column(db.Text)

    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=True) # 会员消费
    member = db.relationship("Member", backref=db.backref("orders", lazy="dynamic"))
    openid = db.Column(db.String(64), db.ForeignKey('member_openid.openid'), nullable=True) # 会员消费
    member_openid = db.relationship("MemberOpenid", backref=db.backref("orders", lazy="dynamic"))

    promotion_id = db.Column(db.Integer, db.ForeignKey('promotion.id'), nullable=True)
    promotion = db.relationship('Promotion', back_populates='orders')

    products = db.relationship('OrderProduct', back_populates='order')

    # 订单地址1:1
    address = db.relationship('OrderAddress', uselist=False, back_populates='order')
    pickup_address_id = db.Column(db.Integer, db.ForeignKey('pickup_address.id'))
    pickup_address = db.relationship('PickupAddress', back_populates='orders')
    payments = db.relationship('OrderPayment', back_populates='order')

    shoppoint_id = db.Column(db.Integer, db.ForeignKey('shoppoint.id'), nullable=True)
    shoppoint = db.relationship('Shoppoint',
                         backref=db.backref('orders', lazy="dynamic"))

    partment_id = db.Column(db.Integer, db.ForeignKey('partment.id'), nullable=True)
    partment = db.relationship('Partment',
                         backref=db.backref('orders', lazy="dynamic"))

    def next_index(self):
        next_index = db.session.query(db.func.max(Order.index)).filter_by(promotion_id=self.promotion_id).scalar()
        if next_index:
            next_index += 1
        else:
            next_index = 1

        if next_index == 250:
            next_index += 1

        self.index = next_index

    # 订单成功后，修改已售和库存
    def commit_amount(self):
        if not self.promotion:
            return

        for pp in self.promotion.products:
            for op in self.products:
                if pp.product_id == op.product_id:
                    pp.sold += op.amount
                    pp.stock -= op.amount
                    
                    pp.product.promote_sold = op.amount if not pp.product.promote_sold else pp.product.promote_sold + op.amount
                    pp.product.sold = op.amount if not pp.product.sold else pp.product.sold + op.amount
                    pp.product.promote_stock = -op.amount if not pp.product.promote_stock else pp.product.promote_stock - op.amount
                    pp.product.stock = -op.amount if not pp.product.stock else pp.product.stock - op.amount

    # 订单取消后，恢复已售和库存
    def rollback_amount(self):
        if not self.promotion:
            return

        for pp in self.promotion.products:
            for op in self.products:
                if pp.product_id == op.product_id:
                    pp.sold -= op.amount
                    pp.stock += op.amount
                    
                    pp.product.promote_sold -= op.amount
                    pp.product.sold -= op.amount
                    pp.product.promote_stock += op.amount
                    pp.product.stock += op.amount

class OrderPayment(db.Model):
    __tablename__ = 'order_payment'
    id = db.Column(db.Integer, primary_key=True)
    order_code = db.Column(db.String(32), db.ForeignKey('order.code'))
    #payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), primary_key=True)
    payment_way = db.Integer()
    balance = db.Column(db.Integer, default=0) # 该支付方式支付的实际金额
    #payment = db.relationship("Payment", back_populates="orders")
    order = db.relationship("Order", back_populates="payments")


class OrderProduct(db.Model):
    __tablename__ = 'order_product'

    id = db.Column(db.Integer, primary_key=True)
    order_code = db.Column(db.String(32), db.ForeignKey('order.code'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    size_id = db.Column(db.Integer, db.ForeignKey('size.id'))

    price = db.Column(db.Integer, default=0) # 商品在该订单中实际支付的价格
    amount = db.Column(db.Integer, default=0) # 该订单中产品的数量
    refund = db.Column(db.Integer, default=0) # 该商品退款金额

    order = db.relationship("Order", back_populates="products")
    product = db.relationship("Product", back_populates="orders")
    size = db.relationship("Size", backref=db.backref('order_products', lazy='dynamic'))

class OrderAddress(db.Model):
    __tablename__ = 'order_address'

    order_code = db.Column(db.String(32), db.ForeignKey('order.code'), primary_key=True)

    name = db.Column(db.String(128))
    phone = db.Column(db.String(12))
    province = db.Column(db.String(32))
    city = db.Column(db.String(32))
    district = db.Column(db.String(32))
    address = db.Column(db.String(512))

    order = db.relationship("Order", back_populates="address")

    def full_address(self):
        return self.province + self.city + self.district + self.address

class Staff(db.Model):
    __tablename__ = 'staff'
    id = db.Column(db.Integer, primary_key=True)
    openid = db.Column(db.String(64), primary_key=True) # used in weixin
    nickname = db.Column(db.String(128)) # 昵称
    name = db.Column(db.String(128), index=True) # 姓名
    gender = db.Column(db.SmallInteger, default=0) # 会员性别, 0为unkown
    phone = db.Column(db.String(12), unique=True, index=True) #手机号码
    email = db.Column(db.String(64), unique=True, index=True)
    privilege = db.Column(db.Integer, default=0) # every bit as a privilege

    shoppoint_id = db.Column(db.Integer, db.ForeignKey('shoppoint.id'), nullable=True)
    shoppoint = db.relationship('Shoppoint',
                         backref=db.backref('staffs', lazy="dynamic"))


class Member(db.Model):
    __tablename__ = 'member'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, index=True, nullable=True) # 实体会员卡的卡面卡号，没有实体卡，可以使用用户名
    unionid = db.Column(db.String(64), unique=True) # used in weixin
    name = db.Column(db.String(128), index=True) # 会员姓名
    nickname = db.Column(db.String(128)) # 会员昵称
    gender = db.Column(db.SmallInteger, default=0) # 会员性别, 0为unkown
    phone = db.Column(db.String(12), unique=True, index=True) #手机号码
    email = db.Column(db.String(64), unique=True, index=True)
    to_point = db.Column(db.Boolean, default=False) # 该会员是否参与积分
    points = db.Column(db.Integer, default=0) # 积分
    member_since = db.Column(db.DateTime, default=datetime.now)
    member_end = db.Column(db.DateTime, default=None)
    address = db.Column(db.String(512)) # 会员备注地址
    about_me = db.Column(db.Text)
    note = db.Column(db.Text)

    shoppoint_id = db.Column(db.Integer, db.ForeignKey('shoppoint.id'), nullable=True)
    shoppoint = db.relationship('Shoppoint',
                         backref=db.backref('members', lazy="dynamic"))

class MemberOpenid(db.Model):
    __tablename__ = 'member_openid'
    openid = db.Column(db.String(64), primary_key=True) # used in weixin
    nickname = db.Column(db.String(128)) # used in weixin
    avatarUrl = db.Column(db.String(2048))
    #session_key = db.Column(db.String(64), unique=True) # used in weixin
    #generate_session_key = db.Column(db.String(128), unique=True) # used in weixin
    privilege = db.Column(db.Integer, default=0) # every bit as a privilege
    name = db.Column(db.String(128)) # 会员姓名
    phone = db.Column(db.String(12)) # 会员电话

    # 针对小程序登录需要的参数
    session_key = db.Column(db.String(256)) # 第三方返回的session key
    access_token = db.Column(db.String(256)) # 用户登录需要的令牌
    expires_time = db.Column(db.BigInteger) # timestamp, 有效期是2hours

    member_id = db.Column(db.Integer, db.ForeignKey('member.id'))
    member = db.relationship('Member', backref=db.backref('openids', lazy='dynamic'))

    shoppoint_id = db.Column(db.Integer, db.ForeignKey('shoppoint.id'), nullable=True)
    shoppoint = db.relationship('Shoppoint',
                         backref=db.backref('openids', lazy="dynamic"))

    def generate_auth_token(self, secret_key, expiration=7200):
        s = TimedSerializer(secret_key, expires_in=expiration)

        return s.dumps({'openid': self.openid})

    def generate_access_token(self, secret_key):
        s = Serializer(secret_key)#, expires_in=expiration)
        self.access_token = s.dumps({'session_key': self.session_key}).decode('UTF-8')

    def verify_access_token(self, secret_key):
        s = Serializer(secret_key)
        try:
            data = s.loads(self.access_token)
        except SignatureExpired:
            return None # valid token, but expired
        except BadSignature:
            return None # invalid token

        #print('session_keys:', self.session_key, data['session_key'])
        return self.session_key == data['session_key']

    def __repr__(self):
        return self.openid

    @staticmethod
    def verify_auth_token(token, secret_key):
        s = TimedSerializer(secret_key)
        try:
            data = s.loads(s)
        except SignatureExpired:
            return None # valid token, but expired
        except BadSignature:
            return None # invalid token

        return MemeberOpenid.query.get(data['openid'])

class MemberOpenidAddress(db.Model):
    __tablename__ = 'openid_address'

    id = db.Column(db.Integer, primary_key=True)
    contact = db.Column(db.String(128))
    phone = db.Column(db.String(12))
    province = db.Column(db.String(32))
    city = db.Column(db.String(32))
    district = db.Column(db.String(32))
    address = db.Column(db.String(512))
    longitude = db.Column(db.Numeric(10, 7)) # 经度
    latitude = db.Column(db.Numeric(10, 7)) # 纬度
    status = db.Column(db.Integer, default=0)
    is_default = db.Column(db.Boolean, default=False)

    openid = db.Column(db.String(64), db.ForeignKey('member_openid.openid')) # used in weixin
    member_openid = db.relationship("MemberOpenid", backref=db.backref('addresses', lazy='dynamic'))


# 主要记录会员充值/消费记录
class History(db.Model):
    __tablename__ = 'history'

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'))
    mode = db.Column(db.SmallInteger, default=0) # 0-消费, 1-充值, 2-退货, 3-反结账, 4-退卡
    trade_balance = db.Column(db.Integer, default=0) # 交易金额
    left_balance = db.Column(db.Integer, default=0) # 该笔交易完成后剩余的金额
    trade_time = db.Column(db.DateTime)
    delivery = db.Column(db.SmallInteger, default=0) # 0-自提; 1-取货

    note = db.Column(db.Text)

    member = db.relationship('Member', backref=db.backref('histories', lazy='dynamic'))
    # 历史订单地址1:1
    address = db.relationship('HistoryAddress', uselist=False, back_populates='history')
    products = db.relationship('HistoryProduct', back_populates='history')

class HistoryProduct(db.Model):
    __tablename__ = 'history_product'

    id = db.Column(db.Integer, primary_key=True)
    history_id = db.Column(db.Integer, db.ForeignKey('history.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    size_id = db.Column(db.Integer, db.ForeignKey('size.id'))

    price = db.Column(db.Integer, default=0) # 商品在该订单中实际支付的价格
    refund = db.Column(db.Integer, default=0) # 该商品退款金额

    product = db.relationship("Product", back_populates="histories")
    history = db.relationship("History", back_populates="products")
    size = db.relationship("Size", backref=db.backref('history_products', lazy='dynamic'))

# History:Address=1:N
class HistoryAddress(db.Model):
    __tablename__ = 'history_address'

    history_id = db.Column(db.Integer, db.ForeignKey('history.id'), primary_key=True)

    name = db.Column(db.String(128))
    phone = db.Column(db.String(12))
    address = db.Column(db.String(1024))

    history = db.relationship("History", back_populates="address")
