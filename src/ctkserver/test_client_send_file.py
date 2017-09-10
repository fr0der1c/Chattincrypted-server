from socket import *
from ctkserver.config import load_config
from ctkserver.commons import recv_msg, send_msg
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
            recv = recv_msg(tcpCliSock)
            if recv:
                data = msgpack.loads(recv, encoding="utf-8")
                print("Received data:%s" % data)
                if data == {"status": "success", "description": "Bye-bye"}:
                    break


class SendingThread(threading.Thread):
    def run(self):
        print("Sending thread start")
        time.sleep(2)
        with open('test_image.png', 'rb') as f:
            data_json = {
                "action": "send-message",
                "parameters": {
                    "type": "file",
                    "data": f.read(),
                    "receiver": "frederic",
                    "time1": "time",
                    "time": int(round(time.time() * 1000)),
                }
            }
        data_2 = msgpack.dumps(data_json, use_bin_type=True)
        send_msg(tcpCliSock, data_2)


if __name__ == '__main__':
    data_json = {
        "action": "user-login",
        "parameters": {
            "username": "lavender",
            "password": "pass_lavender",
        }
    }
    data = msgpack.dumps(data_json)
    send_msg(tcpCliSock, data)

    sender = SendingThread()
    refresher = ReceivingThread()

    refresher.start()
    sender.start()
    refresher.join()
    sender.join()

    tcpCliSock.close()
