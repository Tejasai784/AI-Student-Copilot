"""Adaptive Study Planner View."""
import streamlit as st
from datetime import date, timedelta
from database.database import get_db
from database.crud import get_subjects
from database.academic_crud import get_active_study_plan, complete_study_task, get_upcoming_exams
from services.planner_service import generate_study_plan
from ui.components import render_header, render_metric_card


def render_planner_page():
    render_header(
        title="📅 Adaptive Study Planner",
        subtitle="Automated, personalized day-by-day timetables prioritizing upcoming exams and weak areas.",
        badge="Adaptive Timetable Engine"
    )

    with get_db() as db:
        subjects = get_subjects(db)
        active_plan = get_active_study_plan(db)
        upcoming_exams = get_upcoming_exams(db)

    # Controls to generate new study plan
    with st.expander("⚙️ Generate New Adaptive Study Plan", expanded=not bool(active_plan)):
        col1, col2, col3 = st.columns(3)
        with col1:
            horizon = st.selectbox("Schedule Horizon", ["weekly", "daily"], index=0)
        with col2:
            session_min = st.number_input("Session Length (min)", min_value=15, max_value=120, value=45, step=15)
        with col3:
            weekly_hrs = st.number_input("Weekly Study Target (hours)", min_value=2, max_value=40, value=10, step=2)

        exam_focus = st.text_input("Exam Focus / Special Goal (Optional)", placeholder="e.g. Final Semester Exams, Python Exam")

        if st.button("✨ Generate Optimized Timetable", type="primary", use_container_width=True):
            with st.spinner("Analyzing syllabus, upcoming exams, and weakness data..."):
                with get_db() as db:
                    new_plan = generate_study_plan(
                        db=db,
                        horizon=horizon,
                        session_minutes=int(session_min),
                        weekly_hours=int(weekly_hrs),
                        exam_focus=exam_focus
                    )
                st.success(f"Generated {new_plan.title} with {len(new_plan.tasks)} scheduled sessions!")
                st.rerun()

    if not active_plan:
        st.info("No active study plan. Click 'Generate New Adaptive Study Plan' above to build your personalized timetable.")
        return

    st.subheader(f"📌 Active Plan: {active_plan.title}")
    if active_plan.notes:
        st.caption(active_plan.notes)

    # Group tasks by scheduled date
    tasks_by_date = {}
    for task in active_plan.tasks:
        d = task.scheduled_date or date.today()
        if d not in tasks_by_date:
            tasks_by_date[d] = []
        tasks_by_date[d].append(task)

    sorted_dates = sorted(tasks_by_date.keys())
    
    # Progress overview
    total_tasks = len(active_plan.tasks)
    done_tasks = sum(1 for t in active_plan.tasks if t.status == "COMPLETED")
    pct = round((done_tasks / total_tasks * 100.0), 1) if total_tasks > 0 else 0.0

    c1, c2 = st.columns([3, 1])
    with c1:
        st.progress(pct / 100.0, text=f"Overall Plan Completion: {pct}% ({done_tasks}/{total_tasks} sessions)")
    with c2:
        st.metric("Total Study Time", f"{sum(t.duration_minutes for t in active_plan.tasks)} min")

    st.markdown("### 🗓️ Daily Timetable")
    for d in sorted_dates:
        is_today = (d == date.today())
        badge = "🔥 TODAY" if is_today else d.strftime("%A, %b %d")
        
        with st.container():
            st.markdown(f"#### {badge}")
            for t in tasks_by_date[d]:
                col_box, col_info = st.columns([0.08, 0.92])
                with col_box:
                    is_completed = (t.status == "COMPLETED")
                    toggled = st.checkbox("", value=is_completed, key=f"plan_task_{t.id}")
                    if toggled != is_completed:
                        with get_db() as db:
                            complete_study_task(db, t.id)
                        st.rerun()
                with col_info:
                    strike = "~~" if t.status == "COMPLETED" else ""
                    pri_color = "#DC2626" if t.priority == 1 else ("#F59E0B" if t.priority == 2 else "#2563EB")
                    st.markdown(
                        f"<span style='color:{pri_color}; font-weight:bold;'>[{t.task_type}]</span> "
                        f"{strike}<strong>{t.title}</strong>{strike} • {t.duration_minutes} mins",
                        unsafe_allow_html=True
                    )
                    if t.notes:
                        st.caption(t.notes)
            st.markdown("---")
