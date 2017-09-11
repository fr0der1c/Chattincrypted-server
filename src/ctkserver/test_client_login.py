from socket import *
from ctkserver.config import load_config
from ctkserver.commons import recv_msg, send_msg
import msgpack

CONFIG = load_config()

HOST = CONFIG.REMOTE_HOST
PORT = CONFIG.REMOTE_PORT
BUFSIZE = CONFIG.BUFSIZE
ADDR = (HOST, PORT)

tcpCliSock = socket(AF_INET, SOCK_STREAM)
tcpCliSock.connect(ADDR)

data = msgpack.dumps(CONFIG.data_login_lavender)

send_msg(tcpCliSock, data)

while True:
    recv = recv_msg(tcpCliSock)
    if recv:
        print(recv)
        data = msgpack.loads(recv, encoding="utf-8")
        print("Received data:%s" % data)
        if data == {"status": "success", "description": "Bye-bye"}:
            break
