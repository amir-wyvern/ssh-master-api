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


def transfer(from_, to_, value):

    try:
        
        data = {
            'user_id': from_,
            'to_user': to_,
            'value': value
        }
        for _ in range(2):
            resp = requests.post('http://localhost:8050/transfer/request', json= data, headers= header(),timeout=10)
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




