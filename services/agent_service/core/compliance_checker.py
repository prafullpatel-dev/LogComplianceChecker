from core.embeddings import retrieve_relevant_docs
from langchain_groq import ChatGroq
import os
import json
import time

# Configure Groq API key
groq_api_key = os.getenv("GROQ_API_KEY")

# Initialize model for generating text
model = ChatGroq(model="llama-3.3-70b-versatile", api_key=groq_api_key, temperature=0.1)

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def check_compliance(audit_statement: str):
    """
    Determines compliance of the given audit statement
    based on context from retrieved policy documents.
    Returns a parsed dict with 'is_compliant' and 'reason' keys.
    """
    context_docs = retrieve_relevant_docs(audit_statement)

    prompt = f"""
    You are a compliance auditor. Based on the following reference documents,
    determine if the described audit action is compliant or not.

    Context Documents:
    {context_docs}

    Audit Statement:
    {audit_statement}

    Respond in strict JSON format:
    {{
        "is_compliant": "compliant" or "partially-compliant" or "non-compliant",
        "reason": "short explanation"
    }}
    """

    for attempt in range(MAX_RETRIES):
        try:
            response = model.invoke(prompt)
            raw_text = response.content.strip()

            # Strip markdown code fences if present
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[1]  # remove first line
                raw_text = raw_text.rsplit("```", 1)[0]  # remove closing fence
                raw_text = raw_text.strip()

            return json.loads(raw_text)

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}. Raw response: {raw_text[:200]}")
            # Return a structured fallback instead of a raw string
            return {
                "is_compliant": "unknown",
                "reason": f"LLM returned unparseable response: {raw_text[:300]}"
            }
        except Exception as e:
            print(f"Groq call failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))  # exponential-ish backoff
            else:
                return {
                    "is_compliant": "error",
                    "reason": f"LLM call failed after {MAX_RETRIES} retries: {str(e)}"
                }
