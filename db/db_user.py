from sqlalchemy.orm.session import Session
from sqlalchemy import and_
from schemas import (
    UserRegisterForDataBase,
    UserRole,
    Status
)
from db.models import DbUser


def create_user(request: UserRegisterForDataBase, db: Session, commit=True):

    user = DbUser(
        chat_id= request.chat_id,
        name= request.name,
        phone_number= request.phone_number,
        email= request.email,
        bot_token= request.bot_token,
        username= request.username,
        password= request.password,
        status= request.status,
        role= request.role,
    )
    db.add(user)

    if commit:
        db.commit()
        db.refresh(user)
    
    return user

def get_all_users(db:Session, status: Status= None):

    if status == None:
        return db.query(DbUser).all()
    
    else:
        return db.query(DbUser).filter(DbUser.status == status).all()
    
def get_all_users_by_role(role: UserRole, db:Session, status: Status= None):

    if status == None:
        return db.query(DbUser).filter(DbUser.role == role).all()
    
    else:
        return db.query(DbUser).filter(and_(DbUser.role == role , DbUser.status == status)).all()


def get_user_by_user_id(user_id, db:Session):
    return db.query(DbUser).filter(DbUser.user_id == user_id ).first()

def get_user_by_bot_token(bot_token, db:Session):
    return db.query(DbUser).filter(DbUser.bot_token == bot_token ).first()


def get_user_by_chat_id(chat_id, db:Session):
    return db.query(DbUser).filter(DbUser.chat_id == chat_id ).first()

def get_user_by_phone_number(phone_number, db:Session):
    return db.query(DbUser).filter(DbUser.phone_number == phone_number).first()


def get_user_by_email(email, db:Session):
    return db.query(DbUser).filter(DbUser.email == email).first()


def get_user_by_username(username, db:Session):
    return db.query(DbUser).filter(DbUser.username == username ).first()
    

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


def delete_user(user_id, db:Session):

    user = get_user_by_user_id(user_id, db)
    db.delete(user)
    db.commit()

    return True


def change_status(user_id, new_status, db: Session, commit=True):

    user = db.query(DbUser).filter(DbUser.user_id == user_id )
    user.update({DbUser.status: new_status})

    if commit:
        db.commit()
    
    return True    