#!/bin/bash
# master
tmux new-session -d -s master
tmux split-window -v -t master
tmux split-window -v -t master
tmux send-keys -t master:0.0 'cd /root/ssh-master-api;source venv/bin/activate;uvicorn main:app --host 0.0.0.0 --port 80' Enter
tmux send-keys -t master:0.1 'cd /root/ssh-master-api;source venv/bin/activate;python extensions/check_service_time/check_expire.py' Enter
tmux send-keys -t master:0.2 'cd /root/ssh-master-api;source venv/bin/activate;celery -A celery_notification.main worker --concurrency=4 --loglevel=info -n notification_worker.%h' Enter

# financial
tmux new-session -d -s financial
tmux split-window -v -t financial
tmux send-keys -t financial:0.0 'cd /root/financial-vpn-api;source venv/bin/activate;uvicorn main:app --port 8050' Enter
tmux send-keys -t financial:0.1 'cd /root/financial-vpn-api;source venv/bin/activate;celery -A celery_transfer.main worker --concurrency=4 --loglevel=info -n transfer_worker.%h' Enter

# telegram
tmux new-session -d -s telegram
tmux send-keys -t telegram 'cd /root/telegram-client-vpn;source venv/bin/activate;python main.py' Enter

# slave 
tmux new-session -d -s slave
tmux send-keys -t slave 'cd /root/ssh-slave-api;source venv/bin/activate;uvicorn main:app --host 0.0.0.0 --port 8090' Enter

