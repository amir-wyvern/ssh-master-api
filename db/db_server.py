from sqlalchemy.orm.session import Session
from db.models import DbServer
from schemas import (
    ServerRegister,
    ServerStatusDb,
    ServerType
)
from typing import List
from sqlalchemy import and_


def __get_attrs(**kwargs):

    dic_attrs = {
        'server_ip': DbServer.server_ip,
        'location': DbServer.location,
        'generate_status': DbServer.generate_status,
        'update_expire_status': DbServer.update_expire_status,
        'status': DbServer.status
    }
    prepar_attrs = []
    for item, value in kwargs.items():
        if item in dic_attrs:
            prepar_attrs.append(dic_attrs[item] == value)
    return prepar_attrs



def create_server(request: ServerRegister, db: Session) -> DbServer:
    
    server = DbServer(
        server_ip= request.server_ip,
        location= request.location,
        ssh_port= request.ssh_port,
        max_users= request.max_users, 
        ssh_accounts_number= request.ssh_accounts_number,
        v2ray_accounts_number= request.v2ray_accounts_number,
        root_password= request.root_password,
        manager_password= request.manager_password,
        server_type= request.server_type,
        generate_status= request.generate_status,
        update_expire_status= request.update_expire_status,
        status= request.status 
    )

    db.add(server)

    db.commit()
    db.refresh(server)

    return server


def get_all_server(db: Session,
                   generate_status: ServerStatusDb= None,
                   update_expire_status: ServerStatusDb= None,
                   status: ServerStatusDb= None) -> List[DbServer]:
    
    args = []
    
    if generate_status != None:

        args.append(DbServer.generate_status == generate_status)
    
    if update_expire_status != None: 
        args.append(DbServer.update_expire_status == update_expire_status)
    
    if status != None:
        args.append(DbServer.status == status)

    if args:
        return db.query(DbServer).filter(and_(*args)).all()

    else:
        return db.query(DbServer).all()


def get_servers_by_type(type_: ServerType, 
                        db: Session, generate_status: ServerStatusDb= None,
                        update_expire_status: ServerStatusDb= None,
                        status: ServerStatusDb= None) -> List[DbServer]:

    args = [DbServer.server_type == type_]

    if generate_status != None:
        args.append(DbServer.generate_status == generate_status)
    
    if update_expire_status != None:
        args.append(DbServer.update_expire_status == update_expire_status)
    
    if status != None:
        args.append(DbServer.status == status)

    if args:
        return db.query(DbServer).filter(and_(*args)).all()

    else:
        return db.query(DbServer).filter(DbServer.server_type == type_ ).all()


def get_server_by_ip(ip, db: Session) -> DbServer:

    return db.query(DbServer).filter(DbServer.server_ip == ip ).first()


def get_server_by_location(location, db: Session,
                           generate_status: ServerStatusDb= None,
                           update_expire_status: ServerStatusDb= None,
                           status: ServerStatusDb= None) -> List[DbServer]:
    
    args = [DbServer.location == location]

    if generate_status != None:
        args.append(DbServer.generate_status == generate_status)
    
    if update_expire_status != None:
        args.append(DbServer.update_expire_status == update_expire_status)
    
    if status != None:
        args.append(DbServer.status == status)


    if args:
        return db.query(DbServer).filter(and_( *args)).all()

    else:
        return db.query(DbServer).filter(DbServer.location == location ).all()


def update_max_user(server_ip, new_caps, db: Session):

    server = db.query(DbServer).filter(DbServer.server_ip == server_ip )

    server.update({DbServer.max_users: new_caps })
    db.commit()

    return server


def increase_ssh_accounts_number(server_ip, db: Session, commit= True, number= 1):

    server = db.query(DbServer).filter(DbServer.server_ip == server_ip )
    server.update({DbServer.ssh_accounts_number: server.first().ssh_accounts_number + number})
    
    if commit:
        db.commit()

    return server


def decrease_ssh_accounts_number(server_ip, db: Session, commit= True, number= 1):

    server = db.query(DbServer).filter(DbServer.server_ip == server_ip )

    if (server.first().ssh_accounts_number - number) > 0 :
        server.update({DbServer.ssh_accounts_number: server.first().ssh_accounts_number - number})
        if commit:
            db.commit()

    return server


def increase_v2ray_accounts_number(server_ip, db: Session):

    server = db.query(DbServer).filter(DbServer.server_ip == server_ip )

    server.update({DbServer.v2ray_accounts_number: server.v2ray_accounts_number + 1})
    db.commit()

    return server


def get_servers_by_attrs(db: Session, **kwargs) -> List[DbServer]:

    attrs = __get_attrs(**kwargs)
    return db.query(DbServer).filter(and_(*attrs)).all()


def change_generate_status(server_ip, new_status: ServerStatusDb, db: Session, commit= True):
    
    server = db.query(DbServer).filter(DbServer.server_ip == server_ip )
    server.update({DbServer.generate_status: new_status})
    
    if commit:
        db.commit()

    return server


def change_update_expire_status(server_ip, new_status: ServerStatusDb, db: Session, commit= True):
    
    server = db.query(DbServer).filter(DbServer.server_ip == server_ip )
    server.update({DbServer.update_expire_status: new_status})
    
    if commit:
        db.commit()

    return server


def change_server_status(server_ip, new_status: ServerStatusDb, db: Session, commit= True):
    
    server = db.query(DbServer).filter(DbServer.server_ip == server_ip )
    server.update({DbServer.status: new_status})
    
    if commit:
        db.commit()

    return server


def change_server_type(server_ip, new_type: ServerType, db: Session, commit= True):
    
    server = db.query(DbServer).filter(DbServer.server_ip == server_ip )
    server.update({DbServer.server_type: new_type})
    
    if commit:
        db.commit()

    return server