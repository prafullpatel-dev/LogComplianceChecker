"""
embed_setup.py — One-time knowledge base builder.

Run this ONCE from the terminal before starting the app:
    python embed_setup.py

Just paste your API key when prompted (only needed for LLM segmentation).
After it finishes, the chroma_store/ folder is permanently stored.

Embeddings use a local sentence-transformers model (no API key needed).
"""

import os
import sys
import time
import chromadb
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer

# ──────────────────────────────────────────────────────────────────────────────
# PATHS
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_store")
COMPLIANCE_DOCS_PATH = os.path.join(
    BASE_DIR, "..", "services", "agent_service", "data", "compliance_docs"
)

CHUNK_SIZE    = 1000   # characters per chunk
CHUNK_OVERLAP = 100    # overlap between chunks for context continuity

# Local embedding model — no API key needed
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def extract_text_from_pdf(pdf_path: str) -> str:
    text = ""
    with open(pdf_path, "rb") as f:
        reader = PdfReader(f)
        total = len(reader.pages)
        for i, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
            if i % 20 == 0:
                print(f"    Read page {i}/{total}...")
    return text.strip()


def split_into_chunks(text: str) -> list:
    """Simple fixed-size text splitter with overlap. No LLM calls needed."""
    chunks = []
    start  = 0
    while start < len(text):
        end   = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end].strip()
        if len(chunk) > 50:          # skip tiny fragments
            chunks.append(chunk)
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def progress_bar(current: int, total: int, width: int = 30) -> str:
    filled = int(width * current / total) if total else 0
    bar    = "█" * filled + "░" * (width - filled)
    pct    = int(100 * current / total) if total else 0
    return f"[{bar}] {pct:3d}%  ({current}/{total})"


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
def main():

    print("\n" + "=" * 60)
    print("  Compliance Audit Agent — Knowledge Base Builder")
    print("  Using local sentence-transformers embeddings")
    print("=" * 60)

    # ── Validate PDF folder ───────────────────────────────────────────────────
    if not os.path.exists(COMPLIANCE_DOCS_PATH):
        print(f"\nERROR: Compliance docs folder not found:\n  {COMPLIANCE_DOCS_PATH}")
        sys.exit(1)

    pdfs = [f for f in os.listdir(COMPLIANCE_DOCS_PATH) if f.endswith(".pdf")]
    if not pdfs:
        print(f"\nERROR: No PDFs found in:\n  {COMPLIANCE_DOCS_PATH}")
        sys.exit(1)

    print(f"\nFound {len(pdfs)} compliance PDF(s):")
    for p in pdfs:
        kb = os.path.getsize(os.path.join(COMPLIANCE_DOCS_PATH, p)) // 1024
        print(f"  📄 {p}  ({kb} KB)")

    # ── Init ChromaDB ─────────────────────────────────────────────────────────
    print(f"\nOpening ChromaDB at: {CHROMA_PATH}")
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        chroma_client.delete_collection("audit_docs")
        print("Deleted old collection to reset dimension schema.")
    except Exception:
        pass  # Collection might not exist yet

    collection = chroma_client.get_or_create_collection(name="audit_docs")

    # ── Process PDFs ─────────────────────────────────────────────────────────
    total_stored = 0

    for pdf_num, filename in enumerate(pdfs, start=1):
        pdf_path = os.path.join(COMPLIANCE_DOCS_PATH, filename)
        print(f"\n{'─'*55}")
        print(f"[{pdf_num}/{len(pdfs)}] {filename}")
        print(f"{'─'*55}")

        # Step 1 — Extract text
        print("  Extracting text...")
        try:
            text = extract_text_from_pdf(pdf_path)
        except Exception as e:
            print(f"  ERROR reading PDF: {e}")
            continue

        if not text:
            print("  WARNING: No text extracted (image-based PDF?). Skipping.")
            continue
        print(f"  Extracted {len(text):,} characters.")

        # Step 2 — Chunk (no LLM needed — fast and reliable)
        chunks = split_into_chunks(text)
        print(f"  Split into {len(chunks)} chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}).")

        # Step 3 — Embed locally + store
        print(f"  Embedding chunks into ChromaDB...")
        stored   = 0
        failures = 0

        for idx, chunk in enumerate(chunks):
            try:
                vector = embedding_model.encode(chunk).tolist()
                collection.add(
                    documents  =[chunk],
                    embeddings =[vector],
                    ids        =[f"{filename}_{idx}"],
                    metadatas  =[{"source": filename, "chunk_index": idx}],
                )
                stored      += 1
                total_stored += 1
            except Exception as e:
                failures += 1
                print(f"\n  ⚠ Chunk {idx} failed: {e}")

            # Print progress every 10 chunks
            if (idx + 1) % 10 == 0 or (idx + 1) == len(chunks):
                print(f"\r  {progress_bar(idx+1, len(chunks))}", end="", flush=True)

        print()   # newline after progress bar
        print(f"  ✅ Stored {stored} chunks  (failures: {failures})")

    # ── Done ──────────────────────────────────────────────────────────────────
    final_count = collection.count()
    print(f"\n{'=' * 55}")
    if final_count > 0:
        print(f"  ✅  KNOWLEDGE BASE READY!")
        print(f"  Total vectors in ChromaDB : {final_count}")
        print(f"  Stored at                 : {CHROMA_PATH}")
        print(f"\n  You can now run the app:")
        print(f"      streamlit run app.py")
    else:
        print("  ❌  Something went wrong — 0 vectors stored.")
        print("  Check your terminal and try again.")
    print(f"{'=' * 55}\n")


if __name__ == "__main__":
    main()
