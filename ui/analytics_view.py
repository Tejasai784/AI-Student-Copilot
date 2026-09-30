"""Performance Analytics & Weakness Detection View."""
import streamlit as st
import pandas as pd
import plotly.express as px
from database.database import get_db
from database.crud import get_subjects
from services.analytics_service import compute_performance, detect_weak_topics, generate_knowledge_map
from ui.components import render_header, render_metric_card


def render_analytics_page():
    render_header(
        title="📈 Progress & Weakness Analytics",
        subtitle="Visual performance diagnostic, automatic weakness identification, and knowledge graph mapping.",
        badge="Analytics & Diagnostics"
    )

    with get_db() as db:
        subjects = get_subjects(db)
        perf = compute_performance(db)
        weaknesses = detect_weak_topics(db)
        kmap = generate_knowledge_map(db)

    # Top Metric Overview
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Overall Accuracy", f"{perf.get('overall_accuracy', 0.0)}%", "Across mock assessments", border_color="#3B82F6")
    with c2:
        render_metric_card("Total Attempts", str(perf.get("total_attempts", 0)), "Graded sessions", border_color="#10B981")
    with c3:
        render_metric_card("Weak Topics Flagged", str(len(weaknesses)), "Requires reinforcement", border_color="#EF4444")
    with c4:
        render_metric_card("Knowledge Graph Nodes", str(kmap.get("total_nodes", 0)), "Connected syllabus concepts", border_color="#8B5CF6")

    # Tabs for analytics
    tab1, tab2, tab3 = st.tabs(["🚨 Detected Weaknesses", "📊 Accuracy Breakdown", "🗺️ Knowledge Graph Map"])

    with tab1:
        st.subheader("Identified Academic Weaknesses")
        if not weaknesses:
            st.success("🎉 No persistent weak topics detected! Your current diagnostic accuracy meets proficiency standards.")
        else:
            for w in weaknesses:
                with st.container():
                    st.markdown(
                        f"<div style='border: 1px solid #FECACA; background: #FEF2F2; padding: 12px; border-radius: 8px; margin-bottom: 10px;'>"
                        f"<strong style='color:#DC2626;'>⚠️ {w.get('topic_name')}</strong> &bull; Accuracy: <strong>{w.get('accuracy')}%</strong> ({w.get('subject')})<br>"
                        f"<span style='color:#7F1D1D;'>Reason: {w.get('reason')}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

    with tab2:
        st.subheader("Performance Breakdown")
        topic_mastery = perf.get("topic_mastery", [])
        if topic_mastery:
            df_topics = pd.DataFrame(topic_mastery)
            fig = px.bar(
                df_topics,
                x="topic_name",
                y="accuracy",
                color="accuracy",
                title="Topic Mastery Index (%)",
                color_continuous_scale="RdYlGn",
                labels={"topic_name": "Topic", "accuracy": "Accuracy (%)"}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Complete practice quizzes in 'Quizzes & Mock Exams' to generate performance charts.")

    with tab3:
        st.subheader("Knowledge Map & Topic Connectivity")
        nodes = kmap.get("nodes", [])
        edges = kmap.get("edges", [])
        st.caption(f"Knowledge Graph: {len(nodes)} concept nodes, {len(edges)} relational prerequisite edges.")

        for n in nodes:
            tier_color = "#059669" if n.get("tier") == "Mastered" else ("#F59E0B" if n.get("tier") == "Developing" else "#DC2626")
            st.markdown(
                f"- **{n.get('label')}** ({n.get('type')}) &bull; Status: <span style='color:{tier_color}; font-weight:bold;'>{n.get('tier', 'Standard')}</span>",
                unsafe_allow_html=True
            )
