# server.py
# Description: main server
import socketserver
import msgpack
import os
import time
import threading
import ssl
import json
import datetime
from sqlalchemy import Column, String, Boolean, Text, TIMESTAMP, ForeignKey, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from ctkserver.commons import get_time, generate_md5, recv_msg, send_msg
from ctkserver.config import load_config
from ctkserver.predefined_text import TEXT, text
from ctkserver.user import log_in, heartbeat

print("Hello")
CONFIG = load_config()
LOGGED_IN_USERS = {}
ORMBaseModel = declarative_base()
db_engine = create_engine('mysql+pymysql://{}:{}@{}:{}/{}'
                          .format(CONFIG.DB['user'], CONFIG.DB['password'],
                                  CONFIG.DB['host'], CONFIG.DB['port'],
                                  CONFIG.DB['database']),
                          encoding='utf-8',
                          pool_size=50
                          )
DBSession = sessionmaker(bind=db_engine)


class User(ORMBaseModel):
    __tablename__ = 'ctk_users'
    mail = Column(String(255))
    username = Column(String(40), primary_key=True)
    nickname = Column(String(40))
    password = Column(String(100), nullable=False)
    public_key = Column(String(5000), nullable=False)
    signature = Column(String(100))
    avatar = Column(Boolean)

    def __repr__(self):
        return "<User `{}`>".format(self.username)


class Message(ORMBaseModel):
    __tablename__ = 'ctk_messages'
    message_id = Column(String(130), primary_key=True)
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
    message_id = Column(String(130), ForeignKey('ctk_messages.message_id'), primary_key=True)
    filename = Column(String(255), nullable=False)

    def __repr__(self):
        return "<Attachment `{}` filename=`{}`>".format(self.message_id, self.filename)


class Blacklist(ORMBaseModel):
    __tablename__ = 'ctk_blacklists'
    username = Column(String(40), ForeignKey('ctk_users.username'), primary_key=True)
    blocked_users = Column(String(4000), nullable=False)

    def __repr__(self):
        return "<Blacklist of `{}`:{}>".format(self.username, self.blocked_user)


class Contact(ORMBaseModel):
    __tablename__ = 'ctk_user_contacts'
    username = Column(String(40), ForeignKey('ctk_users.username'), primary_key=True)
    contacts = Column(String(4000), nullable=False)

    def __repr__(self):
        return "<Contact of `{}`:{}>".format(self.username, self.contact)


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
                and "password" in parameters and "public_key" in parameters:
            db_session.add(User(mail=parameters['mail-address'],
                                username=parameters['username'],
                                nickname=parameters['nickname'],
                                password=parameters['password'],
                                public_key=parameters['public_key'],
                                avatar=False))
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
    # Return value : TEXT["unexpected_behaviour"] or TEXT["successfully-updated-info"]
    @staticmethod
    def action_update_personal_info(db_session, parameters, username=None):
        me = db_session.query(User).filter(User.username == username).first()
        if me:
            if "new-nickname" in parameters:
                me.nickname = parameters["new-nickname"]
            if "new-passwd" in parameters:
                me.password = parameters["new-passwd"]
            if "new-signature" in parameters:
                me.signature = parameters["new-signature"]
            if "new-avatar" in parameters:
                with open(os.path.join(os.getcwd(), "attachments/avatar/{}".format(username)), 'wb') as f:
                    f.write(parameters["new-avatar"])
                me.avatar = True
            db_session.commit()
            return TEXT["successfully-updated-info"]
        else:
            return TEXT["unexpected_behaviour"]

    # Function name: action_get_user_info
    # Description  : Get info of a user
    # Return value : "unexpected_behaviour" or msg_to_return
    @staticmethod
    def action_get_user_info(db_session, parameters, username=None):
        if "username" not in parameters:
            return text("incomplete_parameters")
        user = db_session.query(User).filter(User.username == parameters["username"]).first()
        if user:
            msg_to_return = {
                "action": "get-user-info",
                "username": user.username,
                "nickname": user.nickname,
                "public_key": user.public_key,
                "signature": user.signature if user.signature else '',
                "mail": user.mail,
            }
            if user.avatar:
                msg_to_return["avatar"] = True
                with open(os.path.join(os.getcwd(),
                                       "attachments/avatar/{}.jpg".format(user.username)), "rb"
                          ) as f:
                    msg_to_return["avatar_data"] = f.read()
            else:
                msg_to_return["avatar"] = False
            return msg_to_return
        else:
            return text("unexpected_behaviour")

    # Function name: action_get_user_info
    # Description  : Add a user to contact
    # Return value : "unexpected_behaviour", "successfully_added_contact" or 'incomplete_parameters'
    @staticmethod
    def action_add_contact(db_session, parameters, username=None):
        if "username" not in parameters:
            return text('incomplete_parameters')
        user_to_add = db_session.query(User).filter(User.username == parameters["username"]).first()

        # User not exist
        if not user_to_add:
            return text("unexpected_behaviour")

        my_contacts = db_session.query(Contact).filter(Contact.username == username).first()
        if my_contacts:
            # change my entry
            contacts = json.loads(my_contacts.contacts)
            if parameters["username"] not in contacts:
                contacts.append(parameters["username"])
            my_contacts.contacts = json.dumps(contacts)
        else:
            # add entry
            db_session.add(Contact(username=username,
                                   contacts=json.dumps([parameters["username"], ])
                                   ))
        db_session.commit()
        return text("successfully_added_contact", parameters["username"])

    # Function name: action_del_contact
    # Description  : Del a user from contact
    # Return value : 'incomplete_parameters', "unexpected_behaviour" or "successfully_deleted_contact"
    @staticmethod
    def action_del_contact(db_session, parameters, username=None):
        # incomplete parameters
        if "username" not in parameters:
            return text("incomplete_parameters")

        contact_in_db = db_session.query(Contact).filter(Contact.username == username).first()

        # No contact
        if not contact_in_db:
            return text("unexpected_behaviour")

        # Not in my contacts
        contacts = json.loads(contact_in_db.contacts)
        if parameters["username"] not in contacts:
            return text("unexpected_behaviour")

        # Update contacts
        contact_in_db.contacts = json.dumps(contacts.remove(parameters["username"]))
        db_session.commit()
        return text("successfully_deleted_contact", parameters["username"])

    # Function name: action_add_blacklist
    # Description  : Add a user to blacklist
    # Return value : "unexpected_behaviour", "successfully_added_blacklist" or 'incomplete_parameters'
    @staticmethod
    def action_add_blacklist(db_session, parameters, username=None):
        # Incomplete parameters
        if "username" not in parameters:
            return text('incomplete_parameters')

        my_blacklist = db_session.query(Blacklist).filter(Blacklist.username == username).first()
        if my_blacklist:
            # change
            blacklist_list = json.loads(my_blacklist.contacts)
            if parameters["username"] not in blacklist_list:
                blacklist_list.append(parameters["username"])
            my_blacklist.contacts = json.dumps(blacklist_list)
        else:
            # add
            db_session.add(Contact(username=username,
                                   blocked_users=json.dumps([parameters["username"], ])))

        db_session.commit()
        return text("successfully_added_blacklist", parameters["username"])

    # Function name: action_del_blacklist
    # Description  : Del a user from blacklist
    # Return value : "successfully_removed_blacklist", "unexpected_behaviour" or 'incomplete_parameters'
    @staticmethod
    def action_del_blacklist(db_session, parameters, username=None):
        # incomplete parameters
        if "username" not in parameters:
            return TEXT['incomplete_parameters']

        # No contact
        blacklists = db_session.query(Blacklist).filter(Blacklist.username == username).first()
        if not blacklists:
            return text("unexpected_behaviour")

        # Not in my contacts
        blocked_users = json.loads(blacklists.blocked_users)
        if parameters["username"] not in blocked_users:
            return text("unexpected_behaviour")

        # Update info
        blacklists.blocked_users = json.dumps(blocked_users.remove(parameters["username"]))
        db_session.commit()
        return text("successfully_removed_blacklist", parameters["username"])

    # Function name: action_get_my_contacts
    # Description  : Get a user's contacts
    # Return value : TEXT["unexpected_behaviour"] or TEXT["successfully_added_contact"]
    @staticmethod
    def action_get_my_contacts(db_session, parameters, username=None):
        my_contacts_in_db = db_session.query(Contact).filter(Contact.username == username).first()
        contacts_str = ""
        if not my_contacts_in_db or not my_contacts_in_db.contacts:
            msg_to_return = {
                "action": "get-my-contacts",
                "contacts": "",
            }
        else:
            contacts_list = json.loads(my_contacts_in_db.contacts)
            for u in contacts_list:
                contacts_str = contacts_str + u + ','
            msg_to_return = {
                "action": "get-my-contacts",
                "contacts": contacts_str,
            }
        return msg_to_return

    # Function name: action_send_message
    # Description  : Handle messages sent from clients
    # Return value : TEXT['incomplete_parameters'], TEXT["unexpected_behaviour"] or
    #                text("message_sent")
    @staticmethod
    def action_send_message(db_session, parameters, username=None):
        # Incomplete parameters
        if "type" not in parameters or "time" not in parameters or "receiver" not in parameters:
            return TEXT['incomplete_parameters']

        # Wrong type
        if parameters["type"] not in CONFIG.AVAILABLE_MESSAGE_TYPE:
            return TEXT['unexpected_behaviour']

        # Incomplete parameters
        if (parameters["type"] == "text" and "message" not in parameters) or \
                (parameters["type"] != "text" and ("data" not in parameters or "filename" not in parameters)):
            return TEXT['incomplete_parameters']

        # Check if was blocked
        receiver_blocking_list = db_session.query(Blacklist)\
                                           .filter(Blacklist.username == parameters["receiver"]).first()
        if receiver_blocking_list and username in json.loads(receiver_blocking_list):
            return text("blocked_by_user")

        # Receiver not exists
        if not db_session.query(User).filter(User.username == parameters["receiver"]).first():
            return TEXT['unexpected_behaviour']

        # Generate message
        message = {
            'type': parameters['type'],
            'time': parameters['time'],
            'receiver': parameters['receiver'],
            'sender': username
        }
        message["message_id"] = generate_md5(message["type"] + str(message["time"]) + message["sender"] +
                                             message["receiver"])

        # Message with same id in rare situations
        if db_session.query(Message).filter(Message.message_id == message["message_id"]).first():
            return text("duplicated_message", message["message_id"])

        if parameters["type"] == "text":
            print("text")
            message["message"] = parameters["message"]
            # Save message to database
            db_session.add(Message(message_id=message["message_id"],
                                   type=message["type"],
                                   time=message["time"],
                                   sender=message["sender"],
                                   receiver=message["receiver"],
                                   message=message["message"]))
            db_session.commit()

            return text("message_sent", message["message_id"])
        else:
            # Save file to local
            with open(os.path.join(os.getcwd(), "attachments/{}".format(message["message_id"])), 'wb') as f:
                f.write(parameters["data"])

            # Save message to database
            db_session.add(Message(message_id=message["message_id"],
                                   type=message["type"],
                                   time=message["time"],
                                   sender=message["sender"],
                                   receiver=message["receiver"]))
            db_session.add(Attachment(message_id=message["message_id"],
                                      filename=parameters["filename"]))
            db_session.commit()

            return text("message_sent", message["message_id"])

    # Function name: action_message_received
    # Description  : Handle message-received request, delete message from database
    # Return value : no return value
    @staticmethod
    def action_message_received(db_session, parameters, username=None):
        if "message_id" not in parameters:
            return TEXT['incomplete_parameters']
        message = db_session.query(Message).filter(Message.message_id == parameters["message_id"]).first()
        if message.receiver == username:
            # Delete message from database
            db_session.delete(message)
            db_session.commit()

            if message.type != "text":
                # delete attachment from server
                os.remove(os.path.join(os.getcwd(), "attachments/{}".format(message.message_id)))

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
            "get-user-info": RequestHandler.action_get_user_info,
            "add-contact": RequestHandler.action_add_contact,
            "del-contact": RequestHandler.action_del_contact,
            "get-my-contacts": RequestHandler.action_get_my_contacts,
            "add-blacklist": RequestHandler.action_add_blacklist,
            "del-blacklist": RequestHandler.action_del_blacklist,
            "send-message": RequestHandler.action_send_message,
            "message-received": RequestHandler.action_message_received,
            "heartbeat": RequestHandler.action_heartbeat,
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
    # Description  : Thread for forwardly sending user message EVERY 0.5 SECOND
    # Return value : no return value
    @staticmethod
    def forwardly_sending_message_thread(sock, db_session, current_user):
        flag_to_quit = False
        while True:
            # If logged in and have message to send
            if current_user:
                messages = db_session.query(Message).filter(Message.receiver == current_user).all()
                for each_message in messages:
                    if not each_message.last_send_time \
                            or datetime.datetime.now() - each_message.last_send_time > datetime.timedelta(seconds=10):
                        # Send message
                        msg_to_send = {
                            "action": "receive-message",
                            "message_id": each_message.message_id,
                            "type": each_message.type,
                            "sender": each_message.sender,
                            "time": each_message.time,
                        }
                        if each_message.type == "text":
                            msg_to_send["message"] = each_message.message
                        else:
                            attachment = db_session.query(Attachment) \
                                .filter(Attachment.message_id == each_message.message_id).first()
                            msg_to_send["filename"] = attachment.filename
                            with open(os.path.join(os.getcwd(),
                                                   "attachments/{}".format(each_message.message_id)), "rb"
                                      ) as f:
                                msg_to_send["data"] = f.read()
                        try:
                            send_msg(sock, msgpack.dumps(msg_to_send, use_bin_type=True))
                            print("[INFO]Send message %s" % each_message)
                        except BrokenPipeError:
                            # Client closed connection
                            flag_to_quit = True
                            break

                        # Update last_send_time of message
                        db_session.query(Message) \
                            .filter(Message.message_id == each_message.message_id) \
                            .update({"last_send_time": datetime.datetime.now()})
                        db_session.commit()
            if flag_to_quit:
                break
            time.sleep(0.5)

    # Function name: handle_user_request_thread
    # Description  : Thread for handling user requests
    # Return value : no return value
    @staticmethod
    def handle_user_request_thread(sock, db_session, current_user):
        while True:
            try:
                recv = recv_msg(sock)
                if recv:
                    accept_data = msgpack.loads(recv, encoding='utf-8')
                    if len(accept_data) > 500:
                        print("[INFO]Accepted data %s...%s" % (accept_data[0:50], accept_data[-50:-1]))
                    else:
                        print("[INFO]Accepted data %s." % accept_data)

                    if "parameters" not in accept_data:
                        send_data = TEXT['incomplete_parameters']

                    # If Bye-bye
                    if accept_data["action"] == "Bye-bye":
                        if current_user:
                            LOGGED_IN_USERS.pop(current_user[0])
                        break

                    if current_user:
                        send_data = RequestHandler.do_action(db_session, accept_data["action"],
                                                             accept_data, username=current_user[0])
                    else:
                        send_data = RequestHandler.do_action(db_session, accept_data["action"],
                                                             accept_data)

                    if send_data:
                        send_msg(sock, msgpack.dumps(send_data, use_bin_type=True))

                    # if successfully log in, save username to variable username
                    if send_data and "description" in send_data.keys() \
                            and send_data["description"] == "Login successfully":
                        current_user.append(accept_data["username"])
                        print("[INFO]User {} logged in.".format(current_user[0]))

            except msgpack.exceptions.UnpackValueError:
                # Client closed connection
                print("[INFO]Client closed the connection(msgpack.exceptions.UnpackValueError).")
                break
            except msgpack.exceptions.ExtraData:
                # Not a msgpack file
                print("[EXCEPTION]Not a msgpack file(msgpack.exceptions.ExtraData)")
                break
            except ConnectionResetError:
                # Client trying to connect, but server closed the connection
                print("[INFO]ConnectionResetError.")
                break
            except BrokenPipeError:
                # Server trying to write to socket, but client closed the connection
                print("[INFO]Client closed the connection(BrokenPipeError).")
                break
            except OSError as e:
                print("[ERROR]OS ERROR %s." % e)
                break

    # Function name: handle
    # Description  : Rewrite handle method of RequestHandler
    # Return value : No return value
    def handle(self):
        db_session = DBSession()
        socket = self.request
        address = self.client_address
        ssl_sock = socket
        print("[INFO]{} connected.".format(address))
        current_user = []

        # Open handling and forwardly sending thread for each client
        handling_thread = threading.Thread(target=RequestHandler.handle_user_request_thread,
                                           args=(ssl_sock, db_session, current_user))
        sending_thread = threading.Thread(target=RequestHandler.forwardly_sending_message_thread,
                                          args=(ssl_sock, db_session, current_user))
        handling_thread.start()
        sending_thread.start()
        handling_thread.join()
        sending_thread.join()

        # After joining two threads(client log out)
        print("[INFO]Socket close.")
        ssl_sock.close()
        db_session.close()


if __name__ == '__main__':
    # Start TCP server
    server = socketserver.ThreadingTCPServer((CONFIG.HOST, CONFIG.PORT), RequestHandler)
    print("[INFO]Sever started on port %s." % CONFIG.PORT)
    try:
        # Open threads for sending messages and removing offline users
        threads = [RemoveOfflineUserThread()]
        for each_thread in threads:
            each_thread.start()

        server.serve_forever()

    except KeyboardInterrupt:
        server.shutdown()
        print("[INFO]Server stopped.")
