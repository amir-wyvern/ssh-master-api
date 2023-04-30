from sqlalchemy.orm.session import Session
from schemas import NewAgentForDataBase, Status
from db.models import DbAgent
from sqlalchemy import and_



def create_agent(request: NewAgentForDataBase, db: Session):


    agent = DbAgent(
        user_id= request.user_id,
        bot_token= request.bot_token,
        username= request.username,
        password= request.password,
        status= request.status
    )
    db.add(agent)

    db.commit()
    db.refresh(agent)
    return agent

def get_all_agents(db:Session, status: Status = None):

    if status == None:
        return db.query(DbAgent).all()
    
    else:
        return db.query(DbAgent).filter(DbAgent.status == status).all()


def get_agent_by_user_id(user_id, db:Session, status: Status = None):
    
    if status == None:
        return db.query(DbAgent).filter(DbAgent.user_id == user_id ).first()
    
    else:
        return db.query(DbAgent).filter(and_(DbAgent.status == status, DbAgent.user_id == user_id)).first()

def get_agent_by_username(username, db:Session, status: Status = None):
    
    if status == None:
        return db.query(DbAgent).filter(DbAgent.username == username ).first()
    
    else:
        return db.query(DbAgent).filter(and_(DbAgent.status == status, DbAgent.username == username)).first()

def update_password(user_id, password: str, db:Session):

    user = db.query(DbAgent).filter(DbAgent.user_id == user_id )
    user.update({DbAgent.password: password})
    db.commit()
    
    return user 

def update_bot_token(user_id, bot_token: str, db:Session):

    user = db.query(DbAgent).filter(DbAgent.user_id == user_id )
    user.update({DbAgent.bot_token: bot_token})
    db.commit()
    
    return user 

def change_status(user_id, new_status: Status, db:Session):

    agent = db.query(DbAgent).filter(DbAgent.user_id == user_id )
    agent.update({DbAgent.status: new_status})
    db.commit()
    
    return agent 

def delete_agent(user_id, db:Session):

    agent = db.query(DbAgent).filter(DbAgent.user_id == user_id )
    db.delete(agent)
    db.commit()
    return True
