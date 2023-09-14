from fastapi import ( 
    status, 
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import UserFinancial
from sqlalchemy.orm.session import Session
from financial_api.user import get_balance 
import logging


def check_balance(user: UserFinancial, price: float, db: Session, logger: logging.Logger):
     
    resp, err = get_balance(user.user_id)
    if err:
        logger.error(f'[check balance] failed to get agent balance (agent_id: {user.user_id})')
        return None, err
    
    balance = resp['balance'] 

    if balance < price :
        logger.error(f'[check balance] Insufficient balance (agent_id: {user.user_id} -balance: {balance} -interface_price: {price})')
        return None, HTTPException(status_code= status.HTTP_409_CONFLICT, detail= {'message': 'Insufficient balance', 'internal_code': 1412} )

    return balance, None
