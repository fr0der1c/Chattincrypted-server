# Echo client program  
from socket import *
from ctkserver.config import load_config
import json

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
data = json.dumps(data_json)

tcpCliSock.sendall(data.encode())

while True:
    data = json.loads(tcpCliSock.recv(BUFSIZE).decode())
    print("Received data:%s" % data)

    if data == {"status": "success", "description": "Bye-bye"}:
        break


tcpCliSock.close()
