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
# from router import auth
from schemas import AdminForDataBase, UserRegisterForDataBase, UserRole
from db import models, db_user, db_admin
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

ch_user = db_user.get_user(user_id=1 ,db=db)

if ch_user is None:

    user_data = {
        'tel_id': None,
        'name': None,
        'phone_number': None,
        'email': None,
        'role': UserRole.ADMIN
    }

    new_user = db_user.create_user(UserRegisterForDataBase(**user_data), db)
    
    admin_data = {
        'user_id': new_user.user_id,
        'username': os.getenv('ADMIN_USERNAME'),
        'password': os.getenv('ADMIN_PASSWORD')
    }
    db_admin.create_admin(AdminForDataBase(**admin_data), db)
