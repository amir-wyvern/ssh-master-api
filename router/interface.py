from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import (
    Status,
    SshInterfaceState,
    PlanResponse,
    SshInterfaceRegister,
    SshInterfaceResponse,
    InterfaceMode,
    HTTPError,
    TokenUser
)
from db import (
    db_server,
    db_ssh_interface
)

from typing import List
from db.database import get_db
from auth.auth import get_admin_user, get_agent_user

router = APIRouter(prefix='/interface', tags=['Interfaces'])

@router.get('/ssh/fetch', response_model= List[PlanResponse], tags=['Agent-Profile'])
def fetch_ssh_interface(mode: InterfaceMode= InterfaceMode.BEST, current_user: TokenUser= Depends(get_agent_user), db: Session=Depends(get_db)):
    
    if mode == InterfaceMode.ALL:
        interfaces = db_ssh_interface.get_all_interface(db, status= Status.ENABLE)
        return interfaces

    elif mode == InterfaceMode.BEST:
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


@router.post('/ssh/new', response_model= SshInterfaceResponse, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError} })
def create_new_ssh_interface(request: SshInterfaceRegister, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):
    
    server = db_server.get_server_by_ip(request.server_ip, db)

    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'message': 'Server not exists', 'internal_code': 2406})
    
    interface = db_ssh_interface.create_interface(request, db)  
    return {'interface_id': interface.interface_id}


@router.post('/ssh/status', response_model= SshInterfaceResponse)
def update_ssh_interface_status(request: SshInterfaceState, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):
    
    interface = db_ssh_interface.change_status(request.interface_id, request.new_status, db)  
    return {'interface_id': request.interface_id}
