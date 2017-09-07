# Echo client program
from socket import *
from ctkserver.config import load_config
import msgpack

CONFIG = load_config()

HOST = CONFIG.HOST
PORT = CONFIG.PORT
BUFSIZE = CONFIG.BUFSIZE
ADDR = (HOST, PORT)

tcpCliSock = socket(AF_INET, SOCK_STREAM)
tcpCliSock.connect(ADDR)

data_json = {
    "action": "user-login",
    "parameters": {
        "username": "frederic",
        "password": "pass_frederic",
    }
}
data = msgpack.dumps(data_json)

tcpCliSock.sendall(data)

while True:
    data = msgpack.loads(tcpCliSock.recv(BUFSIZE), encoding="utf-8")
    print("Received data:%s" % data)

    if data == {"status": "success", "description": "Bye-bye"}:
        break

tcpCliSock.close()
