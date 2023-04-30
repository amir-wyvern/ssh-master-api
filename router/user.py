from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import (
    UserDisplay,
    HTTPError,
    Status,
    ServiceType,
    TokenUser,
    UserRole,
    SshService,
    ServiceType,
    NewUserViaService,
    UserSShServiceDisplay,
    UserRegisterForDataBase,
    NewUserViaServiceResponse
)
from db import db_user, db_ssh_service, db_server, db_ssh_interface
from db.database import get_db
from auth.auth import get_agent_user, get_admin_user
import pytz

from financial_api.user import get_balance, create_user_if_not_exist
from slave_api.ssh import create_ssh_account

from datetime import datetime, timedelta
import random
import string
import hashlib
import os

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create a file handler to save logs to a file
file_handler = logging.FileHandler('user_route.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

FINANCIAL_URL= os.getenv('FINANCIAL_URL')

router = APIRouter(prefix='/user', tags=['user'])

def generate_password():

    length = 12
    chars = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(chars) for i in range(length))
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()[:20]

    return hashed_password

@router.get('/info', response_model= UserDisplay, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}, status.HTTP_408_REQUEST_TIMEOUT:{'model':HTTPError}, status.HTTP_409_CONFLICT:{'model':HTTPError}})
def get_user_info_via_telegram(tel_id: str, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    user = db_user.get_user_by_telegram_id(tel_id, db)

    if user == None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= {'message': 'The user could not be found', 'internal_code': 2404} )

    services = db_ssh_service.get_service_by_user_id(user.user_id, db, status= Status.ENABLE)

    ls_service = []
    for service in services:
        
        ssh_service = db_ssh_service.get_service_by_id(service.service_id, db)

        if current_user.role == UserRole.ADMIN or ssh_service.agent_id == current_user.user_id:
            service_data = {
                'service_type': ServiceType.SSH,
                'detail': UserSShServiceDisplay(**{
                    'service_id': ssh_service.service_id,
                    'agent_id': ssh_service.agent_id,
                    'host': ssh_service.server_ip,
                    'port': ssh_service.port,
                    'username': ssh_service.username,
                    'password': ssh_service.password,
                    'expire': ssh_service.expire.replace(tzinfo=pytz.utc)
                })
            }

            ls_service.append(service_data)
        
    status_code, resp = get_balance(user.user_id)
    
    if status_code == 2419 :
        raise HTTPException(status_code= status.HTTP_408_REQUEST_TIMEOUT, detail={'message': f'Connection Error Or Connection Timeout', 'internal_code': 2419})
        
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail= resp.json()['detail'] )

    user_info = {
        'tel_id': user.tel_id,
        'phone_number': user.phone_number,
        'email': user.email,
        'role': user.role
    }
    
    resp = {
        'user': UserRegisterForDataBase(**user_info),
        'balance': resp.json()['balance'],
        'services': ls_service
    }
    return UserDisplay(**resp)


@router.post('/service/new', response_model= NewUserViaServiceResponse, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}, status.HTTP_408_REQUEST_TIMEOUT:{'model':HTTPError}})
def add_new_user_via_service(request: NewUserViaService, service_type: ServiceType= ServiceType.SSH, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    user = None
    agent_id = current_user.user_id

    if request.tel_id :
        user = db_user.get_user_by_telegram_id(request.tel_id, db)
        if user is None:
            raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= {'message': 'The user could not be found', 'internal_code': 2404} )

    if request.agent_id :
        agent_user = db_user.get_user(request.agent_id, db)
        agent_id= agent_user.user_id

        if agent_user is None:
            raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= {'message': 'The agent_id could not be found', 'internal_code': 2407} )

    if service_type == ServiceType.SSH:

        interface = db_ssh_interface.get_interface_by_id(request.interface_id, db, status=Status.ENABLE)

        if interface is None:
            raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= {'message': 'Interface_id not exists', 'internal_code': 2410} )

        service = db_ssh_service.get_service_by_username(request.username, db)

        if service is not None:
            raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail= {'message': 'Username is already have a service ', 'internal_code': 2422} )

        data = {
            'tel_id': request.tel_id,
            'name': request.name,
            'phone_number': request.phone_number,
            'role': UserRole.CUSTOMER
        }
        
        user = db_user.create_user(UserRegisterForDataBase(**data), db)
        status_code, resp = create_user_if_not_exist(user.user_id)
        logger.info(f'successfully created account in financial [agent: {agent_id} -username: {request.username} -server: {interface.server_ip}]')
        
        if status_code == 2419 :
            db_user.delete_user(user.user_id, db)
            raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Error Or Connection Timeout', 'internal_code': 2419})
            
        if status_code != 200:
            db_user.delete_user(user.user_id, db)
            raise HTTPException(status_code=resp.status_code ,detail= resp.json()['detail'])

        logger.info(f'send request for create new ssh account [agent: {current_user.user_id} -username: {request.username} -server: {interface.server_ip}]')
        status_code, ssh_resp = create_ssh_account(interface.server_ip, request.username, request.password)
        
        if status_code == 2419 :
            logger.info(f'failed create ssh account [agent: {current_user.user_id}]')
            raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': f'networt error [{interface.server_ip}]', 'internal_code': 2419})
            
        if status_code != 200:
            logger.info(f'failed create ssh account [agent: {current_user.user_id} -price: {interface.price}, resp_code: {status_code}]')
            raise HTTPException(status_code=status_code, detail= ssh_resp.json()['detail'])
        
        logger.info(f'successfully created ssh account [agent: {current_user.user_id} -username: {request.username} -server: {interface.server_ip}]')
        
        service_data = {
            'server_ip': interface.server_ip,
            'agent_id': agent_id,
            'password': request.password,
            'username': request.username,
            'user_id': user.user_id,
            'port': interface.port,
            'limit': interface.limit,
            'interface_id': interface.interface_id,
            'expire': request.expire,
            'status': request.service_status
        }
        
        service = db_ssh_service.create_ssh(SshService(**service_data), db)
        db_server.increase_ssh_accounts_number(interface.server_ip, db)

        return {'service_id': service.service_id, 'user_id': user.user_id}

