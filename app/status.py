STATUS_OK = 0
STATUS_NO_REQUIRED_HEADERS = 1000
STATUS_NO_REQUIRED_ARGS = 1001
STATUS_NO_RESOURCE = 2000
STATUS_SOLD_OUT = 2001
STATUS_CANNOT_LOGIN = 3000
STATUS_TOKEN_INVALID = 3001
STATUS_TOKEN_EXPIRED = 3002
STATUS_NO_ORDER_STATUS = 4000
STATUS_NO_VALUE_CARD_INFO = 4001
STATUS_CANNOT_DECRYPT = 5001

MESSAGES = {
    STATUS_NO_REQUIRED_HEADERS: 'access token or version was not existed in request header',
    STATUS_NO_REQUIRED_ARGS: "no %s argument(s) in request",
    STATUS_NO_RESOURCE: 'The resource you required was not existed in system',
    STATUS_SOLD_OUT: 'the product(s) was sold out',
    STATUS_CANNOT_LOGIN: 'You cannot login sytem using code: %s',
    STATUS_TOKEN_INVALID: 'the access token in header was invalid',
    STATUS_TOKEN_EXPIRED: 'the access token in header was expired',
    STATUS_NO_ORDER_STATUS: 'status code is invalid in request',
    STATUS_NO_VALUE_CARD_INFO: 'value card info was not binding to the member',
    STATUS_CANNOT_DECRYPT: 'cannot decrypt the request things',
}
