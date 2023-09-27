from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import (
    TokenUser,
    DomainRegister,
    DomainRegisterForDb,
    FetchDomainResponse,
    UpdateDomainStatus,
    HTTPError,
    DomainStatusDb,
    ServerStatusDb,
    UpdateServerInDomain,
    NewDomainResponse,
    ServiceStatusDb,
    DomainTransfer,
    DomainTransferResponse,
    UpdateServerInDomainResponse
)
from db.database import get_db
from db import db_domain, db_server, db_ssh_service

from slave_api.ssh import block_ssh_account_via_groups, create_ssh_account_via_group, delete_ssh_account_via_group
from cloudflare_api.subdomain import new_subdomain, update_subdomain
from auth.auth import get_admin_user
import logging
import re

# Create a file handler to save logs to a file
logger = logging.getLogger('domain_router.log') 
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('domain_router.log') 
file_handler.setLevel(logging.INFO) 
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s') 
file_handler.setFormatter(formatter) 
logger.addHandler(file_handler) 

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

router = APIRouter(prefix='/domain', tags=['Domain'])


@router.post('/new', response_model= NewDomainResponse, responses={status.HTTP_409_CONFLICT:{'model':HTTPError}})
def add_new_domain(request: DomainRegister, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):
    
    domain = db_domain.get_domain_by_name(request.domain_name, db) 
    
    if domain != None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT ,detail={'message': 'domain already exists', 'internal_code': 2447})

    if not re.match(r"^(?:[a-zA-Z0-9\-]+\.)*abc-cluster\.online$", request.domain_name):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT ,detail={'message': 'regex domain is wrong ,right format is [xxx.abc-cluster.online]', 'internal_code': 2460})

    server = db_server.get_server_by_ip(request.server_ip, db)
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'message': 'Server not exists', 'internal_code': 2406})
    
    resp, err = new_subdomain(request.server_ip, request.domain_name)
    if err:
        logger.error(f'[new domain] error in cloudflare (agent_id: {current_user.user_id} -domain: {request.domain_name} -server: {request.server_ip} -error_code: {err.status_code} -error_resp: {err.detail})')
        raise HTTPException(status_code= err.status_code ,detail={'message': err.detail, 'internal_code': 4600})
    identifier = resp['result']['id']

    new_domain = db_domain.create_domain(DomainRegisterForDb(
        domain_name= request.domain_name,
        server_ip= request.server_ip,
        identifier= identifier,
        status= request.status
    ), db)

    logger.info(f'[new domain] successfully register new domain (identifier: {identifier} -domain: {request.domain_name} -server: {request.server_ip} -resp: {resp})')

    return new_domain


@router.get('/fetch', response_model= FetchDomainResponse, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def fetch_domain(domain_id: int = None,
                server_ip: str= None,
                domain_name: str = None,
                status_: DomainStatusDb = None,
                current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):
    
    args_dict = {
        'domain_id': domain_id,
        'server_ip': server_ip,
        'domain_name': domain_name,
        'status': status_
    }
    prepar_dict = {key: value for key, value in args_dict.items() if value is not None}
    
    resp_domains = db_domain.get_domains_by_attrs(db, **prepar_dict)

    return FetchDomainResponse(count= len(resp_domains), result= resp_domains) 


@router.put('/status', response_model= str, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def update_domain_status(request: UpdateDomainStatus, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    # NOTE: the func get_domain_by_name is work accroding to unique domain name
    domain = db_domain.get_domain_by_name(request.domain_name, db)
    
    if domain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2449, 'message':'Domain not exists'})
    
    if domain.status == request.new_status:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': 'domain already has this status', 'internal_code': 2456})

    server = db_server.get_server_by_ip(domain.server_ip, db)

    if server.status == ServerStatusDb.DISABLE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2427, 'message':f'The Server [{server.server_ip}] has disable'})
    
    domains_server = db_domain.get_domains_by_server_ip(domain.server_ip, db, status= DomainStatusDb.ENABLE)

    if len(domains_server) <= 1 and request.new_status == ServerStatusDb.DISABLE:
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': "You cannot disable all domains of this server", 'internal_code': 2457})
    
    db_domain.change_status(domain.domain_id,request.new_status, db)

    logger.info(f'[change domain status] successfully (domain: {request.domain_name} -new_status: {request.new_status})')
    
    return f'Domain status successfully changed (domain: {request.domain_name} -new_status: {request.new_status})'


@router.put('/server/update', response_model= UpdateServerInDomainResponse, responses={status.HTTP_404_NOT_FOUND:{'model':HTTPError}})
def update_server_max_users(request: UpdateServerInDomain ,current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):

    domain = db_domain.get_domain_by_name(request.domain_name, db)

    if domain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'message': 'Domain not exists', 'internal_code': 2449})
    
    if not re.match(r"^(?:[a-zA-Z0-9\-]+\.)*abc-cluster\.online$", request.domain_name):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT ,detail={'message': 'regex domain is wrong ,right format is [xxx.abc-cluster.online]', 'internal_code': 2460})


    resp, err = update_subdomain(domain.identifier, request.server_ip, request.domain_name)
    if err:
        logger.error(f'[update domain] error in cloudflare (agent_id: {current_user.user_id} identifier: {domain.identifier} -domain: {request.domain_name} -server: {request.server_ip} -error_code: {err.status_code} -error_resp: {err.detail})')
        raise HTTPException(status_code= err.status_code ,detail={'message': err.detail, 'internal_code': 4600})

    db_domain.update_server_ip(domain.domain_id, request.server_ip, db)

    logger.info(f'[update domain] successfully updated domain (identifier: {domain.identifier} -domain: {request.domain_name} -server: {request.server_ip} -resp: {resp})')

    return UpdateServerInDomainResponse(
        domain_id= domain.domain_id,
        server_ip= request.server_ip,
        domain_name= domain.domain_name,
        status= domain.status)


@router.post('/transfer', response_model= DomainTransferResponse, responses={
    status.HTTP_404_NOT_FOUND:{'model': HTTPError},
    status.HTTP_500_INTERNAL_SERVER_ERROR:{'model': HTTPError},
    status.HTTP_408_REQUEST_TIMEOUT:{'model': HTTPError},
    status.HTTP_409_CONFLICT:{'model':HTTPError}})
def transfer_configs_via_domain(request: DomainTransfer, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):


    if not (bool(request.new_domain_name) ^ bool(request.new_server_ip)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'just needed to one keys (new_server_ip or new_domain_name)', 'internal_code':2471})


    old_domain = db_domain.get_domain_by_name(request.old_domain_name, db)
    
    if old_domain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'old domain is not exists', 'internal_code':2454})
    
    if old_domain.server_ip == new_domain.server_ip:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'message': 'new domain and old domain have same server', 'internal_code':2458})

    dest = None
    new_ip = None
    if request.new_domain_name:
        new_domain = db_domain.get_domain_by_name(request.new_domain_name, db)
        
        if new_domain.status == DomainStatusDb.DISABLE:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'new domain is disable ', 'internal_code':2451})

        dest = new_domain.domain_name
        new_ip = new_domain.server_ip


    if request.new_server_ip:

        new_server = db_server.get_server_by_ip(request.new_server_ip, db)
        
        if new_server.status == ServerStatusDb.DISABLE:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={'message': 'new server is disable ', 'internal_code':2421})
        
        dest = new_server.server_ip
        new_ip = new_server.server_ip

    enable_old_users = db_ssh_service.get_services_by_domain_id(old_domain.domain_id, db, status= ServiceStatusDb.ENABLE)
    disable_old_users = db_ssh_service.get_services_by_domain_id(old_domain.domain_id, db, status= ServiceStatusDb.DISABLE)
    expired_old_users = db_ssh_service.get_services_by_domain_id(old_domain.domain_id, db, status= ServiceStatusDb.EXPIRED)

    listed_enable_old_users = [{'username': user.username, 'password': user.password} for user in enable_old_users]
    listed_disable_old_users = [{'username': user.username, 'password': user.password} for user in disable_old_users]
    listed_expired_old_users = [{'username': user.username, 'password': user.password} for user in expired_old_users]

    listed_new_users = listed_enable_old_users + listed_disable_old_users + listed_expired_old_users
    listed_block_users = listed_disable_old_users + listed_expired_old_users
    
    resp_create, err = create_ssh_account_via_group(new_ip, listed_new_users, ignore_exists_users= True)

    if err:
        logger.error(f'[transfer domain] (create) ssh group account failed (from_domain_name: {old_domain.domain_name} -from_server_ip: {old_domain.server_ip} -to: {dest} -resp_code: {err.status_code} -content: {err.detail})')
        raise err
    
    success_users = resp_create['success_users'] 
    
    logger.info(f'[transfer domain] (create) ssh group account was successfully (from_domain_name: {old_domain.domain_name} -from_server_ip: {old_domain.server_ip} -to: {dest} -resp: {resp_create})')

    resp_block = {'not_exists_users': []}
    if listed_block_users:
        listed_old_users_for_blocking = [user['username'] for user in listed_block_users]
        resp_block, err = block_ssh_account_via_groups(new_ip, listed_old_users_for_blocking, ignore_exists_users= True)
        if err:
            logger.error(f'[transfer domain] (block) ssh group account failed (from_domain_name: {old_domain.domain_name} -from_server_ip: {old_domain.server_ip} -to: {dest} -resp_code: {err.status_code} -content: {err.detail})')
            raise err

        logger.info(f'[transfer domain] (block) ssh group account was created successfully (from_domain_name: {old_domain.domain_name} -from_server_ip: {old_domain.server_ip} -to: {dest} -resp: {resp_block})')
        success_users = list( set(success_users) & set(resp_block['success_users'])) 

    resp_del = {'not_exists_users': []}
    if request.delete_old_users: 
        listed_new_users_for_delete = [user['username'] for user in listed_new_users]
        resp_del, err = delete_ssh_account_via_group(old_domain.server_ip, listed_new_users_for_delete, ignore_not_exists_users= True)
        if err:
            logger.error(f'[transfer domain] (delete) ssh group account failed (from_domain_name: {old_domain.domain_name} -from_server_ip: {old_domain.server_ip} -resp_code: {err.status_code} -content: {err.detail})')
            raise err

        logger.info(f'[transfer domain] (delete) ssh group account was successfully (from_domain_name: {old_domain.domain_name} -from_server_ip: {old_domain.server_ip} -to: {dest} -resp: {resp_del})')
        success_users = list( set(success_users) & set(resp_del['success_users'])) 

    if request.new_server_ip:

        _, err = update_subdomain(old_domain.identifier, request.new_server_ip, db)
        if err:
            logger.error(f'[transfer domain] (domain) failed to update cloudflare records (domain: {old_domain.domain_name} -new_server: {request.new_server_ip} -err_code: {err.status_code} -err_resp: {err.detail})')
            raise err

        db_domain.update_server_ip(old_domain.domain_id, request.new_server_ip, db)
        logger.info(f'[transfer domain] (domain) successfully updated domain (domain: {old_domain.domain_name} -from_server_ip: {old_domain.server_ip} -to_server_ip: {request.new_server_ip} )')
        
        if request.delete_old_users:
            db_server.decrease_ssh_accounts_number(old_domain.server_ip, db, number= len(set(resp_del['success_users']))) 
        
        db_server.increase_ssh_accounts_number(request.new_server_ip, db, number= len(resp_create['success_users']) )
        
        resp = DomainTransferResponse(
            old_domain_name= old_domain.domain_name,
            from_server= old_domain.server_ip,
            to_server= request.new_server_ip,
            success_users= success_users,
            create_exists_users= resp_create['exists_users'],
            block_not_exists_users= resp_block['not_exists_users'],
            delete_not_exists_users= resp_del['not_exists_users']
        )
    

    elif request.new_domain_name:

        try:

            db_ssh_service.transfer_users_by_domain(old_domain.domain_id, new_domain.domain_id, db, not_status= ServiceStatusDb.DELETED, commit= False)

            if request.delete_old_users:
                db_server.decrease_ssh_accounts_number(old_domain.server_ip, db, commit= False, number= len(set(resp_del['success_users']))) 
            
            elif request.disable_old_domain:
                db_domain.change_status(old_domain.domain_id, DomainStatusDb.DISABLE, db, commit= False)

            db_server.increase_ssh_accounts_number(new_domain.server_ip, db, commit= False, number= len(resp_create['success_users']) )
            db.commit()

        except Exception as e: 
            logger.error(f'[transfer domain] error in database (agent: {current_user.user_id} -error: {e})')
            db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='check the logs for more info')

        resp = DomainTransferResponse(
            old_domain_name= old_domain.domain_name,
            new_domain_name= new_domain.domain_name,
            from_server= old_domain.server_ip,
            to_server= new_domain.server_ip,
            success_users= success_users,
            create_exists_users= resp_create['exists_users'],
            block_not_exists_users= resp_block['not_exists_users'],
            delete_not_exists_users= resp_del['not_exists_users']
        )
    
    logger.info(f'[transfer domain] successfully transfer users (from_domain_name: {old_domain.domain_name} -from_server_ip: {old_domain.server_ip} -to: {dest})')

    return resp


