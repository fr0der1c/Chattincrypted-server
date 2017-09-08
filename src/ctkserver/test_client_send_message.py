# Echo client program
from socket import *
from ctkserver.config import load_config
import msgpack
import threading
import time

CONFIG = load_config()

HOST = CONFIG.HOST
PORT = CONFIG.PORT
BUFSIZE = CONFIG.BUFSIZE
ADDR = (HOST, PORT)

tcpCliSock = socket(AF_INET, SOCK_STREAM)
tcpCliSock.connect(ADDR)


class ReceivingThread(threading.Thread):
    def run(self):
        print("Receiving thread start")
        while True:
            data = msgpack.loads(tcpCliSock.recv(BUFSIZE), encoding="utf-8")
            print("Received data:%s" % data)
            if data == {"status": "success", "description": "Bye-bye"}:
                break


class SendingThread(threading.Thread):
    def run(self):
        print("Sending thread start")
        time.sleep(2)
        data_json = {
            "action": "send-message",
            "parameters": {
                "type": "text",
                "message": "message",
                "receiver": "lavender",
                "time": "time",
            }
        }
        data_2 = msgpack.dumps(data_json)
        tcpCliSock.sendall(data_2)


if __name__ == '__main__':
    data_json = {
        "action": "user-login",
        "parameters": {
            "username": "lavender",
            "password": "pass_lavender",
        }
    }
    data = msgpack.dumps(data_json)
    tcpCliSock.sendall(data)

    sender = SendingThread()
    refresher = ReceivingThread()

    refresher.start()
    sender.start()
    refresher.join()
    sender.join()

    tcpCliSock.close()
