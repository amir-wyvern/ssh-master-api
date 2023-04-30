import celery


class NotificationCeleryTask(celery.Task):
    name = 'notifiaction_celery_task'

    def run(self, payload):
        """
        place holder method
        """
        pass
