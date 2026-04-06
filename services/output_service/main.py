"""
Output Service — Bridges Kafka audit results to the n8n orchestrator.

Continuously consumes compliance verdicts from the 'audit_results' Kafka topic
and forwards them via HTTP POST to the n8n webhook endpoint for automated
alerting and remediation workflows.

Also persists all audit results to a local JSON file for backup/traceability.
"""

from kafka import KafkaConsumer
import json
import os
import time
import requests

# ─── Configuration ────────────────────────────────────────────────────────────
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
AUDIT_TOPIC = os.getenv("AUDIT_TOPIC", "audit_results")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/audit-alerts")
RESULTS_FILE = os.getenv("RESULTS_FILE", "/app/audit_results.json")


# ─── Connect to Kafka with retries ───────────────────────────────────────────
def connect_kafka():
    """Initialize Kafka consumer with retry logic."""
    for attempt in range(10):
        try:
            consumer = KafkaConsumer(
                AUDIT_TOPIC,
                bootstrap_servers=KAFKA_BROKER,
                group_id="output_service_group",
                auto_offset_reset="earliest",
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )
            print("Connected to Kafka broker!")
            return consumer
        except Exception as e:
            print(f"Kafka not ready ({e}), retrying in 5s... (attempt {attempt + 1}/10)")
            time.sleep(5)

    raise Exception("Kafka broker not available after 10 retries.")


def save_result_to_file(result: dict):
    """Append audit result to a persistent JSON lines file."""
    try:
        with open(RESULTS_FILE, "a") as f:
            f.write(json.dumps(result) + "\n")
    except Exception as e:
        print(f"Failed to write result to file: {e}")


def forward_to_n8n(result: dict) -> bool:
    """
    Forward the audit result to n8n via webhook.
    Returns True if successful, False otherwise.
    """
    try:
        response = requests.post(
            N8N_WEBHOOK_URL,
            json=result,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if response.status_code == 200:
            print(f"Successfully forwarded to n8n (HTTP {response.status_code})")
            return True
        else:
            print(f"n8n returned HTTP {response.status_code}: {response.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        print("n8n webhook not reachable — result saved to file only.")
        return False
    except Exception as e:
        print(f"Error forwarding to n8n: {e}")
        return False


# ─── Main Consumer Loop ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Starting Output Service...")
    print(f"Listening on Kafka topic: '{AUDIT_TOPIC}'")
    print(f"Forwarding to n8n webhook: {N8N_WEBHOOK_URL}")

    consumer = connect_kafka()

    for message in consumer:
        result = message.value
        print(f"\nReceived audit result:")
        print(json.dumps(result, indent=2)[:500])

        # Always persist to file for traceability
        save_result_to_file(result)

        # Attempt to forward to n8n
        forwarded = forward_to_n8n(result)

        if not forwarded:
            print("Result saved locally — will not retry n8n forwarding.")

        print("─" * 60)
