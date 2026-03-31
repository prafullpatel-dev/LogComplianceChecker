"""
agent.py — LLM + RAG functions using Groq and local embeddings.
"""

import os
import json
import re
import chromadb
from langchain_groq import ChatGroq
from sentence_transformers import SentenceTransformer

# Local embedding model — no API key needed
_embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


def get_llm(api_key: str):
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=api_key,
        temperature=0.1,
    )


def get_query_embedding(text: str) -> list:
    """Embed a query using local sentence-transformers model."""
    return _embedding_model.encode(text).tolist()


def generate_audit_statement(normalized_log: dict, api_key: str) -> str:
    """
    Converts a normalized ECS log into a human-readable audit statement
    using Groq LLM.
    """
    llm = get_llm(api_key)

    prompt = f"""
You are an audit assistant. Convert the following normalized security log into a
clear, concise, single-sentence audit statement.

Example Input:
{{
  "@timestamp": "2025-10-29T10:00:00Z",
  "event": {{"type": "file_modified", "severity": "medium"}},
  "user": {{"name": "root"}},
  "message": "Critical system file modified: /etc/passwd"
}}
Example Output:
"Root user modified the critical system file /etc/passwd on October 29, 2025."

Now convert this log:
{json.dumps(normalized_log, indent=2)}

Return ONLY the audit statement as a plain string with no extra explanation.
"""

    response = llm.invoke(prompt)
    return response.content.strip().strip('"')


def retrieve_relevant_docs(query_text: str, api_key: str, chroma_path: str) -> str:
    """
    Generates an embedding for the audit statement and retrieves top 3
    matching compliance policy chunks from ChromaDB.
    """
    chroma_client = chromadb.PersistentClient(path=chroma_path)
    collection = chroma_client.get_or_create_collection(name="audit_docs")

    if collection.count() == 0:
        return "No compliance documents have been indexed yet. Please run embed_setup.py first."

    query_embedding = get_query_embedding(query_text)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(3, collection.count()),
    )

    docs = [doc for sublist in results.get("documents", []) for doc in sublist]
    return "\n\n---\n\n".join(docs) if docs else "No relevant documents found."


def check_compliance(audit_statement: str, api_key: str, chroma_path: str) -> dict:
    """
    Retrieves relevant compliance policy context and uses the LLM to
    determine compliance status.
    Returns a dict with: is_compliant, reason, context_used
    """
    llm = get_llm(api_key)
    context_docs = retrieve_relevant_docs(audit_statement, api_key, chroma_path)

    prompt = f"""
You are a senior cybersecurity compliance auditor.

Based on the reference compliance policy documents below, determine whether the
described audit action is compliant with security regulations.

=== POLICY CONTEXT ===
{context_docs}

=== AUDIT STATEMENT ===
{audit_statement}

Respond ONLY in this exact JSON format (no markdown, no code blocks):
{{
  "is_compliant": "compliant" or "partially-compliant" or "non-compliant",
  "reason": "A concise explanation citing specific policy requirements"
}}
"""

    response = llm.invoke(prompt)
    raw = response.content.strip()

    # Strip markdown code fences if Groq wraps in ```json ... ```
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Graceful fallback if JSON parsing fails
        result = {
            "is_compliant": "unknown",
            "reason": f"Could not parse LLM response: {raw[:300]}",
        }

    result["context_used"] = context_docs
    return result


def run_full_audit(normalized_log: dict, api_key: str, chroma_path: str) -> dict:
    """
    Full pipeline for a single log: audit statement → RAG retrieval → compliance verdict.
    Returns a combined result dict.
    """
    audit_statement = generate_audit_statement(normalized_log, api_key)
    compliance = check_compliance(audit_statement, api_key, chroma_path)

    return {
        "audit_statement": audit_statement,
        "is_compliant": compliance.get("is_compliant", "unknown"),
        "reason": compliance.get("reason", ""),
        "context_used": compliance.get("context_used", ""),
        "normalized_log": normalized_log,
    }
