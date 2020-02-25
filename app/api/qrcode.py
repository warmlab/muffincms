from flask import current_app, json, request

from urllib.parse import urlencode
from urllib.request import urlopen

from ..models import Shoppoint, Partment, MemberOpenid, Product, Promotion
from ..status import STATUS_NO_RESOURCE, STATUS_NO_VALUE_CARD_INFO, MESSAGES

from . import api
from .base import login_required


def _generateQRCode(upload_folder, path, partment, target, user, type):
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

        try:
            os.mkdir(base_path)
        except Exception as e:
            pass
        file_path = os.path.join(base_path, str(target.id))+'.jpeg'
        image = open(file_path, 'wb')
        image.write(result)
        image.close()

        return {'qr_image_path': user.openid + '/' + str(target.id) + '.jpeg'}

@api.route('/qrcode', methods=['POST'])
@login_required
def qrcode():
    shop = Shoppoint.query.filter_by(code=request.headers.get('X-SHOPPOINT')).first_or_404()
    partment = Partment.query.filter_by(shoppoint_id=shop.id, code=request.headers.get('X-PARTMENT')).first_or_404()
    member = MemberOpenid.query.filter_by(shoppoint_id=shop.id, access_token=request.headers.get('X-ACCESS-TOKEN')).first_or_404()
    if request.json.get('type') == 'promotion':
      target = Promotion.query.get_or_404(request.json.get('id'))
      if target.shoppoint_id != shop.id:
          abort(make_response(jsonify(errcode=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE]), 404))
    else:
      target = Product.query.get_or_404(request.json.get('id'))
      if target.shoppoint_id != shop.id:
          abort(make_response(jsonify(errcode=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE]), 404))

    #path = request.json.get('path'] + '?code='+data['product') + '&user='+member.openid
    # print(path)

    return _generateQRCode(current_app.config['UPLOAD_FOLDER'], request.json.get('path'), partment, target, member, request.json.get('type'))
