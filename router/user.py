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
    UserRegisterForDataBase
)
from db import db_user, db_ssh_service
from db.database import get_db
from auth.auth import get_auth

import random
import string
import hashlib
import requests
import os

FINANCIAL_URL= os.getenv('FINANCIAL_URL')

router = APIRouter(prefix='/user', tags=['user'])

def generate_password():

    length = 12
    chars = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(chars) for i in range(length))
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()[:20]

    return hashed_password


@router.post('/info', response_model= UserDisplay, responses={404:{'model':HTTPError}})
def info(request: UserInfo, token: str= Depends(get_auth), db: Session=Depends(get_db)):

    user = db_user.get_user_by_telegram_id(request.tel_id, db)

    if user == None:
        raise HTTPException(status_code=403, detail= {'message': 'user not fount', 'internal_code': 404} )

        return  
    
    
    services = db_ssh_service.get_service_by_user_id(user.user_id, db, status= Status.ENABLE)

    ls_service = []
    for service in services:
        
        ssh_service = db_ssh_service.get_service_by_id(service.service_id, db)

        service_data = {
            'service_type': ServiceType.SSH,
            'detail': UserSShServiceDisplay(**{
                'service_id': ssh_service.service_id,
                'host': ssh_service.server_ip,
                'port': ssh_service.port,
                'username': ssh_service.username,
                'password': ssh_service.password,
                'expire': ssh_service.expire
            })
        }

        ls_service.append(service_data)
        
    # balance = get_balance(user.user_id)
    user_info = {
        'tel_id': user.tel_id,
        'phone_number': user.phone_number,
        'email': user.email,
        'role': user.role
    }
    
    resp = {
        'user': UserRegisterForDataBase(**user_info),
        'balance': 11,
        'services': ls_service
    }
    return UserDisplay(**resp)


def get_balance(user_id):
    
    requests.get(FINANCIAL_URL + 'user')