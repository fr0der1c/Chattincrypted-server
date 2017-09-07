import socketserver
import msgpack
import os
import time
import mysql.connector
import threading
from ctkserver.commons import get_time, generate_md5
from ctkserver.config import load_config
from ctkserver.predefined_text import TEXT, text
from ctkserver.user import log_in, heartbeat

CONFIG = load_config()
LOGGED_IN_USERS = {}


# Function name: action_user_register
# Description: Handle register request from client
# Return value: Json-like text
def action_user_register(parameters, username=None):
    query = "SELECT * FROM ctk_users WHERE username=%s"
    cursor.execute(query, (parameters["username"],))
    # If found entry, tell client that this username is already in use.
    if cursor.fetchall():
        return TEXT["username_already_in_use"]
    # If all parameters are met, add new user. Else tell client incomplete parameters.
    if "mail-address" in parameters and "username" in parameters and "nickname" in parameters and \
                    "password" in parameters and "fingerprint" in parameters:
        query = "INSERT INTO ctk_users (mail, username, nickname, password, fingerprint) " \
                "VALUES (%s, %s, %s, %s, %s) "
        cursor.execute(query, (parameters["mail-address"], parameters["username"], parameters["nickname"],
                               parameters["password"], parameters["fingerprint"]))
        mysql_conn.commit()
        return TEXT["successfully_registered"]
    else:
        return TEXT['incomplete_parameters']


# Function name: action_user_login
# Description: Handle login request from client
# Return value: Json-like text
def action_user_login(parameters, username=None):
    if "username" in parameters and "password" in parameters:
        query = "SELECT password FROM ctk_users WHERE username=%s"
        cursor.execute(query, (parameters["username"],))
        fetch_result = cursor.fetchall()
        if fetch_result:
            if fetch_result[0][0] == parameters["password"]:
                log_in(LOGGED_IN_USERS, parameters["username"])
                return TEXT["successfully-login"]
            else:
                return TEXT["incorrect-password"]
        else:
            return TEXT["no-such-user"]
    else:
        return TEXT['incomplete_parameters']


# Function name: action_update_personal_info
# Description: Handle update personal info request from client
# Return value: Json-like text
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
            return TEXT["successfully-updated-info"]
        except:
            return TEXT["internal_error"]
    else:
        return TEXT["unexpected_behaviour"]


# Function name: action_send_message
# Description: Handle messages sent from clients
# Return value: Json-like text
def action_send_message(parameters, username=None):
    print("action_send_message:%s" % username)
    if "type" in parameters and "time" in parameters and "receiver" in parameters:
        # Validate type and sender
        if parameters["type"] in CONFIG.AVAILABLE_MESSAGE_TYPE and parameters["sender"] == username:
            message = {
                'type': parameters['type'],
                'time': parameters['time'],
                'receiver': parameters['receiver'],
                'sender': parameters['sender']
            }
            # Generate message_id
            message["message_id"] = generate_md5(message["type"] + message["time"] + message["sender"] +
                                                 message["receiver"])
            if parameters["type"] == "text":
                message["message"] = parameters["message"]

                # Save message to database
                query = "INSERT INTO ctk_messages " \
                        "(message_id, if_sent, type, time, sender,receiver,message,is_attachment) " \
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                cursor.execute(query, (message["message_id"], False, message["type"], message["time"],
                                       message["sender"], message["receiver"], message["message"], False))
                mysql_conn.commit()

                return text("message_sent", message["message_id"])
            else:
                # Save file to local
                with open(os.path.join(os.getcwd(), "attachments/{}".format(message["message_id"])), 'wb') as f:
                    f.write(parameters["data"])

                # Save message to database
                query = "INSERT INTO ctk_messages " \
                        "(message_id, if_sent, type, time, sender,receiver,is_attachment) " \
                        "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                cursor.execute(query, (message["message_id"], False, message["type"], message["time"],
                                       message["sender"], message["receiver"], True))
                mysql_conn.commit()

                return text("message_sent", message["message_id"])
        else:
            return TEXT["unexpected_behaviour"]
    else:
        return TEXT['incomplete_parameters']


# Function name: action_heartbeat
# Description: Handle heartbeat from client
# Return value: Json-like text
def action_heartbeat(parameters, username=None):
    if username:
        heartbeat(LOGGED_IN_USERS, username)
        return TEXT["heartbeat"]
    else:
        return TEXT["unexpected_behaviour"]


# Function name: do_action
# Description: Select an specific action to do
# Return value: a dict to return to client
def do_action(action, parameters, username=None):
    print("do_action username:%s" % username)
    actions = {
        "user-register": action_user_register,
        "user-login": action_user_login,
        "update-personal-info": action_update_personal_info,
        "send-message": action_send_message,
        "heartbeat": action_heartbeat,
    }
    if action in actions:
        # If logged in, pass to specific action function
        if username:
            return actions[action](parameters, username=username)
        # If not logged in and the request doesn't require to be logged in
        elif action == "user-login" or action == "user-register":
            return actions[action](parameters)
        # If not logged in and the request needs to be logged in
        else:
            return text("not_login")
    # Action not found
    else:
        return TEXT["no_such_action"]


# Class: RequestHandler
# Description: Handle each client
class RequestHandler(socketserver.BaseRequestHandler):
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
                accept_data = msgpack.loads(accept_data_json, encoding='utf-8')
                if accept_data_json:
                    print("[INFO]Accepted data %s." % accept_data)
                if "parameters" in accept_data and "action" in accept_data:
                    # If Bye-bye
                    if accept_data["action"] == "Bye-bye":
                        send_data = TEXT["bye-bye"]
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
                    send_data_json = msgpack.dumps(TEXT['incomplete_parameters'])
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


# Class: SendingThread
# Description: Check if logged in users have new message and send it to them.
class SendingThread(threading.Thread):
    def run(self):
        pass
        # if


# Class: RemoveOfflineUserThread
# Description: Remove offline users from LOGGED_IN_USERS every minute
class RemoveOfflineUserThread(threading.Thread):
    def run(self):
        while True:
            for (k, v) in LOGGED_IN_USERS.items():
                if get_time() - v["time"] > 60:
                    LOGGED_IN_USERS.pop(k)
            time.sleep(60)


if __name__ == '__main__':
    # Connect to database
    mysql_conn = mysql.connector.connect(**CONFIG.MYSQL_CONFIG)
    cursor = mysql_conn.cursor()

    # Start TCP server
    server = socketserver.ThreadingTCPServer((CONFIG.HOST, CONFIG.PORT), RequestHandler)
    print("[INFO]Sever started on port %s." % CONFIG.PORT)
    try:
        server.serve_forever()

        # Open threads for sending messages and removing offline users
        sending_thread = SendingThread()
        threads = [sending_thread]
        for each_thread in threads:
            each_thread.start()
    except KeyboardInterrupt:
        server.shutdown()
        cursor.close()
        mysql_conn.close()
        print("[INFO]Server stopped.")
