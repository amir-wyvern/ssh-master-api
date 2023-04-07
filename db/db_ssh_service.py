from sqlalchemy.orm.session import Session
from db.models import DbSshService
from schemas import SshService
from sqlalchemy import and_
from datetime import datetime

def create_ssh(request: SshService, db: Session):
    
    service = DbSshService(
        server_ip= request.server_ip,
        port= request.port,
        user_id= request.user_id,
        password= request.password,
        username= request.username,
        interface_id= request.interface_id,
        limit= request.limit,
        expire= request.expire,
        status= request.status
    )
    
    db.add(service)
    db.commit()
    db.refresh(service)

    return service


def get_service_by_id(service_id , db: Session, status= None):

    if status == None:
        return db.query(DbSshService).filter(DbSshService.service_id == service_id ).first()
    
    else:
        return db.query(DbSshService).filter(and_(DbSshService.service_id == service_id, DbSshService.status == status)).first()

def get_service_by_username(username , db: Session, status= None):

    if status == None:
        return db.query(DbSshService).filter(DbSshService.username == username ).first()
    
    else:
        return db.query(DbSshService).filter(and_(DbSshService.username == username, DbSshService.status == status)).first()


def get_service_by_user_id(user_id , db: Session, status= None):

    if status == None:
        return db.query(DbSshService).filter(DbSshService.user_id == user_id ).all()
    
    else:
        return db.query(DbSshService).filter(and_(DbSshService.user_id == user_id, DbSshService.status == status)).all()


def get_service_by_interface(interface_id , db: Session, status= None):

    if status == None:
        return db.query(DbSshService).filter(DbSshService.interface_id == interface_id ).all()
    
    else:
        return db.query(DbSshService).filter(and_(DbSshService.interface_id == interface_id, DbSshService.status == status)).all()


def get_service_by_server_ip(server_ip, db: Session, status= None):

    if status == None:
        return db.query(DbSshService).filter(DbSshService.server_ip == server_ip ).all()

    else:
        return db.query(DbSshService).filter(and_(DbSshService.server_ip == server_ip, DbSshService.status == status)).all()


def get_service_by_range_time(start_time: datetime, end_time: datetime, db: Session, status= None):

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