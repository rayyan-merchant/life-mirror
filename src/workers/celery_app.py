from celery import Celery
import os
from celery.schedules import crontab


BROKER_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
celery = Celery('lifemirror', broker=BROKER_URL)
celery.conf.task_routes = {'src.workers.tasks.*': {'queue': 'media'}}

celery_app.conf.beat_schedule = {
    "check-notifications-every-6-hours": {
        "task": "src.workers.tasks.check_notifications_async",
        "schedule": crontab(minute=0, hour="*/6"),  # every 6 hours
    },
}

