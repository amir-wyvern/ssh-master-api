from requests.exceptions import ConnectTimeout, ConnectionError, ReadTimeout
from fastapi import HTTPException, status
import requests
import os

def header():

    header = os.getenv('FINANCIAL_TOKEN')
    return {
        'token': header,
        'accept': 'application/json'
        }


def create_user_if_not_exist(user_id):

    try:
        data = {
            'user_id': user_id
        }

        for _ in range(2):
            resp = requests.post('http://localhost:8050/user/register', json= data, headers=header(), timeout=10)
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


def get_balance(user_id):

    try:
        for _ in range(2):
            resp = requests.get('http://localhost:8050/user/balance', params={'user_id': user_id}, headers=header(), timeout=10)
            if resp.status_code == 200:
                break
            
        if resp.status_code != 200:
            return None, HTTPException(status_code=resp.status_code, detail= resp.content.decode())

        return resp.json(), None

    except ConnectTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Timeout', 'internal_code': 2419})
    
    except ConnectionError:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ConnectionError', 'internal_code': 2419})

    except ReadTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ReadTimeout', 'internal_code': 2419})


def set_balance(user_id, new_balance):
    
    try:
        data = {
            'user_id': user_id,
            'balance': new_balance
        }
        for _ in range(2):
            resp = requests.post('http://localhost:8050/user/balance', json=data, headers=header(), timeout=10)
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

