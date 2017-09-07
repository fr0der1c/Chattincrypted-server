import json
import socketserver
import msgpack
import mysql.connector
from commons import get_time
from ctkserver.config import load_config
from ctkserver.predefined_text import JSONS
from ctkserver.user import log_in, heartbeat

CONFIG = load_config()
LOGGEDIN_USERS = {}


def action_user_register(parameters, username=None):
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


def action_user_login(parameters, username=None):
    if "username" in parameters and "password" in parameters:
        query = "SELECT password FROM ctk_users WHERE username=%s"
        cursor.execute(query, (parameters["username"],))
        fetch_result = cursor.fetchall()
        if fetch_result:
            if fetch_result[0][0] == parameters["password"]:
                log_in(LOGGEDIN_USERS, parameters["username"])
                return JSONS["successfully-login"]
            else:
                return JSONS["incorrect-password"]
        else:
            return JSONS["no-such-user"]
    else:
        return JSONS['incomplete_parameters']


def action_update_personal_info(parameters, username=None):
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
            return JSONS["internal_error"]
    else:
        return JSONS["unexpected_behaviour"]


def action_send_message(parameters, username=None):
    if "type" in parameters and "time" in parameters and "receiver" in parameters:
        if parameters["type"] in CONFIG.AVAILABLE_MESSAGE_TYPE:
            message = {
                'type': parameters['type'],
                'time': parameters['time'],
                'receiver': parameters['receiver'],
                'sender': parameters['sender']
            }
            if parameters["type"] == "text":
                message["message"] = parameters["message"]
            else:
                pass
                # save file
        else:
            return JSONS["unexpected_behaviour"]
    else:
        return JSONS['incomplete_parameters']


def action_heartbeat(username=None):
    if username:
        heartbeat(LOGGEDIN_USERS, username)
        return JSONS["heartbeat"]
    else:
        return JSONS["unexpected_behaviour"]


# Function name: _offline_user_clean
# Description: Clean offline users in LOGGEDIN_USERS
# Return value: no return value
def _offline_user_clean():
    for (k, v) in LOGGEDIN_USERS.items():
        if get_time() - v["time"] > 60:
            LOGGEDIN_USERS.pop(k)


# Function name: do_action
# Description: Select an specific action to do
# Return value: a dict to return to client
def do_action(action, parameters, username=None):
    actions = {
        "user-register": action_user_register,
        "user-login": action_user_login,
        "update-personal-info": action_update_personal_info,
        "send-message": action_send_message,
        "heartbeat": action_heartbeat,
    }
    if action in actions:
        if username:
            return actions[action](parameters, username=username)
        else:
            return actions[action](parameters)
    else:
        return JSONS["no_such_action"]


class Server(socketserver.BaseRequestHandler):
    def handle(self):
        sock = self.request
        address = self.client_address
        print("[INFO]{} connected.".format(address))
        while True:
            try:
                recv = sock.recv(CONFIG.BUFSIZE)
                accept_data_json = recv
                if 'username' in locals().keys():
                    send_data_json = msgpack.dumps("This is %s" % username)
                    sock.sendall(send_data_json)
                accept_data = msgpack.loads(accept_data_json,encoding='utf-8')
                if accept_data_json:
                    print("[INFO]Accepted data %s." % accept_data)
                if "parameters" in accept_data and "action" in accept_data:
                    # If Bye-bye
                    if accept_data["action"] == "Bye-bye":
                        send_data = JSONS["bye-bye"]
                        send_data_json = msgpack.dumps(send_data)
                        break
                    else:
                        if "username" in locals().keys():
                            send_data = do_action(accept_data["action"], accept_data["parameters"],
                                                  username=username)
                        else:
                            send_data = do_action(accept_data["action"], accept_data["parameters"])
                        send_data_json = msgpack.dumps(send_data)

                        # if successfully log in, save username to variable username
                        if send_data["description"] == "Login successfully":
                            username = accept_data["parameters"]["username"]
                            print("[INFO]User {} logged in.".format(username))
                else:
                    # if action and parameters is not present together
                    send_data_json = msgpack.dumps(JSONS['incomplete_parameters'])
                sock.sendall(send_data_json)
            except msgpack.exceptions.UnpackValueError:
                # Client closed connection
                print("[INFO]Client closed the connection.")
                break
            except msgpack.exceptions.ExtraData:
                # Not a msgpack file
                print("[EXCEPTION]Not a msgpack file")
                break
            except ConnectionResetError:
                # Client trying to connect, but server closed the connection
                print("[WARNING]ConnectionResetError.")
                break
            except BrokenPipeError:
                # Server trying to write to socket, but client closed the connection
                print("[INFO]Client closed the connection.")
                break
            except OSError as e:
                print("[ERROR]OS ERROR %s." % e)
                break
        print("[INFO]Socket close.")
        sock.close()


if __name__ == '__main__':
    # Connect to database
    mysql_conn = mysql.connector.connect(**CONFIG.MYSQL_CONFIG)
    cursor = mysql_conn.cursor()

    # Start TCP server
    server = socketserver.ThreadingTCPServer((CONFIG.HOST, CONFIG.PORT), Server)
    print("[INFO]Sever started on port %s." % CONFIG.PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        cursor.close()
        mysql_conn.close()
        print("[INFO]Server stopped.")
