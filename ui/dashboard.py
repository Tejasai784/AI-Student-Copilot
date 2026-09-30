import streamlit as st
from database.database import get_db
from database.crud import get_dashboard_summary, get_subjects
from ui.components import render_header, render_metric_card, render_empty_state

def render_dashboard_page():
    """Renders the main student dashboard."""
    with get_db() as db:
        summary = get_dashboard_summary(db)
        subjects = get_subjects(db)

    student_name = summary.get("student_name")
    
    greeting = f"Welcome back, {student_name}!" if student_name else "Welcome to AI Student Copilot!"
    subtext = (
        f"{summary.get('course')} • {summary.get('branch')} • {summary.get('year')} ({summary.get('semester')})"
        if student_name
        else "Your personalized AI academic assistant for college courses, exam prep, and study planning."
    )
    
    render_header(
        title=greeting,
        subtitle=subtext,
        badge="Active" if student_name else "New Student"
    )

    if not student_name:
        st.info("💡 **Getting Started**: Set up your academic profile in the **Student Profile** tab to personalize your study experience.")

    # ------------------------------------------------------------------------
    # TOP METRICS ROW
    # ------------------------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_metric_card(
            title="Enrolled Subjects",
            value=str(summary.get("total_subjects", 0)),
            subtitle="Registered courses",
            border_color="#3B82F6"
        )
    with col2:
        render_metric_card(
            title="Syllabus Progress",
            value=f"{summary.get('study_progress', 0.0)}%",
            subtitle=f"{summary.get('completed_topics', 0)} of {summary.get('total_topics', 0)} topics done",
            border_color="#10B981"
        )
    with col3:
        render_metric_card(
            title="Study Materials",
            value=str(summary.get("total_materials", 0)),
            subtitle="Documents & PDFs (Phase 2)",
            border_color="#8B5CF6"
        )
    with col4:
        render_metric_card(
            title="Quiz Accuracy",
            value=f"{summary.get('quiz_accuracy', 0.0)}%",
            subtitle="Practice score (Phase 5)",
            border_color="#F59E0B"
        )

    # ------------------------------------------------------------------------
    # PROGRESS BAR & SYLLABUS STATUS
    # ------------------------------------------------------------------------
    st.markdown("### 📊 Learning Progress")
    progress_val = float(summary.get("study_progress", 0.0)) / 100.0
    st.progress(progress_val)

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("#### 📚 Enrolled Subjects Overview")
        if not subjects:
            render_empty_state(
                message="No subjects added yet.",
                action_text="Navigate to 'Subjects & Syllabus' in the sidebar to add your first course.",
                icon="📘"
            )
        else:
            for subj in subjects:
                total_t = len(subj.topics)
                done_t = sum(1 for t in subj.topics if t.is_completed)
                pct = round((done_t / total_t) * 100, 1) if total_t > 0 else 0.0
                
                with st.container():
                    st.markdown(
                        f"""
                        <div style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.8rem 1.2rem; margin-bottom: 0.6rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span style="font-weight: 600; color: #1E293B;">{subj.name}</span>
                                    <span style="color: #64748B; font-size: 0.85rem; margin-left: 8px;">({subj.code})</span>
                                </div>
                                <span style="font-size: 0.85rem; font-weight: 600; color: {'#10B981' if pct == 100 else '#3B82F6'};">{pct}% completed</span>
                            </div>
                            <div style="font-size: 0.8rem; color: #94A3B8; margin-top: 0.3rem;">
                                {done_t} of {total_t} syllabus topics completed • {subj.semester}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    with col_right:
        st.markdown("#### 🎯 Weak Topics & Focus Areas")
        weak_topics = summary.get("weak_topics", [])
        if not weak_topics:
            render_empty_state(
                message="No weak topics identified yet.",
                action_text="Weak topics are automatically detected after practice quizzes (Phase 5).",
                icon="🎯"
            )
        else:
            for wt in weak_topics:
                st.warning(f"⚠️ {wt.get('name')}: {wt.get('accuracy')}%")

        st.markdown("#### 📅 Upcoming Exams")
        render_empty_state(
            message="No upcoming exams scheduled.",
            action_text="Exam countdowns and revision alerts activate with the Study Planner.",
            icon="📅"
        )
