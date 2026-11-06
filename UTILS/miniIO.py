import os
import boto3
from botocore.client import Config
from minio import Minio

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", f"http://{MINIO_ENDPOINT}")
AWS_ACCESS_KEY_ID = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
AWS_SECRET_ACCESS_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET_NAME = os.getenv("BUCKET_NAME", "files")

client = Minio(
    endpoint=MINIO_ENDPOINT.replace("http://", "").replace("https://", ""),
    access_key=AWS_ACCESS_KEY_ID,
    secret_key=AWS_SECRET_ACCESS_KEY,
    secure=False,
)

s3_client = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT_URL,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)
