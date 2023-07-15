from fastapi import (
    APIRouter,
    Depends,
    status,
    Query,
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import (
    TokenUser,
    NewServer,
    ServerResponse,
    UpdateMaxUserServer,
    UpdateServerStatus,
    FetchStatusServer,
    HTTPError,
    ServerStatus,
    InterfaceStatus
)
from db.database import get_db
from db import db_server, db_ssh_interface, db_ssh_service

from slave_api.server import get_users
from auth.auth import get_admin_user

from typing import List
import logging

# Create a file handler to save logs to a file
logger = logging.getLogger('server_route.log') 

file_handler = logging.FileHandler('server_route.log') 
file_handler.setLevel(logging.INFO) 
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s') 
file_handler.setFormatter(formatter) 
logger.addHandler(file_handler) 

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

router = APIRouter(prefix='/server', tags=['Server'])


@router.post('/new', responses={status.HTTP_409_CONFLICT:{'model':HTTPError}})
def add_new_server(request: NewServer, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):
    
    server = db_server.get_server_by_ip(request.server_ip, db) 
    
    if server != None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT ,detail={'message': 'Server already exists', 'internal_code': 2405})
    
    # this section will active after test on a server 

    # data={
    #     'ssh_port': request.ssh_port,
    #     'manager_password': request.manager_password
    # }
    
    # header = os.getenv('TOKEN')
    # resp = requests.post(f'http://{request.server_ip}/server/init', data=data, headers=header)

    # if resp.status_code != 200:
    #     raise HTTPException(status_code= 403, detail={'message': f'error {resp.content}', 'internal_code': 1403})
    
    server = db_server.create_server(request, db)
    logger.info(f'[new server] successfully (server_ip: {request.server_ip})')

    return 'Server successfully created'

@router.get('/fetch', response_model= List[ServerResponse], responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def fetch_server_or_servers(ip: str = None, mode: FetchStatusServer= FetchStatusServer.ALL, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    if mode == FetchStatusServer.ALL:
        server = db_server.get_all_server(db)
        
        return server
    
    else:
        server = db_server.get_server_by_ip(ip , db)
        
        if server is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'internal_code':2406, 'message':'Server not exists'})

        return [server]


@router.post('/status', response_model= str, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def update_server_status(request: UpdateServerStatus , new_status: ServerStatus =Query(...) ,current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    server = db_server.get_server_by_ip(request.server_ip, db)

    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2406, 'message':'Server not exists'})
    
    if server.status == new_status:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'server already has this status', 'internal_code': 2431})

    try:
        # ==================== Begin ====================
        if new_status == ServerStatus.DISABLE:

            interfaces = db_ssh_interface.get_interface_by_server_ip(request.server_ip, db, status= InterfaceStatus.ENABLE)

            for interface in interfaces:
                
                db_ssh_interface.change_status(interface.interface_id, InterfaceStatus.DISABLE, db, commit= False)
            
        db_server.change_status(request.server_ip, new_status, db, commit= False)
        db.commit()
        # ==================== Commit ====================
        
    except Exception as e:
        logger.error(f'[change server status] error while change status to {new_status} (server_ip: {request.server_ip} -error: {e})')
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='check the logs for more info')

    logger.info(f'[change server status] successfully (server_ip: {request.server_ip}) -status: {new_status})')
    
    return 'Server status successfully changed!'


@router.get('/users', response_model= List[str], responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}, status.HTTP_408_REQUEST_TIMEOUT:{'model':HTTPError}})
def get_server_users(server_ip: str ,current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    server = db_server.get_server_by_ip(server_ip, db)

    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2406, 'message':'Server not exists'})
    
    resp, err = get_users(server_ip)
    if err:
        logger.error(f'[get users] error (server_ip: {server_ip}) -detail: {err.detail})')
        raise err

    return resp


@router.post('/max_users', response_model= str, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def update_server_max_users(request: UpdateMaxUserServer ,current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    server = db_server.get_server_by_ip(request.server_ip, db)

    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'message': 'Server not exists', 'internal_code': 2406})
    
    db_server.update_max_user(request.server_ip, request.new_max_user, db)
    logger.info(f'[change max user] successfully (server_ip: {request.server_ip} -new_max_users: {request.new_max_user})')

    return 'Server max_user successfully updated!'
