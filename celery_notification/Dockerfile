FROM python:3.8
ADD ./celery_notification/requirements.txt /
ADD ./celery_notification/main.py /
ADD ./celery_notification/ /celery_tasks/
RUN pip3 install -r requirements.txt
ENTRYPOINT celery -A main worker --concurrency=4 --loglevel=info -n notification_worker.%h