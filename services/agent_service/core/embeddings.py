from sentence_transformers import SentenceTransformer
import os
import chromadb

# ChromaDB connection - uses standalone ChromaDB container via HTTP
CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

# Local embedding model — no API key needed
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


def retrieve_relevant_docs(query_text: str):
    """
    Generates an embedding for the given query using a local sentence-transformers model
    and retrieves top related compliance documents from ChromaDB.
    Uses HttpClient to connect to the standalone ChromaDB container.
    """
    chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    collection = chroma_client.get_or_create_collection(name="audit_docs")

    # Generate embedding locally
    query_embedding = embedding_model.encode(query_text).tolist()
    print("Embedding generated out of Audit Statement\n")

    # Query ChromaDB for relevant documents
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    docs = [doc for sublist in results.get("documents", []) for doc in sublist]
    print("Relevant docs extracted:", docs)

    return "\n".join(docs) if docs else "No relevant documents found."
