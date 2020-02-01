import os
from flask import Flask
from celery import Celery

from app.models import db
from config import config

def make_celery(app):
    celery = Celery('muffintaskq',
                    backend=app.config['CELERY_RESULT_BACKEND'],
                    broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                    with app.app_context():
                            return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

flask_app = Flask(__name__)
flask_app.config.from_object(config[os.getenv('FLASK_CONFIG') or 'default'])
db.init_app(flask_app)
app = make_celery(flask_app)
