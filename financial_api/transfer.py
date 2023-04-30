from requests.exceptions import ConnectTimeout, ConnectionError, ReadTimeout
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

        resp = requests.post('http://localhost:8050/transfer/request', json= data, headers= header(),timeout=10)
        
        return resp.status_code, resp

    except ConnectTimeout:

        return 2419, None
    
    except ConnectionError:

        return 2419, None

    except ReadTimeout:

        return 2419, None



