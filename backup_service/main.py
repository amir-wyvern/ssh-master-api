import sys

sys.path.append('../')

from celery_tasks.utils import create_worker_from
from celery_tasks.tasks import NotificationCeleryTask
from dotenv import load_dotenv
from telegram import Bot
from time import sleep
import subprocess
import hashlib
import logging
import os

load_dotenv()

# Create a file handler to save logs to a file
logger = logging.getLogger('backup.log') 
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('backup.log') 
file_handler.setLevel(logging.INFO) 
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s') 
file_handler.setFormatter(formatter) 
logger.addHandler(file_handler) 

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

_, notifocaction_worker = create_worker_from(NotificationCeleryTask)

sql_command = [
    'mysqldump',
    '-u', 'root',
    '--all-databases'
]
sql_backup_file = 'backup.sql'

rdb_path= '/var/lib/redis/dump.rdb'
redis_backup_path= 'backup.rdb'
redis_command = ['cp', rdb_path, redis_backup_path]

if not os.path.exists(redis_backup_path):
    with open(redis_backup_path, 'w') as fi:
        fi.write('')
        
if not os.path.exists(sql_backup_file):
    with open(sql_backup_file, 'w') as fi:
        fi.write('')

backup_bot_token = os.getenv('BACKUP_BOT_TOKEN')
backup_bot = Bot(token= backup_bot_token)

ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')


def calculate_hash(data: str, hash_algorithm="md5", buffer_size=65536):
    raw_data = data.split('-- Dump completed on')[0]
    hasher = hashlib.new(hash_algorithm)
    hasher.update(raw_data.encode())
    return hasher.hexdigest()

def calculate_file_hash(file_path, hash_algorithm="md5", buffer_size=65536):
    hasher = hashlib.new(hash_algorithm)
    with open(file_path, "r") as file:
        while True:
            data = file.read(buffer_size)
            if not data:
                break
            raw_data = data.split('-- Dump completed on')[0]
            hasher.update(raw_data.encode())
    return hasher.hexdigest()

def check_changes(hash_1, hash_2):

    if hash_1 != hash_2:
        return True
    
    return False

logger.info('start ...')

while True:

    try:

        backup = subprocess.run(sql_command, capture_output=True, text= True, check=True)
        
        is_changed = check_changes(calculate_hash(backup.stdout), calculate_file_hash(sql_backup_file))

        if is_changed:
            
            logger.info('Found changing in database')
            
            subprocess.run(['redis-cli', 'save'], check=True)
            subprocess.run(redis_command, check=True)

            with open(sql_backup_file, 'w') as outfile:
                outfile.write(backup.stdout)

            with open(sql_backup_file, 'rb') as sql_outfile , open(redis_backup_path, 'rb') as redis_outfile:

                backup_bot.send_document(chat_id= ADMIN_CHAT_ID, document= sql_outfile)
                backup_bot.send_document(chat_id= ADMIN_CHAT_ID, document= redis_outfile)
                logger.info('Successfully Send the Backup to TelBot')

    except Exception as e:

        payload = {
            'bot_selector': 'admin_log',
            'chat_id': 'admin',
            'message': f'BackUp Error \n\n{e}'
        }
        notifocaction_worker.apply_async(args=(payload,))
        logger.critical(f'error [{e}]')
    
    sleep(30 * 60)

