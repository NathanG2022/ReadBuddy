from fastapi import FastAPI, UploadFile
import boto3
from botocore.exceptions import NoCredentialsError
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()  # This will load the .env file and make the variables available to os.getenv

# AWS S3 Configuration
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")  # Make sure the .env file has the right key names
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
S3_BUCKET = 'scanimage'
S3_REGION = 'us-east-2'  # Example region

# Initialize the S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=S3_REGION
)

# Upload image to S3 bucket
def upload_to_s3(file_obj, file_name):
    bucket_name = S3_BUCKET
    try:
        s3.upload_fileobj(file_obj, bucket_name, file_name)
        file_url = f"https://{bucket_name}.s3.{S3_REGION}.amazonaws.com/{file_name}"
        return {"file_url": file_url}
    except NoCredentialsError:
        return {"error": "AWS credentials not available"}
