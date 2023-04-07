from requests import ConnectionError, ConnectTimeout
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
        resp = requests.get(url=f'http://{server_ip}:8090/server/users', headers= header(), timeout=10)
        return resp.status_code, resp

    except ConnectTimeout:

        return 1419, None
    
    except ConnectionError:

        return 1419, None
