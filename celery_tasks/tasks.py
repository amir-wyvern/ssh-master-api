import celery


class NotificationCeleryTask(celery.Task):
    name = 'notifiaction_celery_task'

    def run(self, payload):
        """
        place holder method
        """
        pass

class ReplaceServerCeleryTask(celery.Task):
    name = 'replace_server_celery_task'

    def run(self, payload):
        """
        place holder method
        """
        pass
