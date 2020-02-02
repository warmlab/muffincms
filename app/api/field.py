from flask_restful import fields

class DateTimeField(fields.DateTime):
    def format(self, value):
        if not value:
            return None

        if self.dt_format.lower() in ('rfc822', 'iso8601'):
            return super.format(value)
        return value.strftime(self.dt_format)

class WebAllowedField(fields.Raw):
    def format(self, value):
        return value & 0x01

class POSAllowedField(fields.Raw):
    def format(self, value):
        return value & 0x02

class PromoteAllowedField(fields.Raw):
    def format(self, value):
        return value & 0x04

class InPromoteField(fields.Raw):
    def format(self, value):
        return (value & 0x04) > 0
