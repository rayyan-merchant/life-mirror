# src/storage/s3.py
import os
import boto3
from botocore.client import Config

S3_ENDPOINT = os.getenv("S3_ENDPOINT")  # e.g., http://minio:9000
S3_BUCKET = os.getenv("S3_BUCKET")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_REGION = os.getenv("S3_REGION", "us-east-1")

_client = None

def _client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT or None,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4", region_name=S3_REGION),
        )
    return _client

def upload_file(local_path: str, key: str, content_type: str = None) -> str:
    """
    Uploads a file from local_path to S3 bucket under `key`.
    Returns a presigned GET url.
    """
    client = _client()
    extra_args = {}
    if content_type:
        extra_args["ContentType"] = content_type
    client.upload_file(local_path, S3_BUCKET, key, ExtraArgs=extra_args or None)
    # generate presigned GET URL
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=60 * 60 * 24  # 24 hours by default, change if desired
    )
    return url

def get_presigned_put_url(key: str, content_type: str, expires_in: int = 3600) -> str:
    client = _client()
    return client.generate_presigned_url(
        'put_object',
        Params={'Bucket': S3_BUCKET, 'Key': key, 'ContentType': content_type},
        ExpiresIn=expires_in
    )
