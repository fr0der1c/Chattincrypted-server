# Echo client program  
from socket import *
from ctkserver.config import load_config
import json
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
print("data:%s"%data)
tcpCliSock.sendall(data)

while True:
    data = msgpack.loads(tcpCliSock.recv(BUFSIZE))
    print("Received data:%s" % data)

    if data == {"status": "success", "description": "Bye-bye"}:
        break


tcpCliSock.close()
