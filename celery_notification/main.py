import sys

sys.path.append('../')

from db.database import get_db

from celery_tasks.tasks import NotificationCeleryTask 
from celery_tasks.utils import create_worker_from
from schemas import DepositHistoryModelForUpdateDataBase

import json
from dotenv import dotenv_values
from datetime import datetime, timedelta
import logging

from telegram import InlineKeyboardButton, Bot, KeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Create a console handler to show logs on terminal
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Create a file handler to save logs to a file
file_handler = logging.FileHandler('notification_service.log')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)



class NotificationCeleryTaskImpl(NotificationCeleryTask):

    def run(self, payload):
        
        logger.debug(f'Receive a task [payload: {payload}]')

        tel_id = payload["tel_id"]
        bot_token = payload["bot_token"]
        message = payload["message"]
        inline_keyboard = payload["inline_keyboard"]
        button_keyboard = payload["button_keyboard"]

        keyboards = None
        if inline_keyboard:
            inlines= []
            for line in inline_keyboard:
                tmp = []
                for col in line:
                    tmp.append(InlineKeyboardButton(text=col[0], callback_data=col[1]))

                inlines.append(tmp)

            keyboards = InlineKeyboardMarkup(inlines)

        elif button_keyboard:
            inlines = []
            for line in button_keyboard:
                tmp = []
                for col in line:
                    tmp.append(KeyboardButton(text=col))

                inlines.append(tmp)     

            keyboards = ReplyKeyboardMarkup(inlines)

        bot = Bot(bot_token)

        bot.send_message(chat_id= tel_id, text= message ,reply_markup= keyboards)


# create celery app
app, deposit_worker = create_worker_from(NotificationCeleryTaskImpl)


# start worker
if __name__ == '__main__':
    
    app.worker_main()

