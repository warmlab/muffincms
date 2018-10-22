import hashlib

from time import time
from datetime import datetime

from xml.etree import ElementTree as etree

from ..logging import logger

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

    def _generate_text_body(self):
        home_web = "http://m.wecakes.com"
        body = """<xml>
        <ToUserName><![CDATA[%s]]></ToUserName>
        <FromUserName><![CDATA[%s]]></FromUserName>
        <CreateTime>%d</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[亲爱的%s，您好，欢迎关注小麦芬烘焙工作室，请致电13370836021订购或者访问%s]]></Content>
        </xml>""" % (self.__properties['FromUserName'], self.__properties['ToUserName'],
                     int(time()), self.member.nickname if self.member and self.member.nickname else "", home_web)

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

    @classmethod
    def parse_message(xmlbody):
        try:
            root = etree.fromstring(xmlbody)

            message = Message()
            for e in root:
                logger.debug('xml tag=[%s], content=[%s]', e.tag, e.text)
                message.set_value(e.tag, e.text)

            return message
        except Exception as e:
            return None
