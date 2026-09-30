import streamlit as st
from database.database import get_db
from database.crud import get_student_profile, create_or_update_student_profile
from ui.components import render_header

def render_profile_page():
    """Renders the student profile page."""
    render_header(
        title="Student Profile",
        subtitle="Manage your academic background, degree, and semester information.",
        badge="Profile"
    )

    with get_db() as db:
        current_profile = get_student_profile(db)

        # Default values from existing profile if available
        default_name = current_profile.name if current_profile else ""
        default_course = current_profile.course if current_profile else ""
        default_branch = current_profile.branch if current_profile else ""
        default_year = current_profile.year if current_profile else "1st Year"
        default_semester = current_profile.semester if current_profile else "1st Semester"

    year_options = ["1st Year", "2nd Year", "3rd Year", "4th Year", "Postgraduate", "PhD"]
    semester_options = [f"{i}{'st' if i==1 else 'nd' if i==2 else 'rd' if i==3 else 'th'} Semester" for i in range(1, 9)]

    year_index = year_options.index(default_year) if default_year in year_options else 0
    sem_index = semester_options.index(default_semester) if default_semester in semester_options else 0

    with st.container():
        with st.form("student_profile_form", clear_on_submit=False):
            st.subheader("Academic Details")
            
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input(
                    "Full Name *",
                    value=default_name,
                    placeholder="e.g. Alex Mercer",
                    help="Your legal or preferred student name."
                )
                course = st.text_input(
                    "Degree / Course *",
                    value=default_course,
                    placeholder="e.g. B.Tech Computer Science, B.Sc Physics",
                    help="Your degree program."
                )
                branch = st.text_input(
                    "Branch / Specialization *",
                    value=default_branch,
                    placeholder="e.g. Artificial Intelligence & Data Science",
                    help="Your department or major specialization."
                )

            with col2:
                year = st.selectbox(
                    "Current Year *",
                    options=year_options,
                    index=year_index,
                    help="Select your current year of study."
                )
                semester = st.selectbox(
                    "Current Semester *",
                    options=semester_options,
                    index=sem_index,
                    help="Select your current semester."
                )

            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("💾 Save Profile", use_container_width=True, type="primary")

            if submitted:
                if not name.strip() or not course.strip() or not branch.strip():
                    st.error("Please fill in all required fields (Name, Course, Branch).")
                else:
                    with get_db() as db:
                        create_or_update_student_profile(
                            db=db,
                            name=name,
                            course=course,
                            branch=branch,
                            year=year,
                            semester=semester
                        )
                    st.success("Profile saved successfully!")
                    st.rerun()

    # Information summary card
    if current_profile:
        st.markdown("---")
        st.subheader("Current Active Profile")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown(f"**Name:** {current_profile.name}")
            st.markdown(f"**Course:** {current_profile.course}")
        with col_b:
            st.markdown(f"**Branch:** {current_profile.branch}")
            st.markdown(f"**Year:** {current_profile.year}")
        with col_c:
            st.markdown(f"**Semester:** {current_profile.semester}")
