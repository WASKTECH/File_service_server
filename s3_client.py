# s3_client.py
"""
AWS S3 client initialization.

Creates a shared boto3 S3 client and reads the target bucket name
from environment variables. All modules that interact with S3 should
import `s3` and `BUCKET` from this module.

Required environment variables:
    AWS_REGION:            AWS region (e.g. "us-east-1").
    S3_BUCKET:             Target S3 bucket name.
    AWS_ACCESS_KEY_ID:     AWS IAM access key (read by boto3 automatically).
    AWS_SECRET_ACCESS_KEY: AWS IAM secret key (read by boto3 automatically).
"""

import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION"),
)

BUCKET = os.getenv("S3_BUCKET")
if not BUCKET:
    raise RuntimeError(
        "S3_BUCKET environment variable is not set. "
        "Please configure it in your .env file."
    )