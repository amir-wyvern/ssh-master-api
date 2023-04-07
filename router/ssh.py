from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import (
    NewSsh,
    UserRegisterForDataBase,
    UserRole,
    UserServiceRegister,
    Status,
    NewSshResponse,
    RenewalSsh,
    RenewalSshResponse,
    SshService,
    SshInterfaceState,
    PlanResponse,
    SshInterfaceRegister,
    SshInterfaceResponse,
    DeleteSsh,
    HTTPError
)
from db import (
    db_user,
    db_server,
    db_ssh_service,
    db_ssh_interface
)

from typing import List
from db.database import get_db
from auth.auth import get_auth

from random import randint, choice
import string
import hashlib
from datetime import datetime, timedelta
from slave_api.ssh import create_ssh_account, delete_ssh_account

router = APIRouter(prefix='/ssh', tags=['ssh'])

def generate_password():

    length = 12
    chars = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(choice(chars) for i in range(length))
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()[:20]

    return hashed_password


@router.post('/new', response_model= NewSshResponse, responses= {403:{'model': HTTPError}})
def new(request: NewSsh, db: Session=Depends(get_db)):
    
    user = db_user.get_user_by_telegram_id(request.tel_id, db)

    if user == None:
        data = {
            'tel_id': request.tel_id,
            'role': UserRole.CUSTOMER
            }
        
        user = db_user.create_user(UserRegisterForDataBase(**data), db)

    interface = db_ssh_interface.get_interface_by_id(request.interface_id, db, status= Status.ENABLE)

    if interface == None:
        raise HTTPException(status_code=403, detail={'message':'the interface_id not exists', 'internal_code': 1403})
    
    server = db_server.get_server_by_ip(interface.server_ip, db, status= Status.ENABLE)
    if server.ssh_accounts_number >= server.max_users:
        raise HTTPException(status_code=403, detail={'message':'this server is full', 'internal_code': 1413})

    password = generate_password()
    while True:

        username = 'user_' + str(randint(100_000, 999_000))
        if db_ssh_service.get_service_by_username(username, db) == None:
            break

    # send request to agent
    status_code, agent_resp = create_ssh_account(interface.server_ip, username, password)

    if status_code == 1419 :
        raise HTTPException(status_code=403, detail={'message': f'networt error [{interface.server_ip}]', 'internal_code': 1419})
        
    if status_code != 200:
        raise HTTPException(status_code=403, detail={'message': f'error in slave server [{interface.server_ip}] [{agent_resp.content}]', 'internal_code': 1403})
    

    # NOTE: calcute financial

    data = {
        'server_ip': interface.server_ip,
        'password': password,
        'username': username,
        'user_id': user.user_id,
        'port': interface.port,
        'limit': interface.limit,
        'interface_id': interface.interface_id,
        'expire': datetime.now() + timedelta(days=30),
        'status': Status.ENABLE
    }

    db_ssh_service.create_ssh(SshService(**data), db)
    db_server.increase_ssh_accounts_number(interface.server_ip, db)

    resp = {
        'username': username, 
        'password': password, 
        'host': interface.server_ip,
        'port': interface.port,
        }

    return NewSshResponse(**resp)


@router.post('/renewal', response_model= RenewalSshResponse, responses={403:{'model': HTTPError}})
def renewal(request: RenewalSsh, token: str= Depends(get_auth), db: Session=Depends(get_db)):

    service = db_ssh_service.get_service_by_id(request.service_id, db, status= Status.ENABLE)
    
    if service == None:
        raise HTTPException(status_code=403, detail={'message':'the service_id not exists', 'internal_code': 1403})
    
    # calcute financial
    
    new_expire =  service.expire + timedelta(days=30) 
    db_ssh_service.update_expire(service.service_id, new_expire, db)    

    return RenewalSshResponse(**{'service_id': service.service_id, 'expire': new_expire})

@router.delete('/delete', response_model= str, responses={403:{'model': HTTPError}})
def delete(request: DeleteSsh, token: str= Depends(get_auth), db: Session=Depends(get_db)):

    service = db_ssh_service.get_service_by_username(request.username, db)
    
    status_code ,resp = delete_ssh_account(service.server_ip, request.username)
    
    if status_code == 1419 :
        raise HTTPException(status_code=403, detail={'message': f'networt error [{service.server_ip}]', 'internal_code': 1419})
        
    if status_code != 200:
        raise HTTPException(status_code=403, detail={'message': f'error in slave server [{service.server_ip}] [{resp.content}]', 'internal_code': 1403})
    
    db_server.decrease_ssh_accounts_number(service.server_ip, db) 
    db_ssh_service.change_status(service.service_id, Status.DISABLE, db)

    return f'Successfuly delete user [{request.username}]'


@router.get('/interface/fetch', response_model= List[PlanResponse])
def interface_fetch(mode: str, token: str= Depends(get_auth), db: Session=Depends(get_db)):
    
    if mode == 'all':
        interfaces = db_ssh_interface.get_all_interface(db, status= Status.ENABLE)
        return interfaces

    elif mode == 'best':
        interfaces = db_ssh_interface.get_all_interface(db,  Status.ENABLE)
        
        servers = db_server.get_all_server(db, status= Status.ENABLE)

        def find_server(ip):

            for server in servers:
                if server.server_ip == ip:
                    return server
        
            return False
        
        if interfaces == [] or servers == []:
            return []
        
        best_interface = interfaces[0]
        best_server = servers[0]

        for interface in interfaces:
            server = find_server(interface.server_ip)
            if server and server.ssh_accounts_number < best_server.ssh_accounts_number and server.ssh_accounts_number <= server.max_users:

                best_server = server
                best_interface = interface
                        
        return [best_interface]


@router.post('/interface/new', response_model= SshInterfaceResponse)
def interface_new(request: SshInterfaceRegister, token: str= Depends(get_auth), db: Session=Depends(get_db)):
    
    interface = db_ssh_interface.create_interface(request, db)  
    return {'interface_id': interface.interface_id}


@router.post('/interface/state', response_model= SshInterfaceResponse)
def interface_state(request: SshInterfaceState, token: str= Depends(get_auth), db: Session=Depends(get_db)):
    
    interface = db_ssh_interface.change_status(request.interface_id, request.new_status, db)  
    return {'interface_id': interface.interface_id}