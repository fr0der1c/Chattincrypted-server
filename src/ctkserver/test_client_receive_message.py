from socket import *
from ctkserver.config import load_config
from ctkserver.commons import recv_msg, send_msg

import msgpack
import threading

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
                print("Received data:%s" % recv)
                data = msgpack.loads(recv, encoding="utf-8")
                if data == {"status": "success", "description": "Bye-bye"}:
                    break


if __name__ == '__main__':
    data = msgpack.dumps(CONFIG.data_login_lavender)
    send_msg(tcpCliSock, data)

    refresher = ReceivingThread()
    refresher.start()
    refresher.join()

    tcpCliSock.close()
