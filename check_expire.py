from db import db_ssh_service, db_server
from db.database import get_db
from datetime import datetime, timedelta
from celery_tasks.tasks import NotificationCeleryTask
from celery_tasks.utils import create_worker_from
from cache.database import get_redis_cache
from cache.cache_session import get_check_label, set_check_label
from slave_api.ssh import block_ssh_account, delete_ssh_account
from schemas import ServiceStatus
from time import sleep
import pytz

import logging

logger = logging.getLogger()
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

cache_db = get_redis_cache().__next__()

_, notification_worker = create_worker_from(NotificationCeleryTask)

timedelta_2 = timedelta(days=2)
timedelta_1 = timedelta(days=1)

while True:
    
    try:
        db = get_db().__next__()

        enable_services = db_ssh_service.get_all_services(db, status= ServiceStatus.ENABLE)
        disable_services = db_ssh_service.get_all_services(db, status= ServiceStatus.DISABLE)

        for service in enable_services:

            time_now = datetime.now().replace(tzinfo=pytz.utc)
            service_expire = service.expire.replace(tzinfo=pytz.utc)

            if service.status == ServiceStatus.ENABLE and not get_check_label(service.service_id, cache_db) and service_expire - time_now  < timedelta_2:
        
                # if user.tel_id is not None:

                #     agent = db_agent.get_agent_by_user_id(service.agent_id, db)

                    # payload = {
                    #     'tel_id': user.tel_id,
                    #     'bot_token': agent.bot_token,
                    #     'message': 'تنها ۲ روز تا پایان سروریس شما باقی مونده\nدر صورت تمایل میتونید سرویس خود را تمدید کنید',
                    #     'inline_keyboard': None,
                    #     'button_keyboard': None,
                    # }
                    # notification_worker.apply_async(args=(payload,))

                set_check_label(service.service_id, cache_db)

            if service.status == ServiceStatus.ENABLE and not get_check_label(service.service_id, cache_db) and service_expire - time_now < timedelta_1:

                # if user.tel_id is not None:

                #     agent = db_agent.get_agent_by_user_id(service.agent_id, db)

                    # payload = {
                    #     'tel_id': user.tel_id,
                    #     'bot_token': agent.bot_token,
                    #     'message': 'تنها ۲ روز تا پایان سروریس شما باقی مونده\nدر صورت تمایل میتونید سرویس خود را تمدید کنید',
                    #     'inline_keyboard': None,
                    #     'button_keyboard': None,
                    # }
                    # notification_worker.apply_async(args=(payload,))
                    
                set_check_label(service.service_id, cache_db)

            if service.status == ServiceStatus.ENABLE and time_now > service_expire :

                _ , err = block_ssh_account(service.server_ip, service.username)
                if err:
                    logger.error(f'[expire] failed account blocking [server: {service.server_ip} -username: {service.username} -resp_code: {err.status_code} -detail: {resp.detail}]')
                    continue
            
                db_ssh_service.change_status(service.service_id, ServiceStatus.DISABLE, db)
                logger.info(f'[expire] successfully account blocked  [server: {service.server_ip} -username: {service.username}]')

                # if user.tel_id is not None:

                #     agent = db_agent.get_agent_by_user_id(service.agent_id, db)

                    # payload = {
                    #     'tel_id': user.tel_id,
                    #     'bot_token': agent.bot_token,
                    #     'message': 'تنها ۲ روز تا پایان سروریس شما باقی مونده\nدر صورت تمایل میتونید سرویس خود را تمدید کنید',
                    #     'inline_keyboard': None,
                    #     'button_keyboard': None,
                    # }
                    # notification_worker.apply_async(args=(payload,))

        for service in disable_services:

            time_now = datetime.now().replace(tzinfo=pytz.utc)
            service_expire = service.expire.replace(tzinfo=pytz.utc)
        
            if service.status == ServiceStatus.DISABLE and time_now - service_expire > timedelta(days=7):

                resp ,err = delete_ssh_account(service.server_ip, service.username)
                if err:
                    logger.error(f'[delete] failed account deleted (server: {service.server_ip} -username: {service.username} -resp_code: {err.status_code} -detail: {err.detail})')
                    continue
                    
                try:
                    db.begin()
                    db_server.decrease_ssh_accounts_number(service.server_ip, db, commit= False) 
                    db_ssh_service.change_status(service.service_id, ServiceStatus.DELETED, db, commit= False)
                    db.commit()

                except Exception as e:
                    logger.error(f'[delete] error in database (username: {service.username} -error: {e})')
                    db.rollback()
                    continue                    

                logger.info(f'[delete] successfully account deleted [server: {service.server_ip} -username: {service.username}]')

    except Exception as e:
        logger.error(f'[exception]  [{e}]')
    
    sleep(300)
