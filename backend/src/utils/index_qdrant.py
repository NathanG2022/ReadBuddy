import os
from langchain_qdrant import QdrantVectorStore  # Updated from Qdrant
from langchain_openai import OpenAIEmbeddings  # Updated imports
from langchain_community.document_loaders import WebBaseLoader, PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter
from qdrant_client import QdrantClient, models
from fastapi import UploadFile
# import pypdf  -- pip install needed for pdf parsing
# import python-multipart -- pip install needed for pdf parsing
from dotenv import load_dotenv
from .openai_utils import get_embedding

# Load environment variables from .env file
load_dotenv()  # This will load the .env file and make the variables available to os.getenv

qdrant_api_key = os.getenv("QDRANT_API_KEY")
qdrant_url = os.getenv("QDRANT_URL")
collection_name = "Websites"

client = QdrantClient(
    url=qdrant_url,
    api_key=qdrant_api_key
)

vector_store = QdrantVectorStore(
    client=client,
    collection_name=collection_name,
    embedding=OpenAIEmbeddings(
        api_key=os.getenv("OPENAI_API_KEY")
    )
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, 
    chunk_overlap=20, 
    length_function=len
)

def create_collection(collection_name):
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE)
    )
    print(f"Collection {collection_name} created successfully")

def upload_webpage(url:str):
    if not client.collection_exists(collection_name=collection_name):
        create_collection(collection_name)
        
    loader = WebBaseLoader(url)
    docs = loader.load_and_split(text_splitter)
    for doc in docs:
        doc.metadata = {"source": url}
    
    vector_store.add_documents(docs)
    return f"Successfully uploaded {len(docs)} documents to collection {collection_name} from {url}"

def upload_file(file: UploadFile):
    file_path = file.filename

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    documents = []

    if file.filename.lower().endswith('.pdf'):
        loader = PyPDFLoader(file_path)
        documents = loader.load()
    elif file.filename.lower().endswith('.txt'):
        loader = TextLoader(file_path)
        documents = loader.load()

    if not len(documents):
        return {"message": "document is empty"}

    text_splitter = CharacterTextSplitter(chunk_size=200, chunk_overlap=20)
    docs = text_splitter.split_documents(documents)
    print("docs: %s" % docs)

    vector_store.add_documents(docs)

    # After adding the documents, delete the file
    try:
        os.remove(file_path)
        print(f"Temporary file {file_path} deleted successfully.")
    except OSError as e:
        print(f"Error: {file_path} : {e.strerror}")
        
    return {"message": "done."}

def qdrant_search(query: str):
    vector_search = get_embedding(query)
    docs = client.search(
        collection_name=collection_name,
        query_vector=vector_search,
        limit=4
    )
    return docs


# create_collection(collection_name)
# upload_website_to_collection("https://hamel.dev/blog/posts/evals/")
