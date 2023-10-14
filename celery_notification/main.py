import sys

sys.path.append('../')

from telegram import InlineKeyboardButton, Bot, KeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from celery_tasks.tasks import NotificationCeleryTask 
from celery_tasks.utils import create_worker_from

from dotenv import load_dotenv
import logging
import os

load_dotenv('.env')

logger = logging.getLogger('notification_service.log')
logger.setLevel(logging.INFO)

# Create a file handler to save logs to a file 
file_handler = logging.FileHandler('notification_service.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


vpn_cluster_bot_token = os.getenv('VPN_CLUSTER_BOT_TOKEN')
vpn_cluster_bot = Bot(token= vpn_cluster_bot_token)

admin_log_bot_token = os.getenv('ADMIN_LOG_BOT_TOKEN')
admin_log_bot = Bot(token= admin_log_bot_token)

ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

chat_id_dic = {
    'admin': ADMIN_CHAT_ID
}

bot_selector_dic = {
    'vpn_cluster': vpn_cluster_bot,
    'admin_log': admin_log_bot
}


class NotificationCeleryTaskImpl(NotificationCeleryTask):

    def run(self, payload):
        
        logger.info(f'payload: {payload}')

        bot_selector = payload["bot_selector"]

        chat_id = payload["chat_id"]

        if chat_id in chat_id_dic:
            chat_id = chat_id_dic[chat_id]

        message = payload["message"]

        keyboards = None
        parse_mode= None

        if 'parse_mode' in payload and payload["parse_mode"] in ['html', 'markdown']:
            parse_mode = payload["parse_mode"]

        if 'inline_keyboard' in payload and payload['inline_keyboard']:
            
            inlines= [] 
            for line in payload['inline_keyboard']:
                tmp = []
                for col in line:
                    tmp.append(InlineKeyboardButton(text=col[0], callback_data=col[1]))

                inlines.append(tmp)

            keyboards = InlineKeyboardMarkup(inlines)

        elif 'button_keyboard' in payload and payload['button_keyboard']:
            inlines = []
            for line in payload['button_keyboard']:
                tmp = []
                for col in line:
                    tmp.append(KeyboardButton(text=col))

                inlines.append(tmp)     

            keyboards = ReplyKeyboardMarkup(inlines)


        if bot_selector in bot_selector_dic:

            try:
                bot_selector_dic[bot_selector].send_message(chat_id= chat_id, text= message[:1000] ,reply_markup= keyboards, parse_mode= parse_mode )
            
            except Exception as e:
                logger.error(f'[send notif] error (chat_id: {chat_id} -message: {message} -error: {e})')


# create celery app
app, _ = create_worker_from(NotificationCeleryTaskImpl)


# start worker
if __name__ == '__main__':
    
    app.worker_main()

