# AI-Driven Agentic RAG Platform for Cybersecurity Compliance & Audit Automation

## Overview

This project implements an **AI-driven Agentic Retrieval-Augmented Generation (RAG) platform** to automate cybersecurity compliance monitoring and audit management.

The system continuously ingests security telemetry, normalizes heterogeneous logs, reasons over regulatory knowledge using Large Language Models (LLMs), and produces **explainable, evidence-backed compliance verdicts**.

Unlike traditional rule-based compliance tools, this platform integrates:

- Real-time log ingestion
- LLM-powered contextual reasoning
- Vector-based regulatory knowledge retrieval
- Agent-based workflow orchestration

The result is a **scalable, modular, and intelligent compliance automation system** aligned with modern cybersecurity environments.

---

## Key Features

- Continuous ingestion of SIEM, EDR, network, and asset management logs
- Kafka-based event-driven microservice architecture
- ECS-compliant log normalization
- LLM-generated human-readable audit statements
- RAG-based compliance reasoning using ChromaDB
- Google Gemini LLM and embeddings integration
- Modular agent services with fault tolerance
- Evidence-backed compliance verdicts in JSON format
- Interactive Streamlit dashboard for upload-based auditing

---

## System Architecture

The platform is composed of the following microservices:

| Service                   | Role                                                      |
|---------------------------|-----------------------------------------------------------|
| Telemetry Input Service   | Watches `buffer.json` for new logs and pushes to Kafka    |
| Periodic Input Service    | Reads batch files (TXT, CSV, PDF) and pushes to Kafka     |
| Normalization Service     | LLM-based ECS normalization via Gemini                    |
| Agent Service             | Audit statement generation + RAG compliance reasoning     |
| Output Service            | Forwards verdicts to n8n webhook + persists to file       |
| Streamlit App             | Interactive dashboard for upload-based compliance checks  |
| ChromaDB                  | Vector database for regulatory document embeddings        |
| Kafka (KRaft)             | Event-driven message broker (no Zookeeper)                |
| n8n + PostgreSQL          | Workflow automation for alerting                          |

All services communicate asynchronously via **Kafka topics**, ensuring loose coupling and scalability.

---

## Technology Stack

- **Programming Language:** Python 3.11
- **Message Broker:** Apache Kafka (KRaft mode, no Zookeeper)
- **LLM:** Google Gemini 2.0 Flash
- **Embeddings:** Gemini `gemini-embedding-001`
- **Vector Database:** ChromaDB (standalone container)
- **PDF Processing:** PyPDF2
- **File Monitoring:** Watchdog
- **Containerization:** Docker & Docker Compose
- **Dashboard:** Streamlit

---

## Prerequisites

- **Docker & Docker Compose** (Docker Desktop on Windows/Mac)
- **Google Gemini API Key** — get one free at [Google AI Studio](https://aistudio.google.com/apikey)

---

## Quick Start

### 1. Clone and configure

```bash
git clone <repository-url>
cd Compliance_Audit_Agent-master
```

Copy the example environment file and add your API key:

```bash
cp .env.example .env
```

Edit `.env` and replace `your-google-api-key-here` with your actual Gemini API key:

```
GOOGLE_API_KEY=AIza...your-key-here
```

---

## Running the Project

There are **two independent ways** to run this project:

---

### Option A — Docker Pipeline (Full Live-Tracking System)

This runs the complete Kafka-based microservice architecture. Logs flow through the pipeline automatically:

```
Raw Logs → Kafka → Normalization → Agent (LLM + RAG) → Output → n8n
```

#### Step 1: Start all services

```bash
docker compose up --build
```

This starts: Kafka, ChromaDB, PostgreSQL, n8n, all 5 microservices, and the Streamlit dashboard.

#### Step 2: Embed compliance documents (one-time only)

In a new terminal, run:

```bash
docker compose exec agent_service python /app/scripts/embed_compliance_docs.py
```

This extracts text from the compliance PDFs (ISO 27001, CERT-In Cyber Security Policy), segments them using LLM, embeds the segments, and stores vectors in ChromaDB. **Run this only once** — or when you add/update compliance documents.

#### Step 3: Watch the pipeline in action

The **Telemetry Input Service** watches `services/telemetry_input_service/data/buffer.json` for changes. To trigger processing, add new log entries to that file.

The **Periodic Input Service** reads all files from `services/periodic_input_service/periodic_data/` on startup and sends them through the pipeline.

#### How to verify each stage

| What to check                  | How                                                        |
|--------------------------------|------------------------------------------------------------|
| Kafka receiving raw logs       | Look for `"Sent new log"` in telemetry_input_service logs  |
| Normalization working          | Look for `"Normalized and sent"` in normalization logs      |
| Agent producing verdicts       | Look for `"Published verdict"` in agent_service logs        |
| Output reaching n8n            | Look for `"Successfully forwarded to n8n"` in output logs   |
| Streamlit dashboard            | Open `http://localhost:8501` in your browser               |
| n8n workflow editor            | Open `http://localhost:5678` (admin/admin)                  |

View specific service logs:

```bash
docker compose logs -f agent_service
docker compose logs -f normalization_service
docker compose logs -f output_service
```

#### Simulating real-time log ingestion

To test real-time ingestion, add a new log entry to the buffer file while the system is running:

```bash
# Example: Append a new SIEM log to trigger the pipeline
docker compose exec telemetry_input_service python -c "
import json
with open('data/buffer.json', 'r') as f:
    logs = json.load(f)
logs.append({
    'timestamp': '2025-11-04T12:00:00Z',
    'src_ip': '10.0.0.99',
    'dest_ip': '10.0.0.200',
    'event_type': 'unauthorized_access',
    'severity': 'critical',
    'msg': 'Unauthorized SSH access to production database server',
    'user': 'unknown',
    'hostname': 'prod-db-01',
    'device_vendor': 'Splunk',
    'device_product': 'Splunk Enterprise',
    'source_type': 'siem'
})
with open('data/buffer.json', 'w') as f:
    json.dump(logs, f, indent=2)
print('New log added!')
"
```

---

### Option B — Streamlit App (Standalone Upload Mode)

This runs the Streamlit dashboard **without Docker or Kafka**. It's a simpler way to test the core audit logic by uploading log files directly.

#### Step 1: Install dependencies

```bash
cd streamlit_app
pip install -r requirements.txt
```

#### Step 2: Build the knowledge base (one-time)

```bash
python embed_setup.py
```

When prompted, paste your Gemini API key. This reads the compliance PDFs, chunks them, embeds them, and stores vectors locally in `chroma_store/`.

**You only need to run this once.** The `chroma_store/` folder persists between app restarts.

#### Step 3: Run the app

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

#### How to use the Streamlit app

1. **Enter your Gemini API Key** in the sidebar
2. **Upload a log file** (JSON or CSV) in the "📤 Audit Logs" tab
   - Sample files are provided in `streamlit_app/sample_logs/`
3. **Or enter a log manually** in the "✍️ Manual Entry" tab
4. Click **"🔍 Run Compliance Audit"**
5. View the compliance verdicts with detailed explanations
6. **Export results** as JSON

---

## Kafka Topics

| Topic Name        | Description                     |
|-------------------|---------------------------------|
| raw_logs          | Raw telemetry logs               |
| normalized_logs   | ECS-normalized logs              |
| audit_results     | Compliance verdicts              |
| dead_letter_logs  | Failed normalization attempts    |

---

## Sample Compliance Output

```json
{
  "audit_statement": "Root user on host sec-srv-1 modified the critical system file /etc/passwd from IP address 10.0.0.8 on November 4, 2025.",
  "compliance_result": {
    "is_compliant": "non-compliant",
    "reason": "Modifying /etc/passwd by root from a non-designated admin IP violates ISO 27001 A.9.2.3 (Management of privileged access rights) and CERT-In access control policies."
  }
}
```

---

## Service Breakdown

### 1. Telemetry Input Service
- Uses **Watchdog** to monitor `data/buffer.json` for real-time changes
- Tracks offset to only process new log entries
- Pushes raw logs to Kafka topic `raw_logs`

### 2. Periodic Input Service
- Reads log files from `periodic_data/` folder on startup
- Supports **JSON-per-line (.txt)**, **CSV**, and **PDF** formats
- Auto-detects log type from filename keywords

### 3. Normalization Service
- Consumes raw logs from Kafka topic `raw_logs`
- Uses **Gemini LLM** to dynamically normalize any log format into ECS schema
- Produces structured JSON with typed ECS fields
- Routes failures to `dead_letter_logs` topic

### 4. Agent Service
- Consumes normalized logs from `normalized_logs`
- **Step 1:** Generates human-readable audit statement (Gemini LLM)
- **Step 2:** Retrieves relevant compliance clauses from ChromaDB (RAG)
- **Step 3:** Produces compliance verdict with reasoning (Gemini LLM)
- Publishes results to `audit_results` topic

### 5. Output Service
- Consumes verdicts from `audit_results`
- Forwards to n8n webhook for automated alerting
- Persists all results to local JSON file for traceability

### 6. Streamlit Dashboard
- Upload-based compliance auditing (no Kafka needed)
- Rule-based ECS normalization for 5 log types
- Full audit pipeline: normalize → audit statement → RAG → verdict
- Export results as JSON

---

## Vector Knowledge Base

### Compliance Documents
Located in `services/agent_service/data/compliance_docs/`:
- `iso-27001.pdf` — ISO/IEC 27001 Information Security Standard
- `Comprehensive_Cyber_Security_Audit_Policy_Guidelines.pdf` — CERT-In Policy

### Embedding Pipeline
1. Extract text from PDFs using PyPDF2
2. Split into chunks (1000 chars with 100 char overlap)
3. Embed each chunk using Gemini `gemini-embedding-001`
4. Store vectors in ChromaDB with source metadata

---

## Project Structure

```
Compliance_Audit_Agent-master/
├── .env.example                     # Template for environment variables
├── docker-compose.yml               # Full stack orchestration
├── README.md
├── orchestrator/                    # n8n workflow config
├── services/
│   ├── telemetry_input_service/     # Real-time log watcher
│   │   ├── main.py
│   │   ├── data/buffer.json         # Log buffer (add entries here)
│   │   └── Dockerfile
│   ├── periodic_input_service/      # Batch log reader
│   │   ├── main.py
│   │   ├── periodic_data/           # Drop log files here
│   │   └── Dockerfile
│   ├── normalization_service/       # LLM-based ECS normalizer
│   │   ├── main.py
│   │   └── Dockerfile
│   ├── agent_service/               # Audit + compliance agent
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── llm_agent.py         # Audit statement generation
│   │   │   ├── compliance_checker.py # Compliance reasoning
│   │   │   └── embeddings.py        # ChromaDB RAG retrieval
│   │   ├── scripts/
│   │   │   └── embed_compliance_docs.py  # One-time embedding script
│   │   ├── data/compliance_docs/    # Compliance PDFs
│   │   └── Dockerfile
│   └── output_service/              # n8n webhook forwarder
│       ├── main.py
│       └── Dockerfile
└── streamlit_app/                   # Standalone dashboard
    ├── app.py                       # Main Streamlit UI
    ├── agent.py                     # LLM + RAG functions
    ├── normalizer.py                # Rule-based ECS normalizer
    ├── embed_setup.py               # Knowledge base builder
    ├── sample_logs/                 # Sample log files for testing
    ├── Dockerfile
    └── requirements.txt
```

---

## Design Highlights

- Event-driven, non-blocking architecture
- Agent-based reasoning instead of static rules
- Explainable AI outputs with evidence traceability
- Modular services for easy extension
- Two modes: full Kafka pipeline or standalone Streamlit

---

## Future Enhancements

- Multi-framework compliance mapping
- Confidence scoring per compliance control
- SOAR integration for automated remediation
- Human-in-the-loop approval workflows
- Compliance monitoring and visualization dashboard
- Real-time alerting via email/Slack through n8n

---

## License

This project is intended for educational and research purposes.
