from flask import current_app, json

from flask_restful.reqparse import RequestParser

from urllib.parse import urlencode
from urllib.request import urlopen
#from urllib.request import Request

from .base import BaseResource
from ..models import Shoppoint, Partment, MemberOpenid, Product, Promotion


class QRCodeResource(BaseResource):
    def post(self, shopcode):
        parser = RequestParser()
        parser.add_argument('X-PARTMENT', type=str, required=True, location='headers', help='partment code must be required')
        parser.add_argument('X-ACCESS-TOKEN', type=str, location='headers', required=True, help='access token must be required')
        parser.add_argument('path', type=str, required=True, help='program path must be required')
        parser.add_argument('id', type=int, required=True, help='product/promotion id  must be required')
        parser.add_argument('type', type=str, required=True, help='type[promotion/product]  must be required')
        data = parser.parse_args()

        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        partment = Partment.query.filter_by(shoppoint_id=shop.id, code=data['X-PARTMENT']).first_or_404()
        member = MemberOpenid.query.filter_by(shoppoint_id=shop.id, access_token=data['X-ACCESS-TOKEN']).first_or_404()
        if data['type'] == 'promotion':
          target = Promotion.query.get_or_404(data['id'])
          if target.shoppoint_id != shop.id:
              logger.warning(MESSAGES[STATUS_NO_RESOURCE])
              abort(404, status=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE])
        else:
          target = Product.query.get_or_404(data['id'])
          if target.shoppoint_id != shop.id:
              logger.warning(MESSAGES[STATUS_NO_RESOURCE])
              abort(404, status=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE])

        #path = data['path'] + '?code='+data['product'] + '&user='+member.openid
        # print(path)

        return self._generateQRCode(current_app.config['UPLOAD_FOLDER'], data['path'], partment, target, member, data['type'])

    def _generateQRCode(self, upload_folder, path, partment, target, user, type):
        data = {'auto_color': True}
        if type == 'promotion':
          data['path'] = path + '?id=' + str(target.id) + '&member=' + user.openid
        else:
          data['path'] = path + '?code=' + target.code + '&member=' + user.openid
        print(data)
        #url_param = urlencode(params).encode('utf-8')
        data = json.dumps(data).encode('utf-8')
        # with urlopen("https://api.weixin.qq.com/cgi-bin/wxaapp/createwxaqrcode?access_token=" + self.get_access_token(), data) as f:
        with urlopen("https://api.weixin.qq.com/wxa/getwxacode?access_token=" + partment.get_access_token(), data) as f:
            result = f.read()
            import os.path
            import os
            base_path = os.path.join(upload_folder, user.openid)
            print(base_path)
            try:
                os.mkdir(base_path)
            except Exception as e:
                pass
            file_path = os.path.join(base_path, str(target.id))+'.jpeg'
            image = open(file_path, 'wb')
            image.write(result)
            image.close()

            return {'qr_image_path': user.openid + '/' + str(target.id) + '.jpeg'}
