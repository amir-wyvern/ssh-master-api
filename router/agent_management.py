from fastapi import (
    APIRouter,
    Depends,
    Query,
    HTTPException,
    status
)
from sqlalchemy.orm.session import Session
from schemas import (
    HTTPError,
    UserRegisterForDataBase,
    NewAgentRequest,
    UserRole,
    ChangeAgentStatus,
    AgentListResponse,
    UserStatus,
    ServiceStatus,
    TokenUser
)
from db import db_user, db_ssh_service
from db.database import get_db
from financial_api.user import  create_user_if_not_exist
from auth.auth import get_admin_user
from typing import List
import logging

# Create a file handler to save logs to a file
logger = logging.getLogger('agent_management_route.log') 

file_handler = logging.FileHandler('agent_management_route.log') 
file_handler.setLevel(logging.INFO) 
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s') 
file_handler.setFormatter(formatter) 
logger.addHandler(file_handler) 

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

router = APIRouter(prefix='/agent', tags=['Agent-Menagement'])


@router.post('/new', response_model= str,responses={status.HTTP_409_CONFLICT:{'model':HTTPError}, status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def create_new_agent(request: NewAgentRequest, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    agent = db_user.get_user_by_username(request.username, db)

    if agent:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'Username already exists', 'internal_code': 2409})

    if request.chat_id and db_user.get_user_by_chat_id(request.chat_id, db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'chat_id already exists', 'internal_code': 2423})
    
    if request.bot_token and db_user.get_user_by_bot_token(request.bot_token, db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'bot_token already exists', 'internal_code': 2424})
    
    data = {
        'chat_id': request.chat_id,
        'name': request.name,
        'phone_number': request.phone_number,
        'email': request.email,
        'bot_token': request.bot_token,
        'username': request.username,
        'password': request.password,
        'status': request.status,
        'role': UserRole.AGENT
    }

    user = db_user.create_user(UserRegisterForDataBase(**data), db)

    _, err = create_user_if_not_exist(user.user_id)
    
    if err :
        logger.error(f'[creation agent] failed create the agent [agent: {current_user.user_id} -username: {request.username} -resp_code: {err.resp_code} -error: {err.detail}]')
        db_user.delete_user(user.user_id, db)
        raise err
    
    logger.info(f'[creation agent] successfully ({request.username})')

    return 'agent successfully registered'


@router.post('/status', response_model= str, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def disable_or_enable_agent(request: ChangeAgentStatus, new_status: UserStatus= Query(...), current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    agent = db_user.get_user_by_username(request.username, db)
    
    if agent is None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail={'message': 'username could not be found', 'internal_code': 2407})
    
    if agent.status == new_status:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'agent already has this status', 'internal_code': 2430})

    db_user.change_status(agent.user_id, new_status, db)
    logger.info(f'[change agent status] successfully ({request.username})')

    return f'successfully change the {agent.username} agent status to {new_status}'


@router.get('/list', response_model= List[AgentListResponse])
def get_list_agents(current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    agents = db_user.get_all_users_by_role(UserRole.AGENT, db)
    
    ls_resp = []
    for agent in agents:

        services = db_ssh_service.get_services_by_agent_id(agent.user_id, db)
        
        all_services = 0
        enable_services = 0
        disable_services = 0
        deleted_services = 0

        if services :
            all_services = len(services) 

            for service in services:
                if service.status == ServiceStatus.ENABLE:
                    enable_services += 1

                elif service.status == ServiceStatus.DISABLE:
                    disable_services += 1

                elif service.status == ServiceStatus.DELETED:
                    deleted_services += 1

        data = {
            'agent_id': agent.user_id,
            'username': agent.username,
            'total_ssh_user': all_services,
            'enable_ssh_services': enable_services,
            'disable_ssh_services': disable_services,
            'deleted_ssh_services': deleted_services,
            'status': agent.status
        }

        ls_resp.append(data)

    return ls_resp


