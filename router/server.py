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
    InterfaceStatus,
    UpdateNodesResponse
)
from db.database import get_db
from db import db_server, db_ssh_interface

from slave_api.server import get_users, init_server
from auth.auth import get_admin_user
import paramiko
from paramiko import AuthenticationException

from time import sleep
from typing import List
import logging
import os

# Create a file handler to save logs to a file
logger = logging.getLogger('server_route.log') 
logger.setLevel(logging.INFO)

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
def add_new_server(request: NewServer, deploy_slave: ServerStatus = ServerStatus.ENABLE , current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):
    
    server = db_server.get_server_by_ip(request.server_ip, db) 
    
    if server != None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT ,detail={'message': 'Server already exists', 'internal_code': 2405})
    
    if deploy_slave == ServerStatus.ENABLE:

        slave_token = os.getenv('SLAVE_TOKEN')

        commands = [
            'apt-get -y update && apt-get -y upgrade',
            'apt-get -y install python3',
            'apt-get -y install python-is-python3',
            'apt-get -y install python3-pip',
            'apt-get -y install python3-venv',
            'apt-get -y install vim',
            'apt-get -y install sudo',
            'apt-get -y install git',
            'apt-get -y install tmux',
            'git clone https://github.com/amir-wyvern/ssh-slave-api.git /root/ssh-slave-api',
            'python -m venv /root/ssh-slave-api/venv',
            f'echo "TOKEN=\'{slave_token}\'" > /root/ssh-slave-api/.env',
            'tmux new-session -d -s slave',
            "tmux send-keys -t slave 'cd /root/ssh-slave-api;source venv/bin/activate;pip install -r requirements.txt;uvicorn main:app --host 0.0.0.0 --port 8090' Enter",
        ]

        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(request.server_ip, username= 'root', password=request.root_password, port= 22, timeout= 20*60)
            
            for command in commands:

                logging.info(f'[new server] excuting command (server_ip: {request.server_ip} -command: "{command}")')

                stdin, stdout, stderr = ssh_client.exec_command(command)
                exit_status = stdout.channel.recv_exit_status()

                if exit_status == 0:
                    logging.info(f"[new server] Command executed successfully (server_ip: {request.server_ip} )")

                else:
                    error_command = stderr.read().decode('utf-8')
                    logging.error(f'[new server] Error executing the command (server_ip: {request.server_ip} -command: {command} -error: {error_command})')
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='check the logs for more info')

            ssh_client.close()

        except AuthenticationException as e:
            logging.error(f"[new server] An error AuthenticationException (server_ip: {request.server_ip} -error: {e})")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message': 'Authentication Failed', 'internal_code': 2438})
        
        except Exception as e:
            logging.error(f"[new server] An error occurred (server_ip: {request.server_ip} -error: {e})")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='check the logs for more info')
        
        for _ in range(20):
            sleep(1)

            _, err = get_users(request.server_ip)
            if err:
                continue

            _, err = init_server(request.server_ip, request.ssh_port, request.manager_password)
            if err:
                logging.error(f"[new server] error in init server (server_ip: {request.server_ip} -resp_code: {err.status_code} -error: {err.detail})")
                raise HTTPException(status_code=err.status_code, detail={'message': f'error in init server [{err.detail}]', 'internal_code': 2439})

            break

    server = db_server.create_server(request, db)
    logger.info(f'[new server] successfully saved in database (server_ip: {request.server_ip})')

    return 'Server successfully created'

@router.get('/nodes/update', response_model= UpdateNodesResponse , responses={status.HTTP_409_CONFLICT:{'model':HTTPError}})
def update_nodes(current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):
    
    servers = db_server.get_all_server(db, status= ServerStatus.ENABLE) 
    
    if servers == None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT ,detail={'message': 'There is no server exists', 'internal_code': 2440})
    

    # ========= connect to nodes ========= 

    slave_token = os.getenv('SLAVE_TOKEN')

    commands = [
        'sudo tmux kill-session -t slave',
        'sudo git -C /root/ssh-slave-api stash',
        'sudo git -C /root/ssh-slave-api pull',
        f'echo "TOKEN=\'{slave_token}\'" | sudo tee /root/ssh-slave-api/.env',
        'sudo tmux new-session -d -s slave',
        "sudo tmux send-keys -t slave 'cd /root/ssh-slave-api;source venv/bin/activate;pip install -r requirements.txt;uvicorn main:app --host 0.0.0.0 --port 8090' Enter",
    ]

    ls_error = {}
    for server in servers:
        
        interfaces = db_ssh_interface.get_interface_by_server_ip(server.server_ip, db, status= InterfaceStatus.ENABLE)

        changed_interfaces = []
        for interface in interfaces:
            if interface.status == InterfaceStatus.ENABLE:
                changed_interfaces.append(interface)
                db_ssh_interface.change_status(interface.interface_id, InterfaceStatus.DISABLE, db, commit= False)
        
        db.commit()

        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(server.server_ip, username= 'manager', password= server.manager_password, port= server.ssh_port, timeout= 20*60)
            
            for command in commands:
                
                logging.info(f'-[update nodes] excuting command (server_ip: {server.server_ip} -command: "{command}")')

                stdin, stdout, stderr = ssh_client.exec_command(command, get_pty=True, timeout=30)

                stdin.write(f"{server.manager_password}\n")
                stdin.flush()

                exit_status = stdout.channel.recv_exit_status()

                if exit_status == 0:
                    logging.info(f"-[update nodes] Command executed successfully (server_ip: {server.server_ip} )")

                else:
                    error_command = stderr.read().decode('utf-8')
                    ls_error[server.server_ip] = error_command
                    logging.error(f'-[update nodes] Error executing the command (server_ip: {server.server_ip} -command: {command} -error: {error_command})')
                    continue

            ssh_client.close()

        except AuthenticationException as e:
            logging.error(f"-[update nodes] An error AuthenticationException (server_ip: {server.server_ip} -error: {e})")
            ls_error[server.server_ip] = 'Authentication Faield'

        except Exception as e:
            logging.error(f"-[update nodes] An error occurred (server_ip: {server.server_ip} -error: {e})")
            ls_error[server.server_ip] = f'Exception: [{e}]'
        
        for interface in changed_interfaces:
            
            db_ssh_interface.change_status(interface.interface_id, InterfaceStatus.ENABLE, db, commit= False)
        
        db.commit()
        
        if server.server_ip in ls_error: 
            logger.error(f'[update nodes] failed to updated server (server_ip: {server.server_ip})')
        
        else:
            logger.info(f'[update nodes] successfully updated server (server_ip: {server.server_ip})')

    errors = []
    if ls_error:
        message = 'Failed to updating Some nodes'
        errors =[{'server': server, 'detail': error} for server, error in ls_error.items() ] 
        logger.info(f'[update nodes] Failed to updating Some nodes (servers: {list(ls_error.keys())})')

    else:
        message = 'successfully update all nodes'
        logger.info(f'[update nodes] successfully update all nodes')

    return UpdateNodesResponse(message= message, errors= errors)

@router.get('/fetch', response_model= List[ServerResponse], responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def fetch_server_or_servers(ip: str = None, mode: FetchStatusServer= FetchStatusServer.ALL, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    if mode == FetchStatusServer.ALL:
        server = db_server.get_all_server(db)
        
        return server
    
    else:

        server = db_server.get_server_by_ip(ip , db)
        
        if server is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'internal_code':2406, 'message':'Server is not exists'})

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
