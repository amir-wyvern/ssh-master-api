from sqlalchemy.orm.session import Session
from db.models import DbSshService
from schemas import SshService, ServiceStatusDb, ConfigType
from sqlalchemy import and_
from datetime import datetime
from typing import List


def __get_attrs(**kwargs):

    dic_attrs = {
        'service_type': DbSshService.service_type,
        'agent_id': DbSshService.agent_id,
        'username': DbSshService.username,
        'name': DbSshService.name,
        'phone_number': DbSshService.phone_number,
        'email': DbSshService.email,
        'plan_id': DbSshService.plan_id,
        'domain_id': DbSshService.domain_id,
        'created': DbSshService.created, 
        'expire': DbSshService.expire,
        'status': DbSshService.status
    }
    prepar_attrs = []
    for item, value in kwargs.items():
        if item in dic_attrs:
            if item == 'created':
                prepar_attrs.append(dic_attrs[item] >= value)
                
            elif item == 'expire':
                prepar_attrs.append(dic_attrs[item] <= value)
            
            else:
                prepar_attrs.append(dic_attrs[item] == value)
    return prepar_attrs


def create_ssh(request: SshService, db: Session, commit=True) -> DbSshService:
    
    service = DbSshService(
        service_type= request.service_type,
        agent_id= request.agent_id,
        user_chat_id= request.user_chat_id,
        password= request.password,
        username= request.username,
        name= request.name,
        phone_number= request.phone_number,
        email= request.email,
        plan_id= request.plan_id,
        domain_id= request.domain_id,
        created= request.created, 
        expire= request.expire,
        status= request.status
    )
    
    db.add(service)
    if commit:
        db.commit()
        db.refresh(service)
    
    return service


def get_services_by_attrs(db: Session, **kwargs) -> List[DbSshService]:

    attrs = __get_attrs(**kwargs)
    return db.query(DbSshService).filter(and_(*attrs)).all()


def get_services_by_agent_id(agent_id , db: Session, status: ServiceStatusDb= None, type_ : ConfigType = None) -> List[DbSshService]:

    args = [DbSshService.agent_id == agent_id]

    if status != None:
        args.append(DbSshService.status == status)
    
    if type_ != None:
        args.append(DbSshService.service_type == type_)

    return db.query(DbSshService).filter(and_(*args)).all()

def get_services_by_chat_id(chat_id , db: Session, status: ServiceStatusDb= None, type_ : ConfigType = None) -> List[DbSshService]:

    args = [DbSshService.user_chat_id == chat_id]

    if status != None:
        args.append(DbSshService.status == status)
    
    if type_ != None:
        args.append(DbSshService.service_type == type_)

    return db.query(DbSshService).filter(and_(*args)).all()


def get_services_by_phone_number(phone_number, db:Session, status: ServiceStatusDb= None, type_ : ConfigType = None) -> List[DbSshService]:

    args = [DbSshService.phone_number == phone_number ]

    if status != None:
        args.append(DbSshService.status == status)
    
    if type_ != None:
        args.append(DbSshService.service_type == type_)

    return db.query(DbSshService).filter(and_(*args)).all()


def get_services_by_email(email, db:Session, status: ServiceStatusDb= None, type_ : ConfigType = None) -> List[DbSshService]:

    args = [DbSshService.email == email]

    if status != None:
        args.append(DbSshService.status == status)
    
    if type_ != None:
        args.append(DbSshService.service_type == type_)

    return db.query(DbSshService).filter(and_(*args)).all()


def get_services_by_agent_and_range_time(agent_id, start_time, end_time, db: Session, status: ServiceStatusDb= None, type_ : ConfigType = None, **kwargs) -> List[DbSshService]:

    args = [DbSshService.agent_id == agent_id, DbSshService.created >= start_time, DbSshService.expire <= end_time]

    if status != None:
        args.append(DbSshService.status == status)
    
    if type_ != None:
        args.append(DbSshService.service_type == type_)

    return db.query(DbSshService).filter(and_(*args)).all()


def get_service_by_id(service_id , db: Session) -> DbSshService:

    return db.query(DbSshService).filter(DbSshService.service_id == service_id ).first()


def get_all_services(db: Session, status: ServiceStatusDb= None, type_ : ConfigType = None) -> List[DbSshService]:

    args = []

    if status != None:
        args.append(DbSshService.status == status)
    
    if type_ != None:
        args.append(DbSshService.service_type == type_)

    return db.query(DbSshService).filter(and_(*args)).all()


def get_service_by_username(username , db: Session) -> DbSshService:

    return db.query(DbSshService).filter(DbSshService.username == username ).first()


def get_services_by_plan_id(plan_id , db: Session, status: ServiceStatusDb= None, type_ : ConfigType = None) -> List[DbSshService]:

    args = [DbSshService.plan_id == plan_id]

    if status != None:
        args.append(DbSshService.status == status)
    
    if type_ != None:
        args.append(DbSshService.service_type == type_)

    return db.query(DbSshService).filter(and_(*args)).all()

 
def get_services_by_domain_id(domain_id, db: Session, status: ServiceStatusDb= None, type_ : ConfigType = None) -> List[DbSshService]:

    args = [DbSshService.domain_id == domain_id]

    if status != None:
        args.append(DbSshService.status == status)
    
    if type_ != None:
        args.append(DbSshService.service_type == type_)

    return db.query(DbSshService).filter(and_(*args)).all()


def get_services_by_range_time(start_time: datetime, end_time: datetime, db: Session, status: ServiceStatusDb= None, type_ : ConfigType = None) -> List[DbSshService]:

    args = [DbSshService.expire >= start_time, DbSshService.expire <= end_time]

    if status != None:
        args.append(DbSshService.status == status)
    
    if type_ != None:
        args.append(DbSshService.service_type == type_)

    return db.query(DbSshService).filter(and_(*args)).all()


def transfer_users_by_domain(old_domain_id, new_domain_id, db, commit= True):

    services = db.query(DbSshService).filter(DbSshService.domain_id == old_domain_id )

    services.update({DbSshService.domain_id: new_domain_id})
    
    if commit:
        db.commit()

    return services

def transfer_user_by_domain(username, new_domain_id, db, commit= True):

    services = db.query(DbSshService).filter(DbSshService.username == username )

    services.update({DbSshService.domain_id: new_domain_id})
    
    if commit:
        db.commit()

    return services

def update_expire(service_id, new_expire, db: Session, commit= True):
    
    service = db.query(DbSshService).filter(DbSshService.service_id == service_id )

    service.update({DbSshService.expire: new_expire})
    
    if commit:
        db.commit()

    return service


def change_status(service_id, new_status: ServiceStatusDb, db: Session, commit= True):

    service = db.query(DbSshService).filter(DbSshService.service_id == service_id )

    service.update({DbSshService.status: new_status})
    
    if commit:
        db.commit()
    
    return service    


def delete_service(service_id, db:Session):

    service = get_service_by_id(service_id, db)
    db.delete(service)
    db.commit()

    return True

def delete_service_via_group(services, db:Session):

    for service in services:
        service = get_service_by_id(service, db)
        db.delete(service)

    db.commit()
    return True

