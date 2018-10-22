from logging.config import dictConfig
from sys import stdout

logger = None

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        #'stream': 'ext://flask.logging.wsgi_errors_stream',
        'stream': stdout,
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

def init_logging(app):
    global logger
    logger = app.logger
