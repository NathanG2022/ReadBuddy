from fastapi import FastAPI, UploadFile
import boto3
from botocore.exceptions import NoCredentialsError
import os
import base64
from dotenv import load_dotenv
from openai import OpenAI
import requests
from PIL import Image
from io import BytesIO
import google.generativeai as genai
# import pytesseract
# import matplotlib.pyplot as plt

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

# Function to download and perform OCR on an image
# def extract_text_from_image_url(image_url):
#     response = requests.get(image_url)
#     image = Image.open(BytesIO(response.content))
#     # Show the image
#     # plt.imshow(image)
#     # plt.axis('off')
#     # plt.show()
#     text = pytesseract.image_to_string(image)
#     print(text)
#     return text.strip()


# Upload image to S3 bucket
def upload_to_s3(file_obj, file_name, content_type="application/octet-stream"):
    bucket_name = S3_BUCKET
    try:
        s3.upload_fileobj(
            file_obj, 
            bucket_name, 
            file_name,
            ExtraArgs={'ContentType': content_type}
        )
        file_url = f"https://{bucket_name}.s3.{S3_REGION}.amazonaws.com/{file_name}"
        # print("DBUG: ", extract_text_from_image_url(file_url))
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

# Function to extract text from an image using Google Gemini 1.5 Pro
async def extract_text_with_gemini(file: UploadFile):
    try:
        # Load the API key from environment variables
        api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Google Gemini API key is missing. Please set it in the .env file.")

        # Configure the Gemini API with the provided API key
        genai.configure(api_key=api_key)

        # Read the uploaded image file content
        file_content = await file.read()

        # Encode the image as base64
        base64_image = base64.b64encode(file_content).decode('utf-8')

        # Initialize the Gemini 1.5 Pro model
        model = genai.GenerativeModel(model_name="gemini-1.5-pro")

        # Prepare the prompt
        prompt = "Extract the text from this image with high accuracy."

        # Send the image and prompt to the Gemini model
        response = model.generate_content(
            [{'mime_type': 'image/jpeg', 'data': base64_image}, prompt]
        )

        # Parse the response to get the extracted text
        extracted_text = response.text
        if not extracted_text:
            raise ValueError("No text extracted from the image.")

        return extracted_text.strip()

    except Exception as e:
        raise ValueError(f"Error with Gemini 1.5 Pro: {e}")

# Function to process image and call OpenAI API
async def process_image(file: UploadFile):
    response_data = {}
    try:
        # Step 1: Extract text using Google Gemini 1.5 Pro
        try:
            extracted_text = await extract_text_with_gemini(file)
            print(f"Extracted Text:\n{extracted_text}")
            response_data["text"] = extracted_text
        except Exception as e:
            print(f"Error extracting text with Gemini: {e}")
            response_data["text"] = None

        # Step 2: Generate explanation using OpenAI GPT
        explanation_text = None
        if response_data.get("text"):
            try:
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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
                explanation_text = response2.choices[0].message.content if response2 and response2.choices else None
                if explanation_text:
                    response_data["explanation_text"] = explanation_text
                else:
                    raise ValueError("Failed to generate explanation text.")
            except Exception as e:
                print(f"Error generating explanation with GPT: {e}")
                response_data["explanation_text"] = None

        # Step 3: Generate image using DALL-E
        resized_image_url = None
        if explanation_text:
            try:
                response3 = client.images.generate(
                    model="dall-e-3",
                    prompt=(
                        "Create a detailed and expressive image based on the following text: \n"
                        + explanation_text +
                        "\nThe scene should feel grounded in reality, with soft lighting and a tranquil, serene atmosphere. "
                        "Use subtle, muted colors to convey calmness but include some visual contrast to highlight the emotions. "
                    ),
                    size="1024x1024",
                    style="vivid"
                )

                # Download and resize the generated image
                image_url = response3.data[0].url
                response = requests.get(image_url)
                image = Image.open(BytesIO(response.content))

                # Resize the image to 256x256
                resized_image = image.resize((240, 240))

                # Save resized image to S3
                resized_image_io = BytesIO()
                resized_image.save(resized_image_io, format="bmp")
                resized_image_io.seek(0)

                # Upload to S3
                s3_file_name = "resized_image_240x240.bmp"
                s3_response = upload_to_s3(resized_image_io, s3_file_name, content_type="image/bmp")
                resized_image_url = s3_response.get("file_url", None)
                response_data["image_url"] = resized_image_url
            except Exception as e:
                print(f"Error generating or resizing image with DALL-E: {e}")
                response_data["image_url"] = None

        # Step 4: Generate MP3 using Amazon Polly
        mp3_url = None
        if explanation_text:
            try:
                polly_client = boto3.client(
                    "polly",
                    aws_access_key_id=AWS_ACCESS_KEY,
                    aws_secret_access_key=AWS_SECRET_KEY,
                    region_name=S3_REGION,
                )
                polly_response = polly_client.synthesize_speech(
                    Text=explanation_text,
                    OutputFormat="mp3",
                    VoiceId="Joanna",
                )

                # Save the MP3 to a BytesIO object
                mp3_io = BytesIO(polly_response["AudioStream"].read())

                # Upload to S3
                mp3_filename = "explanation_audio.mp3"
                s3_audio_response = upload_to_s3(mp3_io, mp3_filename, content_type="audio/mpeg")
                mp3_url = s3_audio_response.get("file_url", None)
                response_data["mp3_url"] = mp3_url
            except Exception as e:
                print(f"Error generating MP3 with Amazon Polly: {e}")
                response_data["mp3_url"] = None

        return response_data

    except Exception as e:
        print(f"Unexpected error: {e}")
        raise e

# Function to process image from URL
async def process_image_from_url(image_url: str):
    try:
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
                                # "Can you please explain the text contained in the attached picture?"
                                "Please extract the text from the attached screenshot with high accuracy, ensuring "
                                "that all punctuation, capitalization, and formatting are preserved as closely as possible. "
                                "The goal is to capture the full text exactly as it appears in the image, without any "
                                "additional characters or missing content. Pay attention to any special characters, italics, "
                                "or unusual spacing to ensure the extracted text matches the original formatting."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url}  # Pass the image URL directly to OpenAI API
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
            model='gpt-4',
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
            "text": explanation_text,
            "image_url": image_url
        }

    except Exception as e:
        print(f"Error processing image or calling OpenAI: {e}")
        raise e
