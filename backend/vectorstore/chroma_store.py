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

# Load Cross-Encoder for reranking, with fallback to keyword-overlap
cross_encoder = None
try:
    from sentence_transformers import CrossEncoder
    print("Loading CrossEncoder (cross-encoder/ms-marco-MiniLM-L-6-v2) for policy reranking...")
    cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    print("CrossEncoder loaded successfully.")
except Exception as e:
    print(f"Could not load CrossEncoder model ({e}). Using keyword-overlap scoring fallback for reranking.")

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
    Query the collection using Hybrid Search (Dense Chroma + Sparse Keyword)
    and reranking candidates using the Cross-Encoder model.
    """
    # 1. Semantic (Dense) Vector Search
    dense_list = []
    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=min(n_results * 2, 10)
        )
        if results and 'documents' in results and results['documents']:
            for i in range(len(results['documents'][0])):
                dense_list.append({
                    "id": results['ids'][0][i],
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })
    except Exception as e:
        print(f"Semantic search query failed: {e}")

    # 2. Sparse Keyword Matching
    sparse_list = []
    try:
        all_docs = collection.get()
        query_tokens = set(query_text.lower().replace(",", " ").replace(".", " ").split())
        insurance_keywords = {"uber", "rideshare", "commercial", "police", "gradual", "wear", "hospital", "date", "sec-102", "sec-103", "sec-105", "sec-106"}
        
        if all_docs and 'documents' in all_docs:
            for idx in range(len(all_docs['documents'])):
                doc_content = all_docs['documents'][idx]
                doc_tokens = set(doc_content.lower().replace(",", " ").replace(".", " ").split())
                
                # Check exact overlaps
                overlap = query_tokens.intersection(doc_tokens)
                score = len(overlap)
                
                # Boost key policy terms / section codes
                for tok in overlap:
                    if tok in insurance_keywords:
                        score += 5
                        
                if score > 0:
                    sparse_list.append({
                        "id": all_docs['ids'][idx],
                        "content": doc_content,
                        "metadata": all_docs['metadatas'][idx],
                        "keyword_score": score
                    })
            
            # Sort sparse matches
            sparse_list = sorted(sparse_list, key=lambda x: x["keyword_score"], reverse=True)[:min(n_results * 2, 10)]
    except Exception as e:
        print(f"Sparse keyword matching query failed: {e}")

    # 3. Merge candidates (Union)
    candidates = {}
    for item in dense_list:
        candidates[item["id"]] = item
    for item in sparse_list:
        if item["id"] not in candidates:
            candidates[item["id"]] = item
            
    candidate_list = list(candidates.values())

    if not candidate_list:
        return []

    # 4. Rerank Candidates
    if cross_encoder:
        try:
            pairs = [[query_text, doc["content"]] for doc in candidate_list]
            scores = cross_encoder.predict(pairs)
            for idx, score in enumerate(scores):
                candidate_list[idx]["rerank_score"] = float(score)
            candidate_list = sorted(candidate_list, key=lambda x: x["rerank_score"], reverse=True)
        except Exception as e:
            print(f"CrossEncoder prediction failed ({e}). Falling back to distance/keyword order.")
            candidate_list = sorted(candidate_list, key=lambda x: x.get("distance", 1.0) or 1.0)
    else:
        # Keyword-overlap fallback scoring
        query_tokens = set(query_text.lower().split())
        for doc in candidate_list:
            doc_tokens = set(doc["content"].lower().split())
            overlap = query_tokens.intersection(doc_tokens)
            doc["rerank_score"] = len(overlap) + (5 if any(kw in doc["content"].lower() for kw in ["uber", "rideshare", "commercial", "police", "leak", "gradual"]) else 0)
        candidate_list = sorted(candidate_list, key=lambda x: x["rerank_score"], reverse=True)

    return candidate_list[:n_results]

