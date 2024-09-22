import json 
from modal import Image, App, asgi_app, Secret
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.utils.chat_rag import get_answer_and_docs, async_get_answer_and_docs
from src.utils.index_qdrant import upload_webpage, upload_file
from src.utils.upload_s3 import upload_to_s3

app = App("readbuddy-backend")

app.image = Image.debian_slim().poetry_install_from_file("./pyproject.toml")

@app.function(secrets=[Secret.from_dotenv()])
@asgi_app()
def endpoint():

    app = FastAPI(
        title="RAG API",

        description="A simple RAG API",
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

    @app.websocket('/async_chat')
    async def async_chat(websocket: WebSocket):
        await websocket.accept()
        while True:
            question = await websocket.receive_text()
            async for event in async_get_answer_and_docs(question):
                if event["event_type"] == "done":
                    await websocket.close()
                    return
                else:
                    await websocket.send_text(json.dumps(event))

    @app.post("/chat", description="Chat with the RAG API through this endpoint")
    def chat_use_rag(message: Message):
        response = get_answer_and_docs(message.message)
        response_content = {
            "question": message.message,
            "answer": response["answer"],
            "documents": [doc.dict() for doc in response["context"]]
        }
        return JSONResponse(content=response_content, status_code=200)

    @app.post("/indexingURL", description="Index a webpage through this endpoint")
    def indexing_URL(url: Message):
        try:
            response = upload_webpage(url.message)
            return JSONResponse(content={"response": response}, status_code=200)
        
        except Exception as e:
            return JSONResponse(content={"error": str(e)}, status_code=400)
        
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
        return result

    return app