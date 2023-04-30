from db import db_ssh_service, db_user, db_agent, db_server
from db.database import get_db
from datetime import datetime, timedelta
from celery_tasks.tasks import NotificationCeleryTask
from celery_tasks.utils import create_worker_from
from cache.database import get_redis_cache
from cache.cache_session import get_check_label, set_check_label
from slave_api.ssh import block_ssh_account
from schemas import Status
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

db = get_db().__next__()

timedelta_2 = timedelta(days=2)
timedelta_1 = timedelta(days=1)

while True:
    
    services = db_ssh_service.get_all_service(db, status= Status.ENABLE)

    for service in services:

        time_now = datetime.now().replace(tzinfo=pytz.utc)
        service_expire = service.expire.replace(tzinfo=pytz.utc)

        if not get_check_label(service.user_id, cache_db) and service_expire - time_now  < timedelta_2:
            user = db_user.get_user(service.user_id, db) 

            if user.tel_id is not None:

                agent = db_agent.get_agent_by_user_id(service.agent_id, db)

                # payload = {
                #     'tel_id': user.tel_id,
                #     'bot_token': agent.bot_token,
                #     'message': 'تنها ۲ روز تا پایان سروریس شما باقی مونده\nدر صورت تمایل میتونید سرویس خود را تمدید کنید',
                #     'inline_keyboard': None,
                #     'button_keyboard': None,
                # }
                # notification_worker.apply_async(args=(payload,))

            set_check_label(service.user_id, cache_db)

        if not get_check_label(service.user_id, cache_db) and service_expire - time_now < timedelta_1:
            user = db_user.get_user(service.user_id, db)

            if user.tel_id is not None:

                agent = db_agent.get_agent_by_user_id(service.agent_id, db)

                # payload = {
                #     'tel_id': user.tel_id,
                #     'bot_token': agent.bot_token,
                #     'message': 'تنها ۲ روز تا پایان سروریس شما باقی مونده\nدر صورت تمایل میتونید سرویس خود را تمدید کنید',
                #     'inline_keyboard': None,
                #     'button_keyboard': None,
                # }
                # notification_worker.apply_async(args=(payload,))
                
            set_check_label(service.user_id, cache_db)

        if time_now > service_expire :
            
            user = db_user.get_user(service.user_id, db)

            status_code ,resp = block_ssh_account(service.server_ip, service.username)

            if status_code == 2419 :
                logging.info(f'account block failed [server: {service.server_ip} -username: {service.username} -status_code: {resp.status_code}, -content: {resp.content}]')
                continue

            if status_code != 200:
                logging.info(f'account block failed [server: {service.server_ip} -username: {service.username} -status_code: {resp.status_code}, -content: {resp.content}]')
                continue
            
            db_server.decrease_ssh_accounts_number(service.server_ip, db) 
            db_ssh_service.change_status(service.service_id, Status.DISABLE, db)

            if user.tel_id is not None:

                agent = db_agent.get_agent_by_user_id(service.agent_id, db)

                # payload = {
                #     'tel_id': user.tel_id,
                #     'bot_token': agent.bot_token,
                #     'message': 'تنها ۲ روز تا پایان سروریس شما باقی مونده\nدر صورت تمایل میتونید سرویس خود را تمدید کنید',
                #     'inline_keyboard': None,
                #     'button_keyboard': None,
                # }
                # notification_worker.apply_async(args=(payload,))

    sleep(60)