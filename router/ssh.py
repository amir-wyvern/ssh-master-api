from fastapi import ( 
    APIRouter, 
    Depends, 
    status, 
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import (
    NewSsh, 
    UserRole, 
    NewSshResponse,  
    UpdateSshExpire,  
    UpdateSshExpireResponse,  
    SshService, 
    DeleteSsh, 
    UnBlockSsh, 
    BlockSsh, 
    HTTPError, 
    PlanStatusDb,
    ServiceStatusDb,
    ServerStatusDb,
    DomainStatusDb,
    UserFinancial,
    RenewSsh,
    TokenUser,
    ConfigType,
)
from db import (
    db_server,
    db_ssh_plan,
    db_ssh_service,
    db_domain,
    db_subset,
    db_user
)
import pytz 

from cache.cache_session import set_test_account_cache, get_test_account_number
from cache.database import get_redis_cache
from db.database import get_db
from auth.auth import get_agent_user

from random import randint
from datetime import datetime, timedelta
from slave_api.ssh import (
    create_ssh_account,
    delete_ssh_account,
    block_ssh_account,
    unblock_ssh_account
)

from utils.password import generate_password
from utils.server import find_best_server
from utils.domain import get_domain_via_server, get_server_via_domain
from utils.financial import check_balance
from financial_api.transfer import transfer 
import logging
import os

# Create a file handler to save logs to a file
logger = logging.getLogger('ssh_route.log') 
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('ssh_route.log') 
file_handler.setLevel(logging.INFO) 
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s') 
file_handler.setFormatter(formatter) 
logger.addHandler(file_handler) 

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

PERCENT_PARTNERSHIP_PROFIT = float(os.getenv('PERCENT_PARTNERSHIP_PROFIT'))
ADMID_ID_FOR_FINANCIAL = 1 
MAX_TEST_ACCOUNT = 3
MAX_USER_DOMAIN = 10

router = APIRouter(prefix='/agent/ssh', tags=['Ssh-Agent'])


@router.post('/test', response_model= NewSshResponse, responses= {
    status.HTTP_409_CONFLICT:{'model': HTTPError},
    status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError},
    status.HTTP_406_NOT_ACCEPTABLE:{'model': HTTPError},
    status.HTTP_404_NOT_FOUND:{'model': HTTPError},
    status.HTTP_400_BAD_REQUEST:{'model':HTTPError},
    status.HTTP_423_LOCKED:{'model':HTTPError},
    status.HTTP_500_INTERNAL_SERVER_ERROR:{'model':HTTPError},
    })
def create_test_ssh_via_agent(request: NewSsh, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    plan = db_ssh_plan.get_plan_by_id(request.plan_id, db)
    
    if plan == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'plan_id not exists', 'internal_code': 2410})
    
    elif plan.status == PlanStatusDb.DISABLE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'plan_id is disable', 'internal_code': 2426})

    test_account_number = get_test_account_number(current_user.user_id, get_redis_cache().__next__())
    if current_user.role != UserRole.ADMIN and test_account_number >= MAX_TEST_ACCOUNT:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':"you'r reach to max test account'", 'internal_code': 2459})

    if request.domain_name:

        selected_domain = db_domain.get_domain_by_name(request.domain_name, db)
        
        if selected_domain is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2449, 'message':'Domain not exists'})
    
        selected_server, err = get_server_via_domain(selected_domain.domain_id, db)
        if err:
            raise err
        
    else:
        
        selected_server = find_best_server(db)
        if selected_server is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2450, 'message':'There is no server for new config'})
        
        selected_domain, err = get_domain_via_server(selected_server, db, logger)
        if err:
            raise err

    password = generate_password()
    while True:

        username = 'user_' + str(randint(100_000, 999_000))
        if db_ssh_service.get_service_by_username(username, db) == None:
            break

    _, err = create_ssh_account(selected_server.server_ip, username, password)
    if err:
        logger.error(f'[new test ssh] ssh account creation failed (agent: {current_user.user_id} -server_ip: {selected_server.server_ip} -domain: {selected_domain.domain_name} -plan_id: {plan.plan_id} -resp_code: {err.status_code} -error: {err.detail})')
        raise err


    service_data = {
        'service_type': ConfigType.TEST,
        'domain_id': selected_domain.domain_id,
        'plan_id': plan.plan_id,
        'password': password,
        'username': username,
        'name': request.name,
        'phone_number': request.phone_number,
        'email': request.email,
        'agent_id': current_user.user_id,
        'user_chat_id': request.chat_id,
        'limit': plan.limit,
        'created': datetime.now().replace(tzinfo=pytz.utc),
        'expire': datetime.now().replace(tzinfo=pytz.utc) + timedelta(days=1),
        'status': ServiceStatusDb.ENABLE
    }

    # ================= Begin =================
    try:
        service = db_ssh_service.create_ssh(SshService(**service_data), db, commit=False)
        db_server.increase_ssh_accounts_number(selected_server.server_ip, db, commit=False)
        db.commit()
        db.refresh(service)

    except Exception as e:
        logger.error(f'[new test ssh] error in database (agent: {current_user.user_id} -username: {username} -error: {e})')
        db.rollback()
        _, err = delete_ssh_account(selected_server.server_ip, username)
        if err:
            logger.error(f'[new test ssh] error in delete account (agent: {current_user.user_id} -username: {username} -server_ip: {selected_server.server_ip} -domain: {selected_domain.domain_name} -resp_code: {err.status_code} -detail: {err.detail})')
        
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='check the logs for more info')
    # ================= Commit =================

    response_message = {
        'username': username, 
        'password': password, 
        'host': selected_domain.domain_name,
        'port': selected_server.ssh_port,
    }

    set_test_account_cache(current_user.user_id, username, 24*60*60, get_redis_cache().__next__())
    logger.info(f'[new test ssh] the ssh account was created successfully (agent: {current_user.user_id} -username: {username} -server_ip: {selected_server.server_ip} -domain: {selected_domain.domain_name} -plan_id: {plan.plan_id})')
    
    return NewSshResponse(**response_message)


@router.post('/new', response_model= NewSshResponse, responses= {
    status.HTTP_409_CONFLICT:{'model': HTTPError},
    status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError},
    status.HTTP_406_NOT_ACCEPTABLE:{'model': HTTPError},
    status.HTTP_404_NOT_FOUND:{'model': HTTPError},
    status.HTTP_400_BAD_REQUEST:{'model':HTTPError},
    status.HTTP_423_LOCKED:{'model':HTTPError},
    status.HTTP_500_INTERNAL_SERVER_ERROR:{'model':HTTPError},
    })
def create_new_ssh_via_agent(request: NewSsh, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):
    
    plan = db_ssh_plan.get_plan_by_id(request.plan_id, db)
    
    if plan == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'plan_id not exists', 'internal_code': 2410})
    
    elif plan.status == PlanStatusDb.DISABLE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'plan_id is disable', 'internal_code': 2426})

    if request.domain_name:

        selected_domain = db_domain.get_domain_by_name(request.domain_name, db)
        
        if selected_domain is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2449, 'message':'Domain not exists'})
    
        selected_server, err = get_server_via_domain(selected_domain.domain_id, db)
        if err:
            raise err
        
    else:
        
        selected_server = find_best_server(db)
        if selected_server is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2450, 'message':'There is no server for new config'})
        
        selected_domain, err = get_domain_via_server(selected_server, db, logger)
        if err:
            raise err

    password = generate_password()
    while True:

        username = 'user_' + str(randint(100_000, 999_000))
        if db_ssh_service.get_service_by_username(username, db) == None:
            break
        
    user_financial = UserFinancial(user_id= current_user.user_id, username= username, password= password)
    
    if current_user.role == UserRole.AGENT:
        
        _, err = check_balance(user_financial, plan.price, db, logger) 
        if err: 
            raise err


    _, err = create_ssh_account(selected_server.server_ip, username, password)
    if err:
        logger.error(f'[new ssh] ssh account creation failed (agent: {current_user.user_id} -server_ip: {selected_server.server_ip} -domain: {selected_domain.domain_name} -plan_id: {plan.plan_id} -resp_code: {err.status_code} -error: {err.detail})')
        raise err
    
    if current_user.role == UserRole.AGENT:

        _, err = transfer(user_financial.user_id, ADMID_ID_FOR_FINANCIAL, plan.price)
        if err:
            logger.error(f'[new ssh] failed to transfer credit  (agent: {user_financial.user_id} -username: {username} -resp_code: {err.status_code} -error: {err.detail})')
            
            _, del_err = delete_ssh_account(selected_server.server_ip, username)
            if del_err:
                logger.error(f'[delete] failed to deleting ssh account (agent: {current_user.user_id} -username: {username} -server_ip: {selected_server.server_ip} -domain: {selected_domain.domain_name} -resp_code: {del_err.status_code} -detail: {del_err.detail})')
            
            raise err
        
        logger.info(f'[new ssh] successfully transfered credit (agent: {user_financial.user_id} -price: {plan.price})')
    
    
    service_data = {
        'service_type': ConfigType.MAIN,
        'domain_id': selected_domain.domain_id,
        'plan_id': plan.plan_id,
        'password': password,
        'username': username,
        'name': request.name,
        'phone_number': request.phone_number,
        'email': request.email,
        'agent_id': current_user.user_id,
        'user_chat_id': request.chat_id,
        'limit': plan.limit,
        'created': datetime.now().replace(tzinfo=pytz.utc),
        'expire': datetime.now().replace(tzinfo=pytz.utc) + timedelta(days=30),
        'status': ServiceStatusDb.ENABLE
    }

    # ================= Begin =================
    try:
        service = db_ssh_service.create_ssh(SshService(**service_data), db, commit=False)
        db_server.increase_ssh_accounts_number(selected_server.server_ip, db, commit=False)
        db.commit()
        db.refresh(service)
    
    except Exception as e:
        logger.error(f'[new ssh] error in database (agent: {current_user.user_id} -username: {username} -error: {e})')
        db.rollback()
        _, err = delete_ssh_account(selected_server.server_ip, username)
        if err:
            logger.error(f'[new ssh] error (agent: {current_user.user_id} -username: {username} -server_ip: {selected_server.server_ip} -domain: {selected_domain.domain_name} -resp_code: {err.status_code} -detail: {err.detail})')
        
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='check the logs for more info')
    # ================= Commit =================

    agent = db_user.get_user_by_user_id(current_user.user_id, db)
    db_subset.increase_not_released_profit_by_user(agent.parent_agent_id, plan.price * PERCENT_PARTNERSHIP_PROFIT, db , commit= False)
    db_subset.increase_number_of_configs_by_user(agent.parent_agent_id, db, commit= False)
    db.commit()

    logger.info(f'[new ssh] increase the parent agent profit (agent: {current_user.user_id} -parent_agent: {agent.parent_agent_id} -profit_value: {plan.price * PERCENT_PARTNERSHIP_PROFIT} -percent: {PERCENT_PARTNERSHIP_PROFIT} -value: {plan.price})')
    
    response_message = {
        'username': username, 
        'password': password, 
        'host': selected_domain.domain_name,
        'port': selected_server.ssh_port,
    }

    logger.info(f'[new ssh] the ssh account was created successfully (agent: {current_user.user_id} -username: {username} -server_ip: {selected_server.server_ip} -domain: {selected_domain.domain_name} -plan_id: {plan.plan_id})')
    
    return NewSshResponse(**response_message)


@router.put('/expire', response_model= UpdateSshExpireResponse, responses={
    status.HTTP_404_NOT_FOUND:{'model': HTTPError},
    status.HTTP_422_UNPROCESSABLE_ENTITY:{'model': HTTPError},
    status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError},
    status.HTTP_400_BAD_REQUEST:{'model':HTTPError},
    status.HTTP_423_LOCKED:{'model':HTTPError},
    status.HTTP_409_CONFLICT:{'model':HTTPError}} )
def update_ssh_account_expire(request: UpdateSshExpire, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    username = request.username.lower()    
    service = db_ssh_service.get_service_by_username(username, db)

    if service == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'This Username have not any service', 'internal_code': 2433})
    
    if service.status == ServiceStatusDb.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'This service had deleted ', 'internal_code': 2437})

    if current_user.role != UserRole.ADMIN and service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})
    
    plan = db_ssh_plan.get_plan_by_id(service.plan_id, db)

    if plan.status == PlanStatusDb.DISABLE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'plan_id is disable', 'internal_code': 2426})

    domain = db_domain.get_domain_by_id(service.domain_id, db)

    if domain.status == DomainStatusDb.DISABLE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'The domain_id is disable', 'internal_code': 2451})
    
    server = db_server.get_server_by_ip(domain.server_ip, db)

    if server.update_expire_status == ServerStatusDb.DISABLE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message': f'The Server [{server.server_ip}] has disable (update expire status)', 'internal_code': 2453})
    
    if server.status == ServerStatusDb.DISABLE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message': f'The Server [{server.server_ip}] has disable (main status)', 'internal_code': 2453})

    request_new_expire = request.new_expire.replace(tzinfo=pytz.utc)
    service_expire = service.expire.replace(tzinfo=pytz.utc)
    
    if request_new_expire <= datetime.now().replace(tzinfo=pytz.utc):
        raise HTTPException(status_code= status.HTTP_422_UNPROCESSABLE_ENTITY, detail={'message': 'invalid parameter for new expire', 'internal_code': 2414}) 
    

    price = None
    user_financial = UserFinancial(user_id= current_user.user_id, username= username)

    
    unit_price = plan.price / (plan.duration * 24 * 60) 
    update_hours = abs(request_new_expire - service_expire) 
    price = (update_hours.total_seconds() / 60) * unit_price 

    if current_user.role == UserRole.AGENT and request_new_expire > service_expire:

        _, err = check_balance(user_financial, price, db, logger)
        if err:
            raise err

    if request.unblock == True:
        _, err = unblock_ssh_account(domain.server_ip, username)
        if err:
            logger.error(f'[expire] unblock user failed (agent: {current_user.user_id} -server_ip: {domain.server_ip} -domain: {domain.domain_name} -username: {username} -resp_code: {err.status_code} -error: {err.detail})')
            raise err

    
    if current_user.role == UserRole.AGENT and request_new_expire > service_expire:

        from_ = service.agent_id
        to_ = ADMID_ID_FOR_FINANCIAL

        _, err = transfer(from_, to_, price)
        if err:
            logger.error(f'[expire] transfer credit Faied (agent: {current_user.user_id} -price: {price} -resp_code: {err.status_code} error: {err.detail})')
            _, err_block = block_ssh_account(domain.server_ip, username)
            if err_block:
                logger.error(f'[expire] (failed transferd) block ssh account failed (agent: {current_user.user_id} -username: {username} -server_ip: {domain.server_ip} -domain: {domain.domain_name} -resp_code: {err_block.status_code} error: {err_block.detail})')

            raise err

        logger.info(f'[expire] successfully transfered credit (agent: {current_user.user_id} -price: {price})')
        
        # add log for increase profit 
        
        agent = db_user.get_user_by_user_id(current_user.user_id, db)
        db_subset.increase_not_released_profit_by_user(agent.parent_agent_id, price * PERCENT_PARTNERSHIP_PROFIT , commit= False, db= db)
        db.commit()

        logger.info(f'[expire] increase the parent agent profit (agent: {current_user.user_id} -parent_agent: {agent.parent_agent_id} -profit_value: {price * PERCENT_PARTNERSHIP_PROFIT} -percent: {PERCENT_PARTNERSHIP_PROFIT} -value: {price})')

    

    # =================== Begin ===================
    db_ssh_service.update_expire(service.service_id, request_new_expire, db, commit= False)
    db_ssh_service.change_status(service.service_id, ServiceStatusDb.ENABLE, db, commit=False)

    db.commit()

    # =================== Commit ===================
    logger.info(f'[expire] successfully update expire (agent: {current_user.user_id} -username:{username} -new_expire: {request.new_expire})')
    
    return UpdateSshExpireResponse(**{'username': service.username, 'expire': request_new_expire})


@router.post('/block', response_model= str, responses={status.HTTP_409_CONFLICT:{'model': HTTPError}, status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError}})
def block_ssh_account_via_agent(request: BlockSsh, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    username = request.username.lower()    
    service = db_ssh_service.get_service_by_username(username, db)

    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'This Username have not any service', 'internal_code':2433})

    if service.status == ServiceStatusDb.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'This service had deleted ', 'internal_code': 2437})

    if current_user.role != UserRole.ADMIN and service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})
    
    if service.status == ServiceStatusDb.DISABLE:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'The user has already been block', 'internal_code': 2415})

    domain = db_domain.get_domain_by_id(service.domain_id, db)

    _ ,err = block_ssh_account(domain.server_ip, username)
    if err:
        logger.error(f'[block] error (agent: {current_user.user_id} -username: {username} -resp_code: {err.status_code} -detail: {err.detail})')
        raise err
    
    db_ssh_service.change_status(service.service_id, ServiceStatusDb.DISABLE, db)
    logger.info(f'[block] successfully blocked (agent: {current_user.user_id} -username: {username})')

    return f'Successfully blocked user [{username}]'


@router.post('/unblock', response_model= str, responses={status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError}, status.HTTP_409_CONFLICT:{'model': HTTPError}})
def unblock_ssh_account_via_agent(request: UnBlockSsh, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    username = request.username.lower()
    service = db_ssh_service.get_service_by_username(username, db)

    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'This Username have not any service', 'internal_code':2433})
    
    if service.status == ServiceStatusDb.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'This service had deleted ', 'internal_code': 2437})

    if current_user.role != UserRole.ADMIN and service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})
    
    if service.status == ServiceStatusDb.ENABLE:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'The user is not blocked', 'internal_code': 2416})
 
    domain = db_domain.get_domain_by_id(service.domain_id, db)

    server = db_server.get_server_by_ip(domain.server_ip, db)

    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': f'Server [{service.server_ip}] is disable', 'internal_code':2421})

    # if server.ssh_accounts_number >= server.max_users:
    #     raise HTTPException(status_code= status.HTTP_406_NOT_ACCEPTABLE, detail={'message': f'The Server [{service.server_ip}] has reached to max users', 'internal_code': 2411})

    _, err = unblock_ssh_account(domain.server_ip, username)
    if err:
        logger.error(f'[unblock] error (agent: {current_user.user_id} -username: {username} -resp_code: {err.status_code} -detail: {err.detail})')
        raise err
    
    db_ssh_service.change_status(service.service_id, ServiceStatusDb.ENABLE, db)
    logger.info(f'[unblock] successfully unblocked (agent: {current_user.user_id} -username: {username})')

    return f'Successfully unblocked user [{username}]'


@router.delete('/delete', response_model= str, responses={
    status.HTTP_404_NOT_FOUND:{'model': HTTPError},
    status.HTTP_500_INTERNAL_SERVER_ERROR:{'model': HTTPError},
    status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError}})
def delete_ssh_account_via_agent(request: DeleteSsh, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    username = request.username.lower()
    service = db_ssh_service.get_service_by_username(username, db)
    
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'This Username have not any service', 'internal_code':2433})

    if service.status == ServiceStatusDb.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'This service had deleted ', 'internal_code': 2437})

    if current_user.role != UserRole.ADMIN and service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})

    domain = db_domain.get_domain_by_id(service.domain_id, db)

    _ ,err = delete_ssh_account(domain.server_ip, username)
    if err:
        logger.error(f'[delete] error (agent: {current_user.user_id} -username: {username} -resp_code: {err.status_code} -detail: {err.detail})')
        raise err
    
    try:
        db_server.decrease_ssh_accounts_number(domain.server_ip, db, commit=False) 
        db_ssh_service.change_status(service.service_id, ServiceStatusDb.DELETED, db, commit=False)
        db.commit()

    except Exception as e:
        logger.error(f'[delete] error in database (agent: {current_user.user_id} -username: {username} -error: {e})')
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='check the logs for more info')

    logger.info(f'[delete] successfully deleted (agent: {current_user.user_id} -username: {username})')
    return f'Successfully delete user [{username}]'


@router.post('/renew', response_model= NewSshResponse, responses={
    status.HTTP_404_NOT_FOUND:{'model': HTTPError},
    status.HTTP_500_INTERNAL_SERVER_ERROR:{'model': HTTPError},
    status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError},
    status.HTTP_409_CONFLICT:{'model':HTTPError}})
def renew_config(request: RenewSsh, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    username = request.username.lower()
    service = db_ssh_service.get_service_by_username(username, db)
    
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'This Username have not any service', 'internal_code':2433})

    if service.status == ServiceStatusDb.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'This service had deleted ', 'internal_code': 2437})

    if current_user.role != UserRole.ADMIN and service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})


    if request.new_domain_name :
        domain = db_domain.get_domain_by_name(request.new_domain_name, db)

        if domain == None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'domain_id not exists', 'internal_code': 2449})
        
        if service.domain_id == domain.domain_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'new domain is same with old domain', 'internal_code': 2467})
        
        selected_domain = domain
        selected_server, err = get_server_via_domain(domain.domain_id, db)
        if err:
            raise err

    else:

        selected_server = find_best_server(db, std_dev=2 ,except_domain_id= service.domain_id)
        if selected_server is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2450, 'message':'There is no server for new config'})
        
        selected_domain, err = get_domain_via_server(selected_server, db, logger)
        if err: 
            raise err


    old_domain = db_domain.get_domain_by_id(service.domain_id, db)
    logger.info(f'[renew] successfully find new server and domain (agent: {current_user.user_id} -username: {service.username} -old_domain: {old_domain.domain_name} -new_domain: {selected_domain.domain_name} -old_server: {old_domain.server_ip} -new_server: {selected_server.server_ip}')

    _, err = create_ssh_account(selected_server.server_ip, service.username, service.password)
    if err:
        logger.error(f'[renew] ssh account creation failed (agent: {current_user.user_id} -username: {service.username} -new_domain: {selected_domain.domain_name} -new_server: {selected_server.server_ip} -resp_code: {err.status_code} -detail: {err.detail})')
        raise err
    
    logger.info(f'[renew] ssh account successfully created (agent: {current_user.user_id} -username: {service.username} -new_domain: {selected_domain.domain_name} -new_server: {selected_server.server_ip})')
    
    if service.status == ServiceStatusDb.DISABLE or service.status == ServiceStatusDb.EXPIRED:
        _, err = block_ssh_account(selected_server.server_ip, service.username)
        if err:
            logger.error(f'[renew] ssh block account failed (agent: {current_user.user_id} -username: {service.username} -new_domain: {selected_domain.domain_name} -new_server: {selected_server.server_ip} -resp_code: {err.status_code} -detail: {err.detail})')
            raise err

        logger.info(f'[renew] successfully blocked ssh account (agent: {current_user.user_id} -username: {service.username} -new_domain: {selected_domain.domain_name} -new_server: {selected_server.server_ip})')
    
    _, err = delete_ssh_account(old_domain.server_ip, username)
    if err:
        logger.error(f'[renew] delete ssh account failed (agent: {current_user.user_id} -username: {service.username} -new_domain: {selected_domain.domain_name} -new_server: {selected_server.server_ip} -resp_code: {err.status_code} -detail: {err.detail})')
        # raise err
    
    logger.info(f'[renew] ssh account successfully deleted (agent: {current_user.user_id} -username: {service.username} -new_domain: {selected_domain.domain_name} -new_server: {selected_server.server_ip})')
    
    try:
        db_server.decrease_ssh_accounts_number(old_domain.server_ip, db, commit= False) 
        db_ssh_service.transfer_user_by_domain(service.username, selected_domain.domain_id, db, commit=False)
        db_server.increase_ssh_accounts_number(selected_server.server_ip, db, commit= False)
        db.commit()

    except Exception as e: 
        logger.error(f'[renew] error in database (agent: {current_user.user_id} -username: {service.username} -error: {e})')
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='check the logs for more info')
    
    response_message = {
        'username': username, 
        'password': service.password, 
        'host': selected_domain.domain_name,
        'port': selected_server.ssh_port,
    }
    
    logger.info(f'[renew] renew config successfully Done (-username: {service.username} -old_domain: {old_domain.domain_name} -new_domain: {selected_domain.domain_name} -old_server: {old_domain.server_ip} -new_server: {selected_server.server_ip}')
    return NewSshResponse(**response_message)

