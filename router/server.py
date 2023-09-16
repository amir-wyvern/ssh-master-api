from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import (
    TokenUser,
    NewServer,
    FetchServerResponse,
    UpdateMaxUserServer,
    UpdateServerStatus,
    HTTPError,
    ServerStatusDb,
    ActiveUsersResponse,
    DeployStatus,
    DomainStatusDb,
    UsersResponse,
    BestServerForNewConfig,
    UpdateNodesResponse
)
from db.database import get_db
from db import db_server, db_domain

from utils.server import find_best_server
from slave_api.server import get_users, init_server, active_users
from auth.auth import get_admin_user
import paramiko
from paramiko import AuthenticationException

from time import sleep
from typing import List, Dict
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
def add_new_server(request: NewServer, deploy_slave: DeployStatus = DeployStatus.ENABLE , current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):
    
    server = db_server.get_server_by_ip(request.server_ip, db) 
    
    if server != None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT ,detail={'message': 'Server already exists', 'internal_code': 2405})
    
    if deploy_slave == DeployStatus.ENABLE:

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
        
        for _ in range(30):
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
    
    servers = db_server.get_all_server(db, status= ServerStatusDb.ENABLE) 
    
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
        
        flag_changed_status = False

        if server.generate_status == ServerStatusDb.ENABLE:
            db_server.change_generate_status(server.server_ip, ServerStatusDb.DISABLE, db)
            flag_changed_status= True

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

        if server.server_ip in ls_error: 
            logger.error(f'[update nodes] failed to updated server (server_ip: {server.server_ip})')
        
        else:
            logger.info(f'[update nodes] successfully updated server (server_ip: {server.server_ip})')
        
        if flag_changed_status:
            db_server.change_generate_status(server.server_ip, ServerStatusDb.ENABLE, db)

    errors = []
    if ls_error:
        message = 'Failed to updating Some nodes'
        errors =[{'server': server, 'detail': error} for server, error in ls_error.items() ] 
        logger.info(f'[update nodes] Failed to updating Some nodes (servers: {list(ls_error.keys())})')

    else:
        message = 'successfully update all nodes'
        logger.info(f'[update nodes] successfully update all nodes')

    return UpdateNodesResponse(message= message, errors= errors)

@router.get('/fetch', response_model= FetchServerResponse, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def fetch_server_or_servers(ip: str = None,
                            location: str= None,
                            generate_status: ServerStatusDb = None,
                            update_expire_status: ServerStatusDb = None,
                            status_: ServerStatusDb = None,
                            current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    args_dict = {
        'server_ip': ip,
        'location': location,
        'generate_status': generate_status,
        'update_expire_status': update_expire_status,
        'status': status_
    }
    prepar_dict = {key: value for key, value in args_dict.items() if value is not None}
    
    resp_servers = db_server.get_servers_by_attrs(db, **prepar_dict)

    return FetchServerResponse(count= len(resp_servers), result= resp_servers)


@router.put('/status', response_model= str, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def update_server_status(request: UpdateServerStatus, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    server = db_server.get_server_by_ip(request.server_ip, db)

    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2406, 'message':'Server not exists'})
    
    if request.new_generate_status is None and request.new_update_expire_status is None and request.new_status is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2446, 'message':'there is no change status'})

    if request.new_status and server.status == request.new_status:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'server already has this status', 'internal_code': 2431})
    
    if request.new_generate_status and server.generate_status == request.new_generate_status:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'server already has this generate status', 'internal_code': 2444})
    
    if request.new_update_expire_status and server.update_expire_status == request.new_update_expire_status:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'server already has this update expire status', 'internal_code': 2445})

    if request.new_generate_status:
        if server.status == ServerStatusDb.DISABLE:
            raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': f'The Server [{request.server_ip}] has disable', 'internal_code': 2427})

        db_server.change_generate_status(request.server_ip, request.new_generate_status, db)

    if request.new_update_expire_status:
        if server.status == ServerStatusDb.DISABLE:
            raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': f'The Server [{request.server_ip}] has disable', 'internal_code': 2427})
        
        db_server.change_update_expire_status(request.server_ip, request.new_update_expire_status, db)

    try:
        if request.new_status:
            if request.new_status == ServerStatusDb.DISABLE:
                domains = db_domain.get_domains_by_server_ip(request.server_ip, db, DomainStatusDb.ENABLE)

                for domain in domains:
                    db_domain.change_status(domain.domain_id, DomainStatusDb.DISABLE, db, commit= False)
                    
                db_server.change_generate_status(request.server_ip, ServerStatusDb.DISABLE, db, commit= False)
                db_server.change_update_expire_status(request.server_ip, ServerStatusDb.DISABLE, db, commit= False)

            db_server.change_server_status(request.server_ip, request.new_status, db, commit= False)
    
            db.commit()
        
    except Exception as e:
        logger.error(f'[change server status] error while change status (server_ip: {request.server_ip} -to_status(gen_upd_ser): {request.new_generate_status}_{request.new_update_expire_status}_{request.new_status} -error: {e})')
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='check the logs for more info')

    logger.info(f'[change server status] successfully (server_ip: {request.server_ip}) -gen_upd_ser: {request.new_generate_status}_{request.new_update_expire_status}_{request.new_status})')
    
    return f'Server status successfully changed to gen_upd_ser: {request.new_generate_status}_{request.new_update_expire_status}_{request.new_status}'


@router.get('/users', response_model= UsersResponse, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}, status.HTTP_408_REQUEST_TIMEOUT:{'model':HTTPError}})
def get_server_users(server_ip: str ,current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    server = db_server.get_server_by_ip(server_ip, db)

    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2406, 'message':'Server not exists'})
    
    resp, err = get_users(server_ip)
    if err:
        logger.error(f'[get users] error (server_ip: {server_ip}) -detail: {err.detail})')
        raise err
    
    return UsersResponse(detail= resp, number_of_users= len(resp))

@router.get('/best', response_model= BestServerForNewConfig, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}, status.HTTP_408_REQUEST_TIMEOUT:{'model':HTTPError}})
def get_best_server(current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    selected_server = find_best_server(db)

    if selected_server is None :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2450, 'message':'There is no server for new config'})

    return selected_server


@router.get('/active_users', response_model= ActiveUsersResponse, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}, status.HTTP_408_REQUEST_TIMEOUT:{'model':HTTPError}})
def get_active_users(server_ip: str ,current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    server = db_server.get_server_by_ip(server_ip, db)

    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2406, 'message':'Server not exists'})
    
    resp, err = active_users(server_ip)
    if err:
        logger.error(f'[active users] error (server_ip: {server_ip}) -detail: {err.detail})')
        raise err

    number_active_users = len(resp)
    number_active_sessions = sum([item['count'] for item in resp])
    return ActiveUsersResponse(detail= resp, active_users= number_active_users, active_sessions= number_active_sessions)


@router.put('/max_users', response_model= str, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def update_server_max_users(request: UpdateMaxUserServer ,current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    server = db_server.get_server_by_ip(request.server_ip, db)

    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'message': 'Server not exists', 'internal_code': 2406})
    
    db_server.update_max_user(request.server_ip, request.new_max_user, db)
    logger.info(f'[change max user] successfully (server_ip: {request.server_ip} -new_max_users: {request.new_max_user})')

    return 'Server max_user successfully updated!'
