# s3_client.py
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION"),
)
BUCKET = os.getenv("S3_BUCKET")