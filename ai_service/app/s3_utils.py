import os
import boto3
from botocore.exceptions import ClientError
from io import BytesIO

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET_NAME = "medichat-uploads"

s3_client = boto3.client(
    's3',
    endpoint_url=f"http://{MINIO_ENDPOINT}",
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    region_name='us-east-1'
)

def init_bucket():
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
    except ClientError:
        # Bucket does not exist, create it
        s3_client.create_bucket(Bucket=BUCKET_NAME)
        # Set bucket policy to allow public reads for downloaded files (optional, depends on architecture)
        # We will keep it private and use pre-signed URLs or download via backend

# Initialize bucket on startup
init_bucket()

def upload_file_to_s3(file_data: bytes, object_name: str):
    """Upload a file to an S3 bucket"""
    try:
        s3_client.put_object(Bucket=BUCKET_NAME, Key=object_name, Body=file_data)
        return True
    except ClientError as e:
        print(f"Error uploading to S3: {e}")
        return False

def download_file_from_s3(object_name: str) -> bytes:
    """Download a file from an S3 bucket"""
    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=object_name)
        return response['Body'].read()
    except ClientError as e:
        print(f"Error downloading from S3: {e}")
        return None
