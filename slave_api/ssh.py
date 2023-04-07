import requests
from requests.exceptions import ConnectTimeout, ConnectionError
import os

def header():

    header = os.getenv('SLAVE_TOKEN')
    return {
        'token': header,
        'accept': 'application/json'
        }

def create_ssh_account(server_ip, username, password):
    
    data = {
        'username': username,
        'password': password
    }
    try:
        resp = requests.post(url=f'http://{server_ip}:8090/ssh/create', json= data, headers= header(), timeout=10)
        return resp.status_code, resp
    
    except ConnectTimeout:

        return 1419, None
    
    except ConnectionError:

        return 1419, None

def delete_ssh_account(server_ip, username):
    
    data = {
        'username': username
    }
    try:
        resp = requests.delete(url=f'http://{server_ip}:8090/ssh/delete', json= data, headers= header(), timeout=10)
        return resp.status_code, resp
    
    except ConnectTimeout:

        return 1419, None
    
    except ConnectionError:

        return 1419, None


def block_ssh_account(server_ip, username):
    
    data = {
        'username': username
    }
    try:
        resp = requests.post(url=f'http://{server_ip}:8090/ssh/block', json= data, headers= header(), timeout=10)
        return resp.status_code, resp

    except ConnectTimeout:

        return 1419, None
    
    except ConnectionError:

        return 1419, None

def unblock_ssh_account(server_ip, username):
    
    data = {
        'username': username
    }
    try:
        resp = requests.post(url=f'http://{server_ip}:8090/ssh/unblock', json= data, headers= header(), timeout=10)
        return resp.status_code, resp

    except ConnectTimeout:

        return 1419, None
    
    except ConnectionError:

        return 1419, None
