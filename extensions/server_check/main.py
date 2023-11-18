import sys

sys.path.append('/root/ssh-master-api')

from celery_tasks.tasks import ReplaceServerCeleryTask, NotificationCeleryTask
from celery_tasks.utils import create_worker_from
from cache.database import get_redis_cache
from cache.database import get_redis_cache
from checkhost_api.main import check_host
from fastapi import HTTPException
from dotenv import load_dotenv
from time import sleep
import traceback
import requests
import logging
import os


logger = logging.getLogger('server_check.log') 
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('server_check.log') 
file_handler.setLevel(logging.INFO) 
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s') 
file_handler.setFormatter(formatter) 
logger.addHandler(file_handler) 

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

_, replace_server_worker = create_worker_from(ReplaceServerCeleryTask)
_, notifocaction_worker = create_worker_from(NotificationCeleryTask)

header = {
    'Accept': 'application/json'
}

class CheckHosts:

    def __init__(self, url, username, password):
        
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = {
            'grant_type': '',
            'username': username,
            'password': password,
            'scope': 'admin',
            'client_id': '',
            'client_secret': ''
        }
        self.url = url 
        resp = requests.post(self.url + 'auth/login', data= data, headers= headers)

        if resp.status_code != 200:
            logger.error(f'username or password is wrong (err_code: {resp.status_code} -err_resp: {resp.content})')
            raise 'Username or Password is Wrong'
        
        self.headers = {
            'accept': 'application/json',
            'Authorization': 'Bearer {0}'.format(resp.json()['access_token'])
        }

        self.db_cache = get_redis_cache().__next__()
        logger.info('Successfully Connect.')


    def get_servers(self):
        
        params = {
            'status_': 'enable'
        }
        
        for _ in range(3):
            resp = requests.get(self.url + 'server/fetch', params= params, headers= self.headers)
            
            if resp.status_code == 200:
                break
        
        if resp.status_code != 200:
            raise HTTPException(status_code= resp.status_code, detail={'internal_code': 5103, 'detail': f'cant fetch server data from api (error: {resp.content})'})


        return resp.json()['result']


    def worker(self):

        while True:
            
            try:
                servers = self.get_servers()

                for server in servers:
                    
                    status = check_host(server['server_ip'])

                    if status == False:
                        payload = {
                            'host': server['server_ip'],
                            'task': 'CheckHostCeleryTask'
                        }
                        replace_server_worker.apply_async(args=(payload,))

                        payload = {
                            'parse_mode': 'markdown',
                            'bot_selector': 'admin_log',
                            'chat_id': 'admin',
                            'message': 'The Server [`{0}`] is filtered'.format(server['server_ip'])
                        }
                        notifocaction_worker.apply_async(args=(payload,))
                    sleep(2)

            except Exception as e:

                if hasattr(e, 'detail'):
                    error_msg = f'occur an error [err_status: {e.status_code} -err_msg: {e.detail}]'
                    type_alarm = '❗ Error'
                    logger.error(error_msg)

                else:
                    error_msg = f'error [{traceback.format_exc()}]'
                    type_alarm = '🚨 Critical'
                    logger.critical(error_msg)
                
                file = 'Server_Check.py'
                message = f'{type_alarm}\nFile: {file}\nMessage: {error_msg}'

                payload = {
                    'bot_selector': 'admin_log',
                    'chat_id': 'admin',
                    'message': message
                }
                notifocaction_worker.apply_async(args=(payload,))
                sleep(60)

            sleep(30)



if __name__ == '__main__':


    load_dotenv('.env')

    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
    MAIN_URL = os.getenv('MAIN_URL')

    CheckHosts(MAIN_URL, ADMIN_USERNAME, ADMIN_PASSWORD).worker()



