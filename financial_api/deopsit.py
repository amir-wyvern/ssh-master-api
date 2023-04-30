from requests.exceptions import ConnectTimeout, ConnectionError, ReadTimeout
import requests
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

        resp = requests.post('http://localhost:8050/deposit/request', json=data, headers= header(), timeout=10)
        return resp.status_code, resp

    except ConnectTimeout:

        return 2419, None 
    
    except ConnectionError:

        return 2419, None

    except ReadTimeout:

        return 2419, None

    
def deposit_confirmation(user_id, tx_hash):

    try:
        
        data = {
            'tx_hash': tx_hash,
            'user_id': user_id
        }

        resp = requests.post('http://localhost:8050/deposit/confirmation', json=data, headers= header(), timeout=10)
        return resp.status_code, resp

    except ConnectTimeout:

        return 2419, None
    
    except ConnectionError:

        return 2419, None

    except ReadTimeout:

        return 2419, None


