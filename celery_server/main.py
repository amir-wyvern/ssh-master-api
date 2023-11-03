import sys

sys.path.append('../')

from cache.cache_session import set_server_number, get_server_number, set_server_proccessing, get_server_proccessing
from celery_tasks.tasks import ReplaceServerCeleryTask, NotificationCeleryTask
from celery_tasks.utils import create_worker_from
from celery_server.server_provider import VPS4
from cache.database import get_redis_cache
from checkhost_api.main import check_host
from fastapi import HTTPException
from dotenv import load_dotenv
import traceback
import requests
import logging
import os

load_dotenv('.env')

logger = logging.getLogger('celery_server_service.log')
logger.setLevel(logging.INFO)

# Create a file handler to save logs to a file 

file_handler = logging.FileHandler('celery_server_service.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

provider_4vps = VPS4()

class ReplaceServerCeleryTaskImpl(ReplaceServerCeleryTask):

    def __init__(self):

        ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
        ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
        MANAGER_PASSWORD_SLAVE = os.getenv('MANAGER_PASSWORD_SLAVE')
        MAIN_URL = os.getenv('MAIN_URL')

        self.main_api = MainApi(MAIN_URL, ADMIN_USERNAME, ADMIN_PASSWORD, MANAGER_PASSWORD_SLAVE)

        if get_server_number(get_redis_cache().__next__()) is None:
            set_server_number(1, get_redis_cache().__next__())

    def run(self, payload):

        logger.info(f'payload: {payload}')

        try:
            old_host = payload['host'] 
            if get_server_proccessing(old_host, get_redis_cache().__next__()):
                return
            
            message = f'❕ Receive a signal about filtered server [{old_host}]'
            payload = {
                'bot_selector': 'admin_log',
                'chat_id': 'admin',
                'message': message
            }
            notifocaction_worker.apply_async(args=(payload,))

            set_server_proccessing(old_host, get_redis_cache().__next__())

            # add this featcher : check server for active for stoped ,coz if server stoped , we dont need to buy new server and we need to recharge
            while True:
                server_ip, server_id, password, location = self.requests_to_provider_for_new_server()

                logger.info(f'send requests to submit new server ... (ip: {server_ip})')
                new_server_resp = self.main_api.submit_new_server(server_ip, password, location)
                if new_server_resp == False:
                    provider_4vps.automatic_renewal(server_id, server_ip)
                    continue

                break

            logger.info(f'successfully submited new server (ip: {server_ip} -msg: {new_server_resp})')
            
            logger.info(f'send request to transfer server (old_server: {old_host} -new_server: {server_ip})')
            transfer_server_resp = self.main_api.transfer_server(old_host, server_ip)
            logger.info(f'successfully transfer new server (old_server: {old_host} -new_server: {server_ip} -msg: {transfer_server_resp})')

            provider_4vps.disable_old_server(old_host)
            
            message = f'Server [{old_host}] has filtered and replace with this server [{server_ip}]'
            payload = {
                'bot_selector': 'admin_log',
                'chat_id': 'admin',
                'message': message
            }
            notifocaction_worker.apply_async(args=(payload,))

        except Exception as e:

            if hasattr(e, 'detail'):
                error_msg = f'occur an error [err_status: {e.status_code} -err_msg: {e.detail}]'
                type_alarm = '❗ Error'
                logger.error(error_msg)

            else:
                error_msg = f'error [{traceback.format_exc()}]'
                type_alarm = '🚨 Critical'
                logger.critical(error_msg)
            
            file = 'celery_server/main.py'
            message = f'{type_alarm}\nFile: {file}\nMessage: {error_msg}'

            payload = {
                'bot_selector': 'admin_log',
                'chat_id': 'admin',
                'message': message
            }
            notifocaction_worker.apply_async(args=(payload,))

    def request_new_server(self):
        
        current_server_number = int(get_server_number(get_redis_cache().__next__()) )
        new_server_number = current_server_number + 1
        new_server_name = f'server-{new_server_number}'
        set_server_number(new_server_number, get_redis_cache().__next__() )

        server_ip, server_id, password, data_center = provider_4vps.buy_server(new_server_name)
        
        return server_ip, server_id, password, data_center

    def requests_to_provider_for_new_server(self):

        while True:

            while True:
                try:
                    server_ip, server_id, password, location = self.request_new_server()
                    break

                except Exception as e:
                    if not hasattr(e, 'detail'):
                        raise e


            status = check_host(server_ip)
            if status:
                break

            provider_4vps.automatic_renewal(server_id, server_ip)

        return server_ip, server_id, password, location


class MainApi:

    def __init__(self, url, admin_username, admin_password, manager_password):

        self.url = url
        self.manager_password = manager_password

        self.no_token_headers = {
            'accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        token = self._login(admin_username, admin_password)

        self.token_headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }


    def submit_new_server(self, server_ip, password, location):
        
        data = {
            "server_ip": server_ip,
            "server_type": "main",
            "location": location,
            "ssh_port": 6379,
            "max_users": 70,
            "ssh_accounts_number": 0,
            "v2ray_accounts_number": 0,
            "root_password": password,
            "manager_password": self.manager_password,
            "generate_status": "enable",
            "update_expire_status": "enable",
            "status": "enable"
        }

        params = {
            'deploy_slave': 'enable',
            'create_domain': 'disable'
        }
        
        resp = requests.post(self.url + 'server/new', params= params, json= data, headers= self.token_headers)

        if resp.status_code != 200:
            logger.error(f'(submit_new_server) failed to submit new server (ip: {server_ip} -err_status: {resp.status_code} -err_msg: {resp.content})')
            if resp.status_code == 409 and hasattr(resp, 'json') and 'internal_code' in resp.json()['detail']:
                return False
            
            raise HTTPException(status_code= resp.status_code, detail= resp.json())
        
        return resp.json()


    def transfer_server(self, old_server_ip, new_server_ip):

        data = {
            'old_server_ip': old_server_ip,
            'new_server_ip': new_server_ip,
            'disable_old_server': True,
            'delete_old_users': False
        }

        resp = requests.post(self.url + 'server/transfer', json= data, headers= self.token_headers)

        if resp.status_code != 200:
            logger.error(f'(transfer_server) failed to transfer server (old_server: {old_server_ip} -new_server: {new_server_ip} -err_status: {resp.status_code} -err_msg: {resp.content})')
            raise HTTPException(status_code= resp.status_code, detail= resp.json())
        
        return resp.json()


    def _login(self, admin_username, admin_password):

        data = {
            'grant_type': '',
            'username': admin_username,
            'password': admin_password,
            'scope': 'admin',
            'client_id': '',
            'client_secret': ''
        }

        resp = requests.post(self.url + 'auth/login', data= data, headers= self.no_token_headers)

        if resp.status_code == 200:
            return resp.json()['access_token']

        if resp.status_code == 401:
            return HTTPException(status_code= 6401, detail='Incorrect username or password')
        
        if resp.status_code != 200:
            raise HTTPException(status_code= resp.status_code, detail=resp.content)


app, _ = create_worker_from(ReplaceServerCeleryTaskImpl)
_, notifocaction_worker = create_worker_from(NotificationCeleryTask)


# start worker
if __name__ == '__main__':
    
    app.worker_main()
