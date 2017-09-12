from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine
from ctkserver.config import load_config

CONFIG = load_config()
LOGGED_IN_USERS = {}
ORMBaseModel = declarative_base()
db_engine = create_engine('mysql+pymysql://{}:{}@{}:{}/{}'
                          .format(CONFIG.DB['user'], CONFIG.DB['password'],
                                  CONFIG.DB['host'], CONFIG.DB['port'],
                                  CONFIG.DB['database']),
                          encoding='utf-8'
                          )


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
    blocked_user = Column(String(40), ForeignKey('ctk_users.username'), nullable=False)

    def __repr__(self):
        return "<Blacklist of `{}`:{}>".format(self.username, self.blocked_user)


class Contact(ORMBaseModel):
    __tablename__ = 'ctk_user_contacts'
    username = Column(String(40), ForeignKey('ctk_users.username'), primary_key=True)
    contact = Column(String(40), ForeignKey('ctk_users.username'), nullable=False)

    def __repr__(self):
        return "<Contact of `{}`:{}>".format(self.username, self.contact)


ORMBaseModel.metadata.create_all(db_engine)
Session = sessionmaker(bind=db_engine)
session = Session()
userinfo = {
    "mail": "vencent.stevens@gmail.com",
    "username": "lavender",
    "nickname": "lavender",
    "password": "pass_lavender",
    "public_key": "FINGERPRINT1",
    "avatar": "1"
}
session.add(User(**userinfo))
session.commit()
user = session.query(User).filter(User.username == "lavender1").first()

print(user)
session.close()
