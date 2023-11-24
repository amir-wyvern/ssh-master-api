import sys

sys.path.append('/root/ssh-master-api')

from fastapi import HTTPException
from dotenv import load_dotenv
from typing import Dict, List
from time import sleep
import traceback
import requests
import logging
import os
from slave_api.ssh import create_ssh_account_via_group, delete_ssh_account_via_group

logger = logging.getLogger('sync_server.log') 
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('sync_server.log') 
file_handler.setLevel(logging.INFO) 
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s') 
file_handler.setFormatter(formatter) 
logger.addHandler(file_handler) 

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class SyncServer:

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
            raise HTTPException(status_code= 403, detail='Username or Password is Wrong')
        
        self.headers = {
            'accept': 'application/json',
            'Authorization': 'Bearer {0}'.format(resp.json()['access_token'])
        }

        slave_token_resp = requests.get(self.url + 'auth/slave_token', headers= self.headers)

        if slave_token_resp.status_code != 200:
            logger.error(f'error while getting slave token (err_code: {resp.status_code} -err_resp: {resp.content})')
            raise HTTPException(status_code= 409, detail='error while getting slave token')
        
        self.slave_header = {
            'accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'token': slave_token_resp.json()['token']
        }

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
    
    def get_users_server(self, server_ip, source):
        
        params = {
            'server_ip': server_ip,
            'source': source
        }
        
        for _ in range(3):
            resp = requests.get(self.url + 'server/users', params= params, headers= self.headers)
            
            if resp.status_code == 200:
                break
        
        if resp.status_code != 200:
            raise HTTPException(status_code= resp.status_code, detail={'internal_code': 5103, 'detail': f'cant fetch server data from api (error: {resp.content})'})


        return resp.json()['result']
    
    def get_domains_server(self, server_ip):
        
        params = {
            'server_ip': server_ip,
            'status_': 'enable'
        }
        
        for _ in range(3):
            resp = requests.get(self.url + 'domain/fetch', params= params, headers= self.headers)
            
            if resp.status_code == 200:
                break
        
        if resp.status_code != 200:
            raise HTTPException(status_code= resp.status_code, detail={'internal_code': 5103, 'detail': f'cant fetch server data from api (error: {resp.content})'})

        return resp.json()['result']
    
    def create_users(self, server_ip, list_users: Dict[str, str]):
        
        data = {
            "ignore_exists_users": True,
            "users": list_users
        }
        
        for _ in range(3):
            
            resp = requests.post(f'http://{server_ip}:8090/' + 'ssh/create', json= data, headers= self.slave_header)
            
            if resp.status_code == 200:
                break
        
        if resp.status_code != 200:
            raise HTTPException(status_code= resp.status_code, detail={'internal_code': 5103, 'detail': f'cant create users (users: {list_users} -error: {resp.content})'})

        return resp.json()
    
    def delete_users(self, server_ip, list_users: List[str]):
        
        data = {
            "ignore_not_exists_users": True,
            "users": list_users
        }
        
        for _ in range(3):
            
            resp = requests.delete(f'http://{server_ip}:8090/' + 'ssh/delete', json= data , headers= self.slave_header)
            
            if resp.status_code == 200:
                break
        
        if resp.status_code != 200:
            raise HTTPException(status_code= resp.status_code, detail={'internal_code': 5103, 'detail': f'cant delete users (users: {list_users} -error: {resp.content})'})

        return resp.json()
    
    def user_detail(self, username):

        params = {
            'username': username
        }
        
        for _ in range(3):
            
            resp = requests.get(self.url + 'service/search', params= params, headers= self.headers)
            
            if resp.status_code == 200:
                break
        
        if resp.status_code != 200:
            raise HTTPException(status_code= resp.status_code, detail={'internal_code': 5103, 'detail': f'cant detch user detail (username: {username} -error: {resp.content})'})

        return resp.json()

    def push_notif(self, message):

        data = {
            "message": message,
            "parse_mode": False,
            "except_agents": [],
            "accept_agents": ["vpn_cluster"],
            "bot": "admin_log"
        }
        
        for _ in range(3):
            
            resp = requests.post(self.url + 'notif/publish', json= data, headers= self.headers)
            
            if resp.status_code == 200:
                break
        
        if resp.status_code != 200:
            raise HTTPException(status_code= resp.status_code, detail={'internal_code': 5103, 'detail': f'cant send message to server (message: {message} -error: {resp.content.decode()})'})

        return resp.json()

    def worker(self):

        while True:
            
            try:
                servers = self.get_servers()

                for server in servers:
                    
                    database_users = self.get_users_server(server['server_ip'], 'database')
                    server_users = self.get_users_server(server['server_ip'], 'slave_server')

                    create_users = set(database_users) - set(server_users)  
                    delete_users = set(server_users) - set(database_users)
                    deleted_users_listed = [user for user in delete_users if user.startswith('user_')]

                    if create_users:
                        list_create_users = []
                        
                        for user in create_users:
                            resp = self.user_detail(user)
                            list_create_users.append({
                                'username': resp['result'][0]['username'],
                                'password': resp['result'][0]['password']
                            })

                        create_ssh_account_via_group(server['server_ip'], list_create_users)

                    if deleted_users_listed:

                        delete_ssh_account_via_group(server['server_ip'], deleted_users_listed)


            except Exception as e:

                if hasattr(e, 'detail'):
                    error_msg = f'occur an error in sync server [err_status: {e.status_code} -err_msg: {e.detail}]'
                    type_alarm = '❗ Error'
                    logger.error(error_msg)

                else:
                    error_msg = f'error in sync server [{traceback.format_exc()}]'
                    type_alarm = '🚨 Critical'
                    logger.critical(error_msg)
                
                file = 'sync_servers/server.py'
                message = f'{type_alarm}\nFile: {file}\nMessage: {error_msg}'

                self.push_notif(message)
                sleep(60)
                continue

            sleep(60*60)



if __name__ == '__main__':


    load_dotenv('.env')

    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
    MAIN_URL = os.getenv('MAIN_URL')

    SyncServer(MAIN_URL, ADMIN_USERNAME, ADMIN_PASSWORD).worker()



