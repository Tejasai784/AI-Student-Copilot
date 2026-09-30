import streamlit as st
from database.database import get_db
from database.crud import (
    get_subjects,
    get_subject_by_id,
    create_subject,
    delete_subject,
    get_topics_by_subject,
    add_topic,
    bulk_add_topics,
    toggle_topic_completion,
    delete_topic
)
from ui.components import render_header, render_empty_state

def render_subjects_page():
    """Renders the Subject and Syllabus Management page."""
    render_header(
        title="Subjects & Syllabus",
        subtitle="Organize your courses, units, and learning objectives.",
        badge="Curriculum"
    )

    tab1, tab2 = st.tabs(["📚 My Subjects", "➕ Add New Subject"])

    # ------------------------------------------------------------------------
    # TAB 1: VIEW & MANAGE SUBJECTS
    # ------------------------------------------------------------------------
    with tab1:
        with get_db() as db:
            subjects = get_subjects(db)

        if not subjects:
            render_empty_state(
                message="No subjects added yet.",
                action_text="Click on 'Add New Subject' to register your first course and syllabus.",
                icon="📚"
            )
        else:
            st.write(f"Total enrolled courses: **{len(subjects)}**")
            
            for subject in subjects:
                with st.expander(f"📘 **{subject.name}** ({subject.code}) — {subject.semester}", expanded=False):
                    col_info1, col_info2 = st.columns([3, 1])
                    with col_info1:
                        if subject.description:
                            st.caption(subject.description)
                    with col_info2:
                        if st.button("🗑️ Delete Subject", key=f"del_subj_{subject.id}", type="secondary"):
                            with get_db() as db:
                                delete_subject(db, subject.id)
                            st.success(f"Subject '{subject.name}' deleted.")
                            st.rerun()

                    st.markdown("##### Syllabus Units & Topics")
                    
                    with get_db() as db:
                        topics = get_topics_by_subject(db, subject.id)

                    if not topics:
                        st.info("No syllabus topics added for this subject yet.")
                    else:
                        # Group topics by unit
                        units = sorted(list(set(t.unit_number for t in topics)))
                        for unit in units:
                            st.markdown(f"**Unit {unit}**")
                            unit_topics = [t for t in topics if t.unit_number == unit]
                            for t in unit_topics:
                                c1, c2 = st.columns([0.85, 0.15])
                                with c1:
                                    is_checked = st.checkbox(
                                        label=t.topic_name,
                                        value=t.is_completed,
                                        key=f"topic_chk_{t.id}"
                                    )
                                    if is_checked != t.is_completed:
                                        with get_db() as db:
                                            toggle_topic_completion(db, t.id)
                                        st.rerun()
                                with c2:
                                    if st.button("✕", key=f"del_topic_{t.id}", help="Delete topic"):
                                        with get_db() as db:
                                            delete_topic(db, t.id)
                                        st.rerun()

                    # Add topic section inside subject
                    st.markdown("---")
                    st.markdown("###### Add Topics to this Subject")
                    
                    topic_mode = st.radio(
                        "Input format",
                        options=["Single Topic", "Bulk Add (Line-by-line)"],
                        key=f"topic_mode_{subject.id}",
                        horizontal=True
                    )

                    if topic_mode == "Single Topic":
                        with st.form(f"add_single_topic_{subject.id}"):
                            c_u, c_n = st.columns([1, 3])
                            with c_u:
                                unit_num = st.number_input("Unit No.", min_value=1, max_value=20, value=1, key=f"u_single_{subject.id}")
                            with c_n:
                                t_name = st.text_input("Topic Name", placeholder="e.g. Relational Algebra", key=f"t_single_{subject.id}")
                            
                            sub_btn = st.form_submit_button("Add Topic", type="primary")
                            if sub_btn:
                                if t_name.strip():
                                    with get_db() as db:
                                        add_topic(db, subject.id, int(unit_num), t_name)
                                    st.success(f"Topic '{t_name}' added!")
                                    st.rerun()
                                else:
                                    st.warning("Please enter a topic name.")
                    else:
                        with st.form(f"add_bulk_topics_{subject.id}"):
                            b_unit = st.number_input("Target Unit No.", min_value=1, max_value=20, value=1, key=f"b_unit_{subject.id}")
                            b_text = st.text_area(
                                "Topic List (one topic per line)",
                                placeholder="ER Diagrams\nRelational Schema\nIntegrity Constraints\nForeign Keys",
                                key=f"b_text_{subject.id}"
                            )
                            bulk_btn = st.form_submit_button("Bulk Add Topics", type="primary")
                            if bulk_btn:
                                lines = [line.strip() for line in b_text.splitlines() if line.strip()]
                                if lines:
                                    topics_data = [{"unit_number": int(b_unit), "topic_name": line} for line in lines]
                                    with get_db() as db:
                                        bulk_add_topics(db, subject.id, topics_data)
                                    st.success(f"Added {len(lines)} topics to Unit {b_unit}!")
                                    st.rerun()
                                else:
                                    st.warning("Please enter at least one topic line.")

    # ------------------------------------------------------------------------
    # TAB 2: ADD NEW SUBJECT FORM
    # ------------------------------------------------------------------------
    with tab2:
        with st.form("add_subject_form", clear_on_submit=True):
            st.subheader("Subject Information")
            
            c_code, c_sem = st.columns(2)
            with c_code:
                subj_name = st.text_input("Subject Name *", placeholder="e.g. Database Management Systems")
                subj_code = st.text_input("Subject Code *", placeholder="e.g. CS601")
            with c_sem:
                subj_semester = st.selectbox(
                    "Semester *",
                    options=[f"{i}{'st' if i==1 else 'nd' if i==2 else 'rd' if i==3 else 'th'} Semester" for i in range(1, 9)],
                    index=5
                )
                subj_desc = st.text_area("Description / Syllabus Outline (Optional)", placeholder="Brief overview of course topics...")

            st.markdown("<br>", unsafe_allow_html=True)
            submit_subj = st.form_submit_button("✨ Register Subject", use_container_width=True, type="primary")

            if submit_subj:
                if not subj_name.strip() or not subj_code.strip():
                    st.error("Please enter both Subject Name and Subject Code.")
                else:
                    with get_db() as db:
                        create_subject(
                            db=db,
                            name=subj_name,
                            code=subj_code,
                            semester=subj_semester,
                            description=subj_desc
                        )
                    st.success(f"Subject '{subj_name} ({subj_code})' created successfully!")
                    st.rerun()
