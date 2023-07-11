from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import (
    HTTPError,
    ServiceType,
    TokenUser,
    UserRole,
    SshService,
    ServiceType,
    UserServices,
    NewUserViaService,
    ServiceStatus,
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


# Create a file handler to save logs to a file
file_handler = logging.FileHandler('user_route.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
file_handler.setFormatter(formatter)
logger = logging.getLogger('user_route.log')
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

FINANCIAL_URL= os.getenv('FINANCIAL_URL')

router = APIRouter(prefix='/user', tags=['user'])

def generate_password():

    length = 12
    chars = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(chars) for i in range(length))
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()[:20]

    return hashed_password


@router.get('/test')
def test():
    print(logger)
    logger.info('user')

@router.get('/services', response_model= UserServices, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}, status.HTTP_408_REQUEST_TIMEOUT:{'model':HTTPError}, status.HTTP_409_CONFLICT:{'model':HTTPError}})
def get_user_services_via_telegram(chat_id: str= None,username: str= None, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    if username is None and chat_id is None:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'you shoud send at least username or chat_id', 'internal_code': 2432})
    
    if chat_id:
        services = db_ssh_service.get_services_by_chat_id(chat_id, db, status= ServiceStatus.ENABLE)
        if services == [] :
            raise  HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail={'message': 'this chat_id have not any active service', 'internal_code': 2425})
    
    else:
        service = db_ssh_service.get_service_by_username(username, db)
        if service is None :
            raise  HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail={'message': 'This Username have not any active service', 'internal_code': 2433})

        services = [service]

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
                    'interface_id': service.interface_id,
                    'name': service.name,
                    'email': service.email,
                    'phone_number': service.phone_number,
                    'username': service.username,
                    'password': service.password,
                    'created': service.created,
                    'expire': service.expire.replace(tzinfo=pytz.utc),
                    'status': service.status
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

        service = db_ssh_service.get_service_by_username(request.username, db)

        if service is not None:
            raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail= {'message': 'Username is already have a service ', 'internal_code': 2422} )

        resp, err = get_users(interface.server_ip)
        if err:
            raise err

        if request.username not in resp:
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
        
        try:
            service = db_ssh_service.create_ssh(SshService(**service_data), db, commit= False)
            db_server.increase_ssh_accounts_number(interface.server_ip, db, commit= False)
            db.commit()

        except Exception as e:
            logger.error(f'[new service] error in database (agent_id: {current_user.user_id} -username: {request.username} -interface_id: {request.interface_id})')
            db.rollback() 
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='check the logs for more info')

        logger.info(f'[new service] successfully (agent_id: {current_user.user_id} -username: {request.username} -interface_id: {request.interface_id})')
        return {'service_id': service.service_id, 'agent_id': agent_id}

