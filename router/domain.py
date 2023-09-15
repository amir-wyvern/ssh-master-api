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
    UpdateServerInDomainResponse
)
from db.database import get_db
from db import db_domain, db_server

from cloudflare_api.subdomain import new_subdomain, update_subdomain
from auth.auth import get_admin_user
from typing import List
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

    if len(domains_server) <= 1 :
        raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail={'message': "You cannot disable all domains of this server", 'internal_code': 2457})
    
    db_domain.change_status(domain.domain_id,request.new_status, db)

    logger.info(f'[change domain status] successfully (server_ip: {request.server_ip}) -gen_upd_ser: {request.new_generate_status}_{request.new_update_expire_status}_{request.new_status})')
    
    return f'Server status successfully changed to gen_upd_ser: {request.new_generate_status}_{request.new_update_expire_status}_{request.new_status}'


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


