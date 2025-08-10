from .celery_app import celery
import requests
from uuid import UUID

@celery.task(name='src.workers.tasks.process_media')
def process_media(media_id: str, storage_url: str):
    # download media from object storage (using requests + presigned GET if private)
    # extract thumbnails/keyframes (ffmpeg)
    # enqueue smaller tasks: face detection, embedder, posture, fashion
    # placeholder: write to analyses table when complete
    print('processing', media_id, storage_url)
    # TODO: implement steps for keyframe extraction, calling detector tools, inserting into DB
