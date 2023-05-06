from fastapi import FastAPI
from router import (
    agent_management,
    agent_profile,
    financial,
    interface,
    server,
    ssh,
    auth,
    user
)
from schemas import UserRegisterForDataBase, UserRole, Status
from db import models, db_user
from db.database import engine, get_db
from dotenv import load_dotenv
import os 

load_dotenv()

app = FastAPI(    
    title="VPN-Cluster",
    version="0.2.1",
) 


app.include_router(ssh.router)
app.include_router(agent_profile.router)
app.include_router(agent_management.router)
app.include_router(interface.router)
app.include_router(server.router)
app.include_router(financial.router)
app.include_router(user.router)
app.include_router(auth.router)

models.Base.metadata.create_all(engine)


db = get_db().__next__()

ch_user = db_user.get_user_by_username(username= os.getenv('ADMIN_USERNAME'),db=db)

if ch_user is None:

    user_data = {
        'chat_id': None,
        'name': None,
        'phone_number': None,
        'email': None,
        'bot_token': os.getenv('ADMIN_BOT_TOKEN'),
        'username': os.getenv('ADMIN_USERNAME'),
        'password': os.getenv('ADMIN_PASSWORD'),
        'status': Status.ENABLE,
        'role': UserRole.ADMIN
    }

    db_user.create_user(UserRegisterForDataBase(**user_data), db)
    
