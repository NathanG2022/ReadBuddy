import os
from langchain_community.vectorstores import Redis
from langchain_huggingface import HuggingFaceEmbeddings  # Updated imports
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from decouple import config
from fastapi import UploadFile

redis_url = config("REDIS_URL")
index_name = "Websites"
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

vector_store = Redis(redis_url=redis_url, index_name=index_name, embedding=embeddings)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, 
    chunk_overlap=20, 
    length_function=len
)

temp_folder = "./temp"

if not os.path.exists(temp_folder):
    os.makedirs(temp_folder)

def upload_website(url:str):
    loader = WebBaseLoader(url)
    docs = loader.load_and_split(text_splitter)
    for doc in docs:
        doc.metadata = {"source_url": url}
    
    vector_store.add_documents(docs)
    return f"Successfully uploaded {len(docs)} documents to index {index_name} from {url}"

def upload_pdf(file: UploadFile):
    file_path = os.path.join(temp_folder, file.filename)

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

    return {"message": "done."}


def vector_search(query: str):
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 6})
    docs = retriever.invoke(query)
    return docs


# create_collection(collection_name)
# upload_website_to_collection("https://hamel.dev/blog/posts/evals/")
