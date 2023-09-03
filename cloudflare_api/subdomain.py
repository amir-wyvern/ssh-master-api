from requests.exceptions import ConnectTimeout, ConnectionError, ReadTimeout
from fastapi import HTTPException, status
import requests
import os


def header():

    token = os.getenv('CLOUDFLARE_TOKEN')
    header = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
        }
    
    return header


def new_subdomain(server_ip, sub_domain):
    
    zone_id = os.getenv('CLOUDFLARE_ZONE_ID')

    data = {
        'content': server_ip,
        'name': sub_domain,
        'proxied': False,
        'type': 'A',
        'comment': '',
        'tags': [],
        'ttl': 3600
    }

    url = f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records'

    try:
        for _ in range(2):
            resp = requests.post(url= url, json= data, headers= header())
            if resp.status_code == 200:
                break

        if resp.status_code != 200:
            return None, HTTPException(status_code=resp.status_code ,detail= resp.json())
        
        return resp.json(), None

    except ConnectTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Timeout', 'internal_code': 2419})
    
    except ConnectionError:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ConnectionError', 'internal_code': 2419})

    except ReadTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ReadTimeout', 'internal_code': 2419})


def update_subdomain(identifier, server_ip, new_sub_name):

    zone_id = os.getenv('CLOUDFLARE_ZONE_ID')

    data = {
        'content': server_ip,
        'name': f'{new_sub_name}.abc-cluster.online',
        'proxied': False,
        'type': 'A',
        'comment': '',
        'tags': [],
        'ttl': 3600
    }
    
    url = f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{identifier}'

    try:
        for _ in range(2):
            resp = requests.put(url= url, json= data, headers= header())
            if resp.status_code == 200:
                break

        if resp.status_code != 200:
            return None, HTTPException(status_code=resp.status_code ,detail= resp.json())
        

        return resp.json(), None

    except ConnectTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'Connection Timeout', 'internal_code': 2419})
    
    except ConnectionError:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ConnectionError', 'internal_code': 2419})

    except ReadTimeout:

        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ReadTimeout', 'internal_code': 2419})

    except Exception as e:
        return None, HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail={'message': 'ReadTimeout', 'internal_code': 2419})
