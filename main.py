from fastapi import FastAPI
from router import (
    agent_management,
    agent_profile,
    notification,
    financial,
    service,
    domain,
    server,
    plan,
    ssh,
    auth
)
from schemas import UserRegisterForDataBase, UserRole, Status, CreateSubsetProfit
from cache.cache_session import get_last_domain, set_last_domain
from cache.database import get_redis_cache
from db import models, db_user, db_subset, db_domain
from db.database import engine, get_db
from dotenv import load_dotenv
import os 
import logging

root_logger = logging.getLogger()
root_logger.handlers.clear()

load_dotenv()

app = FastAPI(    
    title="VPN-Cluster",
    version="0.2.1",
) 


app.include_router(ssh.router)
app.include_router(agent_profile.router)
app.include_router(agent_management.router)
app.include_router(plan.router)
app.include_router(domain.router)
app.include_router(server.router)
app.include_router(financial.router)
app.include_router(service.router)
app.include_router(auth.router)
app.include_router(notification.router)

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
        'referal_link': 'admin',
        'parent_agent_id': 1,
        'subset_limit': 999999,
        'status': Status.ENABLE,
        'role': UserRole.ADMIN
    }

    admin = db_user.create_user(UserRegisterForDataBase(**user_data), db)
    db_subset.create_subset(CreateSubsetProfit(
        user_id= admin.user_id,
        not_released_profit= 0,
        total_profit= 0,
        number_of_configs= 0), db)

CURRENT_DOMAIN = os.getenv('CURRENT_DOMAIN')

if not CURRENT_DOMAIN :
    root_logger.error('there is no valid domain')
    exit(0)

if get_last_domain(get_redis_cache().__next__()) is None:

    last_domain_obj = db_domain.get_last_domain(db)
    if last_domain_obj is None:
        last_domain = f'z1.{CURRENT_DOMAIN}' 
    
    else:
        last_domain = last_domain_obj.domain_name

    set_last_domain(last_domain, get_redis_cache().__next__())


