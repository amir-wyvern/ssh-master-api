import requests
from requests.exceptions import ConnectTimeout, ConnectionError
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
        resp = requests.post('http://localhost:8050/user/register', json= data, headers=header(), timeout=10)
        return resp.status_code, resp

    except ConnectTimeout:

        return 1419, None
    
    except ConnectionError:

        return 1419, None


def get_balance(user_id):

    try:
        resp = requests.get('http://localhost:8050/user/balance', params={'user_id': user_id}, headers=header(), timeout=10)
        return resp.status_code, resp
    
    except ConnectTimeout:

        return 1419, None

    except ConnectionError:

        return 1419, None
