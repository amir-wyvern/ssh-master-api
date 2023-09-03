from db.database import Base
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Enum,
    Float
    )
from schemas import (
    UserRole,
    ServerType,
    ServerStatusDb,
    ServiceStatusDb,
    PlanStatusDb,
    UserStatusDb,
    DomainStatusDb,
    ConfigType
)   

class DbUser(Base):

    __tablename__ = 'user'

    user_id = Column(Integer, index=True, primary_key=True, autoincrement=True)
    chat_id = Column(String(50), unique=True, index=True, nullable=True)
    name = Column(String(50), index=True, nullable=True)
    phone_number = Column(String(20), index=True, unique=True, nullable=True)
    email = Column(String(100), index=True, unique=True, nullable=True)
    bot_token = Column(String(100), index=True, nullable=True, unique= True)
    username = Column(String(100), index=True, nullable=False, unique= True)
    password = Column(String(100), nullable=False) 
    status = Column(Enum(UserStatusDb), index=True, nullable=False)
    referal_link = Column(String(100), index=True, unique=True, nullable=False )
    parent_agent_id = Column(Integer, index=True, nullable=False)
    subset_limit = Column(Integer, nullable=False)
    role = Column(Enum(UserRole), index=True, nullable=False)


class DbServer(Base):

    __tablename__ = 'server' 

    server_ip = Column(String(20), primary_key=True, unique=True, index=True, nullable=False) 
    root_password = Column(String(50), nullable=False)
    manager_password = Column(String(50), nullable=False)
    ssh_port =  Column(Integer, nullable=False)
    location = Column(String(100), index=True, nullable=False)
    max_users = Column(Integer, nullable=False)
    ssh_accounts_number = Column(Integer, nullable=False)
    v2ray_accounts_number = Column(Integer, nullable=False)
    server_type = Column(Enum(ServerType), index=True, nullable=False)
    generate_status = Column(Enum(ServerStatusDb), index=True, nullable=False)
    update_expire_status = Column(Enum(ServerStatusDb), index=True, nullable=False)
    status = Column(Enum(ServerStatusDb), index=True, nullable=False)


# class DbV2rayInterface(Base):

#     __tablename__ = 'v2ray_interface'

#     interface_id = Column(Integer, index=True, primary_key=True, autoincrement=True)


# class DbV2rayService(Base):

#     __tablename__ = 'v2ray_service'

#     service_id = Column(Integer, index=True, primary_key=True, autoincrement=True)
    # server_ip = Column(String(20), ForeignKey('server.server_ip'), index=True, nullable=False)
    # port = Column(Integer, index=True, nullable=False)
    # transmission: Column(VARCHAR(20), index=True, nullable=False)
    # protocol = Column(VARCHAR(20), index=True, nullable=False)
    # traffic_used = Column(Float(15,3), index=True, nullable=False)
    # status = Column(Enum(Status), index=True, nullable=False)
    

class DbSshPlan(Base):

    __tablename__ = 'ssh_plan'

    plan_id = Column(Integer, index=True, primary_key=True, autoincrement=True)
    limit = Column(Integer,nullable=False, index=True) 
    price = Column(Integer,nullable=False, index=True)
    traffic = Column(Integer,nullable=False, index=True) 
    duration = Column(Integer,nullable=False, index=True) 
    status = Column(Enum(PlanStatusDb), index=True, nullable=False)


class DbSshService(Base):

    __tablename__ = 'ssh_service'

    service_id = Column(Integer, index=True, primary_key=True, autoincrement=True)
    service_type = Column(Enum(ConfigType), index=True, nullable=False)
    agent_id = Column(Integer, ForeignKey('user.user_id'), index=True, nullable=False)
    user_chat_id = Column(String(20), index=True, nullable=True)
    name = Column(String(50), index=True, nullable=True)
    phone_number = Column(String(20), index=True, nullable=True)
    email = Column(String(100), index=True, nullable=True)
    username = Column(String(30), index=True, unique= True, nullable=False)
    password = Column(String(30), nullable=False)

    plan_id = Column(Integer, ForeignKey('ssh_plan.plan_id'), index=True, nullable=False)
    domain_id = Column(Integer, ForeignKey('domain.domain_id'), index=True, nullable=False)

    created = Column(DateTime, index=True, nullable=False)
    expire = Column(DateTime, index=True, nullable=False)
    status = Column(Enum(ServiceStatusDb), index=True, nullable=False)


class DbDomain(Base):

    __tablename__ = 'domain'

    domain_id = Column(Integer, index=True, primary_key=True, autoincrement=True)
    identifier =  Column(String(100), index=True, unique=True, nullable=False)
    domain_name = Column(String(100), index=True, unique=True, nullable=False)
    server_ip = Column(String(20), ForeignKey('server.server_ip'), index= True, nullable=False)
    status = Column(Enum(DomainStatusDb), index=True, nullable=False)


class DbSubsetProfit(Base):

    __tablename__ = 'subset_profit'
    user_id = Column(Integer, ForeignKey('user.user_id'), index=True, primary_key=True)
    not_released_profit = Column(Float(15,3), nullable= False)
    total_profit = Column(Float(15,3), nullable= False)
    number_of_configs = Column(Integer, nullable= False)


