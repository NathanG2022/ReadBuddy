from io import BytesIO
import os
import base64
import requests
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_openai import ChatOpenAI
from fastapi import UploadFile
from operator import itemgetter
from dotenv import load_dotenv
from openai import OpenAI
from .index_qdrant import vector_store, qdrant_search
from .openai_utils import stream_completion

# Load environment variables from .env file
load_dotenv()  # This will load the .env file and make the variables available to os.getenv

openai_api_key=os.getenv("OPENAI_API_KEY")

model = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=openai_api_key,
    temperature=0,
)

prompt_template = """
Answer the question based on the context, in a concise manner, in markdown and using bullet points where applicable.

Context: {context}
Question: {question}
Answer:
"""

prompt = ChatPromptTemplate.from_template(prompt_template)

retriever = vector_store.as_retriever()


# Function to fetch the image from the URL and encode it to base64
def encode_image_to_base64(image_url: str):
    # Fetch the image from the URL
    response = requests.get(image_url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch image from URL: {image_url}")

    # Read the image and convert it to base64
    image_data = BytesIO(response.content)
    base64_image = base64.b64encode(image_data.getvalue()).decode('utf-8')
    
    # Convert to a data URL format
    base64_img_str = f"data:image/png;base64,{base64_image}"
    
    return base64_img_str


def create_chain():
    chain = (
        {
            "context": retriever.with_config(top_k=4),
            "question": RunnablePassthrough(),
        }
        | RunnableParallel({
            "response": prompt | model,
            "context": itemgetter("context"),
            })
    )
    return chain


def get_answer_and_docs(question: str):
    chain = create_chain()
    response = chain.invoke(question)
    answer = response["response"].content
    context = response["context"]
    return {
        "answer": answer,
        "context": context
    }


# async def async_get_answer_and_docs(question: str):
#     chain = create_chain()
#     async for event in chain.astream_events(question, version='v1'):
#         event_type = event['event']
#         if event_type == "on_retriever_end":
#             yield {
#                 "event_type": event_type,
#                 "content": [doc.dict() for doc in event['data']['output']['documents']]
#             }
#         elif event_type == "on_chat_model_stream":
#             yield {
#                 "event_type": event_type,
#                 "content": event['data']['chunk'].content
#             }
    
#     yield {
#         "event_type": "done"
#     }


async def async_get_answer_and_docs(question: str):
    docs = qdrant_search(query=question)
    docs_dict = [doc.payload for doc in docs]
    yield {
        "event_type": "on_retriever_end",
        "content": docs_dict
    }

    async for chunk in stream_completion(question, docs_dict):
        yield {
            "event_type": "on_chat_model_stream",
            "content": chunk
    }

    yield {
        "event_type": "done"
    }


# Async function to handle OpenAI image + text explanation
async def async_get_text():
    try:
        # Convert the file content (bytes) to a base64-encoded string
        base64_img = encode_image_to_base64("https://metalbyexample.com/wp-content/uploads/figure-65.png")
        client = OpenAI(api_key=openai_api_key)
        # Create a chat completion request with the base64-encoded image
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Return JSON document with data. Only return JSON not other text"},
                            {
                                "type": "image_url",
                                # for online images
                                # "image_url": {"url": image_url}
                                "image_url": {"url": base64_img}
                            }
                        ],
                }
            ],
            temperature=0,
            max_tokens=500,
        )

        # Yield the response from OpenAI
        yield {
            "event_type": "on_image_process",
            "content": response.choices[0].message.content
        }

    except Exception as e:
        print(f"Error processing image or calling OpenAI: {e}")
        yield {
            "event_type": "error",
            "content": str(e)
        }

    yield {
        "event_type": "done"
    }