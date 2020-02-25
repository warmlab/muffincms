import os, hashlib

from time import time
from datetime import datetime

from flask import current_app, request, jsonify, abort, make_response

from werkzeug.datastructures import FileStorage

from PIL import Image as PLImage

from ..status import STATUS_NO_REQUIRED_ARGS, STATUS_NO_RESOURCE, MESSAGES

from ..models import db
from ..models import Shoppoint, Image

from . import api
from .base import UserView, login_required


@api.route('/images', methods=['GET'])
@login_required
def images():
    shop = Shoppoint.query.filter_by(code=request.headers['X-SHOPPOINT']).first_or_404()
    images = Image.query.filter(Image.type.op('&')(int(request.args.get('type')))>0, Image.shoppoint_id==shop.id).all()

    return jsonify([i.to_json() for i in images])


class ImageView(UserView):
    methods = ['GET', 'POST', 'DELETE']
    def generate_filename(self, filename):
        pos = filename.rfind('.')
        if pos > 0:
            ext = filename[pos+1:]
            return '.'.join([str(time()), ext])
        else:
            return str(time())

    def generate_hash_value(self, file_storage):
        md5 = hashlib.md5()
        md5.update(file_storage.read())
        file_storage.seek(0)

        return md5.hexdigest()

    def get(self):
        shop = Shoppoint.query.filter_by(code=request.headers['X-SHOPPOINT']).first_or_404()
        image = Image.query.filter_by(name=request.args.get('name'), shoppoint_id=shop.id).first()
        if not image:
            abort(make_response(jsonify(errcode=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE] % 'image info'), 404))

        return jsonify(image.to_json())

    def post(self):
        shop = Shoppoint.query.filter_by(code=request.headers['X-SHOPPOINT']).first_or_404()

        try:
            image_type = int(request.values.get('type'))
        except Exception as e:
            print('image type is invalid, set it to default value 2')
            image_type = 2
        upload_file = request.files.get('upload-files')

        hash_value = self.generate_hash_value(upload_file)
        filename = self.generate_filename(upload_file.filename)
        print('upload file name: ', upload_file.filename, ' hash value ', hash_value)

        image = Image.query.filter_by(hash_value=hash_value, shoppoint_id=shop.id).first()
        if not image:
            print('to create an image item')
            image = Image()
            image.hash_value = hash_value
            image.name = filename
            image.type = 0 # 
            image.shoppoint_id = shop.id
            image.shoppoint = shop
            db.session.add(image)

            original_file = os.path.join(current_app.config['UPLOAD_FOLDER'], 'full', filename)
            upload_file.save(original_file) # original file
            if int(request.values.get('type')) != 4:
                im = PLImage.open(original_file)
                im.thumbnail((200,200))
                im.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename), 'JPEG')
            else:
                im = PLImage.open(original_file)
                im.thumbnail((750,330))
                im.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename), 'JPEG')

        image.title = request.values.get('title')
        image.note = request.values.get('note')
        image.type = image.type | image_type

        db.session.commit()
        return jsonify(image.to_json()), 201

    def delete(self):
        shop = Shoppoint.query.filter_by(code=request.headers['X-SHOPPOINT']).first_or_404()
        image = Image.query.filter_by(id=request.json.get('id'), shoppoint_id=shop.id).first()
        if not image:
            abort(make_response(jsonify(errcode=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE]), 404))

        if image.type == 4:
            try:
                os.unlink(os.path.join(current_app.config['UPLOAD_FOLDER'], 'full', image.name))
                os.unlink(os.path.join(current_app.config['UPLOAD_FOLDER'], image.name))
            except Exception as e:
                print('remove file error', e)
            db.session.delete(image)
        else:
            image.type = image.type & ~4

        db.session.commit()

        return jsonify(image.to_json()), 201


api.add_url_rule('/image', view_func=ImageView.as_view('image'))
