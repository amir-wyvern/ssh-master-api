from sqlalchemy.orm.session import Session
from db.models import DbSshService
from schemas import SshService
from sqlalchemy import and_
from datetime import datetime

def create_ssh(request: SshService, db: Session):
    
    service = DbSshService(
        server_ip= request.server_ip,
        port= request.port,
        agent_id= request.agent_id,
        user_chat_id= request.user_chat_id,
        password= request.password,
        username= request.username,
        name= request.name,
        phone_number= request.phone_number,
        email= request.email,
        interface_id= request.interface_id,
        limit= request.limit,
        created= request.created, 
        expire= request.expire,
        status= request.status
    )
    
    db.add(service)
    db.commit()
    db.refresh(service)

    return service


def get_services_by_agent_id(agent_id , db: Session, status= None):

    if status == None:
        return db.query(DbSshService).filter(DbSshService.agent_id == agent_id ).all()
    
    else:
        return db.query(DbSshService).filter(and_(DbSshService.agent_id == agent_id, DbSshService.status == status)).all()

def get_services_by_chat_id(chat_id , db: Session, status= None):

    if status == None:
        return db.query(DbSshService).filter(DbSshService.user_chat_id == chat_id ).all()
    
    else:
        return db.query(DbSshService).filter(and_(DbSshService.user_chat_id == chat_id, DbSshService.status == status)).all()


def get_service_by_phone_number(phone_number, db:Session):
    return db.query(DbSshService).filter(DbSshService.phone_number == phone_number).first()


def get_service_by_email(email, db:Session):
    return db.query(DbSshService).filter(DbSshService.email == email).first()


def get_services_by_agent_and_range_time(agent_id, start_time, end_time, db: Session, status= None):

    if status == None:
        return db.query(DbSshService).filter(and_(DbSshService.agent_id == agent_id, DbSshService.expire >= start_time, DbSshService.expire <= end_time) ).all()
    
    else:
        return db.query(DbSshService).filter(and_(DbSshService.agent_id == agent_id, DbSshService.expire >= start_time, DbSshService.expire <= end_time, DbSshService.status == status)).all()


def get_service_by_id(service_id , db: Session):

    return db.query(DbSshService).filter(DbSshService.service_id == service_id ).first()


def get_all_services(db: Session, status= None):

    if status == None:
        return db.query(DbSshService).all()
    
    else:
        return db.query(DbSshService).filter(DbSshService.status == status).all()

def get_service_by_username(username , db: Session):

    return db.query(DbSshService).filter(DbSshService.username == username ).first()


def get_service_by_interface(interface_id , db: Session, status= None):

    if status == None:
        return db.query(DbSshService).filter(DbSshService.interface_id == interface_id ).all()
    
    else:
        return db.query(DbSshService).filter(and_(DbSshService.interface_id == interface_id, DbSshService.status == status)).all()


def get_services_by_server_ip(server_ip, db: Session, status= None):

    if status == None:
        return db.query(DbSshService).filter(DbSshService.server_ip == server_ip ).all()

    else:
        return db.query(DbSshService).filter(and_(DbSshService.server_ip == server_ip, DbSshService.status == status)).all()


def get_services_by_range_time(start_time: datetime, end_time: datetime, db: Session, status= None):

    if status == None:
        return db.query(DbSshService).filter(and_(DbSshService.expire >= start_time, DbSshService.expire <= end_time) ).all()

    else:
        return db.query(DbSshService).filter(and_(DbSshService.expire >= start_time, DbSshService.expire <= end_time, DbSshService.status == status)).all()

def update_expire(service_id, new_expire, db: Session):
    
    service = db.query(DbSshService).filter(DbSshService.service_id == service_id )

    service.update({DbSshService.expire: new_expire})
    db.commit()

    return service


def change_status(service_id, new_status, db: Session):

    service = db.query(DbSshService).filter(DbSshService.service_id == service_id )

    service.update({DbSshService.status: new_status})
    db.commit()
    
    return service    