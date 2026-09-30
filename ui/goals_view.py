"""My Goals & Subtasks View."""
import streamlit as st
from database.database import get_db
from database.crud import get_goals, get_goal_by_id, create_goal, create_task, toggle_task_completion, get_subjects
from services.goal_service import create_goal_and_tasks_from_prompt
from services.autonomous_workflow import AutonomousLearningCoordinator
from ui.components import render_header, render_metric_card


def render_goals_page():
    render_header(
        title="🎯 My Academic Goals",
        subtitle="Define high-level exam goals, decompose into actionable tasks, and run autonomous preparation.",
        badge="Autonomous Goal Engine"
    )

    with get_db() as db:
        subjects = get_subjects(db)
        goals = get_goals(db)

    # Quick One-Click Autonomous Goal Launcher
    st.markdown("### ⚡ Quick Autonomous Exam Preparation")
    st.info("💡 **Primary Acceptance Goal**: Test the full 15-step autonomous multi-agent pipeline with a single click.")
    
    col_a, col_b = st.columns([3, 1])
    with col_a:
        quick_prompt = st.text_input(
            "High-Level Student Goal",
            value="Prepare me for my Python exam in 7 days. I have uploaded my syllabus and previous question papers.",
            help="High-level student goal that triggers autonomous planning, material inspection, quiz generation, and evaluation."
        )
    with col_b:
        st.write("")
        st.write("")
        if st.button("🚀 Launch Autonomous Prep", type="primary", use_container_width=True):
            with st.spinner("🤖 Coordinating 15-step autonomous multi-agent pipeline..."):
                with get_db() as db:
                    coord = AutonomousLearningCoordinator(db=db)
                    res = coord.run_full_preparation_workflow(quick_prompt)
                st.success(f"🎉 Successfully prepared workflow for {res['subject']}! Readiness Index: {res['readiness_score']}%")
                st.rerun()

    st.markdown("---")

    # Custom Goal Creation
    with st.expander("➕ Define a New Custom Goal", expanded=False):
        with st.form("new_goal_form"):
            goal_title = st.text_input("Goal Title *", placeholder="e.g. Master DBMS Normalization and SQL in 5 days")
            goal_obj = st.text_area("Objective & Scope", placeholder="Cover 1NF through BCNF, solve 10 previous exam problems...")
            
            c1, c2 = st.columns(2)
            with c1:
                subj_opts = {"None / General": None, **{f"{s.name} ({s.code})": s.id for s in subjects}}
                chosen_subj_label = st.selectbox("Linked Subject", list(subj_opts.keys()))
                chosen_subj_id = subj_opts[chosen_subj_label]
            with c2:
                days_input = st.number_input("Target Window (Days)", min_value=1, max_value=30, value=7)

            submitted = st.form_submit_button("Create & Decompose Goal", type="primary")
            if submitted:
                if not goal_title.strip():
                    st.error("Please enter a goal title.")
                else:
                    with get_db() as db:
                        create_goal_and_tasks_from_prompt(
                            db=db,
                            prompt=f"{goal_title}. {goal_obj} Target: {days_input} days.",
                            subject_id=chosen_subj_id
                        )
                    st.success(f"Created goal '{goal_title}' with automated subtask breakdown!")
                    st.rerun()

    # Active Goals List
    st.subheader(f"Active Goals ({len(goals)})")
    if not goals:
        st.info("No active goals yet. Launch a quick prep above or define a custom goal to start tracking progress.")
        return

    for goal in goals:
        with st.container():
            st.markdown(f"#### 🎯 {goal.title}")
            st.caption(f"**Objective:** {goal.objective}")
            
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.progress(goal.progress_percentage / 100.0, text=f"Progress: {goal.progress_percentage:.1f}%")
            with c2:
                st.caption(f"Status: **{goal.status}**")
            with c3:
                deadline_str = goal.deadline.strftime("%Y-%m-%d") if goal.deadline else "No deadline"
                st.caption(f"Deadline: **{deadline_str}**")

            # Subtasks checklist
            st.markdown("**Actionable Subtasks:**")
            for t in goal.tasks:
                task_col1, task_col2, task_col3 = st.columns([0.1, 0.7, 0.2])
                with task_col1:
                    is_done = (t.status == "COMPLETED")
                    toggled = st.checkbox("", value=is_done, key=f"goal_{goal.id}_task_{t.id}")
                    if toggled != is_done:
                        with get_db() as db:
                            toggle_task_completion(db, t.id)
                        st.rerun()
                with task_col2:
                    strike = "~~" if t.status == "COMPLETED" else ""
                    st.markdown(f"{strike}**{t.title}**{strike} — _{t.agent_assigned}_ ({t.effort_estimate_minutes} min)")
                    if t.description:
                        st.caption(t.description)
                with task_col3:
                    if t.scheduled_date:
                        st.caption(f"📅 {t.scheduled_date}")

            st.markdown("---")
