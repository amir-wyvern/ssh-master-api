import requests
import sys

sys.path.append('/root/ssh-master-api')

from fastapi import HTTPException
from time import sleep
import logging

logger = logging.getLogger('check_host_api.log') 
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('check_host_api.log') 
file_handler.setLevel(logging.INFO) 
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s') 
file_handler.setFormatter(formatter) 
logger.addHandler(file_handler) 

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


headers = {
    'accept': 'application/json',
    'Content-Type': 'application/x-www-form-urlencoded',
}
nodes = ['ir1.node.check-host.net', 'ir3.node.check-host.net', 'ir4.node.check-host.net', 'ir5.node.check-host.net', 'ir6.node.check-host.net']


def check_host(host):

    params = '&'.join([f'node={node}' for node in nodes])
    resp = requests.get(f'https://check-host.net/check-ping?host={host}&{params}', headers= headers)

    if resp.status_code != 200:
        logger.error(f'failed in send requests to check host (host: {host} -err_status: {resp.status_code} -err_msg: {resp.content})')
        raise HTTPException(status_code= resp.status_code, detail={'internal_code': 5101, 'detail': f'check-host (error: {resp.content})'})

    request_id = resp.json()['request_id']  
    sleep(2)      

    status = request_id_worker(request_id)
    return status

def request_id_worker(request_id):

    while True:

        for _ in range(3):
            result = requests.get(f'https://check-host.net/check-result/{request_id}', headers= headers)

            if result.status_code != 200:
                logger.error(f'failed in send requests to get result of check host (request_id: {request_id} -err_status: {result.status_code} -err_msg: {result.content})')
                raise HTTPException(status_code= result.status_code, detail={'internal_code': 5102, 'detail': f'check-result (error: {result.content})'})

            check_none_result = any(item is None for item in result.json().values())
            if check_none_result is True:
                sleep(2)
                continue 
        
        if check_none_result is True:
            continue 

        res_nodes = []
        for node_result in result.json().values():
            res = [1 if (res and res[0] == 'OK') else 0 for res in node_result[0] ]
            if sum(res) >= len(node_result[0]) // 2:
                res_nodes.append(1)
        
        status = False
        if sum(res_nodes) > len(result.json()) // 2:
            status = True

        return status
    
