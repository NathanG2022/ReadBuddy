import os
from langchain_qdrant import QdrantVectorStore 
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import WebBaseLoader, PyPDFLoader, TextLoader
# import chardet --pip install needed for txt auto detect encoding
# import pypdf  -- pip install needed for pdf parsing
# import python-multipart -- pip install needed for pdf parsing
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter
from qdrant_client import QdrantClient, models
from fastapi import UploadFile
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


def create_collection(collection_name):
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE)
    )
    print(f"Collection {collection_name} created successfully")


def ensure_collection_exists(collection_name):
    if not client.collection_exists(collection_name=collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE)
        )
        print(f"Collection {collection_name} created successfully")
    else:
        print(f"Collection {collection_name} already exists.")


ensure_collection_exists(collection_name)

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


def upload_webpage(url:str):
    ensure_collection_exists(collection_name)
        
    loader = WebBaseLoader(url)
    docs = loader.load_and_split(text_splitter)

    for doc in docs:
        doc.metadata = {"source": url}
    
    vector_store.add_documents(docs)
    return f"Successfully uploaded {len(docs)} documents to collection {collection_name} from URL."


def upload_file(file: UploadFile):
    ensure_collection_exists(collection_name)

    with open(file.filename, "wb") as f:
        f.write(file.file.read())

    documents = []

    # Check if the file is a text file
    if file.filename.lower().endswith('.txt'):
        try:
            loader = TextLoader(file_path=file.filename, autodetect_encoding=True)  # Assuming TextLoader can take a file-like object
            documents = loader.load()
        except Exception as e:
            print(f"Error loading text file: {e}")
            return {"error": f"Failed to load text file: {e}"}
    elif file.filename.lower().endswith('.pdf'):
        loader = PyPDFLoader(file.filename)
        documents = loader.load()

    if not len(documents):
        return f"Document is empty."

    text_splitter = CharacterTextSplitter(chunk_size=200, chunk_overlap=20)
    docs = text_splitter.split_documents(documents)
    # print("docs: %s" % docs)

    vector_store.add_documents(docs)

    # After adding the documents, delete the file
    try:
        os.remove(file.filename)
        print(f"Temporary file {file.filename} deleted successfully.")
    except OSError as e:
        print(f"Error: {file.filename} : {e.strerror}")

    return f"Successfully uploaded {len(docs)} documents from {file.filename}."        
    

def qdrant_search(query: str):
    ensure_collection_exists(collection_name)

    vector_search = get_embedding(query)
    docs = client.search(
        collection_name=collection_name,
        query_vector=vector_search,
        limit=4
    )
    return docs


# create_collection(collection_name)
# upload_website_to_collection("https://hamel.dev/blog/posts/evals/")
