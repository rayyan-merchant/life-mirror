import os
import boto3
from botocore.client import Config

S3_ENDPOINT = os.getenv('S3_ENDPOINT')  # leave blank for AWS
S3_BUCKET = os.getenv('S3_BUCKET')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

_session = None

def _client():
    global _session
    if _session is None:
        _session = boto3.client(
            's3',
            endpoint_url=S3_ENDPOINT or None,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4')
        )
    return _session


def get_presigned_put_url(key: str, content_type: str, expires_in: int = 3600) -> str:
    client = _client()
    return client.generate_presigned_url(
        'put_object',
        Params={'Bucket': S3_BUCKET, 'Key': key, 'ContentType': content_type},
        ExpiresIn=expires_in
    )
