from typing import Annotated

from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from db import db_user
from db.database import get_db
from schemas import Token, UserRole, UserStatusDb
from auth.auth import authenticate_user, create_access_token
import logging

# Create a file handler to save logs to a file
logger = logging.getLogger('auth_router.log') 
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('auth_router.log') 
file_handler.setLevel(logging.INFO) 
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s') 
file_handler.setFormatter(formatter) 
logger.addHandler(file_handler) 

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

router = APIRouter(prefix='/auth', tags=['Auth'])

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db= Depends(get_db)):
    
    if form_data.scopes and 'admin' in form_data.scopes :
        
        scopes = ['admin', 'agent']
        role = 'admin'

    elif form_data.scopes and 'agent' in form_data.scopes:
        
        scopes = ['agent']
        role = 'agent'

    else : 
        raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unkown Scopes",
        )
    try:
        try:
            user_unchecked = db_user.get_user_by_username(form_data.username, db) 
        
        except Exception as e:
            user_unchecked = db_user.get_user_by_username(form_data.username, db) 

    except Exception as e:
        logger.error(f'[login] error in database (user:{form_data.username} -error: {e})')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='check the logs for more info')
    
    user = authenticate_user(user_unchecked, form_data.password, getattr(UserRole, role.upper()) )

    if user == False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    
    if user.status == UserStatusDb.DISABLE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This Username is Disable")

    access_token = create_access_token(
        data={"user": user.user_id, 'role': role, "scopes": scopes},
    )

    return {"access_token": access_token, "token_type": "bearer"}
