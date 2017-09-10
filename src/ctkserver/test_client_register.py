from socket import *
from ctkserver.config import load_config
from ctkserver.commons import send_msg, recv_msg
import msgpack

CONFIG = load_config()

HOST = CONFIG.HOST
PORT = CONFIG.PORT
BUFSIZE = CONFIG.BUFSIZE
ADDR = (HOST, PORT)

tcpCliSock = socket(AF_INET, SOCK_STREAM)
tcpCliSock.connect(ADDR)

data_json = {
    "action": "user-register",
    "parameters": {
        "mail-address": "vencent.stevens@gmail.com",
        "username": "lavender",
        "nickname": "lavender",
        "password": "pass_lavender",
        "fingerprint": "FINGERPRINT1"
    }
}
data = msgpack.dumps(data_json)
send_msg(tcpCliSock, data)

while True:
    recv = recv_msg(tcpCliSock)
    if recv:
        data = msgpack.loads(recv, encoding='utf-8')
        print("Received data:%s" % data)

        if data == {"status": "success", "description": "Bye-bye"}:
            break

tcpCliSock.close()
