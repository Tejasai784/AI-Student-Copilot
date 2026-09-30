import pytest
from database.database import Base, engine, get_db, init_db
from database.crud import (
    get_student_profile,
    create_or_update_student_profile,
    get_subjects,
    create_subject,
    add_topic,
    toggle_topic_completion,
    get_dashboard_summary
)

def test_full_phase1_workflow(db_session):
    # Step 1: Initial empty state check (no hardcoded fake student)
    initial_profile = get_student_profile(db_session)
    assert initial_profile is None
    
    initial_summary = get_dashboard_summary(db_session)
    assert initial_summary["student_name"] is None
    assert initial_summary["total_subjects"] == 0
    assert initial_summary["total_topics"] == 0
    assert initial_summary["completed_topics"] == 0
    assert initial_summary["study_progress"] == 0.0

    # Step 2: Create student profile
    profile = create_or_update_student_profile(
        db=db_session,
        name="Alex Mercer",
        course="B.Tech Computer Science",
        branch="Artificial Intelligence",
        year="3rd Year",
        semester="6th Semester"
    )
    assert profile.name == "Alex Mercer"

    # Step 3: Add subjects
    subj_dbms = create_subject(
        db=db_session,
        name="Database Management Systems",
        code="CS601",
        semester="6th Semester",
        description="Relational database design, Normalization, SQL, and Transactions."
    )
    subj_os = create_subject(
        db=db_session,
        name="Operating Systems",
        code="CS602",
        semester="6th Semester",
        description="Processes, concurrency, memory management, and file systems."
    )
    assert subj_dbms.id is not None
    assert subj_os.id is not None

    # Step 4: Add syllabus topics
    t1 = add_topic(db_session, subj_dbms.id, 1, "Relational Model & Keys")
    t2 = add_topic(db_session, subj_dbms.id, 2, "Normalization (1NF, 2NF, 3NF, BCNF)")
    t3 = add_topic(db_session, subj_os.id, 1, "Process Scheduling Algorithms")
    t4 = add_topic(db_session, subj_os.id, 2, "Deadlocks & Banker's Algorithm")

    # Step 5: Verify topics added
    subjects = get_subjects(db_session)
    assert len(subjects) == 2

    # Step 6: Mark topic 1 and 3 completed
    toggle_topic_completion(db_session, t1.id)
    toggle_topic_completion(db_session, t3.id)

    # Step 7: Check dashboard summary metrics
    summary = get_dashboard_summary(db_session)
    assert summary["student_name"] == "Alex Mercer"
    assert summary["total_subjects"] == 2
    assert summary["total_topics"] == 4
    assert summary["completed_topics"] == 2
    assert summary["study_progress"] == 50.0

def test_app_imports():
    """Verify that app and all ui modules import without syntax or runtime error."""
    import app
    import ui.components
    import ui.dashboard
    import ui.profile
    import ui.subjects
    assert app is not None
