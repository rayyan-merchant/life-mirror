import os
import boto3
from botocore.client import Config
from typing import Optional

S3_ENDPOINT = os.getenv('S3_ENDPOINT')  # e.g. "http://minio:9000" or None for AWS
S3_BUCKET = os.getenv('S3_BUCKET')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

_client = None

def _client():
    global _client
    if _client is None:
        # If endpoint is not set, boto3 uses AWS defaults
        _client = boto3.client(
            's3',
            endpoint_url=S3_ENDPOINT or None,
            aws_access_key_id=AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY or None,
            config=Config(signature_version='s3v4')
        )
    return _client

def upload_bytes(data: bytes, key: str, content_type: str = 'application/octet-stream', bucket: Optional[str] = None) -> None:
    """
    Upload raw bytes to S3/MinIO under `key`. Does not return URL (use presigned getter).
    """
    client = _client()
    b = bucket or S3_BUCKET
    if not b:
        raise RuntimeError("S3_BUCKET not configured")
    client.put_object(Bucket=b, Key=key, Body=data, ContentType=content_type)

def get_presigned_get_url(key: str, expires_in: int = 3600, bucket: Optional[str] = None) -> str:
    """
    Generate a presigned GET URL for a stored object.
    """
    client = _client()
    b = bucket or S3_BUCKET
    if not b:
        raise RuntimeError("S3_BUCKET not configured")
    url = client.generate_presigned_url(
        'get_object',
        Params={'Bucket': b, 'Key': key},
        ExpiresIn=expires_in
    )
    return url
