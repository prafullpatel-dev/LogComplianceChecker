import os
import json
import time
from kafka import KafkaProducer
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Kafka configuration
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TOPIC_NAME = os.getenv("TOPIC_NAME", "raw_logs")

# Log buffer path (the file where other systems write logs)
DATA_PATH = os.path.join(os.path.dirname(__file__), "data/buffer.json")

# Keep track of how many logs we've already processed
offset_file = os.path.join(os.path.dirname(__file__), "data/.offset_tracker.json")


def load_offset():
    """Load last processed offset (number of logs processed)."""
    if os.path.exists(offset_file):
        with open(offset_file, "r") as f:
            return json.load(f).get("offset", 0)
    return 0


def save_offset(offset):
    """Save latest offset."""
    with open(offset_file, "w") as f:
        json.dump({"offset": offset}, f)


def connect_kafka():
    """Initialize Kafka producer with retries."""
    for i in range(10):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )
            print("Connected to Kafka broker!")
            return producer
        except Exception as e:
            print(f"Kafka not ready ({e}), retrying in 5s...")
            time.sleep(5)
    raise Exception("Kafka broker not available after 10 retries.")


class BufferFileHandler(FileSystemEventHandler):
    """Watchdog handler that triggers on buffer.json modification."""

    def __init__(self, producer):
        self.producer = producer

    def on_modified(self, event):
        if event.src_path.endswith("buffer.json"):
            try:
                print("Detected new changes in buffer.json")
                self.process_new_logs()
            except Exception as e:
                print(f"Error processing buffer: {e}")

    def process_new_logs(self):
        """Reads new logs since last offset and pushes to Kafka."""
        if not os.path.exists(DATA_PATH):
            print("buffer.json not found")
            return

        # Read all logs
        with open(DATA_PATH, "r") as f:
            logs = json.load(f)

        # Get previous offset
        last_offset = load_offset()
        new_logs = logs[last_offset:]

        if not new_logs:
            print("No new logs to process.")
            return

        # Push only new logs
        for log in new_logs:
            self.producer.send(TOPIC_NAME, value=log)
            print(f"Sent new log: {log.get('timestamp', 'unknown')}")

        self.producer.flush()
        save_offset(last_offset + len(new_logs))
        print(f"Processed {len(new_logs)} new logs.")


if __name__ == "__main__":
    print("Starting InputService (Real-time Log Watcher Mode)...")

    # Ensure data dir exists
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)

    # Connect to Kafka
    producer = connect_kafka()

    # Start file watcher
    event_handler = BufferFileHandler(producer)
    observer = Observer()
    observer.schedule(event_handler, path=os.path.dirname(DATA_PATH), recursive=False)
    observer.start()

    print(f"Watching for real-time log updates in {DATA_PATH}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

