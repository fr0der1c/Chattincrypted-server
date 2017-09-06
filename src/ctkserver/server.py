import socketserver, json, mysql.connector
from ctkserver.config import load_config
from ctkserver.predefined_text import JSONS

CONFIG = load_config()
LOGGEDIN_USERS = {}


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
                _log_in(parameters["username"])
                return JSONS["successfully-login"]
            else:
                return JSONS["incorrect-password"]
        else:
            return JSONS["no-such-user"]
    else:
        return JSONS['incomplete_parameters']


def action_update_personal_info(parameters):
    query = "SELECT nickname,password,signature,avatar FROM ctk_users WHERE username=%s"
    cursor.execute(query, (parameters["username"],))
    fetch_result = cursor.fetchall()
    if fetch_result:
        nickname = fetch_result[0][0]
        password = fetch_result[0][1]
        signature = fetch_result[0][2]
        avatar = fetch_result[0][3]
        if "new-nickname" in parameters:
            nickname = parameters["new-nickname"]
        if "new-passwd" in parameters:
            password = parameters["new-passwd"]
        if "new-signature" in parameters:
            signature = parameters["new-signature"]
        if "new-avatar" in parameters:
            avatar = parameters["new-avatar"]
        try:
            query = "UPDATE (nickname,password,signature,avatar) VALUES (%s,%s,%s,%s) in ctk_users WHERE username=%s"
            cursor.execute(query, (nickname, password, signature, avatar))
            mysql_conn.commit()
            return JSONS["successfully-updated-info"]
        except:
            return JSONS["database_error"]
    else:
        return JSONS["unexpected_behaviour"]


def action_send_message(parameters):
    if "type" in parameters and "time" in parameters and "receiver" in parameters:
        if "type" == "text":
            pass
        elif "type" == "file":
            pass

    else:
        return JSONS['incomplete_parameters']


# Function name: _offline_user_clean
# Description: Clean offline users in LOGGEDIN_USERS
# Return value: no return value
def _offline_user_clean():
    for (k, v) in LOGGEDIN_USERS.items():
        if _get_time() - v["time"] > 60:
            LOGGEDIN_USERS.pop(k)


# Function name: _schedule
# Description: Schedule a function to run every interval(seconds)
# Return value: no return value
def _schedule(func_to_run, interval_second):
    import time
    while True:
        func_to_run()
        time.sleep(interval_second)


# Function name: _logged_in
# Description: Check if a user is (precisely) logged in
# Return value: True/False
def _logged_in(username):
    global LOGGEDIN_USERS
    if username in LOGGEDIN_USERS and _get_time() - LOGGEDIN_USERS[username]["time"] <= 60:
        return True
    else:
        return False


# Function name: _log_in
# Description: Log in a new user and return its ID
# Return value: user ID
def _log_in(username):
    global LOGGEDIN_USERS
    id = _generate_random_code()
    while id in LOGGEDIN_USERS:
        id = _generate_random_code()
    LOGGEDIN_USERS[username] = {
        "id": id,
        "time": _get_time(),
    }
    return id


# Function name: _get_time
# Description: Get timestamp of now
# Return value: timestamp(s)
def _get_time():
    import time
    now = int(time.time())
    return now


# Function name: _generate_random_code
# Description: Generate ramdom code
# Return value: 80-bit ramdom code
def _generate_random_code():
    import random
    seed = "1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()_+=-"
    sa = []
    for i in range(80):
        sa.append(random.choice(seed))
    salt = ''.join(sa)
    return salt


# Function name: do_action
# Description: Select an specific action to do
# Return value: a dict to return to client
def do_action(action, parameters):
    actions = {
        "user-register": action_user_register,
        "user-login": action_user_login,
        "update-personal-info": action_update_personal_info,
        "send-message": action_send_message,
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
                    if 'username' in locals().keys():
                        send_data_json = bytes("This is %s" % username, encoding=CONFIG.ENCODE)
                        sock.sendall(send_data_json)
                    if accept_data_json:
                        print("Accepted data json %s" % accept_data_json)
                    try:
                        accept_data = json.loads(accept_data_json)
                        if "parameters" in accept_data and "action" in accept_data:
                            if accept_data["action"] == "Bye-bye":
                                send_data = "Bye-bye"
                            else:
                                # If action is not "Bye-bye"
                                send_data = do_action(accept_data["action"], accept_data["parameters"])
                                if send_data["description"] == "Login successfully":
                                    username = accept_data["parameters"]["username"]
                            send_data_json = bytes(json.dumps(send_data), encoding=CONFIG.ENCODE)
                        else:
                            # if action and parameters is not present together
                            send_data_json = bytes(json.dumps(JSONS['incomplete_parameters']), encoding=CONFIG.ENCODE)
                        sock.sendall(send_data_json)
                    except json.decoder.JSONDecodeError:
                        # Not a JSON file
                        send_data_json = bytes(json.dumps(JSONS['unexpected_behaviour']), encoding=CONFIG.ENCODE)
                        sock.sendall(send_data_json)
                except ConnectionResetError:
                    # Client trying to connect, but server closed the connection
                    print("ConnectionResetError")
                    break
                except BrokenPipeError:
                    # Server trying to write to socket, but client closed the connection
                    print("BrokenPipeError")
                    break

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
