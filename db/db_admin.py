from sqlalchemy.orm.session import Session
from schemas import AdminForDataBase
from db.models import DbAdmin


def create_admin(request: AdminForDataBase, db: Session):

    admin = DbAdmin(
        user_id= request.user_id,
        username= request.username,
        password= request.password,
        bot_token= request.bot_token
    )
    db.add(admin)

    db.commit()
    db.refresh(admin)
    return admin

def get_all_admins(db:Session):
    return db.query(DbAdmin).all()

def get_admin_by_user_id(user_id, db:Session):
    return db.query(DbAdmin).filter(DbAdmin.user_id == user_id ).first()

def get_admin_by_username(username, db:Session):
    return db.query(DbAdmin).filter(DbAdmin.username == username ).first()

def update_password(user_id, password: str, db:Session):

    user = db.query(DbAdmin).filter(DbAdmin.user_id == user_id )
    user.update({DbAdmin.password: password})
    db.commit()
    
    return user 
   
def update_bot_token(user_id, bot_token: str, db:Session):

    user = db.query(DbAdmin).filter(DbAdmin.user_id == user_id )
    user.update({DbAdmin.bot_token: bot_token})
    db.commit()
    
    return user 

def delete_admin(user_id, db:Session):
    admin = db.query(DbAdmin).filter(DbAdmin.user_id == user_id )
    db.delete(admin)
    db.commit()
    return True
