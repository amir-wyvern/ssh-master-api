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
    UpdateNodesResponse,
    ServerTransfer,
    NewServerResponse,
    ServerTransferResponse,
    NodesStatusDetail,
    ServerConnection,
    ServiceStatusDb,
    ActiveUsersDetail,
    NodesStatusResponse
)
from db.database import get_db
from db import db_server, db_domain, db_ssh_service

from utils.server import find_best_server
from slave_api.server import get_users, init_server, active_users
from auth.auth import get_admin_user
import paramiko
from paramiko import AuthenticationException

from cloudflare_api.subdomain import update_subdomain
from utils.domain import register_domain_in_cloudflare
from slave_api.ssh import create_ssh_account_via_group, block_ssh_account_via_groups, delete_ssh_account_via_group
from typing import List
from time import sleep
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


@router.post('/new', response_model= NewServerResponse,responses={status.HTTP_409_CONFLICT:{'model':HTTPError}})
def add_new_server(request: NewServer, deploy_slave: DeployStatus = DeployStatus.ENABLE, create_domain: DeployStatus = DeployStatus.DISABLE , current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):
    
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

                logger.info(f'[new server] excuting command (server_ip: {request.server_ip} -command: "{command}")')

                stdin, stdout, stderr = ssh_client.exec_command(command)
                exit_status = stdout.channel.recv_exit_status()

                if exit_status == 0:
                    logger.info(f"[new server] Command executed successfully (server_ip: {request.server_ip} )")

                else:
                    error_command = stderr.read().decode('utf-8')
                    logger.error(f'[new server] Error executing the command (server_ip: {request.server_ip} -command: {command} -error: {error_command})')
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='check the logs for more info')

            ssh_client.close()

        except AuthenticationException as e:
            logger.error(f"[new server] An error AuthenticationException (server_ip: {request.server_ip} -error: {e})")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={'message': 'Authentication Failed', 'internal_code': 2438})
        
        except Exception as e:
            logger.error(f"[new server] An error occurred (server_ip: {request.server_ip} -error: {e})")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='check the logs for more info')
        
        for _ in range(30):
            sleep(1)

            _, err = get_users(request.server_ip)
            if err:
                continue

            _, err = init_server(request.server_ip, request.ssh_port, request.manager_password)
            if err:
                logger.error(f"[new server] error in init server (server_ip: {request.server_ip} -resp_code: {err.status_code} -error: {err.detail})")
                raise HTTPException(status_code=err.status_code, detail={'message': f'error in init server [{err.detail}]', 'internal_code': 2439})

            break

    server = db_server.create_server(request, db)
    logger.info(f'[new server] successfully saved in database (server_ip: {request.server_ip})')
    
    new_domain = None
    if create_domain == DeployStatus.ENABLE:
        domain, err = register_domain_in_cloudflare(request.server_ip, db, logger)
        if err:
            raise err
        new_domain = domain.domain_name

    return NewServerResponse(sever_ip= request.server_ip, domain_name= new_domain)

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


@router.get('/nodes/status', response_model= NodesStatusResponse, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def get_nodes_status( current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    servers = db_server.get_all_server(db)

    response = []
    for server in servers:
        _, err = active_users(server.server_ip)
        if err:
            response.append( NodesStatusDetail(ip= server.server_ip, status= server.status, connection= ServerConnection.DISCONNECT) )
        
        else:
            response.append( NodesStatusDetail(ip= server.server_ip, status= server.status, connection= ServerConnection.CONNECTED) )
    
    return NodesStatusResponse(count= len(servers), detail= response)


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
def get_active_users(server_ip: str= Query(None) ,current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    if server_ip:

        server = db_server.get_server_by_ip(server_ip, db)

        if server is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2406, 'message':'Server not exists'})
        
        resp, err = active_users(server_ip)
        if err:
            logger.error(f'[active users] error (server_ip: {server_ip}) -detail: {err.detail})')
            raise err

        number_active_users = len(resp)
        number_active_sessions = sum([item['count'] for item in resp])

        server_detail = ActiveUsersDetail(detail= resp, active_users= number_active_users, active_sessions= number_active_sessions)

        return ActiveUsersResponse(total_active_users= number_active_users, total_sessions= number_active_sessions, detail= server_detail)

    else:

        servers = db_server.get_all_server(db, status= ServerStatusDb.ENABLE)

        response = []
        total_active_users= 0
        total_sessions= 0
        for server in servers:
            resp, err = active_users(server.server_ip)
            if err:
                resp = []
                logger.error(f'[active users] error (server_ip: {server.server_ip}) -detail: {err.detail})')

            number_active_users = len(resp)
            number_active_sessions = sum([item['count'] for item in resp])

            total_active_users += number_active_users
            total_sessions += number_active_sessions

            response.append(ActiveUsersDetail(
                detail= resp,
                active_users= number_active_users,
                active_sessions= number_active_sessions
            ))

        return ActiveUsersResponse(server_number= len(servers), total_active_users= total_active_users, total_sessions= total_sessions, detail= response)


@router.put('/max_users', response_model= str, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def update_server_max_users(request: UpdateMaxUserServer ,current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    server = db_server.get_server_by_ip(request.server_ip, db)

    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'message': 'Server not exists', 'internal_code': 2406})
    
    db_server.update_max_user(request.server_ip, request.new_max_user, db)
    logger.info(f'[change max user] successfully (server_ip: {request.server_ip} -new_max_users: {request.new_max_user})')

    return 'Server max_user successfully updated!'


@router.post('/transfer', response_model= ServerTransferResponse, responses={
    status.HTTP_404_NOT_FOUND:{'model': HTTPError},
    status.HTTP_500_INTERNAL_SERVER_ERROR:{'model': HTTPError},
    status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError},
    status.HTTP_409_CONFLICT:{'model':HTTPError}})
def transfer_configs_via_server(request: ServerTransfer, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    old_server = db_server.get_server_by_ip(request.old_server_ip, db)
    if old_server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'old server not exists', 'internal_code':2406})
    
    new_server = db_server.get_server_by_ip(request.new_server_ip, db)
    if new_server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'new server not exists', 'internal_code':2406})

    old_server_domains = db_domain.get_domains_by_server_ip(request.old_server_ip, db)
    
    enable_old_users = []
    disable_old_users = []
    expired_old_users = []

    for domain in old_server_domains:

        enable_tmp_users = db_ssh_service.get_services_by_domain_id(domain.domain_id, db, status= ServiceStatusDb.ENABLE)
        disable_tmp_users = db_ssh_service.get_services_by_domain_id(domain.domain_id, db, status= ServiceStatusDb.DISABLE)
        expired_tmp_users = db_ssh_service.get_services_by_domain_id(domain.domain_id, db, status= ServiceStatusDb.EXPIRED)

        enable_old_users.extend(enable_tmp_users)
        disable_old_users.extend(disable_tmp_users)
        expired_old_users.extend(expired_tmp_users)


    listed_enable_old_users = [{'username': user.username, 'password': user.password} for user in enable_old_users]
    listed_disable_old_users = [{'username': user.username, 'password': user.password} for user in disable_old_users]
    listed_expired_old_users = [{'username': user.username, 'password': user.password} for user in expired_old_users]

    listed_new_users = listed_enable_old_users + listed_disable_old_users + listed_expired_old_users
    listed_blocked_users = listed_disable_old_users + listed_expired_old_users

    resp_create, err = create_ssh_account_via_group(request.new_server_ip, listed_new_users, ignore_exists_users= True)
    if err:
        logger.error(f'[transfer users] (create) ssh group account failed (from_server_ip: {request.old_server_ip} -to_server_ip: {request.new_server_ip} -resp_code: {err.status_code} -content: {err.detail})')
        raise err
    
    success_users = resp_create['success_users'] 
    
    logger.info(f'[transfer users] (create) ssh group account was successfully (from_server_ip: {request.old_server_ip} -to_server_ip: {request.new_server_ip} -resp: {resp_create})')

    resp_block = {'not_exists_users': []}
    if listed_blocked_users:
        listed_old_users_for_blocking = [user['username'] for user in listed_disable_old_users]
        resp_block, err = block_ssh_account_via_groups(request.new_server_ip, listed_old_users_for_blocking, ignore_exists_users= True)
        if err:
            logger.error(f'[transfer users] (block) ssh group account failed (from_server_ip: {request.old_server_ip} -to_server_ip: {request.new_server_ip} -resp_code: {err.status_code} -content: {err.detail})')
            db.rollback()
            raise err

        logger.info(f'[transfer users] (block) ssh group account was created successfully (from_server_ip: {request.old_server_ip} -to_server_ip: {request.new_server_ip} -resp: {resp_block})')
        success_users = list( set(success_users) & set(resp_block['success_users'])) 

    resp_del = {'not_exists_users': []}
    if request.delete_old_users: 
        listed_new_users_for_delete = [user['username'] for user in listed_new_users]
        resp_del, err = delete_ssh_account_via_group(request.old_server_ip, listed_new_users_for_delete, ignore_not_exists_users= True)
        if err:
            logger.error(f'[transfer users] (delete) ssh group account failed (resp_code: {err.status_code} -content: {err.detail})')
            db.rollback()
            raise err

        logger.info(f'[transfer users] (delete) ssh group account was successfully (from_server_ip: {request.old_server_ip} -to_server_ip: {request.new_server_ip} -resp: {resp_del})')
        success_users = list( set(success_users) & set(resp_del['success_users'])) 


    for index, domain in enumerate(old_server_domains):
        _, err = update_subdomain(domain.identifier, request.new_server_ip, domain.domain_name)
        if err:
            not_updated_domains = [i.domain_name for i in old_server_domains[index:]]
            logger.error(f'[transfer server] (domain) failed to update cloudflare records (domain: {domain.domain_name} -new_server: {request.new_server_ip} -not_updated_domains: {not_updated_domains} -err_code: {err.status_code} -err_resp: {err.detail})')
            raise err

        db_domain.update_server_ip(domain.domain_id, request.new_server_ip, db)
        logger.info(f'[transfer server] (domain) successfully updated domain (from_server_ip: {request.old_server_ip} -to_server_ip: {request.new_server_ip} -domain: {domain.domain_name})')
    
    
    if request.delete_old_users:
        db_server.decrease_ssh_accounts_number(request.old_server_ip, db, number= len(set(resp_del['success_users']))) 
    
    if request.disable_old_server:
        db_domain.change_status(request.old_server_ip, ServerStatusDb.DISABLE, db)

    db_server.increase_ssh_accounts_number(request.new_server_ip, db, number= len(resp_create['success_users']) )

    domains = [domain.domain_name for domain in old_server_domains]
    logger.info(f'[transfer server] successfully transfer server (from_server_ip: {request.old_server_ip} -to_server_ip: {request.new_server_ip} -updated_domains: {domains})')

    return ServerTransferResponse(
        from_server= request.old_server_ip,
        to_server= request.new_server_ip,
        success_users= success_users,
        domains_updated= domains,
        create_exists_users= resp_create['exists_users'],
        block_not_exists_users= resp_block['not_exists_users'],
        delete_not_exists_users= resp_del['not_exists_users']
    )


