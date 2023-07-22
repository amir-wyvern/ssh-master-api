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
    InterfaceStatus,
    ServerStatus,
    ServiceStatus,
    RenewSsh,
    TokenUser
)
from db import (
    db_server,
    db_ssh_service,
    db_ssh_interface
)
import pytz 

from db.database import get_db
from auth.auth import get_agent_user, get_admin_user

from random import randint, choice
import string
import hashlib
from datetime import datetime, timedelta
from slave_api.ssh import (
    create_ssh_account,
    delete_ssh_account,
    block_ssh_account,
    unblock_ssh_account
)
from financial_api.user import get_balance 
from financial_api.transfer import transfer 
import logging

# Create a file handler to save logs to a file
logger = logging.getLogger('ssh_route.log') 

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

ADMID_ID_FOR_FINANCIAl = 1 
router = APIRouter(prefix='/agent/ssh', tags=['Ssh-Agent'])


def generate_password():

    length = 12
    chars = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(choice(chars) for i in range(length))
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()[:7]
    
    index_1 = choice(range(len(hashed_password)))
    index_2 = choice(range(len(hashed_password)))
    
    hashed_password= hashed_password.replace(hashed_password[index_1], hashed_password[index_1].upper()) 
    hashed_password= hashed_password.replace(hashed_password[index_2], hashed_password[index_2].upper()) 

    # especial_char= choice(['!','@','#','$','*'])
    # hashed_password = hashed_password.replace(hashed_password[choice(range(len(hashed_password)))], especial_char) 
    
    return hashed_password

@router.post('/test', response_model= NewSshResponse, responses= {
    status.HTTP_409_CONFLICT:{'model': HTTPError},
    status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError},
    status.HTTP_406_NOT_ACCEPTABLE:{'model': HTTPError},
    status.HTTP_404_NOT_FOUND:{'model': HTTPError},
    status.HTTP_400_BAD_REQUEST:{'model':HTTPError},
    status.HTTP_423_LOCKED:{'model':HTTPError},
    status.HTTP_500_INTERNAL_SERVER_ERROR:{'model':HTTPError},
    })
def create_test_ssh_via_agent(request: NewSsh, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):
 
    interface = db_ssh_interface.get_interface_by_id(request.interface_id, db)
    
    if interface == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'Interface_id not exists', 'internal_code': 2410})
    
    elif interface.status == InterfaceStatus.DISABLE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'Interface_id is disable', 'internal_code': 2426})

    server = db_server.get_server_by_ip(interface.server_ip, db)
    
    if server.status == ServerStatus.DISABLE :
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': f'The Server [{interface.server_ip}] has disable', 'internal_code': 2427})
   
    # if server.ssh_accounts_number >= server.max_users:
    #     raise HTTPException(status_code= status.HTTP_406_NOT_ACCEPTABLE, detail={'message': f'The Server [{interface.server_ip}] has reached to max users', 'internal_code': 2411})

    password = generate_password()
    while True:

        username = 'user_' + str(randint(100_000, 999_000))
        if db_ssh_service.get_service_by_username(username, db) == None:
            break

    _, err = create_ssh_account(interface.server_ip, username, password)
    if err:
        logger.error(f'[new test ssh] ssh account creation failed (agent: {current_user.user_id} -username: {username} -interface_id: {interface.interface_id} -resp_code: {err.status_code} -detail: {err.detail})')
        raise err
    
    service_data = {
        'server_ip': interface.server_ip,
        'password': password,
        'username': username,
        'name': request.name,
        'phone_number': request.phone_number,
        'email': request.email,
        'agent_id': current_user.user_id,
        'user_chat_id': request.chat_id,
        'port': interface.port,
        'limit': interface.limit,
        'interface_id': interface.interface_id,
        'created': datetime.now().replace(tzinfo=pytz.utc),
        'expire': datetime.now().replace(tzinfo=pytz.utc) + timedelta(days=1),
        'status': ServiceStatus.ENABLE
    }

    # ================= Begin =================
    try:
        service = db_ssh_service.create_ssh(SshService(**service_data), db, commit=False)
        db_server.increase_ssh_accounts_number(interface.server_ip, db, commit=False)
        db.commit()
        db.refresh(service)

    except Exception as e:
        logger.error(f'[new test ssh] error in database (agent: {current_user.user_id} -username: {username} -interface_id: {interface.interface_id} -error: {e})')
        db.rollback()
        _, err = delete_ssh_account(interface.server_ip, username)
        if err:
            logger.error(f'[delete] error (agent: {current_user.user_id} -username: {username} -resp_code: {err.status_code} -detail: {err.detail})')
        
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='check the logs for more info')
    # ================= Commit =================

    response_message = {
        'username': username, 
        'password': password, 
        'host': interface.server_ip,
        'port': interface.port
    }

    logger.info(f'[new test ssh] the test ssh account was created successfully [agent: {current_user.user_id} -username: {username} -interface_id: {interface.interface_id}]')
    
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
    
    interface = db_ssh_interface.get_interface_by_id(request.interface_id, db)
    
    if interface == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'Interface_id not exists', 'internal_code': 2410})
    
    elif interface.status == InterfaceStatus.DISABLE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'Interface_id is disable', 'internal_code': 2426})

    server = db_server.get_server_by_ip(interface.server_ip, db)
    
    if server.status == ServerStatus.DISABLE :
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': f'The Server [{interface.server_ip}] has disable', 'internal_code': 2427})
   
    if server.ssh_accounts_number >= server.max_users:
        raise HTTPException(status_code= status.HTTP_406_NOT_ACCEPTABLE, detail={'message': f'The Server [{interface.server_ip}] has reached to max users', 'internal_code': 2411})

    password = generate_password()
    while True:

        username = 'user_' + str(randint(100_000, 999_000))
        if db_ssh_service.get_service_by_username(username, db) == None:
            break

    # NOTE: calcute financial

    if current_user.role == UserRole.AGENT:
        resp, err = get_balance(current_user.user_id)
        if err:
            logger.error(f'[new ssh] failed to get agent balance (agent_id: {current_user.user_id})')
            raise err
        
        balance = resp['balance'] 

        if balance < interface.price :
            logger.error(f'[new ssh] Insufficient balance (agent_id: {current_user.user_id} -balance: {balance} -interface_price: {interface.price})')
            raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail= {'message': 'Insufficient balance', 'internal_code': 1412} )

        _, err = transfer(current_user.user_id, ADMID_ID_FOR_FINANCIAl, interface.price)
        if err:
            logger.error(f'[new ssh] transfer credit Faied (agent: {current_user.user_id} -price: {interface.price} -resp_code: {err.status_code}, error: {err.detail})')
            raise err
        
        logger.info(f'[new ssh] successfully transfered credit (agent: {current_user.user_id} -price: {interface.price})')

    _, err = create_ssh_account(interface.server_ip, username, password)
    if err:
        logger.info(f'[new ssh] ssh account creation failed [agent: {current_user.user_id} -interface_id: {interface.interface_id} -resp_code: {err.status_code} -error: {err.detail}]')
        if current_user.role == UserRole.AGENT:
            _, err = transfer(ADMID_ID_FOR_FINANCIAl, current_user.user_id, interface.price)
            if err:
                logger.info(f'[new ssh] the operation of transferring credit to the agent was not done [agent: {current_user.user_id} -price: {interface.price} -resp_code: {err.status_code} -error: {err.detail}]')
                raise err
            
            logger.info(f'[new ssh] the credit was returned to the agent [agent: {current_user.user_id} -price: {interface.price} -resp_code: {err.status_code}]')
        raise err

    
    service_data = {
        'server_ip': interface.server_ip,
        'password': password,
        'username': username,
        'name': request.name,
        'phone_number': request.phone_number,
        'email': request.email,
        'agent_id': current_user.user_id,
        'user_chat_id': request.chat_id,
        'port': interface.port,
        'limit': interface.limit,
        'interface_id': interface.interface_id,
        'created': datetime.now().replace(tzinfo=pytz.utc),
        'expire': datetime.now().replace(tzinfo=pytz.utc) + timedelta(days=30),
        'status': ServiceStatus.ENABLE
    }

    # ================= Begin =================
    try:
        service = db_ssh_service.create_ssh(SshService(**service_data), db, commit=False)
        db_server.increase_ssh_accounts_number(interface.server_ip, db, commit=False)
        db.commit()
        db.refresh(service)
    
    except Exception as e:
        logger.error(f'[new ssh] error in database (agent: {current_user.user_id} -username: {username} -interface_id: {interface.interface_id} -error: {e})')
        db.rollback()
        _, err = delete_ssh_account(interface.server_ip, username)
        if err:
            logger.error(f'[delete] error (agent: {current_user.user_id} -username: {username} -resp_code: {err.status_code} -detail: {err.detail})')
        
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='check the logs for more info')
    # ================= Commit =================

    response_message = {
        'username': username, 
        'password': password, 
        'host': interface.server_ip,
        'port': interface.port,
    }

    logger.info(f'[new ssh] the ssh account was created successfully [agent: {current_user.user_id} -username: {username} -interface_id: {interface.interface_id}]')
    
    return NewSshResponse(**response_message)


@router.post('/expire', response_model= UpdateSshExpireResponse, responses={
    status.HTTP_404_NOT_FOUND:{'model': HTTPError},
    status.HTTP_422_UNPROCESSABLE_ENTITY:{'model': HTTPError},
    status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError},
    status.HTTP_400_BAD_REQUEST:{'model':HTTPError},
    status.HTTP_423_LOCKED:{'model':HTTPError},
    status.HTTP_409_CONFLICT:{'model':HTTPError}} )
def update_ssh_account_expire(request: UpdateSshExpire, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    service = db_ssh_service.get_service_by_username(request.username, db)

    if service == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'This Username have not any service', 'internal_code': 2433})
    
    if service.status == ServiceStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'This service had deleted ', 'internal_code': 2437})

    if current_user.role != UserRole.ADMIN and service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})
    
    request_new_expire = request.new_expire.replace(tzinfo=pytz.utc)
    service_expire = service.expire.replace(tzinfo=pytz.utc)
    
    if request_new_expire <= datetime.now().replace(tzinfo=pytz.utc):
        raise HTTPException(status_code= status.HTTP_422_UNPROCESSABLE_ENTITY, detail={'message': 'invalid parameter for new expire', 'internal_code': 2414}) 
    
    interface = db_ssh_interface.get_interface_by_id(service.interface_id, db)

    if interface.status == InterfaceStatus.DISABLE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'Interface_id is disable', 'internal_code': 2426})

    rollbackTransfer = None
    price = None

    if current_user.role == UserRole.AGENT:
        
        unit_price = interface.price / (interface.duration * 24 * 60) 
        update_hours = abs(request_new_expire - service_expire)
        # NOTE: 0.72 : for update expire a account we used 0.72 and for new account we used 1
        price = (update_hours.total_seconds() / 60) * unit_price * 0.72

        if request_new_expire > service_expire:
            
            resp, err = get_balance(service.agent_id)
            if err:
                logger.error(f'[expire] failed to get agent balance (agent_id: {current_user.user_id})')
                raise err

            balance = resp['balance'] 
            
            if balance < price :
                logger.error(f'[expire] Insufficient balance (agent_id: {current_user.user_id} -balance: {balance} -interface_price: {interface.price})')
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail= {'message': 'Insufficient balance', 'internal_code': 1412} )
            
            _, err = transfer(service.agent_id, ADMID_ID_FOR_FINANCIAl, price)
            if err:
                logger.error(f'[expire] transfer credit Faied (agent: {current_user.user_id} -price: {interface.price} -resp_code: {err.status_code} error: {err.detail})')
                raise err

            rollbackTransfer = {'func':transfer ,'args':[ADMID_ID_FOR_FINANCIAl, service.agent_id, price]}
            logger.info(f'[expire] successfully transfered credit (agent: {current_user.user_id} -price: {price})')

        else:

            _, err = transfer(ADMID_ID_FOR_FINANCIAl, service.agent_id, price)
            if err:
                logger.error(f'[expire] transfer credit Faied (agent: {current_user.user_id} -price: {price} -resp_code: {err.status_code} error: {err.detail})')
                raise err
            
            rollbackTransfer = {'func':transfer ,'args':[service.agent_id, ADMID_ID_FOR_FINANCIAl, price]}

    # =================== Begin ===================
    db_ssh_service.update_expire(service.service_id, request_new_expire, db, commit= False)
        
    if request.unblock == True:
        _, err = unblock_ssh_account(service.server_ip, request.username)
        if err:
            logger.error(f'[expire] unblock user failed (agent: {current_user.user_id} -username: {request.username} -resp_code: {err.status_code} -error: {err.detail})')
            db.rollback() 
            if rollbackTransfer:
                _, err = rollbackTransfer['func'](*rollbackTransfer['args'])
                if err:
                    logger.error(f'[expire] transfer credit Faied  (agent: {current_user.user_id} -price: {price} -resp_code: {err.status_code} -error: {err.detail})')
                    raise err 
                
                logger.error(f'[expire] successfully returned credit (agent: {current_user.user_id} -price: {price})')
            
            raise err
        
        db_ssh_service.change_status(service.service_id, ServiceStatus.ENABLE, db, commit=False)

    db.commit()
    # =================== Commit ===================
    logger.info(f'[expire] successfully update expire (agent: {current_user.user_id} -username:{request.username} -new_expire: {request.new_expire})')
    
    return UpdateSshExpireResponse(**{'username': service.username, 'expire': request_new_expire})


@router.post('/block', response_model= str, responses={status.HTTP_409_CONFLICT:{'model': HTTPError}, status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError}})
def block_ssh_account_via_agent(request: BlockSsh, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    
    service = db_ssh_service.get_service_by_username(request.username, db)

    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'This Username have not any service', 'internal_code':2433})

    if service.status == ServiceStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'This service had deleted ', 'internal_code': 2437})

    if current_user.role != UserRole.ADMIN and service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})
    
    if service.status == ServiceStatus.DISABLE:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'The user has already been block', 'internal_code': 2415})

    _ ,err = block_ssh_account(service.server_ip, request.username)
    if err:
        logger.error(f'[block] error (agent: {current_user.user_id} -username: {request.username} -resp_code: {err.status_code} -detail: {err.detail})')
        raise err
    
    db_ssh_service.change_status(service.service_id, ServiceStatus.DISABLE, db)
    logger.info(f'[block] successfully blocked (agent: {current_user.user_id} -username: {request.username})')

    return f'Successfully blocked user [{request.username}]'


@router.post('/unblock', response_model= str, responses={status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError}, status.HTTP_409_CONFLICT:{'model': HTTPError}})
def unblock_ssh_account_via_agent(request: UnBlockSsh, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    service = db_ssh_service.get_service_by_username(request.username, db)

    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'This Username have not any service', 'internal_code':2433})
    
    if service.status == ServiceStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'This service had deleted ', 'internal_code': 2437})

    if current_user.role != UserRole.ADMIN and service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})
    
    if service.status == ServiceStatus.ENABLE:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'The user is not blocked', 'internal_code': 2416})
 
    server = db_server.get_server_by_ip(service.server_ip, db)

    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': f'Server [{service.server_ip}] is disable', 'internal_code':2421})

    if server.ssh_accounts_number >= server.max_users:
        raise HTTPException(status_code= status.HTTP_406_NOT_ACCEPTABLE, detail={'message': f'The Server [{service.server_ip}] has reached to max users', 'internal_code': 2411})

    _, err = unblock_ssh_account(service.server_ip, request.username)
    if err:
        logger.error(f'[unblock] error (agent: {current_user.user_id} -username: {request.username} -resp_code: {err.status_code} -detail: {err.detail})')
        raise err
    
    db_ssh_service.change_status(service.service_id, ServiceStatus.ENABLE, db)
    logger.info(f'[unblock] successfully unblocked (agent: {current_user.user_id} -username: {request.username})')

    return f'Successfully unblocked user [{request.username}]'


@router.delete('/delete', response_model= str, responses={
    status.HTTP_404_NOT_FOUND:{'model': HTTPError},
    status.HTTP_500_INTERNAL_SERVER_ERROR:{'model': HTTPError},
    status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError}})
def delete_ssh_account_via_agent(request: DeleteSsh, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    service = db_ssh_service.get_service_by_username(request.username, db)
    
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'This Username have not any service', 'internal_code':2433})

    if service.status == ServiceStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'This service had deleted ', 'internal_code': 2437})

    if current_user.role != UserRole.ADMIN and service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})
    
    _ ,err = delete_ssh_account(service.server_ip, request.username)
    if err:
        logger.error(f'[delete] error (agent: {current_user.user_id} -username: {request.username} -resp_code: {err.status_code} -detail: {err.detail})')
        raise err
    
    try:
        db_server.decrease_ssh_accounts_number(service.server_ip, db, commit=False) 
        db_ssh_service.change_status(service.service_id, ServiceStatus.DELETED, db, commit=False)
        db.commit()

    except Exception as e:
        logger.error(f'[delete] error in database (agent: {current_user.user_id} -username: {request.username} -error: {e})')
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='check the logs for more info')

    logger.info(f'[delete] successfully deleted (agent: {current_user.user_id} -username: {request.username})')
    return f'Successfully delete user [{request.username}]'


@router.post('/renew', response_model= NewSshResponse, responses={
    status.HTTP_404_NOT_FOUND:{'model': HTTPError},
    status.HTTP_500_INTERNAL_SERVER_ERROR:{'model': HTTPError},
    status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError}})
def renew_config(request: RenewSsh, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    service = db_ssh_service.get_service_by_username(request.username, db)
    
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'This Username have not any service', 'internal_code':2433})

    if service.status == ServiceStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'This service had deleted ', 'internal_code': 2437})

    if current_user.role != UserRole.ADMIN and service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})

    if request.new_interface_id :
        interface = db_ssh_interface.get_interface_by_id(request.new_interface_id, db)

        if interface == None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'Interface_id not exists', 'internal_code': 2410})
        
        elif interface.status == InterfaceStatus.DISABLE:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message':'Interface_id is disable', 'internal_code': 2426})

        best_interface = interface

    else:

        interfaces = db_ssh_interface.get_all_interface(db,  InterfaceStatus.ENABLE)
    
        servers = db_server.get_all_server(db, status= ServerStatus.ENABLE)

        def find_server(ip):

            for server in servers:
                if server.server_ip == ip:
                    return server
        
            return False
        
        if interfaces == [] or servers == []:
            raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'There is no interface or server for renew config', 'internal_code': 2435})
        
        best_interface = None
        tmp_min = 10**6

        for interface in interfaces:

            server = find_server(interface.server_ip)
            if server.server_ip and server.server_ip != service.server_ip:
                services = db_ssh_service.get_services_by_server_ip(interface.server_ip, db, status= ServiceStatus.ENABLE)

                if len(services) < tmp_min :
                    tmp_min = len(services)
                    best_interface = interface
    
    if best_interface is None:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'There is no best interface for renew config', 'internal_code': 2436})

    _, err = create_ssh_account(best_interface.server_ip, request.username, service.password)
    if err:
        logger.info(f'[renew] ssh account creation failed (agent: {current_user.user_id} -username: {request.username} -resp_code: {err.status_code} -detail: {err.detail})')
        raise err
    
    logger.info(f'[renew] ssh account successfully created (agent: {current_user.user_id} -username: {request.username})')

    _, err = delete_ssh_account(service.server_ip, request.username)
    if err:
        logger.info(f'[renew] delete ssh account failed (agent: {current_user.user_id} -username: {request.username} -resp_code: {err.status_code} -detail: {err.detail})')
        raise err
    
    logger.info(f'[renew] ssh account successfully created (agent: {current_user.user_id} -username: {request.username})')
    
    try:
        db_server.decrease_ssh_accounts_number(service.server_ip, db, commit= False) 
        db_ssh_service.transfer_service([service], best_interface, db, commit=False)
        db_server.increase_ssh_accounts_number(best_interface.server_ip, db, commit= False)
        db.commit()

    except Exception as e: 
        logger.error(f'[renew] error in database (agent: {current_user.user_id} -username: {request.username} -error: {e})')
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='check the logs for more info')
    
    response_message = {
        'username': request.username, 
        'password': service.password, 
        'host': best_interface.server_ip,
        'port': best_interface.port,
    }
    
    logger.info(f'[renew] renew config successfully created (agent: {current_user.user_id} -username: {request.username} -old_interface: {service.interface_id} -new_interface: {request.new_interface_id})')
    return NewSshResponse(**response_message)