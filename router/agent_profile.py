from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import (
    HTTPError,
    Status,
    AgentInfoResponse,
    UsersInfoAgentResponse,
    UpdateAgentPassword,
    UpdateAgentBotToken,
    TokenUser,
    UserRole
)
from typing import List
from db import db_user, db_ssh_service
from db.database import get_db
from auth.auth import  get_agent_user
from datetime import datetime, timedelta
from financial_api.user import get_balance

router = APIRouter(prefix='/agent', tags=['Agent-Profile'])

@router.get('/users', response_model= List[UsersInfoAgentResponse], responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}}, tags=['Agent-Menagement'])
def get_all_agent_users(username: str= Query(None,description='This filed (username) is For Admin'), number_day_to_expire: int= Query(..., gt=0) ,user_status: Status= Status.ALL, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):
    
    if current_user.role == UserRole.ADMIN and username is not None:
        agent = db_user.get_user_by_username(username, db)
        user_id = agent.user_id

        if agent is None:
            raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail={'message': 'username could not be found', 'internal_code': 2407})
        
    else:
        user_id = current_user.user_id

    start_time = datetime.now() 
    end_time = datetime.now() + timedelta(days= number_day_to_expire)
    
    if user_status == Status.ALL:
        services = db_ssh_service.get_services_by_agent_and_range_time(user_id, start_time, end_time, db)
    
    else : 
        services = db_ssh_service.get_services_by_agent_and_range_time(user_id, start_time, end_time, db, status= user_status)
    
    return services


@router.get('/info', response_model= AgentInfoResponse, responses={
    status.HTTP_404_NOT_FOUND:{'model':HTTPError},
    status.HTTP_408_REQUEST_TIMEOUT:{'model':HTTPError},
    status.HTTP_400_BAD_REQUEST:{'model':HTTPError}})
def get_agent_information(username: str= Query(None,description='This filed (agent_id) is For Admin'), current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    if current_user.role == UserRole.ADMIN and username is not None:

        agent = db_user.get_user_by_username(username, db)
        user_id = agent.user_id

        if agent is None:
            raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail={'message': 'username could not be found', 'internal_code': 2407})
        
    else:
        user_id = current_user.user_id

    services = db_ssh_service.get_services_by_agent_id(user_id, db) 

    all_services = 0
    enable_services = 0
    disable_services = 0

    if services :
        all_services = len(services) 

        for user in services:
            if user.status == Status.ENABLE:
                enable_services += 1

            elif user.status == Status.DISABLE:
                disable_services += 1

    status_code, resp = get_balance(user_id)
    
    if status_code == 2419:
        raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail= {'message': 'Connection Error Or Connection Timeout', 'internal_code': 2419} )

    elif status_code != 200:
        raise HTTPException(status_code=status_code, detail= resp.json()['detail'] )

    user = db_user.get_user_by_user_id(user_id, db) 

    data = {
        'agent_id': user.user_id,
        'chat_id': user.chat_id,
        'balance': resp.json()['balance'],
        'name': user.name,
        'phone_number': user.phone_number,
        'email': user.email,
        'bot_token': user.bot_token,
        'username': user.username,
        'total_user': all_services,
        'number_of_enable_services': enable_services,
        'number_of_disable_services': disable_services,
        'role': user.role,
        'status': user.status
    }

    return AgentInfoResponse(**data)

@router.post('/password', response_model= str, responses={status.HTTP_401_UNAUTHORIZED:{'model':HTTPError}})
def update_agent_password(request: UpdateAgentPassword, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    if current_user.role == UserRole.ADMIN :
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail={'message': "admin can't access to this item", 'internal_code': 2418})

    db_user.update_password(current_user.user_id, request.password, db) 
    
    return 'the agent password successfully has changed'


@router.post('/bot_token', response_model= str, responses={status.HTTP_401_UNAUTHORIZED:{'model':HTTPError}})
def update_agent_bot_token(request: UpdateAgentBotToken, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    if current_user.role == UserRole.ADMIN :
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail={'message': "admin can't access to this item", 'internal_code': 2418})

    db_user.update_bot_token(current_user.user_id, request.bot_token, db)
    
    return 'the agent bot_token successfully has changed'




