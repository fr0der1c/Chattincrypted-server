import socketserver
import msgpack
import os
import time
import threading
import datetime
from sqlalchemy import Column, String, Boolean, Text, TIMESTAMP, ForeignKey, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from ctkserver.commons import get_time, generate_md5
from ctkserver.config import load_config
from ctkserver.predefined_text import TEXT, text
from ctkserver.user import log_in, heartbeat

CONFIG = load_config()
LOGGED_IN_USERS = {}
MESSAGES_TO_SEND = {}
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
    type = Column(String(10), nullable=False)
    time = Column(String(255), nullable=False)
    sender = Column(String(40), ForeignKey('ctk_users.username'), nullable=False)
    receiver = Column(String(40), ForeignKey('ctk_users.username'), nullable=False)
    message = Column(Text)
    last_send_time = Column(TIMESTAMP)

    def __repr__(self):
        return "<Message `{}`, last_send_time `{}`>".format(self.message_id, self.last_send_time)


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


# Class      : AddingMessageToSendQueueThread
# Description: Check if logged in users have new message and
#              add their messages to MESSAGES_TO_SEND queue.
class AddingMessageToSendQueueThread(threading.Thread):
    def run(self):
        while True:
            db_session = DBSession()
            for (k, v) in LOGGED_IN_USERS.items():
                messages = db_session.query(Message).filter(Message.receiver == k).all()
                for single_message in messages:
                    # Messages sent in 10 seconds won't be send again
                    print(single_message)
                    print("datetime.datetime.now():%s" % datetime.datetime.now())
                    print("single_message.last_send_time:%s" % single_message.last_send_time)
                    print(datetime.datetime.now() - single_message.last_send_time)
                    if datetime.datetime.now() - single_message.last_send_time > datetime.timedelta(seconds=10):
                        if k in MESSAGES_TO_SEND:
                            # todo change MESSAGES_TO_SEND[single_message.receiver] to a dict
                            # todo but 未使用线程锁导致 dictionary changed size during iteration
                            if single_message.message_id not in MESSAGES_TO_SEND[k]:
                                MESSAGES_TO_SEND[k][single_message.message_id] = single_message
                                print("append after")
                        else:
                            MESSAGES_TO_SEND[k] = {single_message.message_id: single_message}
                            print("append first")

            time.sleep(1)
            db_session.close()


# Class      : RemoveOfflineUserThread
# Description: Remove offline users from LOGGED_IN_USERS every 30 seconds
class RemoveOfflineUserThread(threading.Thread):
    def run(self):
        while True:
            logged_in_users_copy = LOGGED_IN_USERS.copy()
            for (k, v) in logged_in_users_copy.items():
                if get_time() - v["time"] > 60:
                    LOGGED_IN_USERS.pop(k)
            time.sleep(30)


# Class      : RequestHandler
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
        if "type" not in parameters or "time" not in parameters or "receiver" not in parameters:
            return TEXT['incomplete_parameters']
        if parameters["type"] not in CONFIG.AVAILABLE_MESSAGE_TYPE:
            return TEXT['unexpected_behaviour']
        if not db_session.query(User).filter(User.username == parameters["receiver"]).first():
            return TEXT['unexpected_behaviour']
        message = {
            'type': parameters['type'],
            'time': parameters['time'],
            'receiver': parameters['receiver'],
            'sender': username
        }
        # Generate message_id
        message["message_id"] = generate_md5(message["type"] + str(message["time"]) + message["sender"] +
                                             message["receiver"])
        if db_session.query(Message).filter(Message.message_id == message["message_id"]).first():
            return text("duplicated_message", message["message_id"])
        if parameters["type"] == "text":
            message["message"] = parameters["message"]

            # Save message to database
            db_session.add(Message(message_id=message["message_id"], type=message["type"],
                                   time=message["time"], sender=message["sender"],
                                   receiver=message["receiver"],
                                   message=message["message"]))
            db_session.commit()

            return text("message_sent", message["message_id"])
        else:
            # Save file to local
            with open(os.path.join(os.getcwd(), "attachments/{}".format(message["message_id"])), 'wb') as f:
                f.write(parameters["data"])

            # Save message to database
            db_session.add(Message(message_id=message["message_id"], type=message["type"],
                                   time=message["time"], sender=message["sender"],
                                   receiver=message["receiver"]))
            db_session.commit()

            return text("message_sent", message["message_id"])

    # Function name: action_message_received
    # Description  : When receiving message-received request, delete message from database
    # Return value : no return value
    @staticmethod
    def action_message_received(db_session, parameters, username=None):
        if "message_id" not in parameters:
            return TEXT['incomplete_parameters']
        message = db_session.query(Message).filter(Message.message_id == parameters["message_id"]).first()
        if message.receiver == username:
            db_session.delete(message)
            db_session.commit()

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
            "message-received": RequestHandler.action_message_received,
        }
        if action not in actions:
            return TEXT["no_such_action"]

        if username:
            return actions[action](db_session, parameters, username=username)
        elif action == "user-login" or action == "user-register":
            return actions[action](db_session, parameters)
        else:
            return text("not_login")

    # Function name: forwardly_sending_message_thread
    # Description  : Thread for forwardly sending user message EVERY SECOND
    # Return value : no return value
    @staticmethod
    def forwardly_sending_message_thread(sock, db_session, current_user):
        while True:
            # If logged in and have message in MESSAGES_TO_SEND
            if current_user and current_user[0] in MESSAGES_TO_SEND:
                message_to_send_copy = MESSAGES_TO_SEND.copy()
                for (each_message_id, each_message) in message_to_send_copy[current_user[0]].items():
                    # Send message
                    msg_to_send = {
                        "action": "receive-message",
                        "parameters": {
                            "message_id": each_message.message_id,
                            "type": each_message.type,
                            "sender": each_message.sender,
                            "time": each_message.time,
                        }
                    }
                    if each_message.type == "text":
                        msg_to_send["message"] = each_message.message
                    else:
                        pass
                        # todo:file handle
                    try:
                        sock.sendall(msgpack.dumps(msg_to_send))
                    except BrokenPipeError:
                        # Client closed connection
                        break

                    # Update last_send_time of message
                    db_session.query(Message) \
                        .filter(Message.message_id == each_message.message_id) \
                        .update({"last_send_time": datetime.datetime.now()})
                    db_session.commit()

                    # Pop message
                    MESSAGES_TO_SEND[current_user[0]].pop(each_message_id)
                time.sleep(0.5)

    # Function name: handle_user_request_thread
    # Description  : Thread for handling user requests
    # Return value : no return value
    @staticmethod
    def handle_user_request_thread(sock, db_session, current_user):
        while True:
            try:
                recv = sock.recv(CONFIG.BUFSIZE)
                accept_data_json = recv

                # If logged in, tell him who he is
                if current_user:
                    send_data_json = msgpack.dumps("This is %s" % current_user[0])
                    sock.sendall(send_data_json)

                accept_data = msgpack.loads(accept_data_json, encoding='utf-8')
                if accept_data_json:
                    print("[INFO]Accepted data %s." % accept_data)
                if "parameters" not in accept_data or "action" not in accept_data:
                    send_data_json = msgpack.dumps(TEXT['incomplete_parameters'])

                # If Bye-bye
                if accept_data["action"] == "Bye-bye":
                    if current_user:
                        LOGGED_IN_USERS.pop(current_user[0])
                    break

                if current_user:
                    send_data = RequestHandler.do_action(db_session, accept_data["action"],
                                                         accept_data["parameters"], username=current_user[0])
                else:
                    send_data = RequestHandler.do_action(db_session, accept_data["action"],
                                                         accept_data["parameters"])
                send_data_json = msgpack.dumps(send_data)
                if send_data_json:
                    sock.sendall(send_data_json)

                # if successfully log in, save username to variable username
                if send_data["description"] == "Login successfully":
                    current_user.append(accept_data["parameters"]["username"])
                    print("[INFO]User {} logged in.".format(current_user[0]))

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

    # Function name: handle
    # Description  : Rewrite handle method of RequestHandler
    # Return value : No return value
    def handle(self):
        db_session = DBSession()
        sock = self.request
        address = self.client_address
        print("[INFO]{} connected.".format(address))
        current_user = []

        # Open handling and forwardly sending thread for each client
        handling_thread = threading.Thread(target=RequestHandler.handle_user_request_thread,
                                           args=(sock, db_session, current_user))
        sending_thread = threading.Thread(target=RequestHandler.forwardly_sending_message_thread,
                                          args=(sock, db_session, current_user))
        handling_thread.start()
        sending_thread.start()
        handling_thread.join()
        sending_thread.join()

        # After joining two threads(client log out)
        print("[INFO]Socket close.")
        sock.close()
        db_session.close()


if __name__ == '__main__':
    # Start TCP server
    server = socketserver.ThreadingTCPServer((CONFIG.HOST, CONFIG.PORT), RequestHandler)
    print("[INFO]Sever started on port %s." % CONFIG.PORT)
    try:
        # Open threads for sending messages and removing offline users
        threads = [AddingMessageToSendQueueThread(), RemoveOfflineUserThread()]
        for each_thread in threads:
            each_thread.start()

        server.serve_forever()

    except KeyboardInterrupt:
        server.shutdown()
        print("[INFO]Server stopped.")
