from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import (
    NewSsh,
    UserRegisterForDataBase,
    UserRole,
    Status,
    NewSshResponse,
    RenewalSsh,
    RenewalSshResponse,
    SshService,
    DeleteSsh,
    UnBlockSsh,
    BlockSsh,
    HTTPError,
    TokenUser
)
from db import (
    db_user,
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
from financial_api.user import create_user_if_not_exist, get_balance
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
    # hashed_password = hashed_password.replace(hashed_password[choice(range(len(hashed_password)))] ,especial_char)
    
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
    
    interface = db_ssh_interface.get_interface_by_id(request.interface_id, db, status= Status.ENABLE)

    if interface == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'Interface_id not exists', 'internal_code': 2410})

    user = None
    if request.tel_id:

        user = db_user.get_user_by_telegram_id(request.tel_id, db)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'The tel_id is not exist', 'internal_code': 2420})

    server = db_server.get_server_by_ip(interface.server_ip, db, status= Status.ENABLE)
    
    if server.ssh_accounts_number >= server.max_users:
        raise HTTPException(status_code= status.HTTP_406_NOT_ACCEPTABLE, detail={'message': f'The Server [{interface.server_ip}] has reached to max users', 'internal_code': 2411})
    

    password = generate_password()
    while True:

        username = 'user_' + str(randint(100_000, 999_000))
        if db_ssh_service.get_service_by_username(username, db) == None:
            break

    # send request to agent

    if user is None:
        data = {
            'tel_id': request.tel_id,
            'name': request.name,
            'phone_number': request.phone_number,
            'role': UserRole.CUSTOMER
            }
        
        user = db_user.create_user(UserRegisterForDataBase(**data), db)
        status_code, resp = create_user_if_not_exist(user.user_id)
        logger.info(f'successfully created account in financial [agent: {current_user.user_id} -user_id: {user.user_id} -username: {username} -server: {interface.server_ip}]')
        
        if status_code == 2419 :
            db_user.delete_user(user.user_id, db)
            raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Error Or Connection Timeout', 'internal_code': 2419})
            
        if status_code != 200:
            db_user.delete_user(user.user_id, db)
            raise HTTPException(status_code=resp.status_code ,detail= resp.json()['detail'])

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
        
        logger.info(f'failed create ssh account, return cost to agent [agent: {current_user.user_id} -price: {interface.price}, resp_code: {status_code}]')
        raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': f'networt error [{interface.server_ip}]', 'internal_code': 2419})
        
    if status_code != 200:
        if current_user.role == UserRole.AGENT:
            status_code, _ = transfer(ADMID_ID_FOR_FINANCIAl, current_user.user_id, interface.price)
        
        logger.info(f'failed create ssh account, return cost to agent [agent: {current_user.user_id} -price: {interface.price}, resp_code: {ssh_resp.status_code}]')
        raise HTTPException(status_code=status_code, detail= ssh_resp.json()['detail'])
    
    logger.info(f'successfully created ssh account [agent: {current_user.user_id} -username: {username} -server: {interface.server_ip}]')
    
    service_data = {
        'server_ip': interface.server_ip,
        'agent_id': current_user.user_id,
        'password': password,
        'username': username,
        'user_id': user.user_id,
        'port': interface.port,
        'limit': interface.limit,
        'interface_id': interface.interface_id,
        'expire': datetime.now().replace(tzinfo=pytz.utc) + timedelta(days=30),
        'status': Status.ENABLE
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


@router.post('/expire', response_model= RenewalSshResponse, responses={
    status.HTTP_404_NOT_FOUND:{'model': HTTPError},
    status.HTTP_422_UNPROCESSABLE_ENTITY:{'model': HTTPError},
    status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError},
    status.HTTP_400_BAD_REQUEST:{'model':HTTPError},
    status.HTTP_423_LOCKED:{'model':HTTPError},
    status.HTTP_409_CONFLICT:{'model':HTTPError}} )
def update_ssh_account_expire(request: RenewalSsh, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    service = db_ssh_service.get_service_by_id(request.service_id, db, status= Status.ENABLE)

    if service == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message':'the service_id not exists', 'internal_code': 2413})
    
    if service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})
    
    request_new_expire = request.new_expire.replace(tzinfo=pytz.utc)
    service_expire = service.expire.replace(tzinfo=pytz.utc)
    
    if request_new_expire <= service_expire:
        raise HTTPException(status_code= status.HTTP_422_UNPROCESSABLE_ENTITY, detail={'message': 'invalid parameter for expire', 'internal_code': 2414}) 
    
    if current_user.role == UserRole.AGENT:

        interface = db_ssh_interface.get_interface_by_id(service.interface_id, db)

        status_code, resp = get_balance(service.agent_id)
        
        if status_code == 2419 :
            raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Error Or Connection Timeout', 'internal_code': 2419})
            
        if status_code != 200:
            raise HTTPException(status_code=status_code, detail= resp.json()['detail'] )

        balance = resp.json()['balance'] 

        unit_price = interface.price / (interface.duration * 24 * 60) 

        update_hours = request_new_expire - service_expire
        price = (update_hours.total_seconds() / 60) * unit_price
        
        if balance < price :
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail= {'message': 'Insufficient balance', 'internal_code': 1412} )
        
        interface = db_ssh_interface.get_interface_by_id(service.interface_id, db, status= Status.ENABLE)

        status_code, resp = transfer(service.agent_id, ADMID_ID_FOR_FINANCIAl, price)

        if status_code == 2419 :
            raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Error Or Connection Timeout', 'internal_code': 2419})
            
        if status_code != 200:
            raise HTTPException(status_code=status_code, detail= resp.json()['detail'] )

    db_ssh_service.update_expire(service.service_id, request_new_expire, db)    

    return RenewalSshResponse(**{'service_id': service.service_id, 'expire': request_new_expire})


@router.post('/block', response_model= str, responses={status.HTTP_409_CONFLICT:{'model': HTTPError}, status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError}})
def block_ssh_account_via_agent(request: BlockSsh, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    service = db_ssh_service.get_service_by_username(request.username, db)

    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'the service_id not exists', 'internal_code':2413})
    
    if service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})
    
    if service.status == Status.DISABLE:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'The user has already been block', 'internal_code': 2415})

    status_code ,resp = block_ssh_account(service.server_ip, request.username)
    
    if status_code == 2419 :
        raise HTTPException(status_code= status.HTTP_408_REQUEST_TIMEOUT, detail={'message': f'Connection Error Or Connection Timeout', 'internal_code': 2419})
        
    if status_code != 200:
        raise HTTPException(status_code=resp.status_code ,detail= resp.json()['detail'])
    
    db_server.decrease_ssh_accounts_number(service.server_ip, db) 
    db_ssh_service.change_status(service.service_id, Status.DISABLE, db)

    return f'Successfully blocked user [{request.username}]'


@router.post('/unblock', response_model= str, responses={status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError}, status.HTTP_409_CONFLICT:{'model': HTTPError}})
def unblock_ssh_account_via_agent(request: UnBlockSsh, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    service = db_ssh_service.get_service_by_username(request.username, db)

    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'the service_id not exists', 'internal_code':2413})

    if service.agent_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message':'You are not the agent of this user', 'internal_code': 2419})
    
    if service.status == Status.ENABLE:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'The user is not blocked', 'internal_code': 2416})
 
    status_code ,resp = unblock_ssh_account(service.server_ip, request.username)
    
    if status_code == 2419 :
        raise HTTPException(status_code= status.HTTP_408_REQUEST_TIMEOUT, detail={'message': f'Connection Error Or Connection Timeout', 'internal_code': 2419})
        
    if status_code != 200:
        raise HTTPException(status_code=resp.status_code ,detail= resp.json()['detail'] )
    

    server = db_server.get_server_by_ip(service.server_ip, db, status= Status.ENABLE)

    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': f'Server [{service.server_ip}] is disable', 'internal_code':2421})

    if server.ssh_accounts_number >= server.max_users:
        raise HTTPException(status_code= status.HTTP_406_NOT_ACCEPTABLE, detail={'message': f'The Server [{service.server_ip}] has reached to max users', 'internal_code': 2411})
    

    db_server.increase_ssh_accounts_number(service.server_ip, db) 
    db_ssh_service.change_status(service.service_id, Status.ENABLE, db)

    return f'Successfully unblocked user [{request.username}]'


@router.delete('/delete', response_model= str, responses={
    status.HTTP_404_NOT_FOUND:{'model': HTTPError},
    status.HTTP_500_INTERNAL_SERVER_ERROR:{'model': HTTPError},
    status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError}})
def delete_ssh_account_via_agent(request: DeleteSsh, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    service = db_ssh_service.get_service_by_username(request.username, db)
    
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'the service_id not exists', 'internal_code':2413})

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
    db_ssh_service.change_status(service.service_id, Status.DISABLE, db)

    return f'Successfully delete user [{request.username}]'
