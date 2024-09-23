from contextlib import contextmanager
from sqlalchemy import Column, BigInteger, Integer, String, create_engine, ForeignKey, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    bots = relationship('Bot', back_populates='user', uselist=False)

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id})>"
    
class Bot(Base):
    __tablename__ = 'bots'
    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String, unique=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    chat_id = Column(BigInteger, ForeignKey('chats.id'), unique=True)

    user = relationship('User', back_populates='bots')
    chat = relationship('Chat', back_populates='bots')

    def __repr__(self):
        return f"<Bot(id={self.id}, token={self.token})>"

class Chat(Base):
    __tablename__ = 'chats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_chat_id = Column(BigInteger)

    bots = relationship('Bot', back_populates='chat')

    def __repr__(self):
        return f"<Chat(id={self.id}, external_chat_id={self.external_chat_id})>"


engine = create_engine('sqlite:///storage.db')
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

@contextmanager
def session_scope():
    session = Session()
    try:
        yield session  
        session.commit() 
    except:
        session.rollback()
        raise
    finally:
        session.close()