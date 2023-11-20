#!/bin/bash

# master
tmux new-session -d -s master
tmux split-window -v -t master
tmux split-window -v -t master

if [ -d "/root/ssh-master-api/venv" ]; then
    tmux send-keys -t master:0.0 'cd /root/ssh-master-api;source venv/bin/activate;uvicorn main:app --host 0.0.0.0 --port 80' Enter
else
    tmux send-keys -t master:0.0 'cd /root/ssh-master-api;python -m venv /root/ssh-master-api/venv;source venv/bin/activate;pip install -r requirements.txt;uvicorn main:app --host 0.0.0.0 --port 80' Enter
fi

tmux send-keys -t master:0.1 'cd /root/ssh-master-api;source venv/bin/activate;python schedule_service/check_expire.py' Enter


# notif
tmux new-session -d -s notif
tmux send-keys -t notif 'cd /root/ssh-master-api;source venv/bin/activate;celery -A celery_notification.main worker --concurrency=4 --loglevel=info -n notification_worker.%h' Enter


# backup
tmux send-keys -t master:0.1 'cd /root/ssh-master-api;source venv/bin/activate;python backup_service/main.py' Enter


# financial
tmux new-session -d -s financial
tmux split-window -v -t financial
if [ -d "/root/financial-vpn-api/venv" ]; then
    tmux send-keys -t financial:0.0 'cd /root/financial-vpn-api;source venv/bin/activate;uvicorn main:app --port 8050' Enter
else
    tmux send-keys -t financial:0.0 'cd /root/financial-vpn-api;python -m venv /root/financial-vpn-api/venv;source venv/bin/activate;pip install -r requirements.txt;uvicorn main:app --port 8050' Enter
fi
tmux send-keys -t financial:0.0 'cd /root/financial-vpn-api;source venv/bin/activate;uvicorn main:app --port 8050' Enter
tmux send-keys -t financial:0.1 'cd /root/financial-vpn-api;source venv/bin/activate;celery -A celery_transfer.main worker --concurrency=4 --loglevel=info -n transfer_worker.%h' Enter


# telegram
tmux new-session -d -s telegram
if [ -d "/root/financial-vpn-api/venv" ]; then
    tmux send-keys -t telegram 'cd /root/telegram-client-vpn;source venv/bin/activate;python main.py' Enter
else
    tmux send-keys -t telegram 'cd /root/telegram-client-vpn;python -m venv /root/financial-vpn-api/venv;pip install -r requirements.txt;python main.py' Enter
fi


# slave 
# tmux new-session -d -s slave
# if [ -d "/root/ssh-slave-api/venv" ]; then
#     tmux send-keys -t slave 'cd /root/ssh-slave-api;source venv/bin/activate;uvicorn main:app --host 0.0.0.0 --port 8090' Enter
# else
#     tmux send-keys -t slave 'cd /root/ssh-slave-api;python -m venv /root/ssh-slave-api/venv;source venv/bin/activate;pip install -r requirements.txt;uvicorn main:app --host 0.0.0.0 --port 8090' Enter
# fi

# check-servers
# tmux new-session -d -s check-servers
# tmux split-window -v -t check-servers
# -- tmux send-keys -t check-servers:0.0 'cd /root/ssh-master-api;source venv/bin/activate;celery -A celery_server.main worker --concurrency=4 --loglevel=info -n server_service_worker.%h' Enter
# tmux send-keys -t check-servers:0.1 'cd /root/ssh-master-api;source venv/bin/activate;python schedule_service/server_check/main.py' Enter
