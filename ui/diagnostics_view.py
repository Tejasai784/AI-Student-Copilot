"""Developer & Diagnostics Telemetry View."""
import streamlit as st
from datetime import datetime, timezone
from backend.config import settings
from database.database import get_db
from database.crud import get_agent_runs, get_documents, get_subjects, get_goals
from tools.registry import get_tool_registry
from rag.vector_store import get_vector_store
from services.llm_client import get_gemini_diagnostics
from ui.components import render_header, render_metric_card


def render_diagnostics_page():
    render_header(
        title="🛠️ Developer & Diagnostics Console",
        subtitle="Live platform telemetry, database inspection, registered tool registry, and raw agent execution logs.",
        badge="Telemetry & Telemetry Logs"
    )

    settings.reload()
    diag = get_gemini_diagnostics()

    # AI Provider Diagnostics Section (Requirement 9)
    st.markdown("### 🤖 AI Service & Gemini Diagnostics")
    c_diag1, c_diag2, c_diag3, c_diag4 = st.columns(4)
    with c_diag1:
        cfg_color = "#10B981" if diag["gemini_configured"] == "YES" else "#EF4444"
        render_metric_card("Gemini configured", diag["gemini_configured"], "API key presence check", border_color=cfg_color)
    with c_diag2:
        conn_color = "#10B981" if "SUCCESS" in diag["gemini_connection"] else "#EF4444"
        render_metric_card("Gemini connection", diag["gemini_connection"], "Live verification test", border_color=conn_color)
    with c_diag3:
        prov_color = "#10B981" if diag["active_provider"] == "Gemini" else "#3B82F6"
        render_metric_card("Active provider", diag["active_provider"], "Current operational engine", border_color=prov_color)
    with c_diag4:
        render_metric_card("Active model", diag["active_model"], "Configured LLM", border_color="#6366F1")

    st.markdown(f"""
- **Gemini configured:** `{diag['gemini_configured']}`
- **Gemini connection:** `{diag['gemini_connection']}`
- **Active provider:** `{diag['active_provider']}`
- **Active model:** `{diag['active_model']}`
""")

    reg = get_tool_registry()
    v_store = get_vector_store()
    tools_list = reg.list_tools()

    with get_db() as db:
        subjects = get_subjects(db)
        docs = get_documents(db)
        goals = get_goals(db)
        runs = get_agent_runs(db, limit=20)

    # System vitals
    st.markdown("### 📊 Platform Vitals")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Registered Tools", str(len(tools_list)), "Safe execution sandboxes", border_color="#3B82F6")
    with c2:
        render_metric_card("Vector Store Chunks", str(v_store.count()), "Indexed in .npy/.json", border_color="#10B981")
    with c3:
        render_metric_card("Total Documents", str(len(docs)), "Processed materials", border_color="#8B5CF6")
    with c4:
        render_metric_card("Multi-Agent Runs", str(len(runs)), "Executed state machines", border_color="#EC4899")

    # Registered Tools Table
    st.markdown("### 🧰 Registered Agent Tools")
    tool_data = [
        {"Tool Name": t["name"], "Description": t["description"], "Input Schema": str(t["parameters"].get("properties", {}).keys())}
        for t in tools_list
    ]
    st.table(tool_data)

    # Database Entity Stats
    st.markdown("### 🗄️ Database Entity Counts")
    st.markdown(f"""
    - **Registered Subjects:** {len(subjects)}
    - **Uploaded Documents:** {len(docs)}
    - **Student Goals:** {len(goals)}
    - **Multi-Agent Executions:** {len(runs)}
    - **Database Path:** `{settings.DATABASE_URL.split('///')[-1]}`
    - **Vector Store Directory:** `{settings.VECTOR_STORE_PATH}`
    """)

    # Raw Agent Execution Telemetry
    st.markdown("### 📜 Raw Agent Execution Runs")
    if runs:
        for r in runs[:5]:
            with st.expander(f"AgentRun #{r.id} &bull; {r.agent_name} [{r.status}]"):
                st.code(f"Input: {r.input_query}\nStatus: {r.status}\nStarted: {r.started_at}\nFinished: {r.finished_at}")
                if r.plan_json:
                    st.json(r.plan_json)
    else:
        st.info("No agent runs logged yet.")
