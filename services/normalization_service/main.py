"""
Normalization Service — LLM-powered ECS log normalization using Groq Llama 3.3.

Consumes raw logs from Kafka topic 'raw_logs', uses Groq LLM to dynamically
normalize them into Elastic Common Schema (ECS) format, and publishes
the normalized logs to Kafka topic 'normalized_logs'.

Logs that fail normalization are routed to 'dead_letter_logs' for inspection.
"""

from kafka import KafkaConsumer, KafkaProducer
from langchain_groq import ChatGroq
import json
import os
import time
import re

# ─── Configuration ────────────────────────────────────────────────────────────
RAW_TOPIC = os.getenv("RAW_TOPIC", "raw_logs")
NORMALIZED_TOPIC = os.getenv("NORMALIZED_TOPIC", "normalized_logs")
DEAD_LETTER_TOPIC = os.getenv("DEAD_LETTER_TOPIC", "dead_letter_logs")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ─── Configure Groq LLM ──────────────────────────────────────────────────────
model = ChatGroq(model="llama-3.3-70b-versatile", api_key=GROQ_API_KEY, temperature=0.0)

# ─── Normalization Prompt ─────────────────────────────────────────────────────
NORMALIZATION_PROMPT = """You are a cybersecurity log normalization engine.

Your task is to take a raw security log (in any format) and extract all relevant 
fields into the Elastic Common Schema (ECS) format.

Rules:
1. Map ALL identifiable fields from the raw log into the appropriate ECS categories.
2. If a field doesn't exist in the raw log, omit it from the output entirely.
3. Standardize timestamps to ISO 8601 format (e.g., "2025-10-29T10:00:00Z").
4. For the "event.category" field, use one of: security, process, network, inventory, authentication.
5. Set ecs_version to "8.11.0".
6. Preserve all meaningful data — do NOT discard information.

Respond ONLY with valid JSON, no markdown, no code blocks, no explanation.

The JSON should follow this ECS structure (include only fields that have values):
{{
  "timestamp": "ISO 8601",
  "event": {{ "category": "", "type": "", "severity": "", "action": "" }},
  "source": {{ "ip": "", "port": 0 }},
  "destination": {{ "ip": "", "port": 0 }},
  "host": {{ "name": "", "os": "" }},
  "user": {{ "name": "", "id": "" }},
  "process": {{ "name": "", "pid": 0, "parent_name": "" }},
  "network": {{ "protocol": "", "latency_ms": 0.0, "packet_loss": 0.0 }},
  "observer": {{ "vendor": "", "product": "", "name": "" }},
  "asset": {{ "id": "", "type": "", "status": "", "owner": "" }},
  "vulnerability": {{ "cve": [] }},
  "message": "",
  "ecs_version": "8.11.0"
}}

Raw log to normalize:
{raw_log}
"""


# ─── Connect to Kafka with retries ───────────────────────────────────────────
def connect_kafka():
    """Initialize Kafka consumer and producer with retry logic."""
    for attempt in range(10):
        try:
            consumer = KafkaConsumer(
                RAW_TOPIC,
                bootstrap_servers=KAFKA_BROKER,
                group_id="normalization_service_group",
                auto_offset_reset="latest",
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            print("Connected to Kafka.")
            return consumer, producer
        except Exception as e:
            print(f"Kafka not ready yet ({e}), retrying in 5s... (attempt {attempt + 1}/10)")
            time.sleep(5)

    raise Exception("Kafka broker unavailable after 10 retries.")


def normalize_with_llm(raw_log: dict) -> dict | None:
    """
    Use Groq Llama 3.3 to normalize a raw log into ECS format.
    Returns the normalized dict, or None on failure.
    """
    prompt = NORMALIZATION_PROMPT.format(raw_log=json.dumps(raw_log, indent=2))

    try:
        response = model.invoke(prompt)
        raw_text = response.content.strip()

        # Strip markdown code fences if present
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

        normalized = json.loads(raw_text)
        return normalized

    except Exception as e:
        print(f"LLM normalization failed: {e}")
        return None


# ─── Main Consumer Loop ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Starting LLM-based Normalization Service (Groq Llama 3.3)...")

    consumer, producer = connect_kafka()

    print(f"Listening on topic '{RAW_TOPIC}'...")

    for message in consumer:
        raw_log = message.value
        print(f"\nReceived raw log: {json.dumps(raw_log)[:200]}...")

        normalized = normalize_with_llm(raw_log)

        if normalized:
            producer.send(NORMALIZED_TOPIC, value=normalized)
            producer.flush()
            print(f"Normalized and sent to '{NORMALIZED_TOPIC}'")
        else:
            # Route failed logs to dead letter topic for manual inspection
            producer.send(DEAD_LETTER_TOPIC, value={
                "error": "LLM normalization failed",
                "original_log": raw_log,
            })
            producer.flush()
            print(f"Failed log routed to '{DEAD_LETTER_TOPIC}'")
