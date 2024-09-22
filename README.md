backend: under the backend root dir, run: 
    uvicorn src.app:app --reload
to start the backend fastapi

frontend:
    npm start

deploy frontend, under the frontend root dir, run: (Nathan's github sso)
    vercel --prod --yes

deploy backend, under the backend root dir, use ps (or bash), run: (Nathan's github sso, project readbuddy_backend)
    modal profile list
    model profile activate nathang2022
    modal deploy src/app.py

qdrant.io - vectorstore (Nathan's gmail sso)

docker run -d --name redis-stack-server -p 6379:6379 redis/redis-stack-server:latest
docker exec -it redis-stack-server redis-cli
FT._LIST
FT.INFO Websites
FT.DROPINDEX Websites DD

storage: AWS S3 root: jim.guan@gmail.com 1!B
