from flask_restful import fields

from ..logging import logger

class DateTimeField(fields.DateTime):
    def format(self, value):
        if not value:
            return None

        if self.dt_format.lower() in ('rfc822', 'iso8601'):
            return super.format(value)
        return value.strftime(self.dt_format)
