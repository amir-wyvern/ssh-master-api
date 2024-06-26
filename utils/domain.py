from sqlalchemy.orm.session import Session
from schemas import (
    DomainStatusDb,
    ServiceStatusDb,
    DomainStatusDb,
    BestServerForNewConfig,
    ServiceStatusDb,
    DomainRegisterForDb

)
from fastapi import HTTPException, status
from db.models import DbDomain, DbServer
from db import db_domain, db_server, db_ssh_service

from cache.cache_session import get_last_domain, set_last_domain
from cloudflare_api.subdomain import new_subdomain
from cache.database import get_redis_cache

import logging
import re
import os

CURRENT_DOMAIN = os.getenv('CURRENT_DOMAIN')
MAX_USER_NUMBER_IN_DOMAIN = 5

def register_domain_in_cloudflare(server_ip: str, db: Session, logger: logging.Logger) -> DbDomain:

    logger.info(f'[create new subdomain] creating new subdomain (server: {server_ip})' )
    counter = 1

    while True:
        new_domain = generate_subdomain(counter= counter)
        check_domain = db_domain.get_domain_by_name(new_domain, db)
        if check_domain:
            counter += 1
            logger.warning(f'[create new subdomain] domain already exists in database (domain: {new_domain} -server: {server_ip})')
            continue
        
        resp, err = new_subdomain(server_ip, new_domain)
        if err:
            if err.detail['errors'][0]['code'] == 81057:
                counter += 1
                logger.warning(f'[create new subdomain] domain already exists in cloudflare (domain: {new_domain} -server: {server_ip})')
                continue

            logger.error(f'[create new subdomain] error in requesting to cloudflare (domain: {new_domain} -server: {server_ip} -error_code: {err.status_code} -error_resp: {err.detail})')
            return None, err
    
        break
    
    set_last_domain(new_domain, get_redis_cache().__next__())
    logger.info(f'[create new domain] successfully created domain in cloudflare (domain: {new_domain} -server: {server_ip})')
    
    selected_domain = db_domain.create_domain(DomainRegisterForDb(domain_name= new_domain, identifier= resp['result']['id'] ,server_ip= server_ip, status= DomainStatusDb.ENABLE), db)

    logger.info(f'[create new domain] successfully created domain in database (domain: {new_domain} -server: {server_ip})')
    
    return selected_domain, None


def get_domain_via_server(server: BestServerForNewConfig, db: Session, logger: logging.Logger) -> DbDomain:

    domains_server = db_domain.get_domains_by_server_ip(server.server_ip, db)

    if domains_server == []:
        return None, HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2461, 'message':'this server have no any domain for used it'})
    
    min_domain_number = 100_000_00
    selected_domain = None
    total_user_domains_number = 0
    for domain in domains_server:
        if domain.status == DomainStatusDb.ENABLE:
            
            enable_users_domain = db_ssh_service.get_services_by_domain_id(domain.domain_id, db, status= ServiceStatusDb.ENABLE)
            disable_users_domain = db_ssh_service.get_services_by_domain_id(domain.domain_id, db, status= ServiceStatusDb.DISABLE)
            users_domain = enable_users_domain + disable_users_domain
            total_user_domains_number += len(users_domain)
            if len(users_domain) < MAX_USER_NUMBER_IN_DOMAIN and len(users_domain) < min_domain_number:

                min_domain_number = len(users_domain)
                selected_domain = domain

    if selected_domain is None and total_user_domains_number < server.max_users:
        
        selected_domain, err = register_domain_in_cloudflare(server.server_ip, db, logger)
        if err:
            return None, err

    if selected_domain is None:
        return None, HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2472, 'message':'this server has no any useable domain'})

    return selected_domain, None


def get_server_via_domain(domain_id: int, db: Session) -> DbServer:

    domain = db_domain.get_domain_by_id(domain_id, db)
    
    if domain.status == DomainStatusDb.DISABLE:
        return None, HTTPException(status_code=status.HTTP_409_CONFLICT ,detail={'internal_code':2451, 'message':'This domain is disable '})
    
    selected_server = db_server.get_server_by_ip(domain.server_ip, db)

    if selected_server.generate_status == ServiceStatusDb.DISABLE:
        return None, HTTPException(status_code=status.HTTP_409_CONFLICT ,detail={'internal_code':2452, 'message': f'The Server [{selected_server.server_ip}] has disable (generation status)'})
    
    if selected_server.status == ServiceStatusDb.DISABLE:
        return None, HTTPException(status_code=status.HTTP_409_CONFLICT ,detail={'internal_code':2452, 'message': f'The Server [{selected_server.server_ip}] has disable (main status)'})

    if selected_server.ssh_accounts_number >= selected_server.max_users:
        return None, HTTPException(status_code= status.HTTP_406_NOT_ACCEPTABLE, detail={'message': f'The Server [{selected_server.server_ip}] has reached to max users', 'internal_code': 2411})


    return selected_server, None


def generate_subdomain(counter):
        
    last_domain = get_last_domain(get_redis_cache().__next__())

    matches = re.match(r'([a-zA-Z]+)(\d+)', last_domain.split('.')[0])
    text_part = matches.group(1)
    number_part = matches.group(2)
    new_number_part = int(number_part) + counter
    new_sub = f'{text_part}{new_number_part}'
    new_domain = f'{new_sub}.{CURRENT_DOMAIN}'

    return new_domain

