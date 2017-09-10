class Config(object):
    HOST = "127.0.0.1"
    PORT = 50008
    BUFSIZE = 10240000
    ENCODE = "utf8"
    DEBUG = False
    AVAILABLE_MESSAGE_TYPE = ["image", "file", "voice", "text"]
    DB = {
        'user': 'chattincrypted_user',
        'password': 'chattincrypted_pwd',
        'host': '127.0.0.1',
        'port': '3306',
        'database': 'chattincrypted',
        'raise_on_warnings': True,
    }
