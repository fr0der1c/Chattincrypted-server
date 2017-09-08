from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine
from ctkserver.config import load_config

CONFIG = load_config()
LOGGED_IN_USERS = {}
ORMBase = declarative_base()
db_engine = create_engine('mysql+mysqlconnector://{}:{}@{}:{}/{}'
                          .format(CONFIG.DB['user'], CONFIG.DB['password'],
                                  CONFIG.DB['host'], CONFIG.DB['port'],
                                  CONFIG.DB['database']),
                          encoding='utf-8'
                          )


class User(ORMBase):
    __tablename__ = 'ctk_users'
    mail = Column(String(255))
    username = Column(String(40), primary_key=True)
    nickname = Column(String(40))
    password = Column(String(100))
    fingerprint = Column(String(100))
    avatar = Column(String(1024), nullable=True)


class Message(ORMBase):
    __tablename__ = 'ctk_messages'
    message_id = Column(String(255), primary_key=True)
    if_sent = Column(Boolean)
    type = Column(String(10))
    time = Column(String(255))
    sender = Column(String(40), ForeignKey('ctk_users.username'))
    receiver = Column(String(40), ForeignKey('ctk_users.username'))
    message = Column(Text, nullable=True)
    is_attachment = Column(Boolean)


class Attachment(ORMBase):
    __tablename__ = 'ctk_attachments'
    message_id = Column(String(255), ForeignKey('ctk_messages.message_id'), primary_key=True)
    filename = Column(String(255))


class Blacklist(ORMBase):
    __tablename__ = 'ctk_blacklists'
    username = Column(String(40), ForeignKey('ctk_users.username'), primary_key=True)
    blocked_users = Column(Text)


class Contact(ORMBase):
    __tablename__ = 'ctk_user_contacts'
    username = Column(String(40), ForeignKey('ctk_users.username'), primary_key=True)
    contacts = Column(Text)


ORMBase.metadata.create_all(db_engine)
Session = sessionmaker(bind=db_engine)
session = Session()
userinfo = {
    "mail": "vencent.stevens@gmail.com",
    "username": "lavender",
    "nickname": "lavender",
    "password": "pass_lavender",
    "fingerprint": "FINGERPRINT1",
    "avatar": "1"
}
session.add(User(**userinfo))
session.commit()
user = session.query(User).filter(User.username == "lavender").one()

print(user)
session.close()
