from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException
)
from sqlalchemy.orm.session import Session
from schemas import (
    TokenUser,
    HTTPError,
    UserStatusDb,
    PublishNotification,
    PublishNotificationResponse,
    NotificationStatus
)
from db.database import get_db
from db import db_user

from celery_tasks.tasks import NotificationCeleryTask 
from celery_tasks.utils import create_worker_from

from auth.auth import get_admin_user
import logging

# Create a file handler to save logs to a file
logger = logging.getLogger('notification_router.log') 
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('notification_router.log') 
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


router = APIRouter(prefix='/notif', tags=['Notifications'])

@router.post('/publish', response_model= PublishNotificationResponse, responses={status.HTTP_409_CONFLICT:{'model':HTTPError}})
def new_notif(request: PublishNotification, current_user: TokenUser= Depends(get_admin_user), db: Session=Depends(get_db)):
    
    failed_users = []
    list_chat_id = []
    except_agents = request.except_agents
    
    if request.except_agents is None:
        except_agents = []
    
    if request.accept_agents:
        
        for username in request.accept_agents:
            user = db_user.get_user_by_username(username, db)
            if user and user.status == UserStatusDb.ENABLE and user.chat_id:
                list_chat_id.append(user.chat_id)

            else:
                failed_users.append(username)

        if failed_users:
            raise HTTPException(status_code= status.HTTP_409_CONFLICT, detail= PublishNotificationResponse(status= NotificationStatus.FAILED, failed_users= failed_users))

    else:

        all_users = db_user.get_all_users(db, status= UserStatusDb.ENABLE)

        for user in all_users:
            if user.username not in except_agents:
                if user.chat_id:
                    list_chat_id.append(user.chat_id)
                
                else: 
                    failed_users.append(user.chat_id)

    bot = 'vpn_cluster'
    if request.bot :
        bot = request.bot

    for user_chat_id in list_chat_id:
        parse_mode = None
        if request.parse_mode:
            parse_mode = 'markdown'

        payload = {
            'chat_id': user_chat_id,
            'message': request.message,
            'bot_selector': bot,
            'parse_mode': parse_mode,
            'inline_keyboard': [[['👍 مشاهده کردم', 'notif_click']]]
        }
        notification_worker.apply_async(args=(payload,))


    return PublishNotificationResponse(status= NotificationStatus.SUCCESSFULL, failed_users= failed_users)

