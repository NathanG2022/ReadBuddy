import json
from modal import Image, App, asgi_app, Secret
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.utils.chat_rag import get_answer_and_docs, async_get_answer_and_docs, async_get_text
from src.utils.index_qdrant import upload_webpage, upload_file
from src.utils.upload_s3 import upload_to_s3, process_image
from typing import List
from starlette.websockets import WebSocketDisconnect

# app = App("readbuddy-backend")

# app.image = Image.debian_slim().poetry_install_from_file("./pyproject.toml")

# @app.function(secrets=[Secret.from_dotenv()])
# @asgi_app()


# def endpoint():
# List to store active WebSocket connections
active_websockets: List[WebSocket] = []

app = FastAPI(
    title="ReadBuddy API",
    description="API for vector store url/txt/pdf, and AWS s3 store for image, and RAG chat with websocket",
    version="0.1",
)

origins = [
    "https://readbuddyfrontend.vercel.app",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
)

class Message(BaseModel):
    message: str

# WebSocket endpoint for start stop read: Keeps track of connected clients
@app.websocket('/async_read')
async def async_read(websocket: WebSocket):
    await websocket.accept()

    # Add the WebSocket to the list of active connections
    active_websockets.append(websocket)

    try:
        while True:
            # Receive a question from the client
            question = await websocket.receive_text()

            # Stream answer and docs back to the client
            async for event in async_get_answer_and_docs(question):
                if event["event_type"] == "done":
                    continue
                else:
                    await websocket.send_text(json.dumps(event))
            
    except WebSocketDisconnect:
        print("WebSocket connection was closed by the client.")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Ensure WebSocket is removed and closed properly
        if websocket in active_websockets:
            active_websockets.remove(websocket)
            
        # Try to close the WebSocket if it hasn't already been closed
        try:
            await websocket.close()
        except RuntimeError:
            print("WebSocket was already closed.")

# WebSocket endpoint for submit question: Keeps track of connected clients
@app.websocket('/async_chat')
async def async_chat(websocket: WebSocket):
    await websocket.accept()

    # Add the WebSocket to the list of active connections
    active_websockets.append(websocket)

    try:
        # Receive a question from the client
        question = await websocket.receive_text()

        # Stream answer and docs back to the client
        async for event in async_get_answer_and_docs(question):
            if event["event_type"] == "done":
                await websocket.send_text(json.dumps({"final": True}))
                break
            else:
                await websocket.send_text(json.dumps(event))

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Remove WebSocket from the active list if closed
        if websocket in active_websockets:
            active_websockets.remove(websocket)
        await websocket.close()  # Explicitly close the WebSocket connection

# POST endpoint for chat, synchronous version
@app.post("/chat", description="Chat with the RAG API through this endpoint")
def chat_use_rag(message: Message):
    response = get_answer_and_docs(message.message)
    response_content = {
        "question": message.message,
        "answer": response["answer"],
        "documents": [doc.dict() for doc in response["context"]]
    }
    return JSONResponse(content=response_content, status_code=200)

# POST endpoint for uploading a webpage
@app.post("/indexingURL", description="Index a webpage through this endpoint")
def indexing_URL(url: Message):
    try:
        response = upload_webpage(url.message)
        return JSONResponse(content={"response": response}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)

# POST endpoint for uploading a document (PDF or TXT)
@app.post("/indexingDoc", description="Index a pdf or txt file through this endpoint")
def indexing_Doc(file: UploadFile):
    try:
        response = upload_file(file)
        return JSONResponse(content={"response": response}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)

@app.post("/uploadS3", description="Upload image to S3 bucket")
async def upload_image_to_s3(file: UploadFile = File(...)):
    file_name = file.filename
    result = upload_to_s3(file.file, file_name)  # Pass content instead of file object
    
    # Broadcast message to all active WebSocket clients
    disconnected_clients = []
    for websocket in active_websockets:
        try:
            # Pass the file content (bytes) to async_get_text
            async for event in async_get_text():
                if event["event_type"] == "done":
                    continue
                else:
                    await websocket.send_text(json.dumps(event))

        except Exception as e:
            print(f"Failed to send to WebSocket: {e}")
            disconnected_clients.append(websocket)

    # Remove disconnected clients from the list
    for websocket in disconnected_clients:
        active_websockets.remove(websocket)
    
    return result

@app.post("/process_image", description="Process image using GPT-4 API")
async def process_image_endpoint(file: UploadFile = File(...)):
    try:
        # Call the process_image function from image_processing.py
        result = await process_image(file)

        # Broadcast message to all active WebSocket clients
        disconnected_clients = []
        for websocket in active_websockets:
            try:
                event = {
                    "event_type": "on_image_process",
                    "content": result
                }
                await websocket.send_text(json.dumps(event))

            except Exception as e:
                print(f"Failed to send to WebSocket: {e}")
                disconnected_clients.append(websocket)

        # Remove disconnected clients from the list
        for websocket in disconnected_clients:
            active_websockets.remove(websocket)

        return {"message": "Image processed successfully", "response": result}

    except Exception as e:
        print(f"Error processing image: {e}")
        return {"error": str(e)}

    # return app
