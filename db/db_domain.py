from sqlalchemy.orm.session import Session
from db.models import DbDomain
from schemas import (
    DomainRegisterForDb,
    DomainStatusDb
)
from typing import List
from sqlalchemy import and_

def __get_attrs(**kwargs):

    dic_attrs = {
        'server_ip': DbDomain.server_ip,
        'domain_name': DbDomain.domain_name,
        'domain_id': DbDomain.domain_id,
        'identifier': DbDomain.identifier,
        'status': DbDomain.status
    }
    prepar_attrs = []
    for item, value in kwargs.items():
        if item in dic_attrs:
            prepar_attrs.append(dic_attrs[item] == value)
    return prepar_attrs


def create_domain(request: DomainRegisterForDb, db: Session) -> DbDomain:
    
    domain = DbDomain(
        identifier= request.identifier,
        server_ip= request.server_ip,
        domain_name= request.domain_name,
        status= request.status
    )

    db.add(domain)

    db.commit()
    db.refresh(domain)

    return domain

def get_all_domain(db: Session, status: DomainStatusDb= None) -> List[DbDomain]:
    
    if status:
        return db.query(DbDomain).filter(DbDomain.status == status).all()

    else:
        return db.query(DbDomain).all()

def get_last_domain(db: Session) -> DbDomain:

    return db.query(DbDomain).order_by(DbDomain.domain_id.desc()).first()

def get_domain_by_id(domain_id, db: Session) -> DbDomain:

    return db.query(DbDomain).filter(DbDomain.domain_id == domain_id ).first()


def get_domain_by_identifier(identifier, db: Session) -> DbDomain:

    return db.query(DbDomain).filter(DbDomain.identifier == identifier ).first()


def get_domain_by_name(domain_name, db: Session) -> DbDomain:

    return db.query(DbDomain).filter(DbDomain.domain_name == domain_name ).first()


def get_domains_by_server_ip(server_ip, db: Session, status: DomainStatusDb= None) -> List[DbDomain]:

    if status:
        return db.query(DbDomain).filter(and_(DbDomain.server_ip == server_ip, DbDomain.status == status)).all()

    else:
        return db.query(DbDomain).filter(DbDomain.server_ip == server_ip).all()

def get_domains_by_attrs(db: Session, **kwargs) -> List[DbDomain]:

    attrs = __get_attrs(**kwargs)
    return db.query(DbDomain).filter(and_(*attrs)).all()


def update_server_ip(domain_id, new_server_ip, db: Session, commit= True) :

    server = db.query(DbDomain).filter(DbDomain.domain_id == domain_id )

    server.update({DbDomain.server_ip: new_server_ip })
    if commit:
        db.commit()

    return server


def change_status(domain_id, new_status: DomainStatusDb, db: Session, commit= True):
    
    server = db.query(DbDomain).filter(DbDomain.domain_id == domain_id )
    server.update({DbDomain.status: new_status})
    
    if commit:
        db.commit()

    return server

