from requests import ConnectionError, ConnectTimeout, ReadTimeout
from fastapi import HTTPException, status
import requests
import os

def header():

    header = os.getenv('SLAVE_TOKEN')
    return {
        'token': header,
        'accept': 'application/json'
        }

def get_users(server_ip):

    try:
        for _ in range(2):
            resp = requests.get(url=f'http://{server_ip}:8090/server/users', headers= header(), timeout=10)
            if resp.status_code == 200:
                break

        if resp.status_code != 200:
            return None, HTTPException(status_code=resp.status_code ,detail= resp.content.decode())
        
        return resp.json(), None

    except ConnectTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Timeout', 'internal_code': 2419})
    
    except ConnectionError:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ConnectionError', 'internal_code': 2419})

    except ReadTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ReadTimeout', 'internal_code': 2419})

def active_users(server_ip):

    try:
        for _ in range(2):
            resp = requests.get(url=f'http://{server_ip}:8090/server/activeusers', headers= header(), timeout=10)
            if resp.status_code == 200:
                break

        if resp.status_code != 200:
            return None, HTTPException(status_code=resp.status_code ,detail= resp.content.decode())
        
        return resp.json(), None

    except ConnectTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Timeout', 'internal_code': 2419})
    
    except ConnectionError:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ConnectionError', 'internal_code': 2419})

    except ReadTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ReadTimeout', 'internal_code': 2419})

def init_server(server_ip, ssh_port, manager_password):

    try:
        data = {
            'ssh_port': ssh_port,
            'manager_password': manager_password
        }
        for _ in range(2):
            resp = requests.post(url=f'http://{server_ip}:8090/server/init', json= data, headers= header(), timeout=20)
            if resp.status_code == 200:
                break

        if resp.status_code != 200:
            return None, HTTPException(status_code=resp.status_code ,detail= resp.content.decode())
        
        return resp.json(), None

    except ConnectTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Timeout', 'internal_code': 2419})
    
    except ConnectionError:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ConnectionError', 'internal_code': 2419})

    except ReadTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ReadTimeout', 'internal_code': 2419})

