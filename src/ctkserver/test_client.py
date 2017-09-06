# Echo client program  
from socket import *
import json

HOST = '127.0.0.1'
PORT = 50007  # The same port as used by the server
BUFSIZE = 1024
ADDR = (HOST, PORT)

tcpCliSock = socket(AF_INET, SOCK_STREAM)
tcpCliSock.connect(ADDR)

data_json = {
    "action": "user-register",
    "parameters": {
        "mail-address": "frederic.t.chan@gmail.com",
        "username": "frederic",
        "nickname": "frederic",
        "password": "pass_frederic",
        "fingerprint": "FINGERPRINT"
    }
}
data = json.dumps(data_json)

tcpCliSock.sendall(data.encode())

while True:

    data = tcpCliSock.recv(BUFSIZE).decode()
    print("Received data:%s" % data)
    """
        if data == {"status": "success", "description": "Bye-bye"}:
        break
    """

    break

tcpCliSock.close()
