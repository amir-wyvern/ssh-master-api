from fastapi import (
    APIRouter,
    Depends,
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
    ServiceStatusDb,
    TokenUser,
    ListSubsetResponse,
    UpdateSubsetLimit,
    CreateSubsetProfit,
    NewAgentResponse,
    ConfigType
)
from db import db_user, db_ssh_service, db_subset
from db.database import get_db
from financial_api.user import  create_user_if_not_exist
from auth.auth import get_admin_user
from financial_api.user import get_balance
from typing import List
import logging
import string
import random

# Create a file handler to save logs to a file
logger = logging.getLogger('agent_management_route.log') 
logger.setLevel(logging.INFO)

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


@router.post('/new', response_model= NewAgentResponse,responses={status.HTTP_409_CONFLICT:{'model':HTTPError}, status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def create_new_agent(request: NewAgentRequest, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    agent = db_user.get_user_by_username(request.username, db)

    if agent:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'username already exists', 'internal_code': 2409})

    if request.chat_id and db_user.get_user_by_chat_id(request.chat_id, db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'chat_id already exists', 'internal_code': 2423})
    
    if request.bot_token and db_user.get_user_by_bot_token(request.bot_token, db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'bot_token already exists', 'internal_code': 2424})
    
    if request.email and db_user.get_user_by_email(request.email, db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'email already exists', 'internal_code': 2441})
    
    if request.phone_number and db_user.get_user_by_phone_number(request.bot_token, db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'phone number already exists', 'internal_code': 2442})
    
    parent_agent_id = 1
    if request.referal_link:

        parent_agent = db_user.get_user_by_referal_link(request.referal_link, db)
        if parent_agent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'the referal link is not exist', 'internal_code': 2462})

        ls_subset = db_user.get_users_by_parent_agent_id(parent_agent.user_id, db)

        if len(ls_subset) >= parent_agent.subset_limit:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'the parent agent reach to max subset limit', 'internal_code': 2463})

        parent_agent_id = parent_agent.user_id

    while True:
        characters = string.ascii_letters + string.digits
        referal_link = ''.join(random.choice(characters) for _ in range(7))
        if db_user.get_user_by_referal_link(referal_link, db) is None:
            break

    data = {
        'chat_id': request.chat_id,
        'parent_agent_id': parent_agent_id,
        'name': request.name,
        'phone_number': request.phone_number,
        'email': request.email,
        'bot_token': request.bot_token,
        'username': request.username,
        'password': request.password,
        'referal_link': referal_link,
        'subset_limit': request.subset_limit,
        'status': request.status,
        'role': UserRole.AGENT
    }

    user = db_user.create_user(UserRegisterForDataBase(**data), db)

    # create user in financial api
    _, err = create_user_if_not_exist(user.user_id)
    
    if err :
        logger.error(f'[creation agent] failed create the agent [agent: {current_user.user_id} -username: {request.username} -resp_code: {err.status_code} -error: {err.detail}]')
        db_user.delete_user(user.user_id, db)
        raise err
    
    db_subset.create_subset(CreateSubsetProfit(
        user_id= user.user_id,
        not_released_profit= 0,
        total_profit= 0,
        number_of_configs= 0), db)
    
    logger.info(f'[creation agent] successfully ({request.username})')

    return NewAgentResponse(agent_id=user.user_id, referal_link= referal_link)


@router.put('/status', response_model= str, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def disable_or_enable_agent(request: ChangeAgentStatus, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    agent = db_user.get_user_by_username(request.username, db)
    
    if agent is None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail={'message': 'username could not be found', 'internal_code': 2407})
    
    if agent.status == request.new_status:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'agent already has this status', 'internal_code': 2430})

    db_user.change_status(agent.user_id, request.new_status, db)
    logger.info(f'[change agent status] successfully ({request.username})')

    return f'successfully change the {agent.username} agent status to {request.new_status}'


@router.get('/list', response_model= List[AgentListResponse])
def get_list_agents(current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    agents = db_user.get_all_users( db)
    
    ls_resp = []
    for agent in agents:

        services = db_ssh_service.get_services_by_agent_id(agent.user_id, db, type_= ConfigType.MAIN)
        test_services = db_ssh_service.get_services_by_agent_id(agent.user_id, db, type_= ConfigType.TEST)
        
        all_services = 0
        enable_services = 0
        disable_services = 0
        expired_services = 0
        deleted_services = 0

        if services :
            all_services = len(services) 

            for service in services:
                if service.status == ServiceStatusDb.ENABLE:
                    enable_services += 1

                elif service.status == ServiceStatusDb.DISABLE:
                    disable_services += 1

                elif service.status == ServiceStatusDb.DELETED:
                    deleted_services += 1

                elif service.status == ServiceStatusDb.EXPIRED:
                    expired_services += 1

        resp_balance, err = get_balance(agent.user_id)
        if err:
            logger.error(f'[subset profit] get balance (username: {agent.username} -error: {err.detail})')
            resp_balance = {'balance': '***'}

        agent_subset = db_subset.get_subset_by_user(agent.user_id, db)
        number_of_subsets = len(db_user.get_users_by_parent_agent_id(agent.parent_agent_id, db))
        
        data = {
            'agent_id': agent.user_id,
            'username': agent.username,
            'parent_agent_id': agent.parent_agent_id,
            'referal_link': agent.referal_link,
            'balance': resp_balance['balance'],
            'subset_limit': agent.subset_limit,
            'subset_not_released_profit': agent_subset.not_released_profit,
            'subset_total_profit': agent_subset.total_profit,
            'subset_number_of_configs': agent_subset.number_of_configs,
            'number_of_subsets': number_of_subsets,
            'total_ssh_user': all_services,
            'enable_ssh_services': enable_services,
            'disable_ssh_services': disable_services,
            'expired_ssh_services': expired_services,
            'deleted_ssh_services': deleted_services,
            'test_ssh_services': len(test_services),
            'status': agent.status
        }

        ls_resp.append(data)

    return ls_resp


@router.get('/subset/list', response_model= List[ListSubsetResponse],responses={status.HTTP_409_CONFLICT:{'model':HTTPError}, status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def get_subset_via_agent(username: str, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    agent = db_user.get_user_by_username(username, db)

    if agent is None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail={'message': 'username could not be found', 'internal_code': 2407})
    
    ls_subset = db_user.get_users_by_parent_agent_id(agent.user_id, db)
    return ls_subset


@router.put('/subset/limit', response_model= str,responses={status.HTTP_409_CONFLICT:{'model':HTTPError}, status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def update_subset_limit(request: UpdateSubsetLimit, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    agent = db_user.get_user_by_username(request.username, db)
    
    if agent is None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail={'message': 'username could not be found', 'internal_code': 2407})
    
    db_user.update_subset_limit(agent.user_id, request.new_limit, db)

    return f'Successfully update limit of subset (username: {request.username} -new_limit: {request.new_limit})'


