from typing import Annotated

from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from db import db_user
from db.database import get_db
from schemas import Token, UserRole, UserStatus
from auth.auth import authenticate_user, create_access_token


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
    
    user_unchecked = db_user.get_user_by_username(form_data.username, db) 

    user = authenticate_user(user_unchecked, form_data.password, getattr(UserRole, role.upper()) )

    if user == False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    
    if user.status == UserStatus.DISABLE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This Username is Disable")

    access_token = create_access_token(
        data={"user": user.user_id, 'role': role, "scopes": scopes},
    )

    return {"access_token": access_token, "token_type": "bearer"}
