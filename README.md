# How to run locally

- Backend: under the backend root dir, run: 
```
uvicorn src.app:app --reload --host 0.0.0.0
```
to start the backend fastapi

- Frontend:
```
npm start
```

# How to deploy to cloud

- Deploy frontend, under the frontend root dir, run: (Nathan's github sso)
```
vercel whoami
vercel logout
vercel login
vercel --prod --yes
```

- Deploy backend, under the backend root dir, use ps (or bash), run: (Nathan's github sso, project readbuddy_backend)
```
modal profile list
model profile activate nathang2022
modal deploy src/app.py
```

- Deploy qdrant.io - vectorstore (Nathan's gmail sso) 
```
    Websites - for index_qdrant.py
    NewChats - for chat_qdrant.py - with chat history (used to be Redis)
```

- File storage: AWS S3 root: jim.guan@gmail.com 1!B

# Redis related commands - obselete, due to no metadata "source" support

```
docker run -d --name redis-stack-server -p 6379:6379 redis/redis-stack-server:latest
docker exec -it redis-stack-server redis-cli
FT._LIST
FT.INFO Websites
FT.DROPINDEX Websites DD
```

# To make it work locally:

- BE - app.py
1. comment out ln 12-18, indent
```
# app = App("readbuddy-backend")
# app.image = Image.debian_slim().poetry_install_from_file("./pyproject.toml")
# @app.function(secrets=[Secret.from_dotenv()])
# @asgi_app()
````
2. comment out last line
```
    # return app
```
- FE - Questionform.js - ln 9-10:
```
const baseURL = 'http://localhost:8000' // 'https://nathang2022--readbuddy-backend-endpoint.modal.run'
const websocketURL = 'ws://localhost:8000' // 'wss://nathang2022--rag-backend-endpoint.modal.run'
```

