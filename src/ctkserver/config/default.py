class Config(object):
    HOST = "127.0.0.1"
    PORT = 50008
    BUFSIZE = 1024
    ENCODE = "utf8"
    AVAILABLE_MESSAGE_TYPE = ["image", "file", "voice", "text"]
    MYSQL_CONFIG = {
        'user': 'chattincrypted_user',
        'password': 'chattincrypted_pwd',
        'host': '127.0.0.1',
        'port': '3306',
        'database': 'chattincrypted',
        'raise_on_warnings': True,
    }
