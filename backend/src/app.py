import json
from modal import Image, App, asgi_app, Secret
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.utils.chat_rag import get_answer_and_docs, async_get_answer_and_docs
from src.utils.index_qdrant import upload_webpage, upload_file
from src.utils.upload_s3 import upload_to_s3
from typing import List

app = App("readbuddy-backend")

app.image = Image.debian_slim().poetry_install_from_file("./pyproject.toml")

@app.function(secrets=[Secret.from_dotenv()])
@asgi_app()
def endpoint():

    # List to store active WebSocket connections
    active_websockets: List[WebSocket] = []

    app = FastAPI(
        title="ReadBuddy API",
        description="API for vector store url/txt/pdf, and AWS s3 store for image, and RAG chat with websocket",
        version="0.1",
    )

    origins = [
        "https://frontend-opal-alpha.vercel.app",
        "http://localhost:3000"
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
    )

    class Message(BaseModel):
        message: str

    # WebSocket endpoint: Keeps track of connected clients
    @app.websocket('/async_chat')
    async def async_chat(websocket: WebSocket):
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
                
                # Keep connection alive and wait for further events
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            # Remove WebSocket from the active list if closed
            active_websockets.remove(websocket)
            await websocket.close()

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
        result = upload_to_s3(file.file, file_name)
        
        # Broadcast message to all active WebSocket clients
        disconnected_clients = []
        for websocket in active_websockets:
            try:
                print(f"Sending WebSocket notification for file upload: {file_name}")
                async for event in async_get_answer_and_docs("what is RAG"):
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

    return app
