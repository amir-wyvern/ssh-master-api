from sqlalchemy.orm.session import Session
from db.models import DbUserService
from schemas import UserServiceRegister


def create_service(request: UserServiceRegister, db: Session):
    
    service = DbUserService(
        user_id= request.user_id,
        ssh_service_id= request.ssh_service_id
    )

    db.add(service)

    db.commit()
    db.refresh(service)
    
    return service

def get_all_services(db: Session):

    return db.query(DbUserService).all()
    

def get_service_by_ssh_service(service_id , db: Session):
    
    return db.query(DbUserService).filter(DbUserService.ssh_service_id == service_id ).first()
    

def get_service_by_user(user_id , db: Session):
    
    return db.query(DbUserService).filter(DbUserService.user_id == user_id ).all()
    

def delete_user_service(service_id, db: Session):

    db.query(DbUserService).filter(DbUserService.service_id == service_id).delete()
    db.commit()