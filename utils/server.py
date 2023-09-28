from fastapi import HTTPException, status
from schemas import (
    ServerStatusDb,
    BestServerForNewConfig
)
from sqlalchemy.orm.session import Session
from db import db_server, db_domain
from db.models import DbDomain
from operator import itemgetter
import numpy as np
from typing import List, Tuple
from utils.domain import get_domain_via_server
import logging

def find_best_server(db: Session, std_dev: int= 1, except_domains_id: List[int] = [], except_servers: List[str] = []) -> BestServerForNewConfig:

    servers = db_server.get_all_server(generate_status= ServerStatusDb.ENABLE, status= ServerStatusDb.ENABLE, db= db)
    
    if servers == []:
        return None
    
    except_server_via_domain = {domain.server_ip for domain_id in except_domains_id if ( domain := db_domain.get_domain_by_id(domain_id, db)) }
    except_servers.extend(list(except_server_via_domain))
    
    dict_servers = [
        {
            'server_ip': server.server_ip,
            'ssh_port': server.ssh_port,
            'ssh_accounts_number': server.ssh_accounts_number,
            'max_users': server.max_users 
        } for server in servers if server.ssh_accounts_number < server.max_users and \
                server.server_ip not in except_servers
                    ]
    
    if dict_servers == []:
        return None
    
    sorted_servers = sorted(dict_servers, key=itemgetter('ssh_accounts_number')) 

    mean = 1  # Mean of the distribution
    num_samples = 1  # Number of samples to select

    random_indices = np.random.normal(mean, std_dev, num_samples)
    random_indices = np.clip(random_indices, 0, len(sorted_servers) - 1)
    random_indices = np.round(random_indices).astype(int)
    
    selected_server = sorted_servers[int(random_indices)]

    return BestServerForNewConfig(**selected_server)


def find_server_and_domain(db: Session, logger: logging.Logger) -> Tuple[BestServerForNewConfig, DbDomain, HTTPException]:

    expect_servers = []
    
    while True:

        selected_server = find_best_server(db, except_servers= expect_servers )
        if selected_server is None:
            return None, None, HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail={'internal_code':2450, 'message':'There is no server for new config'})
        
        selected_domain, err = get_domain_via_server(selected_server, db, logger)

        if err:
            expect_servers.append(selected_server.server_ip)
            continue
        
        return selected_server, selected_domain, None