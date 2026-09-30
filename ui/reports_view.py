"""Reports & Readiness Evaluations View."""
import streamlit as st
from database.database import get_db
from database.crud import get_subjects
from services.report_service import generate_exam_readiness_report
from ui.components import render_header, render_metric_card


def render_reports_page():
    render_header(
        title="📑 Exam Readiness Reports",
        subtitle="Generate, review, and export certified academic readiness summaries and final revision checklists.",
        badge="Report & Export Engine"
    )

    with get_db() as db:
        subjects = get_subjects(db)

    subj_opts = {f"{s.name} ({s.code})": s.id for s in subjects} if subjects else {"General Studies": None}
    col1, col2 = st.columns([3, 1])
    with col1:
        chosen_label = st.selectbox("Select Target Subject for Readiness Report", list(subj_opts.keys()))
        chosen_id = subj_opts[chosen_label]
    with col2:
        st.write("")
        st.write("")
        gen_btn = st.button("Generate Readiness Report", type="primary", use_container_width=True)

    if gen_btn:
        with st.spinner("Synthesizing mastery diagnostics and generating readiness report..."):
            with get_db() as db:
                report_data = generate_exam_readiness_report(db, subject_id=chosen_id)
            st.session_state["active_report"] = report_data

    active_report = st.session_state.get("active_report")
    if active_report:
        st.markdown("---")
        st.markdown(f"### 📋 Readiness Assessment: {active_report.get('subject')}")
        st.metric("Certified Readiness Score", f"{active_report.get('readiness_score', 85.0):.1f}%")

        # Display Markdown
        st.markdown(active_report.get("markdown_report", ""))

        # Export controls
        c_exp1, c_exp2 = st.columns(2)
        with c_exp1:
            st.download_button(
                label="📥 Download Report as Markdown (.md)",
                data=active_report.get("markdown_report", ""),
                file_name=f"readiness_report_{active_report.get('subject', 'course').replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True
            )
        with c_exp2:
            st.download_button(
                label="🌐 Download Report as HTML (.html)",
                data=active_report.get("html_report", ""),
                file_name=f"readiness_report_{active_report.get('subject', 'course').replace(' ', '_')}.html",
                mime="text/html",
                use_container_width=True
            )
    else:
        st.info("Click 'Generate Readiness Report' to generate an exam readiness summary for your chosen subject.")
