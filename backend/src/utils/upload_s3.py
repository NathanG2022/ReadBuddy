from fastapi import FastAPI, UploadFile
import boto3
from botocore.exceptions import NoCredentialsError
import os
import base64
from dotenv import load_dotenv
from openai import OpenAI

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
    

# Function to encode image file to base64 directly from file object
async def encode_image_to_base64(file: UploadFile):
    # Read the file content asynchronously
    file_content = await file.read()

    # Encode the image in base64
    base64_image = base64.b64encode(file_content).decode('utf-8')

    # Convert to a data URL format (assuming PNG, modify if other formats are possible)
    base64_img_str = f"data:image/png;base64,{base64_image}"

    return base64_img_str


# Function to process image and call OpenAI API
async def process_image(file: UploadFile):
    try:
        # Convert the uploaded image file to base64
        base64_img = await encode_image_to_base64(file)

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Create a chat completion request with the base64-encoded image
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Please extract the text from the image attached"
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": base64_img}  # Pass base64-encoded image to OpenAI API
                        }
                    ],
                }
            ],
            temperature=0,
            max_tokens=500,
        )

        # Return the response from OpenAI
        return response.choices[0].message.content

    except Exception as e:
        print(f"Error processing image or calling OpenAI: {e}")
        raise e
