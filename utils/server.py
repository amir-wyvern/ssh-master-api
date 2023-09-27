from schemas import (
    ServerStatusDb,
    BestServerForNewConfig
)
from sqlalchemy.orm.session import Session
from db import db_server, db_domain
from operator import itemgetter
import numpy as np

def find_best_server(db: Session, std_dev: int= 1, except_domain_id: int = None) -> BestServerForNewConfig:

    servers = db_server.get_all_server(generate_status= ServerStatusDb.ENABLE, status= ServerStatusDb.ENABLE, db= db)
    
    if servers == []:
        return None
    
    except_server_ip = None
    if  except_domain_id:
        domain = db_domain.get_domain_by_id(except_domain_id, db)
        except_server_ip = domain.server_ip

    dict_servers = [{'server_ip': server.server_ip,
                     'ssh_port': server.ssh_port,
                     'ssh_accounts_number': server.ssh_accounts_number,
                     'max_users': server.max_users } 
                     for server in servers if server.ssh_accounts_number < server.max_users and \
                            except_server_ip != server.server_ip
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


