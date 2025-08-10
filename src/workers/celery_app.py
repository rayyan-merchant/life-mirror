from celery import Celery
import os

BROKER_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
celery = Celery('lifemirror', broker=BROKER_URL)
celery.conf.task_routes = {'src.workers.tasks.*': {'queue': 'media'}}
