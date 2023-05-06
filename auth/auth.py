from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import jwt

import os
from dotenv import load_dotenv
from pathlib import Path
from passlib.context import CryptContext
from typing import Annotated
from pydantic import ValidationError
from jose import JWTError, jwt
from schemas import TokenUser, UserRole
from db.models import DbUser
from fastapi import (
  Depends,
  HTTPException,
  status,
  Security
) 

from schemas import Status, TokenData

dotenv_path = Path('.env')
load_dotenv(dotenv_path=dotenv_path) 

OAUTH2_SECRET_KEY = os.getenv('OAUTH2_SECRET_KEY')
OAUTH2_ALGORITHM = os.getenv('OAUTH2_ALGORITHM')

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    scopes={"agent": "agent user for access items", "admin": "administrator user"},
)

def verify_password(plain_password, hashed_password):
    # return pwd_context.verify(plain_passwor
    # d, hashed_password)
    return plain_password == hashed_password


def authenticate_user(user: DbUser, password: str, role: UserRole):
    
    if user is None:
        return False
    
    if user.role != role:
        return False
    
    if not verify_password(password, user.password):
        return False
    
    return user


def create_access_token(data: dict):
    to_encode = data.copy()
    encoded_jwt = jwt.encode(to_encode, OAUTH2_SECRET_KEY, algorithm=OAUTH2_ALGORITHM)
    return encoded_jwt


async def get_current_user(security_scopes: SecurityScopes, token: Annotated[str, Depends(oauth2_scheme)]):
    
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'

    else:
        authenticate_value = "Bearer"

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )

    try:
        payload = jwt.decode(token, OAUTH2_SECRET_KEY, algorithms=[OAUTH2_ALGORITHM])
        user_id: str = payload.get("user")
        if user_id is None:
            raise credentials_exception
        
        token_scopes = payload.get("scopes", [])
        role = payload.get("role", None)
        token_data = TokenData(scopes=token_scopes, user_id=user_id, role=role)
    
    except (JWTError, ValidationError):
        raise credentials_exception

    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )
    return TokenUser(user_id=user_id, role=role)


async def get_agent_user(current_user: Annotated[TokenUser, Security(get_current_user, scopes=["agent"])]):
    
    return current_user

async def get_admin_user(current_user: Annotated[TokenUser, Security(get_current_user, scopes=["admin", "agent"])]):
        
    return current_user

