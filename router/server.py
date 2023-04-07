from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import (
    Status,
    NewServer,
    ServerResponse,
    ServerState,
    HTTPError
)
from db import (
    db_server,
    db_server
)
from slave_api.server import get_users
from auth.auth import get_auth
from db.database import get_db

from typing import List
import requests

router = APIRouter(prefix='/server', tags=['server'])


@router.post('/new', responses={403:{'model':HTTPError}})
def new(request: NewServer, token: str= Depends(get_auth), db: Session=Depends(get_db)):
    
    server = db_server.get_server_by_ip(request.server_ip, db)
    
    if server != None:
        raise HTTPException(status_code=403 ,detail={'message': 'server already exists', 'internal_code': 1403})
    
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

    return True

@router.get('/fetch', response_model= List[ServerResponse], responses={404:{'model':HTTPError}})
def server_fetch(ip: str, token: str= Depends(get_auth), db: Session=Depends(get_db)):

    if ip == 'all':
        server = db_server.get_all_server(db)
        return server
    
    else:
        server = db_server.get_server_by_ip(ip , db, status= Status.ENABLE)
        
        if server == None:
            raise HTTPException(status_code=404, detail={'internal_code':1021, 'message':'server not exists'})

        return [server]

@router.post('/state', response_model= str, responses={403:{'model':HTTPError}})
def server_status(request: ServerState ,token: str= Depends(get_auth), db: Session=Depends(get_db)):

    server = db_server.get_server_by_ip(request.server_ip, db)

    if server == None:
        raise HTTPException(status_code=403 ,detail={'message': 'server not exists', 'internal_code': 1403})
    
    db_server.change_status(request.server_ip, request.new_status, db)

    return 'Server status successfuly changed!'

@router.get('/users', response_model= List[str], responses={403:{'model':HTTPError}})
def server_users(server_ip: str ,token: str= Depends(get_auth), db: Session=Depends(get_db)):

    server = db_server.get_server_by_ip(server_ip, db)

    if server == None:
        raise HTTPException(status_code=403 ,detail={'message': 'server not exists', 'internal_code': 1403})
    
    status_code, resp = get_users(server_ip)

    if status_code == 1419 :
        raise HTTPException(status_code=403, detail={'message': f'networt error [{server_ip}]', 'internal_code': 1419})
        
    if status_code != 200:
        raise HTTPException(status_code=403 ,detail={'message': f'error in slave server [{resp.content}]', 'internal_code': 1403})

    return resp.json()


@router.post('/max_users', response_model= str, responses={403:{'model':HTTPError}})
def server_status(request: ServerState ,token: str= Depends(get_auth), db: Session=Depends(get_db)):

    server = db_server.get_server_by_ip(request.server_ip, db)

    if server == None:
        raise HTTPException(status_code=403 ,detail={'message': 'server not exists', 'internal_code': 1403})
    
    db_server.update_max_user(request.server_ip, request.new_status, db)

    return 'Server max_user successfuly updated!'
