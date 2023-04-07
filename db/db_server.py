from sqlalchemy.orm.session import Session
from db.models import DbServer
from schemas import (
    ServerRegister,
    Status
)
from sqlalchemy import and_

def create_server(request: ServerRegister, db: Session):
    
    server = DbServer(
        server_ip= request.server_ip,
        location= request.location,
        ssh_port= request.ssh_port,
        max_users= request.max_users, 
        ssh_accounts_number= request.ssh_accounts_number,
        v2ray_accounts_number= request.v2ray_accounts_number,
        root_password= request.root_password,
        manager_password= request.manager_password,
        status= request.status
    )

    db.add(server)

    db.commit()
    db.refresh(server)

    return server

def get_all_server(db: Session, status: Status = None):

    if status == None:
        return db.query(DbServer).all()

    else:
        return db.query(DbServer).filter(DbServer.status == status).all()

def get_server_by_ip(ip, db: Session, status: Status = None):

    if status == None:
        return db.query(DbServer).filter(DbServer.server_ip == ip ).first()

    else:
        return db.query(DbServer).filter(and_(DbServer.server_ip == ip, DbServer.status == status)).first()

def get_server_by_location(location, db: Session, status: Status = None):
    
    if status == None:
        return db.query(DbServer).filter(and_(DbServer.location == location) ).all()
    
    else:
        return db.query(DbServer).filter(and_(DbServer.location == location, DbServer.status == status) ).all()

def update_max_user(server_ip, new_caps, db: Session):

    server = db.query(DbServer).filter(DbServer.server_ip == server_ip )

    server.update({DbServer.max_users: new_caps })
    db.commit()

    return server

def increase_ssh_accounts_number(server_ip, db: Session):

    server = db.query(DbServer).filter(DbServer.server_ip == server_ip )

    server.update({DbServer.ssh_accounts_number: server.first().ssh_accounts_number + 1})
    db.commit()

    return server

def decrease_ssh_accounts_number(server_ip, db: Session):

    server = db.query(DbServer).filter(DbServer.server_ip == server_ip )
    if server.first().ssh_accounts_number > 0:
        server.update({DbServer.ssh_accounts_number: server.first().ssh_accounts_number - 1})
        db.commit()

    return server

def increase_v2ray_accounts_number(server_ip, db: Session):

    server = db.query(DbServer).filter(DbServer.server_ip == server_ip )

    server.update({DbServer.v2ray_accounts_number: server.v2ray_accounts_number + 1})
    db.commit()

    return server

def change_status(server_ip, new_status: Status, db: Session):
    
    server = db.query(DbServer).filter(DbServer.server_ip == server_ip )

    server.update({DbServer.status: new_status})
    db.commit()

    return server