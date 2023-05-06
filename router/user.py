from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import (
    HTTPError,
    Status,
    ServiceType,
    TokenUser,
    UserRole,
    SshService,
    ServiceType,
    UserServices,
    NewUserViaService,
    UserSShServiceDisplay,
    NewUserViaServiceResponse
)
from db import db_user, db_ssh_service, db_server, db_ssh_interface
from db.database import get_db
from auth.auth import get_agent_user, get_admin_user
import pytz

import random
import string
import hashlib
import os

from slave_api.server import get_users

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

@router.get('/services', response_model= UserServices, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}, status.HTTP_408_REQUEST_TIMEOUT:{'model':HTTPError}, status.HTTP_409_CONFLICT:{'model':HTTPError}})
def get_user_services_via_telegram(chat_id: str, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    services = db_ssh_service.get_services_by_chat_id(chat_id, db, status= Status.ENABLE)

    if services == [] :
        raise  HTTPException(status_code= status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'this chat_id have not any service', 'internal_code': 2425})

    ls_service = []
    for service in services:
        
        if current_user.role == UserRole.ADMIN or service.agent_id == current_user.user_id:
            service_data = {
                'service_type': ServiceType.SSH,
                'detail': UserSShServiceDisplay(**{
                    'service_id': service.service_id,
                    'agent_id': service.agent_id,
                    'host': service.server_ip,
                    'port': service.port,
                    'username': service.username,
                    'password': service.password,
                    'created': service.created,
                    'expire': service.expire.replace(tzinfo=pytz.utc)
                })
            }

            ls_service.append(service_data)

    resp = {
        'services': ls_service
    }

    return UserServices(**resp)


@router.post('/service/new', response_model= NewUserViaServiceResponse, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}, status.HTTP_408_REQUEST_TIMEOUT:{'model':HTTPError}})
def add_new_user_via_service(request: NewUserViaService, service_type: ServiceType= ServiceType.SSH, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    agent_id = current_user.user_id

    if request.agent_id :
        agent_user = db_user.get_user_by_user_id(request.agent_id, db)
        if agent_user is None:
            raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= {'message': 'The agent_id could not be found', 'internal_code': 2407} )
        
        agent_id= agent_user.user_id

    if service_type == ServiceType.SSH:

        interface = db_ssh_interface.get_interface_by_id(request.interface_id, db)

        if interface is None:
            raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= {'message': 'Interface_id not exists', 'internal_code': 2410} )

        if interface.status == Status.DISABLE:
            raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail= {'message': 'Interface_id is disable', 'internal_code': 2426} )

        service = db_ssh_service.get_service_by_username(request.username, db)

        if service is not None:
            raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail= {'message': 'Username is already have a service ', 'internal_code': 2422} )

        status_code, resp = get_users(interface.server_ip)

        if status_code == 2419 :
            raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': f'networt error [{interface.server_ip}]', 'internal_code': 2419})
            
        if status_code != 200:
            raise HTTPException(status_code=resp.status_code ,detail= resp.json()['detail'])

        if request.username not in resp.json():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': f'the username [{request.username}] not exist in server [{interface.server_ip}]', 'internal_code': 2429})


        service_data = {
            'server_ip': interface.server_ip,
            'user_chat_id': request.chat_id,
            'password': request.password,
            'username': request.username,
            'name': request.name,
            'phone_number': request.phone_number,
            'email': request.email,
            'agent_id': agent_id,
            'port': interface.port,
            'limit': interface.limit,
            'interface_id': interface.interface_id,
            'created': request.created,
            'expire': request.expire,
            'status': request.service_status
        }
        
        service = db_ssh_service.create_ssh(SshService(**service_data), db)
        db_server.increase_ssh_accounts_number(interface.server_ip, db)

        return {'service_id': service.service_id, 'agent_id': agent_id}

