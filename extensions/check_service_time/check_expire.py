import sys

sys.path.append('/root/ssh-master-api')

from db import db_ssh_service, db_server, db_domain, db_user
from db.models import DbSshService
from db.database import get_db
from datetime import datetime, timedelta
from celery_tasks.tasks import NotificationCeleryTask
from celery_tasks.utils import create_worker_from
from cache.database import get_redis_cache
from cache.cache_session import get_check_label, set_check_label
from slave_api.ssh import block_ssh_account, delete_ssh_account
from schemas import ServiceStatusDb, ConfigType
from time import sleep
import pytz
from typing import List

import logging

logger = logging.getLogger('check_expire.log')
logger.setLevel(logging.INFO)

# Create a file handler to save logs to a file
file_handler = logging.FileHandler('check_expire.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


_, notification_worker = create_worker_from(NotificationCeleryTask)

timedelta_1 = timedelta(days=1)


def check_active_users(active_services: List[DbSshService]):

    for service in active_services:

        time_now = datetime.now().replace(tzinfo=pytz.utc)
        service_expire = service.expire.replace(tzinfo=pytz.utc)

        if not get_check_label(service.service_id, cache_db) and service_expire - time_now < timedelta_1:

            user = db_user.get_user_by_user_id(service.agent_id, db)
            if user.chat_id and service.service_type == ConfigType.MAIN:
                payload = {
                    'chat_id': user.chat_id,
                    'message': f'📩 نام کاربری `{service.username}` فردا منقضی میشه',
                    'bot_selector': 'vpn_cluster',
                    'inline_keyboard': [[['👍 مشاهده کردم', 'notif_click']]],
                    'parse_mode': 'markdown'
                }
                notification_worker.apply_async(args=(payload,))
                
            set_check_label(service.service_id, cache_db)

        if time_now > service_expire :
            
            domain = db_domain.get_domain_by_id(service.domain_id, db)
            _ , err = block_ssh_account(domain.server_ip, service.username)
            if err:
                logger.error(f'[expire] failed account blocking [server: {domain.server_ip} -username: {service.username} -resp_code: {err.status_code} -detail: {err.detail}]')
                continue
        
            db_ssh_service.change_status(service.service_id, ServiceStatusDb.EXPIRED, db)
            logger.info(f'[expire] successfully account blocked  [server: {domain.server_ip} -username: {service.username}]')

            user = db_user.get_user_by_user_id(service.agent_id, db)

            if user.chat_id and service.service_type == ConfigType.MAIN:
                payload = {
                    'chat_id': user.chat_id,
                    'message': f'📩 نام کاربری `{service.username}` منقضی و دسترسیش مسدود شد',
                    'bot_selector': 'vpn_cluster',
                    'inline_keyboard': [[['👍 مشاهده کردم', 'notif_click']]],
                    'parse_mode': 'markdown'
                }
                notification_worker.apply_async(args=(payload,))


def check_expired_users(expired_services: List[DbSshService]):

    for service in expired_services:

        time_now = datetime.now().replace(tzinfo=pytz.utc)
        service_expire = service.expire.replace(tzinfo=pytz.utc)

        day= 2
        if service.agent_id in [1, 3, 10, 11,12,14]:
            day = 7

        if service.service_type == ConfigType.TEST:

            domain = db_domain.get_domain_by_id(service.domain_id, db)

            _ ,err = delete_ssh_account(domain.server_ip, service.username)
            if err:
                logger.error(f'[delete] failed account deleted (server: {domain.server_ip} -username: {service.username} -resp_code: {err.status_code} -detail: {err.detail})')
                continue
                
            try:
                db_server.decrease_ssh_accounts_number(domain.server_ip, db) 
                db_ssh_service.change_status(service.service_id, ServiceStatusDb.DELETED, db)

            except Exception as e:
                logger.error(f'[delete] error in database (username: {service.username} -error: {e})')
                continue                    

            logger.info(f'[delete] successfully account deleted [server: {domain.server_ip} -username: {service.username}]')

        elif time_now - service_expire > timedelta(days= day):
            domain = db_domain.get_domain_by_id(service.domain_id, db)

            _ ,err = delete_ssh_account(domain.server_ip, service.username)
            if err:
                logger.error(f'[delete] failed account deleted (server: {domain.server_ip} -username: {service.username} -resp_code: {err.status_code} -detail: {err.detail})')
                continue
                
            try:
                db_server.decrease_ssh_accounts_number(domain.server_ip, db) 
                db_ssh_service.change_status(service.service_id, ServiceStatusDb.DELETED, db)

            except Exception as e:
                logger.error(f'[delete] error in database (username: {service.username} -error: {e})')
                continue                    

            logger.info(f'[delete] successfully account deleted [server: {domain.server_ip} -username: {service.username}]')

            user = db_user.get_user_by_user_id(service.agent_id, db)
            if user.chat_id:
                payload = {
                    'chat_id': user.chat_id,
                    'message': f'📩 نام کاربری `{service.username}` به  دلیل تمدید نکردن حذف شد',
                    'bot_selector': 'vpn_cluster',
                    'inline_keyboard': [[['👍 مشاهده کردم', 'notif_click']]],
                    'parse_mode': 'markdown'
                }
                notification_worker.apply_async(args=(payload,))



if __name__ == '__main__':

    while True:
        try:
            cache_db = get_redis_cache().__next__()
            db = get_db().__next__()

            enable_services = db_ssh_service.get_all_services(db, status= ServiceStatusDb.ENABLE)
            disable_services = db_ssh_service.get_all_services(db, status= ServiceStatusDb.DISABLE)
            active_services = enable_services + disable_services

            check_active_users(active_services)

            expired_services = db_ssh_service.get_all_services(db, status= ServiceStatusDb.EXPIRED)

            check_expired_users(expired_services)

        except Exception as e:
            logger.error(f'[exception]  [{e}]')
        
        sleep(300)
