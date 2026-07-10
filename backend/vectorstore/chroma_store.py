import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

# Load env variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

CHROMA_HOST = os.getenv("CHROMA_HOST", "")
CHROMA_PORT = os.getenv("CHROMA_PORT", "8000")

# Setup the embedding function locally (completely free and offline)
# This will automatically download and cache all-MiniLM-L6-v2
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

def get_chroma_client():
    if CHROMA_HOST:
        print(f"Connecting to ChromaDB server at http://{CHROMA_HOST}:{CHROMA_PORT}")
        try:
            return chromadb.HttpClient(host=CHROMA_HOST, port=int(CHROMA_PORT))
        except Exception as e:
            print(f"Failed to connect to Chroma DB server: {e}. Falling back to local database.")
    
    # Fallback to local persistent client
    persist_dir = os.path.join(os.path.dirname(__file__), "chroma_db")
    print(f"Using local persistent ChromaDB at {persist_dir}")
    return chromadb.PersistentClient(path=persist_dir)

def get_collection(name="policy_documents"):
    client = get_chroma_client()
    # Create or get collection
    collection = client.get_or_create_collection(
        name=name,
        embedding_function=embedding_func,
        metadata={"hnsw:space": "cosine"} # Use cosine similarity
    )
    return collection

def add_documents(collection, texts, metadatas, ids):
    """
    Add documents to the collection.
    """
    collection.add(
        documents=texts,
        metadatas=metadatas,
        ids=ids
    )

def query_policy(collection, query_text, n_results=3):
    """
    Query the collection for the most relevant policy documents.
    """
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results
    )
    
    # Format the results into a clean list of dicts
    formatted = []
    if results and 'documents' in results and results['documents']:
        for i in range(len(results['documents'][0])):
            formatted.append({
                "id": results['ids'][0][i],
                "content": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "distance": results['distances'][0][i] if 'distances' in results else None
            })
    return formatted
