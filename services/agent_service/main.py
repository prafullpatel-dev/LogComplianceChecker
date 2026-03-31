"""
Agent Service — Consumes normalized logs from Kafka, generates audit
statements, checks compliance via RAG, and publishes verdicts.

Pipeline per log:
  1. Generate human-readable audit statement   (LLM)
  2. Retrieve relevant compliance policy docs  (RAG / ChromaDB)
  3. Determine compliance verdict              (LLM)
  4. Publish result to 'audit_results' topic   (Kafka)
"""

from kafka import KafkaConsumer, KafkaProducer
import json
import os
import time
from core.llm_agent import generate_audit_statement
from core.compliance_checker import check_compliance

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
INPUT_TOPIC = "normalized_logs"
OUTPUT_TOPIC = "audit_results"


# ─── Connect to Kafka with retries ───────────────────────────────────────────
def connect_kafka():
    """Initialize Kafka consumer and producer with retry logic."""
    for attempt in range(10):
        try:
            consumer = KafkaConsumer(
                INPUT_TOPIC,
                bootstrap_servers=KAFKA_BROKER,
                group_id="agent_service_group",
                auto_offset_reset="latest",
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            )
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            print("Connected to Kafka broker!")
            return consumer, producer
        except Exception as e:
            print(f"Kafka not ready ({e}), retrying in 5s... (attempt {attempt + 1}/10)")
            time.sleep(5)

    raise Exception("Kafka broker not available after 10 retries.")


# ─── Main Consumer Loop ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Starting Agent Service...")

    consumer, producer = connect_kafka()

    print(f"Listening on topic: '{INPUT_TOPIC}'...")

    for msg in consumer:
        normalized_log = msg.value
        print(f"\nReceived normalized log: {json.dumps(normalized_log)[:200]}...")

        try:
            # Step 1: Generate audit statement
            audit_statement = generate_audit_statement(normalized_log)
            print(f"Audit statement: {audit_statement[:150]}...")

            # Step 2: Check compliance (RAG retrieval + LLM reasoning)
            compliance_result = check_compliance(audit_statement)

            # Step 3: Publish result
            output = {
                "audit_statement": audit_statement,
                "compliance_result": compliance_result,
            }
            producer.send(OUTPUT_TOPIC, value=output)
            producer.flush()
            print(f"Published verdict → {compliance_result.get('is_compliant', 'unknown')}")

        except Exception as e:
            print(f"Error processing log: {e}")
            # Publish error result so the pipeline doesn't silently drop logs
            error_output = {
                "audit_statement": "[PROCESSING FAILED]",
                "compliance_result": {
                    "is_compliant": "error",
                    "reason": str(e),
                },
            }
            producer.send(OUTPUT_TOPIC, value=error_output)
            producer.flush()

        print("─" * 60)
