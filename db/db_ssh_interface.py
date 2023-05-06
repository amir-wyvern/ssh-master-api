from sqlalchemy.orm.session import Session
from db.models import DbSshInterface
from schemas import SshInterface, Status
from sqlalchemy import and_
from datetime import datetime

def create_interface(request: SshInterface, db: Session):
    
    service = DbSshInterface(
        server_ip= request.server_ip,
        port= request.port,
        location= request.location,
        limit= request.limit,
        price= request.price,
        traffic= request.traffic,
        duration= request.duration,
        status= request.status
    )
    
    db.add(service)
    db.commit()
    db.refresh(service)

    return service


def get_all_interface(db: Session, status: Status= None):

    if status == None:
        return db.query(DbSshInterface).all()
    
    else:
        return db.query(DbSshInterface).filter(DbSshInterface.status == status).all()


def get_interface_by_id(interface_id , db: Session) :

    return db.query(DbSshInterface).filter(DbSshInterface.interface_id == interface_id ).first()


def get_interface_by_server_ip(server_ip, db: Session, status: Status= None):

    if status == None:
        return db.query(DbSshInterface).filter(DbSshInterface.server_ip == server_ip ).all()

    else:
        return db.query(DbSshInterface).filter(and_(DbSshInterface.server_ip == server_ip, DbSshInterface.status == status )).all()


def get_interface_by_location(location, db: Session, status: Status= None):

    if status == None:
        return db.query(DbSshInterface).filter(DbSshInterface.location == location ).all()

    else:
        return db.query(DbSshInterface).filter(and_(DbSshInterface.location == location, DbSshInterface.status == status )).all()
    
def change_status(interface_id, new_status: Status, db: Session):
    
    service = db.query(DbSshInterface).filter(DbSshInterface.interface_id == interface_id )

    service.update({DbSshInterface.status: new_status})
    db.commit()

    return service
