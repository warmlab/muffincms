import os, hashlib

from time import time
from datetime import datetime

from flask import current_app, request

from flask_restful import abort
from flask_restful import fields, marshal_with
from flask_restful.reqparse import RequestParser

from werkzeug.datastructures import FileStorage

from ..logging import logger
from ..status import STATUS_NO_REQUIRED_ARGS, STATUS_NO_RESOURCE, MESSAGES

from ..models import db
from ..models import Shoppoint, Image

from .base import BaseResource

image_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'type': fields.Integer,
    #'hash_value': fields.String,
    'title': fields.String,
    'note': fields.String
}

def generate_filename(filename):
    pos = filename.rfind('.')
    if pos > 0:
        ext = filename[pos+1:]
        return '.'.join([str(time()), ext])
    else:
        return str(time())

def generate_hash_value(file_storage):
    md5 = hashlib.md5()
    md5.update(file_storage.read())
    file_storage.seek(0)

    return md5.hexdigest()

class ImageResource(BaseResource):
    @marshal_with(image_fields)
    def get(self, shopcode):
        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()
        parser = RequestParser()
        parser.add_argument('name', type=str, required=True, help='name must be required by getting image info')
        args = parser.parse_args()

        image = Image.query.filter_by(name=args['name'], shoppoint_id=shop.id).first()
        if not image:
            abort(404, status=STATUS_NO_RESOURCE, message=MESSAGES[STATUS_NO_RESOURCE] % 'image info')

        return image

    @marshal_with(image_fields)
    def post(self, shopcode):
        shop = Shoppoint.query.filter_by(code=shopcode).first_or_404()

        parser = RequestParser()
        parser.add_argument('upload-files', type=FileStorage, location='files', action="append", required=True, help='the upload files should be required')
        parser.add_argument('type', type=int)
        args = parser.parse_args()

        images = []
        upload_files = args['upload-files']
        logger.debug('upload files: %s', upload_files)
        for upload_file in upload_files:
            hash_value = generate_hash_value(upload_file)
            filename = generate_filename(upload_file.filename)
            logger.debug('upload file name: %s - %s', upload_file.filename, hash_value)

            image = Image.query.filter_by(hash_value=hash_value, shoppoint_id=shop.id).first()
            if not image:
                logger.debug('to create an image item')
                image = Image()
                image.hash_value = hash_value
                image.name = filename
                image.type = args['type']
                image.shoppoint_id = shop.id
                image.shoppoint = shop

                upload_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

                db.session.add(image)
                db.session.commit()
            else:
              image.type = args['type']
            images.append(image)
        return images
