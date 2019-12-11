import hashlib

from time import time
from datetime import datetime

from xml.etree import ElementTree as etree

class Message():
    def __init__(self):
        #self.message = message
        self.__properties = {}
        self.member = None

    def generate_response_body(self):
        return self._generate_text_body()

    def generate_template_body(self, template_id, touser, url, data):
        dic = {
            'template_id': template_id,
            'touser': touser,
            'url':  url,
        }

        dic['data'] = data

        return dic

    def generate_text_body(self, text):
        body = """<xml>
        <ToUserName><![CDATA[%s]]></ToUserName>
        <FromUserName><![CDATA[%s]]></FromUserName>
        <CreateTime>%d</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[%s]]></Content>
        </xml>""" % (self.__properties['FromUserName'], self.__properties['ToUserName'],
                     int(time()), text)

        return body

    def _generate_news_body(self):
        home_web = "https://wecakes.com"
        body = """<xml>
        <ToUserName><![CDATA[%s]]></ToUserName>
        <FromUserName><![CDATA[%s]]></FromUserName>
        <CreateTime>%d</CreateTime>
        <MsgType><![CDATA[news]]></MsgType>
        <ArticleCount>1</ArticleCount>
        <Articles>
            <item>
              <Title><![CDATA[用心做 不做作]]></Title>
              <Description><![CDATA[地址：青岛市李沧区九水路227号宝龙城市广场3层小麦芬烘焙课堂]]></Description>
              <PicUrl><![CDATA[https://mmbiz.qpic.cn/mmbiz_jpg/oXT2ftOBH9y4xFZHSH4EEQVx0vWUp7aKzSXMIFcicvfZFetBmj3icYsOzV4N7dK86iaTxne1FPaSdEn0UJXmKibVWA/0?wx_fmt=jpeg]]></PicUrl>
              <Url><![CDATA[http://mp.weixin.qq.com/s?__biz=MzAwMjE3MzEyNw==&mid=307737452&idx=1&sn=b35910fcfb0bb2166ff4aea760f5818f&chksm=0d6d62c43a1aebd27b0833473c19a6c0bbf29ab4c7134ff9040fe004158cfb3322f9ddf1ec0e#rd]]></Url>
            </item>
        </Articles>""" % (self.__properties['FromUserName'], self.__properties['ToUserName'],
                     int(time()))

        print(body)


        return body

    def _generate_text_body(self):
        print(self.__properties)
        #home_web = "http://m.wecakes.com"
        body = """<xml>
        <ToUserName><![CDATA[%s]]></ToUserName>
        <FromUserName><![CDATA[%s]]></FromUserName>
        <CreateTime>%d</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[亲爱的%s，您好，欢迎关注小麦芬烘焙工作室，请致电13370882078订购或者访问小麦芬烘焙小店小程序]]></Content>
        </xml>""" % (self.__properties['FromUserName'], self.__properties['ToUserName'],
                     int(time()), self.member.nickname if self.member and self.member.nickname else "")

        return body

    def generate_location_body(self):
        body = """<xml>
                <ToUserName><![CDATA[%s]]></ToUserName>
                <FromUserName><![CDATA[%s]]></FromUserName>
                <CreateTime>%d</CreateTime>
                <MsgType><![CDATA[text]]></MsgType>
                <Content><![CDATA[青岛市李沧区九水路227号宝龙城市广场彩虹城三层小麦芬烘焙课堂]]></Content>
            </xml>""" % (self.__properties['FromUserName'], self.__properties['ToUserName'], int(time()))

        logger.debug('location message body: %s', body)

        return body

    def set_value(self, tag, value):
        self.__properties[tag] = value

    def get_value(self, tag):
        return self.__properties.get(tag)

    @property
    def type(self):
        return self.__properties['MsgType'];

    @property
    def event(self):
        return self.__properties.get('Event');

    @property
    def event_key(self):
        return self.__properties.get('EventKey')

    def check_signature(self, key):
        if 'sign' not in self.__properties:
            return False
        sign = self.__properties.pop('sign')
        t = [(k, v) for k,v in self.__properties.items()]
        self.__properties['sign'] = sign
        t.sort()
        t.append(('key', key))
        r = hashlib.md5(('&'.join(['='.join(i) for i in t])).encode('utf8')).hexdigest().upper()

        if r == sign:
            return True

        return False

    def process_event(self):
        if self.event == 'subscribe':
            info = get_member_info(openid)
            if 'openid' in info:
                member = Member.query.filter_by(weixin_openid=info.get('openid'))
                if member:
                    member.weixin_unionid = info.get('unionid')
                    member.gender = info.get('sex')
                    member.nickname = info.get('nickname')
                    self.member = member
            body = self.generate_response_body()
            response = make_response()
            response.headers['Content-type'] = 'application/xml'
            response.data = body.encode('utf-8')

            return response
        elif self.event == 'user_pay_from_pay_cell':
            data = {
                "productType": {
                    "value":"小麦芬烘焙工作室",
                    },
                "name":{
                    "value":"用心做，不做作",
                    "color":"#754c24"
                    },
                'accountType':{"value":"金额"},
                'account':{
                    "value": '￥' + str(int(self.get_value('Fee')) / 100),
                    "color":"#754c24"
                    },
                "time": {
                    "value": datetime.fromtimestamp(int(self.get_value('CreateTime'))).strftime('%X'),
                    "color":"#754c24"
                    },
                "remark":{
                    "value":"只用天然乳脂奶油。只用优质供应商的高品质原料",
                    "color":"#754c24"
                    }
            }
            body = json.dumps(self.generate_template_body('9EMNExtVNw81PxQt7dT0mTeWhJjDOvmo_dn48Y_tdLE',
                                             self.get_value('FromUserName'), url_for('shop.home'), data))
            post_weixin_api('https://api.weixin.qq.com/cgi-bin/self/template/send', body, access_token=shoppoint.access_token)

            return ""
        elif self.event == 'submit_membercard_user_info':
            #if not openid:
            #    openid = self.get_value('FromUserName')
            #info = get_member_info(openid)
            #print (info)
            data = {
                "first": {
                    "value":"感谢您成为卡诺烘焙会员",
                    },
                "cardNumber":{
                    "value": self.get_value('UserCardCode'),
                    "color":"#754c24"
                    },
                'type':{"value":"卡诺"},
                'address': {
                    "value": shoppoint.address,
                    "color":"#754c24"
                    },
                "remark":{
                    "value":"只用天然乳脂奶油。只用优质供应商的高品质原料",
                    "color":"#754c24"
                    }
            }
            body = json.dumps(self.generate_template_body('YXKo5tUIvkDpd_x9T6HgI3twkIGMLrcDoVIBWNPOkUA',
                                                      self.get_value('FromUserName'), url_for('shop.home'), data))
            post_weixin_api('https://api.weixin.qq.com/cgi-bin/self/template/send', body, access_token=shoppoint.access_token)

            return ""
        elif self.event == 'CLICK':
            if self.event_key == 'my_phone':
                body = self.generate_response_body()
                response = make_response()
                response.headers['Content-type'] = 'application/xml'
                response.data = body.encode('utf-8')

                return response
            elif self.event_key == 'my_location':
                body = self.generate_location_body()
                response = make_response()
                response.headers['Content-type'] = 'application/xml'
                response.data = body.encode('utf-8')

                return response
        else:
            return ""

    @classmethod
    def parse_message(cls, xmlbody):
        try:
            root = etree.fromstring(xmlbody)

            message = Message()
            for e in root:
                logger.debug('xml tag=[%s], content=[%s]', e.tag, e.text)
                message.set_value(e.tag, e.text)

            return message
        except Exception as e:
            return None
