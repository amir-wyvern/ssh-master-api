from requests.exceptions import ConnectTimeout, ConnectionError, ReadTimeout
from fastapi import HTTPException, status
import requests
import os

def header():

    header = os.getenv('SLAVE_TOKEN')
    return {
        'token': header,
        'accept': 'application/json'
        }

def create_ssh_account(server_ip, username, password):
    
    data = { 'users': [{
        'username': username,
        'password': password
    }]}
    try:
        for _ in range(2):
            resp = requests.post(url=f'http://{server_ip}:8090/ssh/create', json= data, headers= header(), timeout=20)
            if resp.status_code == 200:
                break

        if resp.status_code != 200:
            return None, HTTPException(status_code=resp.status_code ,detail= resp.content)
        
        return resp.json(), None
    
    except ConnectTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Timeout', 'internal_code': 2419})
    
    except ConnectionError:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ConnectionError', 'internal_code': 2419})

    except ReadTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ReadTimeout', 'internal_code': 2419})


def create_ssh_account_via_group(server_ip, users: list):
    
    try:

        for _ in range(2):
            resp = requests.post(url=f'http://{server_ip}:8090/ssh/create', json= { 'users': users}, headers= header(), timeout=20)
            if resp.status_code == 200:
                break

        if resp.status_code != 200:
            return None, HTTPException(status_code=resp.status_code ,detail= resp.content)
        
        return resp.json(), None
    
    except ConnectTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Timeout', 'internal_code': 2419})
    
    except ConnectionError:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ConnectionError', 'internal_code': 2419})

    except ReadTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ReadTimeout', 'internal_code': 2419})


def delete_ssh_account(server_ip, username):
    
    data = { 'users':[username]}
    try:
        for _ in range(2):
            resp = requests.delete(url=f'http://{server_ip}:8090/ssh/delete', json= data, headers= header(), timeout=20)
            if resp.status_code == 200:
                break

        if resp.status_code != 200:
            return None, HTTPException(status_code=resp.status_code ,detail= resp.content)
        
        return resp.json(), None
    
    except ConnectTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Timeout', 'internal_code': 2419})
    
    except ConnectionError:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ConnectionError', 'internal_code': 2419})

    except ReadTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ReadTimeout', 'internal_code': 2419})


def delete_ssh_account_via_group(server_ip, users):
    
    try:
        for _ in range(2):
            resp = requests.delete(url=f'http://{server_ip}:8090/ssh/delete', json= {'users': users}, headers= header(), timeout=20)
            if resp.status_code == 200:
                break

        if resp.status_code != 200:
            return None, HTTPException(status_code=resp.status_code ,detail= resp.content)
        
        return resp.json(), None
    
    except ConnectTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Timeout', 'internal_code': 2419})
    
    except ConnectionError:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ConnectionError', 'internal_code': 2419})

    except ReadTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ReadTimeout', 'internal_code': 2419})


def block_ssh_account(server_ip, username):
    
    data = {'users':[username]}
    try:
        for _ in range(2):
            resp = requests.post(url=f'http://{server_ip}:8090/ssh/block', json= data, headers= header(), timeout=20)
            if resp.status_code == 200:
                break

        if resp.status_code != 200:
            return None, HTTPException(status_code=resp.status_code ,detail= resp.content)
        
        return resp.json(), None

    except ConnectTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Timeout', 'internal_code': 2419})
    
    except ConnectionError:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ConnectionError', 'internal_code': 2419})

    except ReadTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ReadTimeout', 'internal_code': 2419})


def block_ssh_account_via_groups(server_ip, users):
    
    try:
        for _ in range(2):
            resp = requests.post(url=f'http://{server_ip}:8090/ssh/block', json= {'users': users}, headers= header(), timeout=20)
            if resp.status_code == 200:
                break
        
        if resp.status_code != 200:
            return None, HTTPException(status_code=resp.status_code ,detail= resp.content)
        
        return resp.json(), None

    except ConnectTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Timeout', 'internal_code': 2419})
    
    except ConnectionError:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ConnectionError', 'internal_code': 2419})

    except ReadTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ReadTimeout', 'internal_code': 2419})


def unblock_ssh_account(server_ip, username):
    
    data = {'users':[username]}
    
    try:
        for _ in range(2):
            resp = requests.post(url=f'http://{server_ip}:8090/ssh/unblock', json= data, headers= header(), timeout=20)
            if resp.status_code == 200:
                break

        if resp.status_code != 200:
            return None, HTTPException(status_code=resp.status_code ,detail= resp.content)
        
        return resp.json(), None

    except ConnectTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Timeout', 'internal_code': 2419})
    
    except ConnectionError:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ConnectionError', 'internal_code': 2419})

    except ReadTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ReadTimeout', 'internal_code': 2419})


def unblock_ssh_account_via_groups(server_ip, users):
    
    try:
        for _ in range(2):
            resp = requests.post(url=f'http://{server_ip}:8090/ssh/unblock', json= {'users':users}, headers= header(), timeout=20)
            if resp.status_code == 200:
                break

        if resp.status_code != 200:
            return None, HTTPException(status_code=resp.status_code ,detail= resp.content)
        
        return resp.json(), None
    
    except ConnectTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Timeout', 'internal_code': 2419})
    
    except ConnectionError:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ConnectionError', 'internal_code': 2419})

    except ReadTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ReadTimeout', 'internal_code': 2419})

