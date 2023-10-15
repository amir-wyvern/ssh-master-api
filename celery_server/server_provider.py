import sys

sys.path.append('../')

from requests.exceptions import ConnectTimeout, ConnectionError, ReadTimeout
from fastapi import HTTPException, status
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from random import choice
from time import sleep
import requests 
import logging
import os
import re

logger = logging.getLogger('server_provider.log')
logger.setLevel(logging.INFO)

# Create a file handler to save logs to a file 

file_handler = logging.FileHandler('server_provider.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


load_dotenv('.env')

class VPS4:

    def __init__(self):

        SERVER_PROVIDER_API_KEY_1 = os.getenv('SERVER_PROVIDER_API_KEY_1')
        SERVER_PROVIDER_URL_1 = os.getenv('SERVER_PROVIDER_URL_1')

        SERVER_PROVIDER_EMAIL_1 = os.getenv('SERVER_PROVIDER_EMAIL_1')
        SERVER_PROVIDER_PASSWORD_1 = os.getenv('SERVER_PROVIDER_PASSWORD_1')

        if not all([SERVER_PROVIDER_API_KEY_1, SERVER_PROVIDER_URL_1, SERVER_PROVIDER_EMAIL_1, SERVER_PROVIDER_PASSWORD_1]):
            raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= {'internal_code': 6001, 'detail': 'Cant load env vars for server provider'})
        
        self.url = SERVER_PROVIDER_URL_1
        self.headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {SERVER_PROVIDER_API_KEY_1}'
        }
        self.login_data = {
            'email': SERVER_PROVIDER_EMAIL_1,
            'password': SERVER_PROVIDER_PASSWORD_1
        }

        self.dashboard_header = {
            'headers': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9,fa;q=0.8,ar;q=0.7,zh-CN;q=0.6,zh;q=0.5',
            'Content-Length': '79',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://4vps.su',
            'Referer': 'https://4vps.su/dashboard/addserver',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
            'Cookie': 'PHPSESSID=4brorcuijh87lcg92uk0a9js;__ddg1_=5IPFiUxSq4rbzFqYjNUG;googtrans=null;googtrans=null;',
            'Sec-Ch-Ua': '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': 'Linux',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Sec-Gpc': '1',
            'Upgrade-Insecure-Requests': '1',
            'X-Requested-With': 'XMLHttpRequest'
        }

        self.server_lib = {
            # 'Turkiye-Izmir':{            
            #     'tarif': 13,
            #     'datacenter': 53,
            #     'ostempl': 25,
            #     'recipe': '',
            #     'count': 1,
            #     'period': 1,
            #     'promocode':'' 
            # }, 
            'Turkiye-Istanbul': {
                'tarif': 19,
                'datacenter': 63,
                'ostempl': 25,
                'recipe': '',
                'count': 1,
                'period': 1,
                'promocode':'' 
            }
        }

    def buy_server(self, server_name):
        
        balance = self.get_balance()

        if balance > 1:
            
            location = choice(list(self.server_lib.keys())) 
            self.login() 

            data= self.server_lib[location].copy() 
            data['name'] = server_name 
            
            self._buy_server(server_name, data)
            server_id, server_ip = self.get_ip(server_name) 

            self.login() 
            password = self.dashboard_message(data) 

            logger.info('(buyserver) finish buy server and ready for use')

            return server_ip, server_id, password, location

        else:
            raise HTTPException(status_code= 403, detail= {'internal_code': 6002, 'detail': 'not enough balance for new server'})
            
    def get_balance(self):
        
        resp = requests.get(self.url + 'api/userBalance', headers= self.headers)

        if resp.status_code != 200:
            raise HTTPException(status_code= resp.status_code, detail= {'internal_code': 6002, 'detail': f'error in get user balance (err: {resp.content})'})

        if resp.json()['error'] == True :
            raise HTTPException(status_code= resp.status_code, detail= {'internal_code': 6005, 'detail': f'false result in get user balance (err: {resp.content})'})
        
        return resp.json()['data']['userBalance']

    def get_ip(self, server_name):

        creating_flag = False
        installing_flag = False

        for _ in range(60):

            for server in self.list_servers()[:5]:
                if server['name'] == server_name:
                    if server['status'] == 'installing' and not installing_flag:
                        installing_flag = True
                        logger.info(f'(get_ip) installing server (name: {server_name})')
                    
                    elif server['status'] == 'creating' and not creating_flag:
                        creating_flag = True
                        logger.info(f'(get_ip) creating server (name: {server_name})')

                    elif server['status'] == 'active':
                        logger.info('(get_ip) successfully created server (name: {0} -id: {1} -ip: {2})'.format(server_name, server['id'], server['ipv4']))
                        return server['id'], server['ipv4']


            sleep(10)

        logger.error(f'(get_ip) failed to created server (name: {server_name})')
        return False, False

    def list_servers(self):
        
        resp = requests.get(self.url + 'api/myservers', headers= self.headers)

        if resp.status_code != 200:
            raise HTTPException(status_code= resp.status_code, detail= {'internal_code': 6002, 'detail': f'error in get list servers (err: {resp.content})'})

        if resp.json()['error'] == True :
            raise HTTPException(status_code= resp.status_code, detail= {'internal_code': 6004, 'detail': f'false result in get list servers (err: {resp.content})'})
        
        return resp.json()['data']['serverlist']

    def automatic_renewal(self, server_id, server_ip):

        data = {
            'serverid': server_id
        }
        resp = requests.post(self.url + 'api/action/autoprolong', data= data, headers= self.headers)

        if resp.status_code != 200:
            logger.error(f'(automatic_renewal) failed in renewal status server (id: {server_id} -ip: {server_ip} -err_status: {resp.status_code} -err_msg: {resp.content})')
            raise HTTPException(status_code= resp.status_code, detail= {'internal_code': 6002, 'detail': f'error in post auto renewal (err: {resp.content})'})

        if resp.json()['error'] == True :
            logger.error(f'(automatic_renewal) failed in renewal status server (id: {server_id} -ip: {server_ip} -err_status: {resp.status_code} -err_msg: {resp.content})')
            raise HTTPException(status_code= resp.status_code, detail= {'internal_code': 6003, 'detail': f'false result in post auto renewal (err: {resp.content})'})
        
        renewl_status = resp.json()['data']
        logger.info(f'(automatic_renewal) renewal status server [{server_ip}] change to [{renewl_status}]  ')
        
        return renewl_status
    
    def list_data_center(self):

        resp = requests.get(self.url + 'api/getDcList', headers= self.headers)

        if resp.status_code != 200:
            raise HTTPException(status_code= resp.status_code, detail= {'internal_code': 6006, 'detail': f'error in get list data center (err: {resp.content})'})

        if resp.json()['error'] == True :
            raise HTTPException(status_code= resp.status_code, detail= {'internal_code': 6007, 'detail': f'false result in get list data center (err: {resp.content})'})
        
        
        return resp.json()['data']
    
    def list_tariff(self):

        resp = requests.get(self.url + 'api/getTarifList', headers= self.headers)

        if resp.status_code != 200:
            raise HTTPException(status_code= resp.status_code, detail= {'internal_code': 6006, 'detail': f'error in get list data center (err: {resp.content})'})

        if resp.json()['error'] == True :
            raise HTTPException(status_code= resp.status_code, detail= {'internal_code': 6007, 'detail': f'false result in get list data center (err: {resp.content})'})
        
        return resp.json()['data']

    def list_images(self):

        resp = requests.get(self.url + f'https://4vps.su/api/getImages/13/16', headers= self.headers)

        if resp.status_code != 200:
            raise HTTPException(status_code= resp.status_code, detail= {'internal_code': 6008, 'detail': f'error in get list os images (err: {resp.content})'})

        if resp.json()['error'] == True :
            raise HTTPException(status_code= resp.status_code, detail= {'internal_code': 6009, 'detail': f'false result in get list os images (err: {resp.content})'})
        
        return resp.json()['data']['images']
    
    def login(self):

        resp = requests.post('https://4vps.su/account/action/login', data= self.login_data, headers= self.dashboard_header)

        if resp.status_code != 200:
            logger.error(f'(login) failed login (err_status: {resp.status_code} -err_msg: {resp.content}')
            raise HTTPException(status_code= resp.status_code, detail= {'internal_code': 6010, 'detail': f'failed to login to dashboard (err: {resp.content})'})

        if resp.json()['status'] != 'success':
            logger.error(f'(login) failed login (err_status: {resp.status_code} -err_msg: {resp.content}')
            raise HTTPException(status_code= resp.status_code, detail= {'internal_code': 6010, 'detail': f'false result in login to dashboard (err: {resp.content})'})

        logger.info('(login) successfully login')
        return True
    
    def _buy_server(self, data):
        
        name = data['name']
        data_center = data['datacenter']

        resp = requests.post('https://4vps.su/dashboard/action/buyServer4', data= data, headers= self.dashboard_header)

        if resp.status_code != 200:
            logger.error(f'(_buy server) failed (err_status: {resp.status_code} -err_msg: {resp.content})')
            raise HTTPException(status_code= resp.status_code, detail= {'internal_code': 6010, 'detail': f'error in buy server (err: {resp.content} -datacenter: {data_center})'})

        if resp.json()['status'] != 'success' :
            logger.error(f'(_buy server) failed (err_status: {resp.status_code} -err_msg: {resp.content})')
            raise HTTPException(status_code= resp.status_code, detail= {'internal_code': 6003, 'detail': f'false result in buy server (err: {resp.content} -datacenter: {data_center})'})
        
        logger.info(f'(buy server) successfuly buy a server (name: {name} -datacenter: {data_center})')
        
        return True

    def dashboard_message(self, data):

        server_name = data['name']

        for _ in range(10):
            
            try:
                resp = requests.get('https://4vps.su/dashboard/messages', data= data, headers= self.dashboard_header)
                if resp.status_code != 200:
                    logger.error(f'false result in get dashboard message (err: {resp.content})')
                    continue

                break

            except (ConnectTimeout, ConnectionError, ReadTimeout):
                logger.error('error in get dashboard message (TimeOut)')
                sleep(1)
        
        return self._scrap(resp.text, server_name)
        
    def _scrap(self, text, server_name):

        soup = BeautifulSoup(text, 'html.parser')

        specific_divs = soup.find_all('div', class_='message-block')[:3]

        for div in specific_divs:

            server_title = div.find('div', class_='header__title')
            match = re.search(f'{server_name}', server_title.text)

            password_obj = div.find('b', class_='eventCopy')
            if hasattr(password_obj, 'text') and match:
                server = match.group()
                password = password_obj.text
                
                if f'{server}' == server_name:
                    return password
        
        return False
