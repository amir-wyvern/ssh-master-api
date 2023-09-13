from sqlalchemy.orm.session import Session
from sqlalchemy import and_
from schemas import (
    UserRegisterForDataBase,
    UserRole,
    UserStatusDb
)
from db.models import DbUser
from typing import List


def __get_attrs(**kwargs):

    dic_attrs = {

        'chat_id': DbUser.chat_id,
        'name': DbUser.name,
        'phone_number': DbUser.phone_number,
        'email': DbUser.email,
        'bot_token': DbUser.bot_token,
        'username': DbUser.username,
        'status': DbUser.status,
        'referal_link': DbUser.referal_link,
        'parent_agent_id': DbUser.parent_agent_id,
        'subset_limit': DbUser.subset_limit,
        'role': DbUser.role
    }
    prepar_attrs = []
    for item, value in kwargs.items():
        if item in dic_attrs:
            prepar_attrs.append(dic_attrs[item] == value)
    return prepar_attrs


def create_user(request: UserRegisterForDataBase, db: Session, commit=True) -> DbUser:

    user = DbUser(
        chat_id= request.chat_id,
        name= request.name,
        phone_number= request.phone_number,
        email= request.email,
        bot_token= request.bot_token,
        username= request.username,
        password= request.password,
        status= request.status,
        referal_link= request.referal_link,
        parent_agent_id= request.parent_agent_id,
        subset_limit= request.subset_limit,
        role= request.role
    )
    db.add(user)

    if commit:
        db.commit()
        db.refresh(user)
    
    return user

def get_userss_by_attrs(db: Session, **kwargs) -> List[DbUser]:

    attrs = __get_attrs(**kwargs)
    return db.query(DbUser).filter(and_(*attrs)).all()


def get_all_users(db:Session, status: UserStatusDb= None) -> List[DbUser]:

    if status:
        return db.query(DbUser).filter(DbUser.status == status).all()
    
    else:
        return db.query(DbUser).all()
    

def get_all_users_by_role(role: UserRole, db:Session, status: UserStatusDb= None) -> List[DbUser]:

    if status:
        return db.query(DbUser).filter(and_(DbUser.role == role , DbUser.status == status)).all()
    
    else:
        return db.query(DbUser).filter(DbUser.role == role).all()


def get_user_by_user_id(user_id, db:Session) -> DbUser:
    return db.query(DbUser).filter(DbUser.user_id == user_id ).first()


def get_user_by_bot_token(bot_token, db:Session) -> DbUser:
    return db.query(DbUser).filter(DbUser.bot_token == bot_token ).first()


def get_user_by_chat_id(chat_id, db:Session) -> DbUser:
    return db.query(DbUser).filter(DbUser.chat_id == chat_id ).first()


def get_user_by_phone_number(phone_number, db:Session) -> DbUser:
    return db.query(DbUser).filter(DbUser.phone_number == phone_number).first()


def get_user_by_email(email, db:Session) -> DbUser:
    return db.query(DbUser).filter(DbUser.email == email).first()


def get_user_by_username(username, db:Session) -> DbUser:
    return db.query(DbUser).filter(DbUser.username == username ).first()
    

def get_user_by_referal_link(referal_link, db:Session) -> DbUser:
    return db.query(DbUser).filter(DbUser.referal_link == referal_link ).first()
    
    
def get_users_by_parent_agent_id(parent_agent_id, db:Session, status: UserStatusDb= None) -> List[DbUser]:

    if status:
        return db.query(DbUser).filter(and_(DbUser.parent_agent_id == parent_agent_id , DbUser.status == status)).all()
    
    else:
        return db.query(DbUser).filter(DbUser.parent_agent_id == parent_agent_id).all()


def update_role(user_id, new_role: UserRole, db:Session):

    user = db.query(DbUser).filter(DbUser.user_id == user_id )
    user.update({DbUser.role: new_role})
    db.commit()
    
    return True


def update_password(user_id, password: str, db:Session):

    user = db.query(DbUser).filter(DbUser.user_id == user_id )
    user.update({DbUser.password: password})
    db.commit()
    
    return True 


def update_bot_token(user_id, bot_token: str, db:Session):

    user = db.query(DbUser).filter(DbUser.user_id == user_id )
    user.update({DbUser.bot_token: bot_token})
    db.commit()
    
    return True 

def update_chat_id(user_id, chat_id: str, db:Session):

    user = db.query(DbUser).filter(DbUser.user_id == user_id )
    user.update({DbUser.chat_id: chat_id})
    db.commit()
    
    return True 

def update_subset_limit(user_id, limit: int, db:Session):

    user = db.query(DbUser).filter(DbUser.user_id == user_id )
    user.update({DbUser.subset_limit: limit})
    db.commit()
    
    return True 


def delete_user(user_id, db:Session):

    user = get_user_by_user_id(user_id, db)
    db.delete(user)
    db.commit()

    return True


def change_status(user_id, new_status: UserStatusDb, db: Session, commit=True):

    user = db.query(DbUser).filter(DbUser.user_id == user_id )
    user.update({DbUser.status: new_status})

    if commit:
        db.commit()
    
    return True    