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

        response1 = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": (
                                "Please extract the text from the attached screenshot with high accuracy, ensuring "
                                "that all punctuation, capitalization, and formatting are preserved as closely as possible. "
                                "The goal is to capture the full text exactly as it appears in the image, without any "
                                "additional characters or missing content. Pay attention to any special characters, italics, "
                                "or unusual spacing to ensure the extracted text matches the original formatting."
                            ),
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

        # Extracted text cleanup: Remove line return characters (\n)
        extracted_text = response1.choices[0].message.content.replace("\n", "") if response1 and response1.choices else None
        if not extracted_text:
            raise ValueError("Failed to extract text from the image")
        print("Extracted text:\n" + extracted_text)

        response2 = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "You are an experienced tutor who teaches middle school kids."
                                "The following text is from a book. Explain it in a simple, engaging, and supportive way."
                                "Make the explanation suitable for neurodivergent students. Use short, clear sentences."
                                "Keep the response under 80 words. Here is the text: " + extracted_text
                            ),
                        },
                    ],
                }
            ],
            temperature=0.7,
            max_tokens=500,
        )

        # Ensure that response2 is valid and contains choices
        explanation_text = response2.choices[0].message.content if response2 and response2.choices else None
        if not explanation_text:
            explanation_text = "Please keep the camera at least 6 inches above the text."
            raise ValueError("Failed to generate an explanation")
        print("\nExplanation text:\n" + explanation_text)
        
        response3 = client.images.generate(
            model="dall-e-3",
            prompt=(
                "Create a detailed and expressive image based on the following excerpt from a book: \n"
                + explanation_text +
                "\nDepict the main character's emotions of confusion and deep thought, capturing their internal struggle. "
                "The scene should feel grounded in reality, with soft lighting and a tranquil, serene atmosphere. "
                "Use subtle, muted colors to convey calmness but include some visual contrast to highlight the character's feelings. "
                "The background can be a peaceful setting, such as a quiet room with natural light filtering through a window or an open landscape. "
                "Pay attention to the character's facial expressions, body language, and surrounding elements to emphasize their thoughtful state."
            ),
            size="1024x1024",
            style="vivid"
        )

        # Ensure that response3 contains image data
        image_url = response3.data[0].url if response3 and response3.data else None
        if not image_url:
            image_url = "/no_image.jpg"
            raise ValueError("Failed to generate the illustrative image")

        # Return the response from OpenAI
        return {
            "text":  explanation_text,
            "image_url": image_url
        }

    except Exception as e:
        print(f"Error processing image or calling OpenAI: {e}")
        raise e
