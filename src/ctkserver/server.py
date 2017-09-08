import socketserver
import msgpack
import os
import time
import threading
from sqlalchemy import Column, String, Boolean, Text, ForeignKey, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from ctkserver.commons import get_time, generate_md5
from ctkserver.config import load_config
from ctkserver.predefined_text import TEXT, text
from ctkserver.user import log_in, heartbeat

CONFIG = load_config()
LOGGED_IN_USERS = {}
ORMBaseModel = declarative_base()
db_engine = create_engine('mysql+pymysql://{}:{}@{}:{}/{}'
                          .format(CONFIG.DB['user'], CONFIG.DB['password'],
                                  CONFIG.DB['host'], CONFIG.DB['port'],
                                  CONFIG.DB['database']),
                          encoding='utf-8'
                          )
DBSession = sessionmaker(bind=db_engine)


class User(ORMBaseModel):
    __tablename__ = 'ctk_users'
    mail = Column(String(255))
    username = Column(String(40), primary_key=True)
    nickname = Column(String(40))
    password = Column(String(100), nullable=False)
    fingerprint = Column(String(100), nullable=False)
    avatar = Column(String(1024))

    def __repr__(self):
        return "<User `{}`>".format(self.username)


class Message(ORMBaseModel):
    __tablename__ = 'ctk_messages'
    message_id = Column(String(255), primary_key=True)
    if_sent = Column(Boolean, nullable=False)
    type = Column(String(10), nullable=False)
    time = Column(String(255), nullable=False)
    sender = Column(String(40), ForeignKey('ctk_users.username'), nullable=False)
    receiver = Column(String(40), ForeignKey('ctk_users.username'), nullable=False)
    message = Column(Text)
    is_attachment = Column(Boolean, nullable=False)

    def __repr__(self):
        return "<Message `{}`>".format(self.message_id)


class Attachment(ORMBaseModel):
    __tablename__ = 'ctk_attachments'
    message_id = Column(String(255), ForeignKey('ctk_messages.message_id'), primary_key=True)
    filename = Column(String(255), nullable=False)

    def __repr__(self):
        return "<Attachment `{}`>".format(self.message_id)


class Blacklist(ORMBaseModel):
    __tablename__ = 'ctk_blacklists'
    username = Column(String(40), ForeignKey('ctk_users.username'), primary_key=True)
    blocked_users = Column(Text, nullable=False)

    def __repr__(self):
        return "<Blacklist of `{}`:{}>".format(self.username, self.blocked_users)


class Contact(ORMBaseModel):
    __tablename__ = 'ctk_user_contacts'
    username = Column(String(40), ForeignKey('ctk_users.username'), primary_key=True)
    contacts = Column(Text, nullable=False)

    def __repr__(self):
        return "<Contact of `{}`:{}>".format(self.username, self.contacts)


# Class: RequestHandler
# Description: Handle each client
class RequestHandler(socketserver.BaseRequestHandler):
    # Function name: action_user_register
    # Description  : Handle register request from client
    # Return value : TEXT['incomplete_parameters'], TEXT["successfully_registered"] or TEXT["username_already_in_use"]
    @staticmethod
    def action_user_register(db_session, parameters, username=None):
        # Search in database if someone has already registered this username
        user = db_session.query(User).filter(User.username == parameters["username"]).first()
        if user:
            return TEXT["username_already_in_use"]

        # If all parameters are met, add new user. Else tell client incomplete parameters.
        if "mail-address" in parameters and "username" in parameters and "nickname" in parameters \
                and "password" in parameters and "fingerprint" in parameters:
            db_session.add(User(mail=parameters['mail-address'], username=parameters['username'],
                                nickname=parameters['nickname'], password=parameters['password'],
                                fingerprint=parameters['fingerprint']))
            db_session.commit()
            return TEXT["successfully_registered"]
        else:
            return TEXT['incomplete_parameters']

    # Function name: action_user_login
    # Description  : Handle login request from client
    # Return value : TEXT['incomplete_parameters'], TEXT["no-such-user"], TEXT["incorrect-password"] or
    #                TEXT["successfully-login"]
    @staticmethod
    def action_user_login(db_session, parameters, username=None):
        if "username" not in parameters or "password" not in parameters:
            return TEXT['incomplete_parameters']
        user = db_session.query(User).filter(User.username == parameters["username"]).first()
        if user:
            if user.password == parameters["password"]:
                log_in(LOGGED_IN_USERS, parameters["username"])
                return TEXT["successfully-login"]
            else:
                return TEXT["incorrect-password"]
        else:
            return TEXT["no-such-user"]

    # Function name: action_update_personal_info
    # Description  : Handle update personal info request from client
    # Return value : TEXT["unexpected_behaviour"], TEXT["internal_error"] or TEXT["successfully-updated-info"]
    @staticmethod
    def action_update_personal_info(db_session, parameters, username=None):
        if not username:
            return TEXT["not_login"]
        user = db_session.query(User).filter(User.username == parameters["username"]).first()
        if user:
            if "new-nickname" in parameters:
                user.nickname = parameters["new-nickname"]
            if "new-passwd" in parameters:
                user.password = parameters["new-passwd"]
            if "new-signature" in parameters:
                user.signature = parameters["new-signature"]
            if "new-avatar" in parameters:
                user.avatar = parameters["new-avatar"]
            db_session.commit()
            return TEXT["successfully-updated-info"]
        else:
            return TEXT["unexpected_behaviour"]

    # Function name: action_send_message
    # Description  : Handle messages sent from clients
    # Return value : TEXT['incomplete_parameters'], TEXT["unexpected_behaviour"] or
    #                text("message_sent", message["message_id"])
    @staticmethod
    def action_send_message(db_session, parameters, username=None):
        if not username:
            return TEXT["not_login"]
        if "type" not in parameters or "time" not in parameters or "receiver" not in parameters:
            return TEXT['incomplete_parameters']
        if parameters["type"] not in CONFIG.AVAILABLE_MESSAGE_TYPE:
            return TEXT['unexpected_behaviour']
        if not db_session.query(User).filter(User.username==parameters["receiver"]).first():
            return TEXT['unexpected_behaviour']
        message = {
            'type': parameters['type'],
            'time': parameters['time'],
            'receiver': parameters['receiver'],
            'sender': username
        }
        # Generate message_id
        message["message_id"] = generate_md5(message["type"] + message["time"] + message["sender"] +
                                             message["receiver"])

        if parameters["type"] == "text":
            message["message"] = parameters["message"]

            # Save message to database
            db_session.add(Message(message_id=message["message_id"], if_sent=False, type=message["type"],
                                   time=message["time"], sender=message["sender"],
                                   receiver=message["receiver"],
                                   message=message["message"], is_attachment=False))
            db_session.commit()

            return text("message_sent", message["message_id"])
        else:
            # Save file to local
            with open(os.path.join(os.getcwd(), "attachments/{}".format(message["message_id"])), 'wb') as f:
                f.write(parameters["data"])

            # Save message to database
            db_session.add(Message(message_id=message["message_id"], if_sent=False, type=message["type"],
                                   time=message["time"], sender=message["sender"],
                                   receiver=message["receiver"],
                                   is_attachment=True))
            db_session.commit()

            return text("message_sent", message["message_id"])

    # Function name: action_heartbeat
    # Description  : Handle heartbeat from client
    # Return value : TEXT["heartbeat"] or TEXT["unexpected_behaviour"]
    @staticmethod
    def action_heartbeat(db_session, parameters, username=None):
        if username:
            heartbeat(LOGGED_IN_USERS, username)
            return TEXT["heartbeat"]
        else:
            return TEXT["unexpected_behaviour"]

    # Function name: do_action
    # Description  : Select an specific action to do
    # Return value : a dict to return to client
    @staticmethod
    def do_action(db_session, action, parameters, username=None):
        if CONFIG.DEBUG:
            print("do_action username:%s" % username)
        actions = {
            "user-register": RequestHandler.action_user_register,
            "user-login": RequestHandler.action_user_login,
            "update-personal-info": RequestHandler.action_update_personal_info,
            "send-message": RequestHandler.action_send_message,
            "heartbeat": RequestHandler.action_heartbeat,
        }
        if action in actions:
            # If logged in, pass to specific action function
            if username:
                return actions[action](db_session, parameters, username=username)
            # If not logged in and the request doesn't require to be logged in
            elif action == "user-login" or action == "user-register":
                return actions[action](db_session, parameters)
            # If not logged in and the request needs to be logged in
            else:
                return text("not_login")
        # Action not found
        else:
            return TEXT["no_such_action"]

    # Function name: handle
    # Description  : Rewrite handle method of RequestHandler
    # Return value : No return value
    def handle(self):
        db_session = DBSession()
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
                            send_data = RequestHandler.do_action(db_session, accept_data["action"],
                                                                 accept_data["parameters"], username=username)
                        else:
                            send_data = RequestHandler.do_action(db_session, accept_data["action"],
                                                                 accept_data["parameters"])
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
        db_session.close()


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
        print("[INFO]Server stopped.")
