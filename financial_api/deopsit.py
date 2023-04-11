import requests
from requests.exceptions import ConnectTimeout, ConnectionError
import os

def header():

    header = os.getenv('FINANCIAL_TOKEN')
    return {
        'token': header,
        'accept': 'application/json'
        }


def deposit_request(user_id, value):

    try:
        
        data = {
            'user_id': user_id,
            'value': value
        }

        resp = requests.post('http://localhost:8050/depoist/request', json=data, timeout=10)
        return resp.status_code, resp

    except ConnectTimeout:

        return 1419, None 
    
    except ConnectionError:

        return 1419, None
    
def deposit_confirmation(user_id, tx_hash):

    try:
        
        data = {
            'tx_hash': tx_hash,
            'user_id': user_id
        }

        resp = requests.post('http://localhost:8050/depoist/confirmation', json=data, timeout=10)
        return resp.status_code, resp

    except ConnectTimeout:

        return 1419, None
    
    except ConnectionError:

        return 1419, None



