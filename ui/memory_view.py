"""Memory & Personalization Controls View."""
import streamlit as st
from database.database import get_db
from database.crud import get_memories, save_memory, delete_memory
from memory.memory_manager import MemoryManager
from ui.components import render_header, render_metric_card


def render_memory_page():
    render_header(
        title="🧠 Student Memory & Personalization",
        subtitle="Manage long-term learning context, view saved preferences, and control private or sensitive information.",
        badge="Memory & Context Layer"
    )

    with get_db() as db:
        mem_mgr = MemoryManager(db)
        memories = get_memories(db)

    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric_card("Total Memory Items", str(len(memories)), "Persistent across sessions", border_color="#3B82F6")
    with c2:
        pref_count = sum(1 for m in memories if m.memory_type == "preference")
        render_metric_card("User Preferences", str(pref_count), "Study style & schedules", border_color="#10B981")
    with c3:
        diag_count = sum(1 for m in memories if m.memory_type in ("weakness", "strength", "active_goal"))
        render_metric_card("Academic Contexts", str(diag_count), "Diagnostic & mastery signals", border_color="#8B5CF6")

    # Add Fact / Preference Form
    with st.expander("➕ Store New Learning Fact or Preference", expanded=False):
        with st.form("add_memory_form"):
            mem_key = st.text_input("Memory Key *", placeholder="e.g. preferred_study_time, learning_style")
            mem_val = st.text_area("Value / Fact *", placeholder="e.g. I learn best with code examples and visual architecture diagrams.")
            mem_type = st.selectbox("Category", ["preference", "context", "active_goal", "weakness", "strength"])
            importance = st.slider("Importance Rank (1 highest, 5 lowest)", 1, 5, 3)

            submitted = st.form_submit_button("Save Memory Item", type="primary")
            if submitted:
                if not mem_key.strip() or not mem_val.strip():
                    st.error("Please provide both key and value.")
                else:
                    with get_db() as db:
                        mgr = MemoryManager(db)
                        res = mgr.store_fact(key=mem_key.strip(), value=mem_val.strip(), memory_type=mem_type, importance=importance)
                        if res:
                            st.success(f"Stored memory item: '{mem_key}'")
                        else:
                            st.warning("Content was flagged as potentially sensitive or confidential and was not stored.")
                    st.rerun()

    st.markdown("### 🗄️ Stored Student Memory Items")
    if not memories:
        st.info("No memory records stored yet. As you interact with the AI Tutor and complete goals, persistent context will appear here.")
        return

    for m in memories:
        with st.container():
            col_info, col_del = st.columns([0.88, 0.12])
            with col_info:
                type_badge = {
                    "preference": "#3B82F6",
                    "active_goal": "#10B981",
                    "weakness": "#EF4444",
                    "strength": "#059669",
                    "context": "#6B7280"
                }.get(m.memory_type, "#6B7280")
                
                st.markdown(
                    f"<span style='background:{type_badge}; color:white; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:bold;'>"
                    f"{m.memory_type.upper()}</span> &bull; <strong>{m.key}</strong> (Importance: {m.importance}/5)",
                    unsafe_allow_html=True
                )
                st.markdown(f"> {m.value}")
                if m.context:
                    st.caption(f"Context: {m.context}")
            with col_del:
                st.write("")
                if st.button("🗑️ Delete", key=f"del_mem_{m.id}"):
                    with get_db() as db:
                        delete_memory(db, m.id)
                    st.success("Memory deleted.")
                    st.rerun()
            st.markdown("---")
