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
from auth.auth import get_agent_user

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

logger = logging.getLogger() 
logger.setLevel(logging.INFO) 

# Create a file handler to save logs to a file
file_handler = logging.FileHandler('ssh_route.log') 
file_handler.setLevel(logging.INFO) 
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s') 
file_handler.setFormatter(formatter) 
logger.addHandler(file_handler) 

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
        status_code, resp = get_balance(current_user.user_id)
        
        if status_code == 2419 :
            raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Error Or Connection Timeout', 'internal_code': 2419})
            
        if status_code != 200:
            raise HTTPException(status_code=status_code, detail= resp.json()['detail'] )

        
        balance = resp.json()['balance'] 

        if balance < interface.price :
            raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail= {'message': 'Insufficient balance', 'internal_code': 1412} )

        logger.info(f'send request for transfer credit [agent: {current_user.user_id} -price: {interface.price}]')

        status_code, resp = transfer(current_user.user_id, ADMID_ID_FOR_FINANCIAl, interface.price)

        if status_code == 2419 :
            raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Error Or Connection Timeout', 'internal_code': 2419})

        if status_code != 200: 
            raise HTTPException(status_code=status_code, detail= resp.json()['detail'] )
        
        logger.info(f'successfully transfered credit [agent: {current_user.user_id} -price: {interface.price}]')


    logger.info(f'send request for create new ssh account [agent: {current_user.user_id} -username: {username} -server: {interface.server_ip}]')
    status_code, ssh_resp = create_ssh_account(interface.server_ip, username, password)
    
    if status_code == 2419 :
        if current_user.role == UserRole.AGENT:
            status_code, _ = transfer(ADMID_ID_FOR_FINANCIAl, current_user.user_id, interface.price)
            if status_code == 200:
                logger.info(f'the credit was returned to the agent [agent: {current_user.user_id} -price: {interface.price}, resp_code: {status_code}]')
            
            else:
                logger.info(f'the operation of transferring credit to the agent was not done [agent: {current_user.user_id} -price: {interface.price}, resp_code: {status_code}]')

        logger.info(f'ssh account creation failed [agent: {current_user.user_id} -price: {interface.price}, resp_code: {status_code}]')
        raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': f'networt error [{interface.server_ip}]', 'internal_code': 2419})
        
    if status_code != 200:
        if current_user.role == UserRole.AGENT:
            status_code, _ = transfer(ADMID_ID_FOR_FINANCIAl, current_user.user_id, interface.price)
            if status_code == 200:
                logger.info(f'the credit was returned to the agent [agent: {current_user.user_id} -price: {interface.price}, resp_code: {status_code}]')
            
            else:
                logger.info(f'the operation of transferring credit to the agent was not done [agent: {current_user.user_id} -price: {interface.price}, resp_code: {status_code}]')
        
        logger.info(f'ssh account creation failed [agent: {current_user.user_id} -price: {interface.price}, resp_code: {ssh_resp.status_code}]')
        raise HTTPException(status_code=status_code, detail= ssh_resp.json()['detail'])
    
    logger.info(f'the ssh account was created successfully [agent: {current_user.user_id} -username: {username} -server: {interface.server_ip}]')
    
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

    db_ssh_service.create_ssh(SshService(**service_data), db)
    db_server.increase_ssh_accounts_number(interface.server_ip, db)

    response_message = {
        'username': username, 
        'password': password, 
        'host': interface.server_ip,
        'port': interface.port,
    }
    
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

    if service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})
    
    request_new_expire = request.new_expire.replace(tzinfo=pytz.utc)
    service_expire = service.expire.replace(tzinfo=pytz.utc)
    
    if request_new_expire <= datetime.now().replace(tzinfo=pytz.utc):
        raise HTTPException(status_code= status.HTTP_422_UNPROCESSABLE_ENTITY, detail={'message': 'invalid parameter for new expire', 'internal_code': 2414}) 
    
    if current_user.role == UserRole.AGENT:

        interface = db_ssh_interface.get_interface_by_id(service.interface_id, db)
        unit_price = interface.price / (interface.duration * 24 * 60) 
        update_hours = abs(request_new_expire - service_expire)
        price = (update_hours.total_seconds() / 60) * unit_price

        if request_new_expire > service_expire:
            
            status_code, resp = get_balance(service.agent_id)
            
            if status_code == 2419 :
                raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Error Or Connection Timeout', 'internal_code': 2419})
                
            if status_code != 200:
                raise HTTPException(status_code=status_code, detail= resp.json()['detail'] )

            balance = resp.json()['balance'] 
            
            if balance < price :
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail= {'message': 'Insufficient balance', 'internal_code': 1412} )
            
            status_code, resp = transfer(service.agent_id, ADMID_ID_FOR_FINANCIAl, price)

            if status_code == 2419 :
                raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Error Or Connection Timeout', 'internal_code': 2419})
                
            if status_code != 200:
                raise HTTPException(status_code=status_code, detail= resp.json()['detail'] )

        else:

            status_code, resp = transfer(ADMID_ID_FOR_FINANCIAl, service.agent_id, price)

            if status_code == 2419 :
                raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Error Or Connection Timeout', 'internal_code': 2419})
                
            if status_code != 200:
                raise HTTPException(status_code=status_code, detail= resp.json()['detail'] )

    db_ssh_service.update_expire(service.service_id, request_new_expire, db)    

    return UpdateSshExpireResponse(**{'username': service.username, 'expire': request_new_expire})


@router.post('/block', response_model= str, responses={status.HTTP_409_CONFLICT:{'model': HTTPError}, status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError}})
def block_ssh_account_via_agent(request: BlockSsh, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    
    service = db_ssh_service.get_service_by_username(request.username, db)

    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'This Username have not any service', 'internal_code':2433})

    if service.status == ServiceStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'This service had deleted ', 'internal_code': 2437})

    if service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})
    
    if service.status == ServiceStatus.DISABLE:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'The user has already been block', 'internal_code': 2415})

    status_code ,resp = block_ssh_account(service.server_ip, request.username)
    
    if status_code == 2419 :
        raise HTTPException(status_code= status.HTTP_408_REQUEST_TIMEOUT, detail={'message': f'Connection Error Or Connection Timeout', 'internal_code': 2419})
        
    if status_code != 200:
        raise HTTPException(status_code=resp.status_code ,detail= resp.json()['detail'])
    
    db_ssh_service.change_status(service.service_id, ServiceStatus.DISABLE, db)

    return f'Successfully blocked user [{request.username}]'


@router.post('/unblock', response_model= str, responses={status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError}, status.HTTP_409_CONFLICT:{'model': HTTPError}})
def unblock_ssh_account_via_agent(request: UnBlockSsh, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    service = db_ssh_service.get_service_by_username(request.username, db)

    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'This Username have not any service', 'internal_code':2433})
    
    if service.status == ServiceStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'This service had deleted ', 'internal_code': 2437})

    if service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})
    
    if service.status == ServiceStatus.ENABLE:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'The user is not blocked', 'internal_code': 2416})
 
    server = db_server.get_server_by_ip(service.server_ip, db)

    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': f'Server [{service.server_ip}] is disable', 'internal_code':2421})

    if server.ssh_accounts_number >= server.max_users:
        raise HTTPException(status_code= status.HTTP_406_NOT_ACCEPTABLE, detail={'message': f'The Server [{service.server_ip}] has reached to max users', 'internal_code': 2411})

    status_code ,resp = unblock_ssh_account(service.server_ip, request.username)
    
    if status_code == 2419 :
        raise HTTPException(status_code= status.HTTP_408_REQUEST_TIMEOUT, detail={'message': f'Connection Error Or Connection Timeout', 'internal_code': 2419})
        
    if status_code != 200:
        raise HTTPException(status_code=resp.status_code ,detail= resp.json()['detail'] )
    
    db_ssh_service.change_status(service.service_id, ServiceStatus.ENABLE, db)

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

    if service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})
    
    logger.debug(f'send request for delete ssh account [agent: {current_user.user_id} -username: {request.username} -server: {service.server_ip}]')

    status_code ,resp = delete_ssh_account(service.server_ip, request.username)
    
    if status_code == 2419 :
        raise HTTPException(status_code= status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Error Or Connection Timeout', 'internal_code': 2419})
        
    if status_code != 200:
        raise HTTPException(status_code=resp.status_code ,detail= resp.json()['detail'] )
    
    logger.debug(f'successfully deleted ssh account [agent: {current_user.user_id} -username: {request.username} -server: {service.server_ip}]')
    
    db_server.decrease_ssh_accounts_number(service.server_ip, db) 
    db_ssh_service.change_status(service.service_id, ServiceStatus.DELETED, db)

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

    if service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})

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

    logger.debug(f'send request for delete ssh account (renew) [agent: {current_user.user_id} -username: {request.username} -server: {service.server_ip}]')

    status_code ,resp = delete_ssh_account(service.server_ip, request.username)
    
    if status_code == 2419 :
        raise HTTPException(status_code= status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Error Or Connection Timeout', 'internal_code': 2419})
        
    if status_code != 200:
        raise HTTPException(status_code=resp.status_code ,detail= resp.json()['detail'] )
    
    logger.debug(f'successfully deleted ssh account (renew) [agent: {current_user.user_id} -username: {request.username} -server: {service.server_ip}]')
    
    db_server.decrease_ssh_accounts_number(service.server_ip, db) 
    db_ssh_service.change_status(service.service_id, ServiceStatus.DELETED, db)



    logger.info(f'send request for create new ssh account (renew) [agent: {current_user.user_id} -username: {request.username} -server: {best_interface.server_ip}]')
    status_code, ssh_resp = create_ssh_account(best_interface.server_ip, request.username, service.password)
    
    if status_code == 2419 :

        logger.info(f'ssh account creation failed (renew) [agent: {current_user.user_id} -price: {best_interface.price}, resp_code: {status_code}]')
        raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': f'networt error [{best_interface.server_ip}]', 'internal_code': 2419})
        
    if status_code != 200:

        logger.info(f'ssh account creation failed (renew) [agent: {current_user.user_id} -price: {best_interface.price}, resp_code: {ssh_resp.status_code}]')
        raise HTTPException(status_code=status_code, detail= ssh_resp.json()['detail'])
    
    logger.info(f'the ssh account was created successfully [agent: {current_user.user_id} -username: {request.username} -server: {best_interface.server_ip}]')
    
    service_data = {
        'server_ip': best_interface.server_ip,
        'password': service.password,
        'username': request.username,
        'name': service.name,
        'phone_number': service.phone_number,
        'email': service.email,
        'agent_id': current_user.user_id,
        'user_chat_id': service.user_chat_id,
        'port': best_interface.port,
        'limit': best_interface.limit,
        'interface_id': best_interface.interface_id,
        'created': service.created,
        'expire': service.expire,
        'status': service.status
    }

    db_ssh_service.create_ssh(SshService(**service_data), db)
    db_server.increase_ssh_accounts_number(best_interface.server_ip, db)
    
    response_message = {
        'username': request.username, 
        'password': service.password, 
        'host': best_interface.server_ip,
        'port': best_interface.port,
    }
    
    return NewSshResponse(**response_message)