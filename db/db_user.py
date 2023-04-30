from sqlalchemy.orm.session import Session
from sqlalchemy import or_
from schemas import UserRegisterForDataBase, UserRole
from db.models import DbUser
from datetime import datetime


def create_user(request: UserRegisterForDataBase, db: Session):


    user = DbUser(
        tel_id= request.tel_id,
        name= request.name,
        phone_number= request.phone_number,
        email= request.email,
        role= request.role,
    )
    db.add(user)

    db.commit()
    db.refresh(user)
    return user

def get_all_users(db:Session):
    return db.query(DbUser).all()


def get_user(user_id, db:Session):
    return db.query(DbUser).filter(DbUser.user_id == user_id ).first()


def get_user_by_telegram_id(tel_id, db:Session):
    return db.query(DbUser).filter(DbUser.tel_id == tel_id ).first()

def get_user_by_phone_number(phone_number, db:Session):
    return db.query(DbUser).filter(DbUser.phone_number == phone_number).first()


def get_user_by_email(email, db:Session):
    return db.query(DbUser).filter(DbUser.email == email).first()

def update_role(user_id, new_role: UserRole, db:Session):

    user = db.query(DbUser).filter(DbUser.user_id == user_id )
    user.update({DbUser.role: new_role})
    db.commit()
    
    return user 
   
def delete_user(user_id, db:Session):
    user = get_user(user_id, db)
    db.delete(user)
    db.commit()
    return True
