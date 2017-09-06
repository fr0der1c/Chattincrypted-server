# Echo client program  
from socket import *
import json

HOST = '127.0.0.1'
PORT = 50007  # The same port as used by the server
BUFSIZE = 1024
ADDR = (HOST, PORT)

tcpCliSock = socket(AF_INET, SOCK_STREAM)
tcpCliSock.connect(ADDR)
while True:
    data_json = {
        "action": "register",
        "parameters": {
            "mail-address": "frederic.t.chan@gmail.com",
            "username": "frederic",
            "nickname": "frederic",
            "password": "pass_frederic",
            "fingerprint": "FINGERPRINT"
        }
    }
    data = json.dumps(data_json)
    if not data:
        break
    tcpCliSock.send(data.encode())
    data = tcpCliSock.recv(BUFSIZE).decode()
    if not data:
        break
    print(data)

tcpCliSock.close()
