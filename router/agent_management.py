from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)
from sqlalchemy.orm.session import Session
from schemas import (
    HTTPError,
    Status,
    UserRegisterForDataBase,
    NewAgentRequest,
    UserRole,
    NewAgentForDataBase,
    ChangeAgentStatus,
    AgentListResponse,
    TokenUser
)
from db import db_user, db_agent, db_ssh_service
from db.database import get_db
from financial_api.user import  create_user_if_not_exist
from auth.auth import get_admin_user
from typing import List
from datetime import datetime, timedelta

router = APIRouter(prefix='/agent', tags=['Agent-Menagement'])

@router.post('/new', response_model= str,responses={status.HTTP_409_CONFLICT:{'model':HTTPError}, status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def create_new_agent(request: NewAgentRequest, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    agent = db_agent.get_agent_by_username(request.username, db)

    if agent:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'Username already exists', 'internal_code': 2409})


    if request.user_id is None:
        
        data = {
            'tel_id': None,
            'name': None,
            'phone_number': None,
            'email': None,
            'role': UserRole.AGENT
        }
        user = db_user.create_user(UserRegisterForDataBase(**data), db)
        status_code, resp = create_user_if_not_exist(user.user_id)
        
        if status_code == 2419 :
            db_user.delete_user(user.user_id, db)
            raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Error Or Connection Timeout', 'internal_code': 2419})
        
        elif status_code != 200:
            db_user.delete_user(user.user_id, db)
            raise HTTPException(status_code=resp.status_code ,detail= resp.json()['detail'])

    else :
        
        user = db_user.get_user(request.user_id, db)
        
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'The user_id could not be found', 'internal_code': 2404})
        
        if user.role in [UserRole.AGENT, UserRole.ADMIN]:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'The user_id already agent', 'internal_code': 2408})


    data = {
        'user_id': user.user_id,
        'bot_token': request.bot_token,
        'username': request.username,
        'password': request.password,
        'status': Status.ENABLE
    }
    
    db_agent.create_agent(NewAgentForDataBase(**data), db)

    # =====================
    # this part for swager for create a new node for telegram bot
    # =====================

    return 'agent successfully registered'

@router.post('/status', response_model= str, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def disable_or_enable_agent(request: ChangeAgentStatus, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    agent = db_agent.get_agent_by_user_id(request.agent_id, db)
    
    if agent is None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail={'message': 'The agent_id could not be found', 'internal_code': 2407})
    
    db_agent.change_status(request.agent_id, request.status, db)

    return f'successfully change the agent status to {request.status}'


@router.get('/list', response_model= List[AgentListResponse])
def get_list_agents(current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    agents = db_agent.get_all_agents(db)
    
    ls_resp = []
    for agent in agents:

        users = db_ssh_service.get_service_by_agent_id(agent.user_id, db)
        
        all_users = 0
        enable_users = 0
        disable_users = 0

        if users :
            all_users = len(users)

            for user in users:
                if user.status == Status.ENABLE:
                    enable_users += 1

                elif user.status == Status.DISABLE:
                    disable_users += 1

        data = {
            'user_id': agent.user_id,
            'username': agent.username,
            'total_user': all_users,
            'number_of_enable_users': enable_users,
            'number_of_disable_users': disable_users,
            'status': agent.status
        }

        ls_resp.append(data)

    return ls_resp


