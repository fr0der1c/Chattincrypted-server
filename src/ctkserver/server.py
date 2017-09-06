import socketserver, json, mysql.connector
from ctkserver.config import load_config
from ctkserver.predefined_text import JSONS

CONFIG = load_config()


def action_user_register(parameters):
    query = "SELECT * FROM ctk_users WHERE username=%s"
    cursor.execute(query, (parameters["username"],))
    # If found entry, tell client that this username is already in use.
    if cursor.fetchall():
        return JSONS["username_already_in_use"]
    # If all parameters are met, add new user. Else tell client incomplete parameters.
    if "mail-address" in parameters and "username" in parameters and "nickname" in parameters and \
                    "password" in parameters and "fingerprint" in parameters:
        query = "INSERT INTO ctk_users (mail, username, nickname, password, fingerprint) " \
                "VALUES (%s, %s, %s, %s, %s) "
        cursor.execute(query, (parameters["mail-address"], parameters["username"], parameters["nickname"],
                               parameters["password"], parameters["fingerprint"]))
        mysql_conn.commit()
        return JSONS["successfully_registered"]
    else:
        return JSONS['incomplete_parameters']


def action_user_login(parameters):
    if "username" in parameters and "password" in parameters:
        query = "SELECT password FROM ctk_users WHERE username=%s"
        cursor.execute(query, (parameters["username"],))
        fetch_result = cursor.fetchall()
        if fetch_result:
            if fetch_result[0][0] == parameters["password"]:
                return JSONS["successfully-login"]
            else:
                return JSONS["incorrect-password"]
        else:
            return JSONS["no-such-user"]
    else:
        return JSONS['incomplete_parameters']


# Function name: do_action
# Description: Select an specific action to do
# Return value: a dict to return to client
def do_action(action, parameters):
    actions = {
        "user-register": action_user_register,
        "user-login": action_user_login,
    }
    if action in actions:
        return actions[action](parameters)
    else:
        return JSONS["no_such_action"]


# 创建一个类，继承自socketserver模块下的BaseRequestHandler类
class Server(socketserver.BaseRequestHandler):
    # 要想实现并发效果必须重写父类中的handle方法，在此方法中实现服务端的逻辑代码
    # （不用再写连接准备，包括bind()、listen()、accept()方法）
    def handle(self):
        while True:
            sock = self.request
            address = self.client_address
            # 上面两行代码，等于 sock,address = socket.accept()，
            # 只不过在socketserver模块中已经替我们包装好了，还替我们包装了包括bind()、listen()、accept()方法
            while True:
                try:
                    recv = sock.recv(CONFIG.BUFSIZE)
                    accept_data_json = str(recv, encoding=CONFIG.ENCODE)
                    if accept_data_json:
                        print("Accepted data json %s" % accept_data_json)
                    try:
                        accept_data = json.loads(accept_data_json)
                        if "parameters" in accept_data and "action" in accept_data:
                            if accept_data["action"] == "Bye-bye":
                                send_data = "Bye-bye"
                            else:
                                send_data = do_action(accept_data["action"], accept_data["parameters"])
                            send_data_json = bytes(json.dumps(send_data), encoding=CONFIG.ENCODE)
                        else:
                            send_data_json = bytes(json.dumps(JSONS['incomplete_parameters']), encoding=CONFIG.ENCODE)
                        sock.sendall(send_data_json)
                    except json.decoder.JSONDecodeError:
                        send_data_json = bytes(json.dumps(JSONS['unexpected_behaviour']), encoding=CONFIG.ENCODE)
                        sock.sendall(send_data_json)
                except ConnectionResetError:
                    pass
                except BrokenPipeError:
                    pass

            sock.close()


if __name__ == '__main__':
    mysql_conn = mysql.connector.connect(**CONFIG.MYSQL_CONFIG)
    cursor = mysql_conn.cursor()
    try:
        server = socketserver.ThreadingTCPServer((CONFIG.HOST, CONFIG.PORT), Server)
        print("Sever started on port %s." % CONFIG.PORT)
        server.serve_forever()
    except KeyboardInterrupt:
        cursor.close()
        mysql_conn.close()
        print("Keyboard interrupt")
