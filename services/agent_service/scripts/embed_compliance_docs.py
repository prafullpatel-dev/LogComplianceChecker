import os
from langchain_groq import ChatGroq
from sentence_transformers import SentenceTransformer
import chromadb
from PyPDF2 import PdfReader
import time
import math

groq_api_key = os.getenv("GROQ_API_KEY")
PDF_FOLDER = "/app/data/compliance_docs"

# Initialize local embedding model (no API key needed)
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Connect to standalone ChromaDB container via HTTP
CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
try:
    chroma_client.delete_collection("audit_docs")
    print("Found old collection — deleting it to reset dimension schema...\n")
except Exception:
    pass

collection = chroma_client.get_or_create_collection(name="audit_docs")


def extract_text_from_pdf(pdf_path: str) -> str:
    """Reads and concatenates text from all pages in a PDF."""
    text = ""
    try:
        with open(pdf_path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        print("Extracted Text from pdf")
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
    return text.strip()


def llm_segment_text(raw_text: str, batch_size: int = 8000, pause_sec: int = 1):
    if not raw_text.strip():
        print("Empty text received, skipping segmentation.")
        return []

    # Initialize Groq LLM for segmentation
    model = ChatGroq(model="llama-3.3-70b-versatile", api_key=groq_api_key, temperature=0.1)

    total_length = len(raw_text)
    total_batches = math.ceil(total_length / batch_size)
    print(f"\nSegmenting text of {total_length:,} characters into {total_batches} batches...")

    all_segments = []

    for i in range(total_batches):
        start = i * batch_size
        end = min((i + 1) * batch_size, total_length)
        text_chunk = raw_text[start:end]

        prompt = f"""
        You are an NLP assistant helping in compliance document processing.
        The following text has been extracted from a regulatory or audit document.
        Your job is to split it into clean, self-contained sentences or paragraphs,
        each representing one distinct compliance idea or clause.

        Return each segment as a new line (no numbering, no bullets).
        ---
        {text_chunk}
        """

        try:
            response = model.invoke(prompt)
            segments = [
                seg.strip() for seg in response.content.split("\n")
                if len(seg.strip()) > 25  # ignore very short or broken lines
            ]

            all_segments.extend(segments)
            print(f"Batch {i+1}/{total_batches}: {len(segments)} segments extracted.")
        except Exception as e:
            print(f"Batch {i+1}/{total_batches} failed: {e}")

        # Prevent hitting rate limits
        time.sleep(pause_sec)

    print(f"\nLLM segmentation complete: {len(all_segments)} total segments generated.")
    return all_segments


def embed_policies_from_folder(folder_path=PDF_FOLDER):
    """Extracts text, segments it via LLM, embeds locally, and stores in ChromaDB."""
    if not os.path.exists(folder_path):
        print(f"Folder not found: {folder_path}")
        return

    embedded_count = 0

    for filename in os.listdir(folder_path):
        if not filename.endswith(".pdf"):
            continue

        pdf_path = os.path.join(folder_path, filename)
        print(f"\nProcessing: {filename}")

        # Step 1: Extract text
        text = extract_text_from_pdf(pdf_path)
        if not text:
            print(f"Skipping {filename}: empty or unreadable.")
            continue

        # Step 2: Segment text using LLM
        segments = llm_segment_text(text)
        if not segments:
            print(f"Skipping {filename}: segmentation failed or empty output.")
            continue

        # Step 3: Embed locally and store
        for idx, segment in enumerate(segments):
            try:
                vector = embedding_model.encode(segment).tolist()
                collection.add(
                    documents=[segment],
                    embeddings=[vector],
                    ids=[f"{filename}_{idx}"],
                    metadatas=[{"source": filename, "chunk_index": idx}]
                )
                embedded_count += 1
                print(f"\nSegment {idx}/{len(segments)} embedding done.")
            except Exception as e:
                print(f"Embedding failed for segment {idx} in {filename}: {e}")

            # Small pause to avoid overwhelming ChromaDB
            time.sleep(0.1)

        print(f"Embedded {len(segments)} segments from {filename}")

    print(f"\nEmbedding complete. Total new vectors added: {embedded_count}")


if __name__ == "__main__":
    print("Starting compliance document embedding with LLM segmentation...\n")
    embed_policies_from_folder()
    print("\nAll compliance policies embedded successfully!")
