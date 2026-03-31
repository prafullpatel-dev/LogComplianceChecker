# 🛡️ Compliance Audit Agent — Streamlit App

A simple, end-to-end AI compliance checker with no Kafka or Docker required.

---

## ⚡ Quick Start

### 1. Install dependencies

```bash
cd streamlit_app
pip install -r requirements.txt
```

### 2. Get a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key (it's free)
3. Copy it — you'll paste it into the app sidebar

### 3. Run the app

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## 🔧 First-Time Setup (IMPORTANT — Do Once)

Before you can audit any logs, you need to build the knowledge base.

1. Open the app in your browser
2. Paste your **Gemini API Key** in the sidebar
3. Click **"▶ Run Knowledge Base Setup"** in the sidebar
4. Wait ~5–10 minutes (it reads the PDFs, calls Gemini to chunk them, then embeds everything)
5. You'll see "X policy clauses indexed" in the sidebar when done

> This only needs to be done **once**. The knowledge base is saved to `streamlit_app/chroma_store/`.

---

## 📂 How to Use

### Option A — Upload a Log File

- Go to **📤 Audit Logs** tab
- Upload a `.json` or `.csv` log file
- The system auto-detects the log type from the filename, or you can select it manually
- Set max logs (default 10 to avoid rate limits)
- Click **🔍 Run Compliance Audit**
- View color-coded results + download as JSON

### Option B — Paste a Single Log

- Go to **✍️ Manual Entry** tab
- Paste any raw log JSON
- Click **🔍 Audit This Log**
- Instant result

---

## 🗂️ Sample Log Files

Ready-to-use test files are in `sample_logs/`:

| File | Type | Contents |
|---|---|---|
| `sample_siem_logs.json` | SIEM | File modification, login failures, port scans |
| `sample_firewall_logs.json` | Firewall | Blocked SSH, allowed HTTPS, RDP traffic |

---

## 📚 Compliance Documents

PDFs used as the knowledge base are in:
```
services/agent_service/vector_db/compliance_docs/
├── iso-27001.pdf
└── Comprehensive_Cyber_Security_Audit_Policy_Guidelines.pdf
```

You can add more PDFs there and re-run setup to include them.

---

## 🧠 How It Works (Pipeline)

```
Upload Log File
      ↓
Normalize (ECS format)
      ↓
Gemini → Human-readable Audit Statement
      ↓
ChromaDB (RAG) → Relevant Policy Clauses
      ↓
Gemini → Compliance Verdict (Compliant / Partial / Non-Compliant)
      ↓
Show Results + Export
```

---

## ⚠️ Rate Limits

Google Gemini Free tier has **rate limits**. If you process many logs:
- Use the `max_logs` slider to limit batch size (10 at a time is safe)
- If you see rate limit errors, wait 60 seconds and try again
- The 1-second delay between logs is built in to help with this
