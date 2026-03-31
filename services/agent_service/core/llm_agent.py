from langchain_groq import ChatGroq
import os
import time

# Configure Groq API key
groq_api_key = os.getenv("GROQ_API_KEY")

# Initialize model for generating text
model = ChatGroq(model="llama-3.3-70b-versatile", api_key=groq_api_key, temperature=0.1)

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def generate_audit_statement(normalized_log: dict) -> str:
    """
    Converts a normalized log into a human-readable audit statement
    using Groq Llama 3.3 with retry logic.
    """
    prompt = f"""
    You are an audit assistant. Convert the following normalized log into a clear, concise audit statement.

    Example:
    Input: {{
        "@timestamp": "2025-10-29T10:00:00Z",
        "event": {{"type": "file_modified", "severity": "medium"}},
        "user": {{"name": "root"}},
        "message": "Critical system file modified: /etc/passwd"
    }}
    Output: "Root user modified the critical system file /etc/passwd on October 29, 2025."

    Now convert this log:
    {normalized_log}
    """

    for attempt in range(MAX_RETRIES):
        try:
            response = model.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            print(f"Groq call failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))  # exponential-ish backoff
            else:
                error_msg = f"[AUDIT GENERATION FAILED after {MAX_RETRIES} retries: {str(e)}]"
                print(error_msg)
                return error_msg
