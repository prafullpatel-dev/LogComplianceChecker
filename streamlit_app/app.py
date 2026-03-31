"""
app.py — Compliance Audit Agent (Streamlit)
A clean, end-to-end compliance checking app without Kafka or Docker.
"""

import os
import json
import time
import streamlit as st
import pandas as pd
import chromadb

from normalizer import normalize_log, detect_source_type_from_filename
from agent import run_full_audit

# ──────────────────────────────────────────────────────────────────────────────
# PATHS
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_store")
COMPLIANCE_DOCS_PATH = os.path.join(
    BASE_DIR, "..", "services", "agent_service", "data", "compliance_docs"
)

# ──────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Compliance Audit Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS — Premium Dark Theme
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Main background */
.stApp {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1526 50%, #0a1020 100%);
    color: #e2e8f0;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1526 0%, #111827 100%);
    border-right: 1px solid rgba(99,179,237,0.15);
}
[data-testid="stSidebar"] * {
    color: #cbd5e1 !important;
}

/* Header banner */
.hero-banner {
    background: linear-gradient(135deg, #1e3a5f 0%, #0f2d4a 50%, #1a3a5c 100%);
    border: 1px solid rgba(99,179,237,0.25);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
.hero-banner h1 {
    font-size: 2.2rem;
    font-weight: 700;
    background: linear-gradient(90deg, #63b3ed, #90cdf4, #4fd1c7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 0.3rem 0;
}
.hero-banner p {
    color: #94a3b8;
    font-size: 1rem;
    margin: 0;
}

/* Cards */
.card {
    background: rgba(17, 25, 40, 0.85);
    border: 1px solid rgba(99,179,237,0.15);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    transition: border-color 0.2s ease;
}
.card:hover {
    border-color: rgba(99,179,237,0.35);
}

/* Verdict badges */
.badge {
    display: inline-block;
    padding: 0.35rem 1rem;
    border-radius: 999px;
    font-weight: 600;
    font-size: 0.85rem;
    letter-spacing: 0.02em;
}
.badge-compliant {
    background: rgba(16,185,129,0.15);
    color: #34d399;
    border: 1px solid rgba(52,211,153,0.3);
}
.badge-partially {
    background: rgba(245,158,11,0.15);
    color: #fbbf24;
    border: 1px solid rgba(251,191,36,0.3);
}
.badge-noncompliant {
    background: rgba(239,68,68,0.15);
    color: #f87171;
    border: 1px solid rgba(248,113,113,0.3);
}
.badge-unknown {
    background: rgba(148,163,184,0.15);
    color: #94a3b8;
    border: 1px solid rgba(148,163,184,0.3);
}

/* Result row */
.result-row {
    background: rgba(17, 25, 40, 0.9);
    border: 1px solid rgba(99,179,237,0.12);
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 0.75rem;
}
.result-statement {
    font-size: 0.95rem;
    color: #e2e8f0;
    margin-bottom: 0.5rem;
    font-weight: 500;
}
.result-reason {
    font-size: 0.83rem;
    color: #94a3b8;
    margin-top: 0.4rem;
}

/* Section headers */
.section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #63b3ed;
    border-bottom: 1px solid rgba(99,179,237,0.2);
    padding-bottom: 0.4rem;
    margin-bottom: 1rem;
}

/* Stat boxes */
.stat-box {
    background: rgba(17,25,40,0.8);
    border: 1px solid rgba(99,179,237,0.15);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    text-align: center;
}
.stat-number {
    font-size: 2rem;
    font-weight: 700;
}
.stat-label {
    font-size: 0.78rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Streamlit overrides */
.stButton > button {
    background: linear-gradient(135deg, #2b6cb0, #2c5282) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.55rem 1.5rem !important;
    transition: all 0.2s ease !important;
    width: 100%;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #3182ce, #2b6cb0) !important;
    box-shadow: 0 0 12px rgba(99,179,237,0.3) !important;
}

div[data-testid="stFileUploader"] {
    background: rgba(17,25,40,0.7);
    border: 1px dashed rgba(99,179,237,0.3);
    border-radius: 10px;
    padding: 0.5rem;
}

div[data-testid="stTextInput"] input {
    background: rgba(17,25,40,0.8) !important;
    border: 1px solid rgba(99,179,237,0.2) !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
}

div[data-testid="stSelectbox"] select {
    background: rgba(17,25,40,0.8) !important;
    color: #e2e8f0 !important;
}

.stExpander {
    border: 1px solid rgba(99,179,237,0.12) !important;
    border-radius: 8px !important;
    background: rgba(17,25,40,0.6) !important;
}

/* Progress steps */
.step-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.82rem;
    color: #64748b;
    margin-bottom: 0.3rem;
}
.step-indicator.done { color: #34d399; }
.step-indicator.active { color: #63b3ed; }

/* Scrollable results area */
.results-container {
    max-height: 600px;
    overflow-y: auto;
    padding-right: 0.5rem;
}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def verdict_badge(verdict: str) -> str:
    v = verdict.lower()
    if "non" in v:
        return '<span class="badge badge-noncompliant">🔴 Non-Compliant</span>'
    elif "partial" in v:
        return '<span class="badge badge-partially">🟡 Partially Compliant</span>'
    elif "compliant" in v:
        return '<span class="badge badge-compliant">🟢 Compliant</span>'
    else:
        return '<span class="badge badge-unknown">⚪ Unknown</span>'


def get_chroma_doc_count() -> int:
    try:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        col = client.get_or_create_collection("audit_docs")
        return col.count()
    except Exception:
        return 0


def parse_uploaded_file(uploaded_file) -> list[dict]:
    """Parse uploaded JSON or CSV into a list of log dicts."""
    filename = uploaded_file.name
    if filename.endswith(".json"):
        content = json.loads(uploaded_file.read().decode("utf-8"))
        if isinstance(content, list):
            return content
        elif isinstance(content, dict):
            return [content]
    elif filename.endswith(".csv"):
        df = pd.read_csv(uploaded_file).fillna("")
        return df.to_dict(orient="records")
    return []


# ──────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛡️ Compliance Audit")
    st.markdown("---")

    st.markdown("### 🔑 API Configuration")
    api_key = st.text_input(
        "Groq API Key",
        type="password",
        placeholder="gsk_...",
        help="Get your key from console.groq.com",
    )

    if api_key:
        st.success("✅ API Key set")
    else:
        st.warning("⚠️ API Key required")

    st.markdown("---")

    # Knowledge Base Status
    doc_count = get_chroma_doc_count()
    st.markdown("### 📚 Knowledge Base")
    if doc_count > 0:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number" style="color:#34d399;">{doc_count}</div>
            <div class="stat-label">Policy Clauses Indexed</div>
        </div>
        """, unsafe_allow_html=True)
        st.caption("✅ Ready to audit logs.")
    else:
        st.markdown("""
        <div class="stat-box">
            <div class="stat-number" style="color:#f87171;">0</div>
            <div class="stat-label">Knowledge Base Empty</div>
        </div>
        """, unsafe_allow_html=True)
        st.warning("Run setup first:")
        st.code("python embed_setup.py", language="bash")
        st.caption("Run this once in your terminal from the `streamlit_app/` folder before starting the app. No API key needed.")

    st.markdown("---")
    st.markdown("### 📋 Compliance Docs")
    try:
        pdf_files = [f for f in os.listdir(COMPLIANCE_DOCS_PATH) if f.endswith(".pdf")]
        for pdf in pdf_files:
            st.caption(f"📄 {pdf}")
    except Exception:
        st.caption("compliance_docs folder not found")


# ──────────────────────────────────────────────────────────────────────────────
# MAIN HEADER
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-banner">
    <h1>🛡️ AI Compliance Audit Agent</h1>
    <p>Upload security logs → Get instant AI-powered compliance verdicts (Groq Llama 3.3 + RAG) against ISO 27001 & Cybersecurity Audit Policy</p>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# TABS
# ──────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📤 Audit Logs", "✍️ Manual Entry", "ℹ️ How It Works"])


# ──────────────────────────────────────────────────────────
# TAB 1: FILE UPLOAD
# ──────────────────────────────────────────────────────────
with tab1:
    col_upload, col_options = st.columns([2, 1])

    with col_upload:
        st.markdown('<div class="section-title">Upload Log File</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Drop your log file here",
            type=["json", "csv"],
            help="JSON: list of log objects. CSV: one log per row.",
            label_visibility="collapsed",
        )

    with col_options:
        st.markdown('<div class="section-title">Options</div>', unsafe_allow_html=True)
        source_type_override = st.selectbox(
            "Log Source Type",
            ["Auto-detect from filename", "siem", "edr", "firewall", "network_monitoring", "asset_management"],
        )
        max_logs = st.slider("Max logs to process", 1, 50, 10)

    if uploaded_file and api_key:
        st.markdown("---")

        # Parse file
        try:
            logs = parse_uploaded_file(uploaded_file)
        except Exception as e:
            st.error(f"Failed to parse file: {e}")
            logs = []

        if not logs:
            st.warning("No logs found in file.")
        else:
            # Determine source type
            if source_type_override == "Auto-detect from filename":
                source_type = detect_source_type_from_filename(uploaded_file.name)
            else:
                source_type = source_type_override

            logs_to_process = logs[:max_logs]

            st.markdown(f"""
            <div class="card">
                📂 <b>{uploaded_file.name}</b> &nbsp;|&nbsp;
                🏷️ Source: <b>{source_type}</b> &nbsp;|&nbsp;
                📊 {len(logs)} logs found &nbsp;|&nbsp;
                ⚡ Processing <b>{len(logs_to_process)}</b>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🔍 Run Compliance Audit", key="audit_btn"):
                if get_chroma_doc_count() == 0:
                    st.error("⚠️ Knowledge base is empty. Run `python embed_setup.py` in your terminal first.")
                else:
                    results = []
                    errors = []

                    overall_progress = st.progress(0, text="Starting audit...")
                    status_text = st.empty()

                    for i, raw_log in enumerate(logs_to_process):
                        status_text.markdown(
                            f'<div class="step-indicator active">⚙️ Processing log {i+1} of {len(logs_to_process)}...</div>',
                            unsafe_allow_html=True,
                        )

                        # Ensure source_type is set on the log
                        if "source_type" not in raw_log:
                            raw_log["source_type"] = source_type

                        # Normalize
                        normalized = normalize_log(raw_log)

                        # Full audit (LLM + RAG)
                        try:
                            result = run_full_audit(normalized, api_key, CHROMA_PATH)
                            result["log_index"] = i + 1
                            results.append(result)
                        except Exception as e:
                            errors.append(f"Log {i+1}: {e}")

                        overall_progress.progress((i + 1) / len(logs_to_process))
                        time.sleep(0.3)  # Rate limit buffer

                    overall_progress.empty()
                    status_text.empty()

                    # ── Summary Stats ──────────────────────────────
                    if results:
                        compliant_n = sum(1 for r in results if "non" not in r["is_compliant"].lower() and "partial" not in r["is_compliant"].lower() and r["is_compliant"] != "unknown")
                        partial_n = sum(1 for r in results if "partial" in r["is_compliant"].lower())
                        noncompliant_n = sum(1 for r in results if "non" in r["is_compliant"].lower())

                        st.markdown("### 📊 Audit Summary")
                        s1, s2, s3, s4 = st.columns(4)
                        with s1:
                            st.markdown(f"""
                            <div class="stat-box">
                                <div class="stat-number" style="color:#63b3ed;">{len(results)}</div>
                                <div class="stat-label">Logs Audited</div>
                            </div>""", unsafe_allow_html=True)
                        with s2:
                            st.markdown(f"""
                            <div class="stat-box">
                                <div class="stat-number" style="color:#34d399;">{compliant_n}</div>
                                <div class="stat-label">Compliant</div>
                            </div>""", unsafe_allow_html=True)
                        with s3:
                            st.markdown(f"""
                            <div class="stat-box">
                                <div class="stat-number" style="color:#fbbf24;">{partial_n}</div>
                                <div class="stat-label">Partial</div>
                            </div>""", unsafe_allow_html=True)
                        with s4:
                            st.markdown(f"""
                            <div class="stat-box">
                                <div class="stat-number" style="color:#f87171;">{noncompliant_n}</div>
                                <div class="stat-label">Non-Compliant</div>
                            </div>""", unsafe_allow_html=True)

                        st.markdown("---")
                        st.markdown("### 📋 Detailed Results")

                        for r in results:
                            badge = verdict_badge(r["is_compliant"])
                            with st.expander(f"Log #{r['log_index']} — {r['audit_statement'][:100]}...", expanded=False):
                                st.markdown(f"**Verdict:** {badge}", unsafe_allow_html=True)
                                st.markdown(f"**Audit Statement:**")
                                st.info(r["audit_statement"])
                                st.markdown(f"**Reason:**")
                                st.write(r["reason"])
                                with st.expander("📄 Normalized Log (ECS)"):
                                    st.json(r["normalized_log"])
                                with st.expander("📚 Policy Context Retrieved"):
                                    st.text(r["context_used"])

                        # Export
                        st.markdown("---")
                        st.markdown("### 💾 Export Results")
                        export_data = [
                            {
                                "log_index": r["log_index"],
                                "audit_statement": r["audit_statement"],
                                "is_compliant": r["is_compliant"],
                                "reason": r["reason"],
                            }
                            for r in results
                        ]
                        st.download_button(
                            "⬇️ Download Results as JSON",
                            data=json.dumps(export_data, indent=2),
                            file_name="compliance_audit_results.json",
                            mime="application/json",
                        )

                    if errors:
                        st.markdown("### ⚠️ Errors")
                        for err in errors:
                            st.error(err)

    elif uploaded_file and not api_key:
        st.warning("⚠️ Please enter your Groq API Key in the sidebar to run the audit.")

    elif not uploaded_file:
        st.markdown("""
        <div class="card" style="text-align:center; padding: 3rem; color:#64748b;">
            <div style="font-size:3rem;">📂</div>
            <div style="font-size:1.1rem; margin-top:0.75rem;">Upload a JSON or CSV log file to get started</div>
            <div style="font-size:0.85rem; margin-top:0.5rem;">
                Supports: SIEM, EDR, Firewall, Network Monitoring, Asset Management logs
            </div>
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
# TAB 2: MANUAL LOG ENTRY
# ──────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-title">Manually Enter a Log Entry</div>', unsafe_allow_html=True)
    st.caption("Paste a raw log JSON below to instantly audit a single event.")

    default_log = json.dumps({
        "timestamp": "2025-11-04T10:12:10Z",
        "src_ip": "10.0.0.8",
        "dest_ip": "10.0.0.15",
        "event_type": "file_modified",
        "severity": "high",
        "msg": "Critical system file modified: /etc/passwd",
        "user": "root",
        "hostname": "sec-srv-1",
        "device_vendor": "Splunk",
        "source_type": "siem"
    }, indent=2)

    manual_log_text = st.text_area(
        "Log JSON",
        value=default_log,
        height=280,
        label_visibility="collapsed",
    )

    if st.button("🔍 Audit This Log", key="manual_audit_btn"):
        if not api_key:
            st.error("Please enter your Groq API Key in the sidebar.")
        elif get_chroma_doc_count() == 0:
            st.error("⚠️ Knowledge base is empty. Run `python embed_setup.py` in your terminal first.")
        else:
            try:
                raw_log = json.loads(manual_log_text)
                normalized = normalize_log(raw_log)

                with st.spinner("🤖 Running audit..."):
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.markdown('<div class="step-indicator active">①  Normalizing log...</div>', unsafe_allow_html=True)
                    with col_b:
                        st.markdown('<div class="step-indicator">②  Generating audit statement...</div>', unsafe_allow_html=True)
                    with col_c:
                        st.markdown('<div class="step-indicator">③  Checking compliance...</div>', unsafe_allow_html=True)

                    result = run_full_audit(normalized, api_key, CHROMA_PATH)

                st.markdown("---")
                badge = verdict_badge(result["is_compliant"])

                st.markdown(f"""
                <div class="card">
                    <div style="font-size:1.5rem; margin-bottom:0.5rem;">{badge}</div>
                    <div class="result-statement">📝 {result['audit_statement']}</div>
                    <div class="result-reason">💬 {result['reason']}</div>
                </div>
                """, unsafe_allow_html=True)

                c1, c2 = st.columns(2)
                with c1:
                    with st.expander("📄 Normalized Log (ECS Format)"):
                        st.json(result["normalized_log"])
                with c2:
                    with st.expander("📚 Policy Context Retrieved"):
                        st.text(result["context_used"])

            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")
            except Exception as e:
                st.error(f"Audit failed: {e}")


# ──────────────────────────────────────────────────────────
# TAB 3: HOW IT WORKS
# ──────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-title">How This System Works</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card">
        <b>Step 1 — Upload Logs</b><br/>
        Upload a <code>.json</code> or <code>.csv</code> file containing raw security/firewall logs.
        The system auto-detects the log type (SIEM, EDR, Firewall, etc.) from the filename.
    </div>
    <div class="card">
        <b>Step 2 — Normalize (ECS Format)</b><br/>
        Raw logs have different field names depending on the source. The normalizer converts them all into
        <b>Elastic Common Schema (ECS)</b> — a single consistent format. This makes cross-source comparison possible.
    </div>
    <div class="card">
        <b>Step 3 — Generate Audit Statement</b><br/>
        Google Gemini reads the normalized log JSON and converts it into a plain English sentence:
        <br/><i>"Root user modified /etc/passwd on sec-srv-1 at 10:12 UTC..."</i>
    </div>
    <div class="card">
        <b>Step 4 — RAG: Retrieve Relevant Policies</b><br/>
        The audit statement is embedded into a vector. ChromaDB searches its knowledge base
        (ISO 27001, Cyber Security Policy) for the top 3 most relevant compliance clauses semantically.
    </div>
    <div class="card">
        <b>Step 5 — Compliance Reasoning</b><br/>
        Gemini receives both the audit statement AND the retrieved policy clauses. It reasons about
        whether the action is <b>Compliant / Partially Compliant / Non-Compliant</b> and explains why.
    </div>
    <div class="card">
        <b>Step 6 — View & Export Results</b><br/>
        Results are shown with color-coded badges and expandable details. You can export everything as JSON.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-title" style="margin-top:1.5rem;">Supported Log Types</div>', unsafe_allow_html=True)
    data = {
        "Log Type": ["siem", "edr", "firewall", "network_monitoring", "asset_management"],
        "Source System": ["Splunk, ArcSight, QRadar", "CrowdStrike, Carbon Black", "Cisco ASA, Palo Alto, pfSense", "Network monitors, Ping tools", "IT Asset Management systems"],
        "Filename Keyword": ["siem", "edr", "firewall / fw", "network / monitor", "patch / asset"],
    }
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
