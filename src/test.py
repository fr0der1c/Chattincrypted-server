# Echo server program
from socket import *
from time import ctime
from .config import default

HOST = '127.0.0.1'  # Symbolic name meaning all available interfaces
PORT = 50008  # Arbitrary non-privileged port
BUFSIZE = 1024
ADDR = (HOST, PORT)

tcpSerSock = socket(AF_INET, SOCK_STREAM)
tcpSerSock.bind(ADDR)
tcpSerSock.listen(5)

try:
    while True:
        print('waiting for connection...')
        tcpCliSock, addr = tcpSerSock.accept()
        print('...connected from:', addr)

        while True:
            data = tcpCliSock.recv(BUFSIZE).decode()
            if not data:
                break
            tcpCliSock.send(('[%s] %s' % (ctime(), data)).encode())


except KeyboardInterrupt:
    tcpSerSock.close()
    print('Keyboard interrupt. End.')