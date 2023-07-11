from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import (
    ServiceStatus,
    InterfaceStatus,
    SshInterfaceState,
    PlanResponse,
    SshInterfaceRegister,
    SshInterfaceResponse,
    UsersTransferToNewInterface,
    InterfaceMode,
    HTTPError,
    UserRole,
    ServerStatus,
    TokenUser,
    NewSshInterfaceResponse
)
from db import (
    db_server,
    db_ssh_interface,
    db_ssh_service
)
from slave_api.ssh import (
    create_ssh_account_via_group, 
    delete_ssh_account_via_group, 
    block_ssh_account_via_groups
)
from typing import List
from db.database import get_db
from auth.auth import get_admin_user, get_agent_user
import logging

# Create a file handler to save logs to a file
file_handler = logging.FileHandler('interface_route.log') 
file_handler.setLevel(logging.INFO) 
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s') 
file_handler.setFormatter(formatter) 

logger = logging.getLogger('interface_route.log') 
logger.addHandler(file_handler) 
 
router = APIRouter(prefix='/interface', tags=['Interfaces'])

@router.get('/ssh/fetch', response_model= List[PlanResponse], tags=['Agent-Profile'])
def fetch_ssh_interface(mode: InterfaceMode= InterfaceMode.BEST, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):

    if mode == InterfaceMode.ALL:
        if current_user.role == UserRole.ADMIN:
            interfaces = db_ssh_interface.get_all_interface(db)
        
        else:
            interfaces = db_ssh_interface.get_all_interface(db, status= InterfaceStatus.ENABLE)

        return interfaces

    elif mode == InterfaceMode.BEST:
        interfaces = db_ssh_interface.get_all_interface(db,  InterfaceStatus.ENABLE)
        
        servers = db_server.get_all_server(db, status= ServerStatus.ENABLE)

        def find_server(ip):

            for server in servers:
                if server.server_ip == ip:
                    return server
        
            return False
        
        if interfaces == [] or servers == []:
            return []
        
        best_interface = []
        tmp_min = 10**6

        for interface in interfaces:

            if find_server(interface.server_ip):
                services = db_ssh_service.get_services_by_server_ip(interface.server_ip, db, status= ServiceStatus.ENABLE)

                if len(services) < tmp_min :
                    tmp_min = len(services)
                    best_interface = interface
            
        return [best_interface]


@router.post('/ssh/new', response_model= NewSshInterfaceResponse, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError} })
def create_new_ssh_interface(request: SshInterfaceRegister, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):
    
    server = db_server.get_server_by_ip(request.server_ip, db)

    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'message': 'Server not exists', 'internal_code': 2406})
    
    interface = db_ssh_interface.create_interface(request, db)  
    logger.info(f'[new ssh interface] successfully (server_ip: {request.server_ip} -price: {request.price} -limit: {request.limit})')

    return {'interface_id': interface.interface_id}


@router.post('/ssh/status', response_model= SshInterfaceResponse)
def update_ssh_interface_status(request: SshInterfaceState, new_status: InterfaceStatus, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):
    
    interface = db_ssh_interface.get_interface_by_id(request.interface_id, db)
    if interface is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'message': 'Interface_id not exists', 'internal_code': 2410})
    
    if interface.status == new_status:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT ,detail={'message': 'Interface_id already has this status', 'internal_code': 2428})
    
    db_ssh_interface.change_status(request.interface_id, new_status, db)  
    logger.info(f'[change ssh interface status] successfully (interface_id: {request.interface_id} -new_status: {new_status})')

    return {'interface_id': request.interface_id, 'status': new_status}


@router.post('/ssh/transfer', response_model= str, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def transfer_ssh_users_to_new_interface(request: UsersTransferToNewInterface ,current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    old_interface = db_ssh_interface.get_interface_by_id(request.old_interface_id, db)
    if old_interface is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'message': 'Old Interface_id not exists', 'internal_code': 2410})

    new_interface = db_ssh_interface.get_interface_by_id(request.new_interface_id, db)
    if new_interface is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'message': 'New Interface_id not exists', 'internal_code': 2410})
    
    enable_old_state_users = db_ssh_service.get_services_by_interface_id(old_interface.interface_id, db, status= ServiceStatus.ENABLE)
    disable_old_state_users = db_ssh_service.get_services_by_interface_id(old_interface.interface_id, db, status= ServiceStatus.DISABLE)
    
    # ============================ Begin ============================ 
    db.begin()

    db_ssh_service.transfer_service(enable_old_state_users, new_interface, db, commit=False)
    db_ssh_service.transfer_service(disable_old_state_users, new_interface, db, commit=False)

    if request.delete_old_users:

        enable_old_state_users_structed = [{'username': user.username} for user in enable_old_state_users]
        resp, err = delete_ssh_account_via_group(old_interface.server_ip, enable_old_state_users_structed)
        if err:
            db.rollback()
            logger.error(f'[transfer users interface] deleted ssh enable group account failed (resp_code: {err.status_code} -content: {err.detail})')
            raise err

        logger.info(f'[transfer users interface] delete ssh enable group account was successfully (server: {old_interface.server_ip}, -users: {enable_old_state_users_structed})')

        disable_old_state_users_structed = [{'username': user.username} for user in disable_old_state_users]
        resp, err = delete_ssh_account_via_group(old_interface.server_ip, disable_old_state_users_structed)
        if err:
            db.rollback()
            logger.error(f'[transfer users interface] deleted ssh disable group account failed (resp_code: {err.status_code} -content: {err.detail})')
            raise err

        logger.info(f'[transfer users interface] delete ssh disable group account was successfully (server: {old_interface.server_ip}, -users: {enable_old_state_users_structed})')

    enable_new_users = [{'username': user.username , 'password': user.password} for user in enable_new_users]
    disable_new_users = [{'username': user.username , 'password': user.password} for user in disable_new_users]

    new_users = enable_new_users + disable_new_users

    resp, err = create_ssh_account_via_group(new_interface.server_ip, new_users)
    
    if err:
        db.rollback()
        logger.error(f'[transfer users interface] ssh group account creation failed (resp_code: {err.status_code} -content: {err.detail})')
        raise err
    
    logger.info(f'[transfer users interface] the ssh group account was created successfully (server: {new_interface.server_ip} -users: {new_users})')

    resp, err = block_ssh_account_via_groups(new_interface.server_ip, disable_new_users)
    
    if err:
        db.rollback()
        logger.error(f'[transfer users interface] ssh group account creation failed (resp_code: {err.status_code} -content: {err.detail})')
        raise err
    
    db.commit()
    # ============================ Commit ============================ 

    logger.info(f'[transfer users interface] the ssh group account was created successfully (server: {new_interface.server_ip} -users: {new_users})')

    return f'Successfully transfered users from interface [{old_interface.interface_id} to interface [{new_interface.interface_id}]'
