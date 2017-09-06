import socketserver, json
from .config import load_config

CONFIG = load_config()


# 创建一个类，继承自socketserver模块下的BaseRequestHandler类
class Server(socketserver.BaseRequestHandler):
    # 要想实现并发效果必须重写父类中的handle方法，在此方法中实现服务端的逻辑代码
    # （不用再写连接准备，包括bind()、listen()、accept()方法）
    def handle(self):
        while True:
            conn = self.request
            addr = self.client_address
            # 上面两行代码，等于 conn,addr = socket.accept()，
            # 只不过在socketserver模块中已经替我们包装好了，还替我们包装了包括bind()、listen()、accept()方法
            while True:
                accept_data = str(conn.recv(CONFIG.BUFSIZE), encoding=CONFIG.ENCODE)
                accept_data_json = json.loads(accept_data)
                print(accept_data_json)
                if accept_data_json["action"] == "byebye":
                    break
                send_data_json = accept_data_json
                send_data = bytes(json.dumps(send_data_json), encoding=CONFIG.ENCODE)
                conn.sendall(send_data)
            conn.close()


if __name__ == '__main__':
    server = socketserver.ThreadingTCPServer((CONFIG.HOST, CONFIG.PORT), Server)
    server.serve_forever()
