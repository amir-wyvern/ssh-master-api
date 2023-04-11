from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import (
    UserInfo,
    UserDisplay,
    HTTPError,
    Status,
    ServiceType,
    UserSShServiceDisplay,
    UserRegisterForDataBase,

    DepositConfirmation,
    DepositRequest,
)
from db import db_user, db_ssh_service
from db.database import get_db
from auth.auth import get_auth

from financial_api.user import get_balance
from financial_api.deopsit import deposit_request, deposit_confirmation

import random
import string
import hashlib


router = APIRouter(prefix='/deposit', tags=['financial'])

def generate_password():

    length = 12
    chars = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(chars) for i in range(length))
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()[:20]

    return hashed_password


@router.post('/request', response_model= str, responses={404:{'model':HTTPError}})
def financial_deposit_request(request: DepositRequest, token: str= Depends(get_auth), db: Session=Depends(get_db)):

    user = db_user.get_user_by_telegram_id(request.tel_id, db)

    if user == None:
        raise HTTPException(status_code=403, detail= {'message': 'user not fount', 'internal_code': 1404} )

    status_code, resp = deposit_request(user.user_id, request.value)

    if status_code != 200:
        print(resp.json())
        # raise HTTPException(status_code=resp.status_code, detail= {'message': resp.content, 'internal_code': 1414} )
    
    return 'request deposit was successfuly'


@router.post('/confirmation', response_model= str, responses={404:{'model':HTTPError}})
def financial_deposit_confirmation(request: DepositConfirmation, token: str= Depends(get_auth), db: Session=Depends(get_db)):

    user = db_user.get_user_by_telegram_id(request.tel_id, db)

    if user == None:
        raise HTTPException(status_code=403, detail= {'message': 'user not fount', 'internal_code': 404} )

    status_code, resp = deposit_confirmation(user.user_id, request.tx_hash)

    if status_code != 200:
        raise HTTPException(status_code=403, detail= {'message': 'there is problem in financial part', 'internal_code': 1414} )
    
    return 'confirmation deposit was successfuly'


