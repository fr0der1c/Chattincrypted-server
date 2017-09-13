from socket import *
from ctkserver.config import load_config
from ctkserver.commons import recv_msg, send_msg

import msgpack
import threading
import datetime
import time

CONFIG = load_config()

HOST = CONFIG.REMOTE_HOST
PORT = CONFIG.REMOTE_PORT
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

        data_json = {
            "action": "get-my-contacts",
        }
        data_2 = msgpack.dumps(data_json)
        send_msg(tcpCliSock, data_2)


if __name__ == '__main__':
    data = msgpack.dumps(CONFIG.data_login_remote_wolfbolin)
    send_msg(tcpCliSock, data)

    sender = SendingThread()
    refresher = ReceivingThread()

    refresher.start()
    sender.start()
    refresher.join()
    sender.join()

    tcpCliSock.close()
