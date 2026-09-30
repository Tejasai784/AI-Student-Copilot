"""Agents & Execution Trace View.
Shows real-time multi-agent execution graphs, tool invocation audits, and critic evaluation scores.
Goal -> Plan -> Current Task -> Agent -> Tool -> Result -> Evaluation -> Final Output.
"""
import streamlit as st
import json
from database.database import get_db
from database.crud import get_agent_runs, get_subjects
from agents.orchestrator import route_request
from ui.components import render_header, render_metric_card


def render_agents_trace_page():
    render_header(
        title="🤖 Agents & Execution Trace",
        subtitle="Transparent, explainable multi-agent orchestration showing real-time state machines, tool calls, and critic rubrics.",
        badge="Multi-Agent Orchestrator"
    )

    with get_db() as db:
        subjects = get_subjects(db)
        runs = get_agent_runs(db, limit=10)

    # Interactive Orchestrator Console
    st.markdown("### ⚡ Interactive Multi-Agent Goal Execution")
    col_q, col_s = st.columns([3, 1])
    with col_q:
        agent_query = st.text_input(
            "Query or Exam Objective for Multi-Agent System:",
            value="Prepare me for my Python exam in 7 days. Focus on data structures, functions, and exam practice.",
            placeholder="e.g. Explain 3NF and calculate BCNF decomposition, or test Python code"
        )
    with col_s:
        subj_map = {"Auto-Detect": None, **{f"{s.name} ({s.code})": s.id for s in subjects}}
        chosen_label = st.selectbox("Subject Filter", list(subj_map.keys()))
        chosen_id = subj_map[chosen_label]

    if st.button("🚀 Run Multi-Agent Orchestration", type="primary", use_container_width=True):
        if not agent_query.strip():
            st.warning("Please enter a query or goal.")
        else:
            with st.spinner("🤖 Orchestrator coordinating specialist agents, tool calls, and critic evaluation..."):
                with get_db() as db:
                    result = route_request(db=db, query=agent_query.strip(), extra={"subject_id": chosen_id})

            st.success("✅ Multi-Agent Orchestration Completed Successfully!")

            # ----------------------------------------------------------------
            # EXPLAINABLE EXECUTION TRACE
            # Goal -> Plan -> Current Task -> Agent -> Tool -> Result -> Evaluation -> Final Output
            # ----------------------------------------------------------------
            st.markdown("### 🧭 Explainable Execution Trace")
            st.caption("Visual breakdown of the deterministic state machine graph:")

            for step in result.execution_trace:
                stage_color = {
                    "Goal": "#3B82F6",
                    "Plan": "#6366F1",
                    "Agent": "#8B5CF6",
                    "Tool": "#EC4899",
                    "Result": "#10B981",
                    "Critic": "#F59E0B",
                    "Revision": "#EF4444",
                    "Final": "#059669"
                }.get(step.stage, "#64748B")

                with st.container():
                    st.markdown(
                        f"<div style='border-left: 4px solid {stage_color}; padding-left: 12px; margin-bottom: 8px; background: #F8FAFC; padding: 10px; border-radius: 6px;'>"
                        f"<strong>[{step.timestamp}] Step {step.step_id} &bull; <span style='color:{stage_color}'>{step.stage.upper()}</span> ({step.agent_name})</strong><br>"
                        f"<span>{step.action_description}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    if step.details:
                        with st.expander(f"View Step {step.step_id} Telemetry", expanded=False):
                            st.json(step.details)

            # Combined Final Output
            st.markdown("### 📋 Orchestrated Output & Specialist Synthesis")
            st.markdown(result.combined_summary)

            if result.evaluation:
                st.markdown("### ⚖️ Critic Agent Quality Rubric")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Factual Consistency", f"{int(result.evaluation.factual_consistency * 100)}%")
                with c2:
                    st.metric("Completeness", f"{int(result.evaluation.completeness * 100)}%")
                with c3:
                    st.metric("Relevance", f"{int(result.evaluation.relevance * 100)}%")
                st.caption(f"**Feedback:** {result.evaluation.feedback}")

    st.markdown("---")
    st.markdown("### 📜 Past Agent Runs History")
    if not runs:
        st.info("No prior agent executions recorded.")
    else:
        for r in runs:
            with st.expander(f"Run #{r.id}: {r.agent_name} &bull; {r.input_query[:60]} ({r.status})"):
                st.write(f"**Started:** {r.started_at}")
                st.write(f"**Status:** {r.status} (Retries: {r.retry_count})")
                st.write(f"**Tool Invocations:** {len(r.tool_calls)}")
                if r.execution_trace_json:
                    try:
                        trace_data = json.loads(r.execution_trace_json)
                        st.json(trace_data)
                    except Exception:
                        pass
                if r.output_result:
                    st.markdown("**Output Excerpt:**")
                    st.text(r.output_result[:500] + "...")
