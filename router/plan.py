from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import (
    PlanStatusDb,
    SshPlanState,
    FetchPlanResponse,
    SshPlanRegister,
    SshPlanResponse,
    HTTPError,
    TokenUser,
    NewSshPlanResponse
)
from db import db_ssh_plan
from typing import List
from db.database import get_db
from auth.auth import get_admin_user, get_agent_user
import logging

# Create a file handler to save logs to a file
logger = logging.getLogger('plan_router.log') 
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('plan_router.log') 
file_handler.setLevel(logging.INFO) 
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s') 
file_handler.setFormatter(formatter) 
logger.addHandler(file_handler) 
 
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

router = APIRouter(prefix='/plan', tags=['Plan'])

@router.get('/ssh/fetch', response_model= FetchPlanResponse)
def fetch_ssh_plan(plan_id: int = None, limit: int= None, price:float =None, duration: int= None, status_: PlanStatusDb = None, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    args_dict = {
        'plan_id': plan_id,
        'limit': limit,
        'price': price,
        'duration': duration,
        'status': status_
    }
    prepar_dict = {key: value for key, value in args_dict.items() if value is not None}

    resp_plan = db_ssh_plan.get_plans_by_attrs(db, **prepar_dict)
    
    return FetchPlanResponse(count= len(resp_plan), result= resp_plan) 


@router.post('/ssh/new', response_model= NewSshPlanResponse, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError} })
def create_new_ssh_plan(request: SshPlanRegister, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):
    

    args_dict = {
        'limit': request.limit,
        'price': request.price,
        'traffic': request.traffic,
        'duration': request.duration,
        'status': request.status
    }
    prepar_dict = {key: value for key, value in args_dict.items() if value is not None}

    resp_plan = db_ssh_plan.get_plans_by_attrs(db, **prepar_dict)
    
    if resp_plan:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT ,detail={'message': 'this plan already exists', 'internal_code': 2443})

    plan = db_ssh_plan.create_plan(request, db)  
    logger.info(f'[new ssh plan] successfully (limit: {request.limit} -price: {request.price} -duration: {request.duration} -traffic: {request.traffic})')

    return {'plan_id': plan.plan_id}


@router.put('/ssh/status', response_model= SshPlanResponse)
def update_ssh_plan_status(request: SshPlanState, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):
    
    plan = db_ssh_plan.get_plan_by_id(request.plan_id, db)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'message': 'plan_id not exists', 'internal_code': 2410})
    
    if plan.status == request.new_status:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT ,detail={'message': 'plan_id already has this status', 'internal_code': 2428})
    
    db_ssh_plan.change_status(request.plan_id, request.new_status, db)  
    logger.info(f'[change ssh plan status] successfully (plan_id: {request.plan_id} -new_status: {request.new_status})')

    return {'plan_id': request.plan_id, 'status': request.new_status}
