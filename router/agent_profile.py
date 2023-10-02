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
    AgentInfoResponse,
    UpdateAgentPassword,
    UpdateAgentBotToken,
    UpdateAgentChatID,
    TokenUser,
    UserRole,
    ConfigType,
    ServiceStatusDb,
    ClaimPartnerShipProfit,
    PaymentMeothodPartnerShip
)
from db import db_user, db_ssh_service, db_subset
from db.database import get_db
from auth.auth import  get_agent_user
from financial_api.user import get_balance, set_balance
import logging

# Create a file handler to save logs to a file
logger = logging.getLogger('agent_profile_route.log') 
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('agent_profile_route.log') 
file_handler.setLevel(logging.INFO) 
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s') 
file_handler.setFormatter(formatter) 
logger.addHandler(file_handler) 

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


router = APIRouter(prefix='/agent', tags=['Agent-Profile'])

@router.get('/info', response_model= AgentInfoResponse, responses={
    status.HTTP_404_NOT_FOUND:{'model':HTTPError},
    status.HTTP_408_REQUEST_TIMEOUT:{'model':HTTPError},
    status.HTTP_400_BAD_REQUEST:{'model':HTTPError}})
def get_agent_information(username: str= Query(None,description='This filed (agent_id) is For Admin'), current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    if current_user.role == UserRole.ADMIN and username is not None:

        agent = db_user.get_user_by_username(username, db)
        
        if agent is None:
            raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail={'message': 'username could not be found', 'internal_code': 2407})
        
        user_id = agent.user_id

    else:
        user_id = current_user.user_id


    resp, err = get_balance(user_id)
    if err:
        logger.error(f'[agent info] get balance (user_id: {user_id} -error: {err.detail})')
        raise err

    services = db_ssh_service.get_services_by_agent_id(user_id, db, type_= ConfigType.MAIN) 
    enable_services_test = db_ssh_service.get_services_by_agent_id(user_id, db, type_= ConfigType.TEST, status= ServiceStatusDb.ENABLE) 
    expired_services_test = db_ssh_service.get_services_by_agent_id(user_id, db, type_= ConfigType.TEST, status= ServiceStatusDb.EXPIRED) 
    disable_services_test = db_ssh_service.get_services_by_agent_id(user_id, db, type_= ConfigType.TEST, status= ServiceStatusDb.DISABLE) 
    services_test = len(enable_services_test) + len(expired_services_test) + len(disable_services_test)

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

    user = db_user.get_user_by_user_id(user_id, db) 
    user_subset = db_subset.get_subset_by_user(user.user_id, db)

    subset_list = []
    for subset in db_user.get_users_by_parent_agent_id(user.user_id, db):
        subset_list.append(subset.username)

    data = {
        'agent_id': user.user_id,
        'chat_id': user.chat_id,
        'balance': resp['balance'],
        'name': user.name,
        'phone_number': user.phone_number,
        'email': user.email,
        'bot_token': user.bot_token,
        'username': user.username,
        'subset_not_released_profit': user_subset.not_released_profit,
        'subset_total_profit': user_subset.total_profit,
        'subset_number_of_configs': user_subset.number_of_configs,
        'subset_number_limit': user.subset_limit,
        'subset_list': subset_list,
        'total_user': all_services,
        'enable_ssh_services': enable_services,
        'disable_ssh_services': disable_services,
        'expired_ssh_services': expired_services,
        'deleted_ssh_services': deleted_services,
        'test_ssh_services': services_test,
        'referal_link': user.referal_link,
        'parent_agent_id': user.parent_agent_id,
        'role': user.role,
        'status': user.status
    }

    return AgentInfoResponse(**data)


@router.put('/password', response_model= str, responses={status.HTTP_401_UNAUTHORIZED:{'model':HTTPError}})
def update_agent_password(request: UpdateAgentPassword, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    db_user.update_password(current_user.user_id, request.password, db) 
    logger.info(f'[change agent password] successfully (user_id: {current_user.user_id})')

    return 'the agent password successfully has changed'


@router.post('/subset/profit', response_model= str, responses={status.HTTP_401_UNAUTHORIZED:{'model':HTTPError}})
def claim_partnership_profit(request: ClaimPartnerShipProfit, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    if current_user.role == UserRole.ADMIN :
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail={'message': "admin can't access to this item", 'internal_code': 2418})

    user_subset = db_subset.get_subset_by_user(current_user.user_id ,db)

    if user_subset == None:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': "you'r not have subset configs yet", 'internal_code': 2464})
    
    not_released_profit = float(user_subset.not_released_profit)

    if not_released_profit == 0.0 or request.value > not_released_profit:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': "you'r not have enough subset configs", 'internal_code': 2465})

    agent = db_user.get_user_by_user_id(current_user.user_id, db)

    if request.method == PaymentMeothodPartnerShip.WALLET:
        
        resp_balance, err = get_balance(current_user.user_id)
        if err:
            logger.error(f'[subset profit] get balance (username: {agent.username} -error: {err.detail})')
            raise err
        
        new_balance = request.value + resp_balance['balance']
        _, err = set_balance(current_user.user_id, new_balance)
        if err:
            logger.error(f'[subset profit] error in set balance (username: {agent.username}, error: {err.detail})')
            raise err
        
        db_subset.decrease_not_released_profit_by_user(current_user.user_id, request.value, db)

        logger.info(f'[subset profit] successfully transfer profit to wallet (username: {agent.username} -used_value: {request.value} -new_balance: {new_balance})')


    elif  request.method == PaymentMeothodPartnerShip.WITHDRAW:
        return 'This part is not yet complete'


    return 'successfully Done'


@router.put('/bot_token', response_model= str, responses={status.HTTP_401_UNAUTHORIZED:{'model':HTTPError}})
def update_agent_bot_token(request: UpdateAgentBotToken, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    db_user.update_bot_token(current_user.user_id, request.bot_token, db)
    logger.info(f'[change agent bot token] successfully (user_id: {current_user.user_id})')

    return 'the agent bot_token successfully has changed'

 
@router.put('/chat_id', response_model= str, responses={status.HTTP_401_UNAUTHORIZED:{'model':HTTPError}})
def update_agent_chat_id(request: UpdateAgentChatID, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    db_user.update_chat_id(current_user.user_id, request.new_chat_id, db)
    logger.info(f'[change agent chat_id] successfully (user_id: {current_user.user_id})')

    return 'the agent chat_id successfully has changed'

