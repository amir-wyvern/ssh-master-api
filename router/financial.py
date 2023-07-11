from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import (
    HTTPError,
    DepositConfirmation,
    DepositRequestResponse,
    DepositRequest,
    SetNewBalance,
    TokenUser,
    UserRole
)
from db import db_user
from db.database import get_db
from auth.auth import get_agent_user, get_admin_user

from financial_api.deopsit import deposit_request, deposit_confirmation
from financial_api.user import set_balance

import random
import string
import hashlib
import logging

# Create a file handler to save logs to a file
file_handler = logging.FileHandler('financial_route.log') 
file_handler.setLevel(logging.INFO) 
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s') 
file_handler.setFormatter(formatter) 

logger = logging.getLogger('financial_route.log') 
logger.addHandler(file_handler) 

router = APIRouter(prefix='/financial', tags=['Financial'])

def generate_password():

    length = 12
    chars = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(chars) for i in range(length))
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()[:20]

    return hashed_password


@router.post('/balance', response_model= str, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}, status.HTTP_408_REQUEST_TIMEOUT:{'model':HTTPError}}, tags=['Agent-Menagement'])
def update_agent_balance(request: SetNewBalance, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    agent = db_user.get_user_by_username(request.username, db)

    if agent is None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= {'message': 'username could not be found', 'internal_code': 2407} )

    resp, err = set_balance(agent.user_id, request.new_balance)
    if err:
        logger.error(f'[update agent balance] error in set balance (username:{agent.username}, error: {err.detail})')
        raise err
    
    logger.info(f'[update agent balance] successfully (username: {request.username})')
    return 'request balance update was successfully'


@router.post('/deposit/request', response_model= DepositRequestResponse, responses={
    status.HTTP_403_FORBIDDEN:{'model':HTTPError},
    status.HTTP_408_REQUEST_TIMEOUT:{'model':HTTPError},
    status.HTTP_423_LOCKED:{'model':HTTPError},
    status.HTTP_409_CONFLICT:{'model':HTTPError},
    status.HTTP_406_NOT_ACCEPTABLE:{'model':HTTPError},
    status.HTTP_417_EXPECTATION_FAILED:{'model':HTTPError}
    })
def financial_deposit_request(request: DepositRequest, current_user: TokenUser= Depends(get_agent_user)):

    if current_user.role == UserRole.ADMIN :
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail={'message': "admin can't access to this item", 'internal_code': 2418})


    resp, err = deposit_request(current_user.user_id, request.value)
    if err:
        logger.error(f'[deposit request] error (agent: {current_user.user_id} -price: {request.value} -error: {err.detail})')
        raise err
    
    logger.info(f'[deposit request] successfully (agent: {current_user.user_id} -price: {request.value})')
    
    return resp


@router.post('/deposit/confirmation', response_model= str, responses={status.HTTP_408_REQUEST_TIMEOUT:{'model':HTTPError}})
def financial_deposit_confirmation(request: DepositConfirmation, current_user: TokenUser= Depends(get_agent_user)):

    if current_user.role == UserRole.ADMIN :
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail={'message': "admin can't access to this item", 'internal_code': 2418})

    resp, err = deposit_confirmation(current_user.user_id, request.tx_hash)
    if err:
        logger.error(f'[deposit comfirmation] error (agent: {current_user.user_id} -tx_hash: {request.tx_hash} -error: {err.detail})')
        raise err

    logger.info(f'[deposit comfirmation] successfully (agent: {current_user.user_id} -tx_hash: {request.tx_hash})')
    
    return 'confirmation deposit was successfully'


