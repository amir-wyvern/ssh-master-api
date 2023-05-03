from db.database import Base
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Enum
    )
from schemas import (
    UserRole,
    Status
)

class DbUser(Base):

    __tablename__ = 'user'

    user_id = Column(Integer, index=True, primary_key=True, autoincrement=True)
    tel_id = Column(String(50), unique=True, index=True, nullable=True)
    name = Column(String(50), index=True, nullable=True)
    phone_number = Column(String(20), index=True, nullable=True)
    email = Column(String(100), index=True, nullable=True)
    role = Column(Enum(UserRole), index=True, nullable=False)


class DbServer(Base):

    __tablename__ = 'server'

    server_ip = Column(String(20), primary_key=True, unique=True, index=True, nullable=False)
    root_password = Column(String(50), nullable=False)
    manager_password = Column(String(50), nullable=False)
    ssh_port =  Column(Integer, nullable=False)
    location = Column(String(100), index=True, unique=True, nullable=False)
    max_users = Column(Integer, nullable=False)
    ssh_accounts_number = Column(Integer, nullable=False)
    v2ray_accounts_number = Column(Integer, nullable=False)
    status = Column(Enum(Status), index=True, nullable=False)


class DbV2rayInterface(Base):

    __tablename__ = 'v2ray_interface'

    interface_id = Column(Integer, index=True, primary_key=True, autoincrement=True)


class DbV2rayService(Base):

    __tablename__ = 'v2ray_service'

    service_id = Column(Integer, index=True, primary_key=True, autoincrement=True)
    # server_ip = Column(String(20), ForeignKey('server.server_ip'), index=True, nullable=False)
    # port = Column(Integer, index=True, nullable=False)
    # transmission: Column(VARCHAR(20), index=True, nullable=False)
    # protocol = Column(VARCHAR(20), index=True, nullable=False)
    # traffic_used = Column(Float(15,3), index=True, nullable=False)
    # status = Column(Enum(Status), index=True, nullable=False)
    

class DbSshInterface(Base):

    __tablename__ = 'ssh_interface'

    interface_id = Column(Integer, index=True, primary_key=True, autoincrement=True)
    server_ip = Column(String(20), ForeignKey('server.server_ip'), index= True, nullable=False)
    location = Column(String(20), ForeignKey('server.location'), index= True, nullable=False)
    port = Column(Integer, index=True, nullable=False)
    limit = Column(Integer,nullable=False)
    price = Column(Integer,nullable=False)
    traffic = Column(Integer,nullable=False)
    duration = Column(Integer,nullable=False)
    status = Column(Enum(Status), index=True, nullable=False)


class DbSshService(Base):

    __tablename__ = 'ssh_service'

    service_id = Column(Integer, index=True, primary_key=True, autoincrement=True)
    server_ip = Column(String(20), ForeignKey('server.server_ip'), index= True, nullable=False)
    user_id = Column(Integer, ForeignKey('user.user_id'), index=True, nullable=False)
    agent_id = Column(Integer, ForeignKey('user.user_id') , index=True, nullable=True)
    interface_id = Column(Integer, ForeignKey('ssh_interface.interface_id'), index=True, nullable=False)
    username = Column(String(30), index=True, unique= True, nullable=False)
    password = Column(String(30), nullable=False)
    port = Column(Integer, index=True, nullable=False) 
    limit = Column(Integer, nullable=False)
    status = Column(Enum(Status), index=True, nullable=False)
    expire = Column(DateTime, index=True, nullable=False)


class DbAgent(Base):

    __tablename__ = 'agent'
    user_id = Column(Integer, ForeignKey('user.user_id'), index=True, primary_key=True)
    bot_token = Column(String(100), index=True, nullable=True, unique= True)
    username = Column(String(100), index=True, nullable=False, unique= True)
    password = Column(String(100), nullable=False)
    status = Column(Enum(Status), index=True, nullable=False)


class DbAdmin(Base):

    __tablename__ = 'admin'
    user_id = Column(Integer, ForeignKey('user.user_id'), index=True, primary_key=True)
    bot_token = Column(String(100), index=True, nullable=True, unique= True)
    username = Column(String(100), index=True, nullable=False, unique= True)
    password = Column(String(100), nullable=False)
