import os
import boto3
from datetime import datetime
from urllib.parse import urlparse

AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "auto")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET", "lifemirror-media")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
UPLOAD_EXPIRE = int(os.getenv("S3_UPLOAD_EXPIRE", "3600"))
DOWNLOAD_EXPIRE = int(os.getenv("S3_DOWNLOAD_EXPIRE", "3600"))

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    endpoint_url=S3_ENDPOINT_URL
)

def generate_upload_url(key: str, content_type: str):
    return s3_client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": S3_BUCKET,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=UPLOAD_EXPIRE,
    )

def generate_download_url(key: str):
    return s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": S3_BUCKET,
            "Key": key,
        },
        ExpiresIn=DOWNLOAD_EXPIRE,
    )

def object_exists(key: str) -> bool:
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=key)
        return True
    except s3_client.exceptions.ClientError:
        return False

def delete_object(key: str):
    s3_client.delete_object(Bucket=S3_BUCKET, Key=key)

def parse_s3_url(url: str) -> str:
    """Extract S3 key from full storage URL."""
    parsed = urlparse(url)
    return parsed.path.lstrip("/")
