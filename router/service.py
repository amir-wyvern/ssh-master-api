from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException,
    Query
)
from sqlalchemy.orm.session import Session
from schemas import (
    HTTPError,
    ConfigType,
    TokenUser,
    UserRole,
    EmailStr,
    PhoneNumberStr,
    ServiceStatusDb,
    SearchResponse
)
from db import db_ssh_service, db_domain, db_user, db_ssh_plan, db_server
from db.database import get_db
from auth.auth import get_agent_user
from datetime import datetime
import logging

# Create a file handler to save logs to a file
logger = logging.getLogger('service_route.log')
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('srevice_route.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


router = APIRouter(prefix='/service', tags=['Service'])


@router.get('/search', response_model= SearchResponse, responses={
    status.HTTP_404_NOT_FOUND:{'model':HTTPError},
    status.HTTP_408_REQUEST_TIMEOUT:{'model':HTTPError}, 
    status.HTTP_409_CONFLICT:{'model':HTTPError}},
    tags=['Agent-Profile'] )
def get_services_by_search(
    service_type: ConfigType= None,
    agent_username: str= Query(None,description='Only admin has access to this field'),
    username: str= None,
    name: str= None,
    phone_number: PhoneNumberStr= None,
    email: EmailStr= None,
    plan_id: int= None,
    domain_name: str= None,
    start_create_time: datetime= None,
    end_expire_time: datetime= None,
    status_:  ServiceStatusDb= None,
    current_user: TokenUser= Depends(get_agent_user),
    db: Session=Depends(get_db)):

    
    if current_user.role == UserRole.AGENT and agent_username:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'Only admin has access to agent_username field', 'internal_code': 2470})

    user_id = current_user.user_id
    if current_user.role == UserRole.ADMIN:
        user_id = None 

    if agent_username:
        agent = db_user.get_user_by_username(agent_username, db)
        if agent is None:
            raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail={'message': 'username could not be found', 'internal_code': 2407})

        user_id = agent.user_id

    domain_id = None
    if domain_name:
        domain = db_domain.get_domain_by_name(domain_name, db)
        if domain is None:
            raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': "Domain is not exists", 'internal_code': 2449})

        domain_id = domain.domain_id


    if username:

        service = db_ssh_service.get_service_by_username(username, db)
        if service is None:
            raise  HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail={'message': 'This Username have not any active service', 'internal_code': 2433})

        if current_user.role != UserRole.ADMIN and service.agent_id != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})

    if plan_id:
        plan = db_ssh_plan.get_plan_by_id(plan_id, db)
        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'plan_id is not found', 'internal_code': 2468})
            

    args_dict = {
        'service_type': service_type,
        'agent_id': user_id,
        'username': username,
        'name': name,
        'phone_number': phone_number,
        'email': email,
        'plan_id': plan_id,
        'domain_id': domain_id,
        'status': status_
    }

    prepar_dict = {key: value for key, value in args_dict.items() if value is not None}

    if start_create_time is not None:
        prepar_dict['created'] = start_create_time

    if end_expire_time is not None:
        prepar_dict['expire'] = end_expire_time
    
    resp_services = db_ssh_service.get_services_by_attrs(db, **prepar_dict)
    prepar_services = []

    for refrence_service in resp_services:
        domain_name_service = db_domain.get_domain_by_id(refrence_service.domain_id, db)
        service_ip = db_server.get_server_by_ip(domain_name_service.server_ip, db)
        prepar_services.append(
            {
                'service_id': refrence_service.service_id,
                'service_type': refrence_service.service_type,
                'domain_id': refrence_service.domain_id,
                'domain_name': domain_name_service.domain_name,
                'server_ip': domain_name_service.server_ip,
                'ssh_port': service_ip.ssh_port,
                'plan_id': refrence_service.plan_id,
                'name': refrence_service.name,
                'email': refrence_service.email,
                'phone_number': refrence_service.phone_number,
                'agent_id': refrence_service.agent_id,
                'password': refrence_service.password,
                'username': refrence_service.username,
                'created': refrence_service.created,
                'expire': refrence_service.expire,
                'status': refrence_service.status
            }
        )

    return SearchResponse(count= len(prepar_services), result= prepar_services)





