import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.database import Base
from database.crud import (
    get_student_profile,
    create_or_update_student_profile,
    get_subjects,
    get_subject_by_id,
    get_subject_by_code,
    create_subject,
    update_subject,
    delete_subject,
    get_topics_by_subject,
    add_topic,
    bulk_add_topics,
    toggle_topic_completion,
    delete_topic,
    get_dashboard_summary,
)

def test_student_profile_crud(db_session):
    # Ensure initially empty
    profile = get_student_profile(db_session)
    assert profile is None

    # Create profile
    created = create_or_update_student_profile(
        db=db_session,
        name="Alex Mercer",
        course="B.Tech Computer Science",
        branch="Computer Science & Engineering",
        year="3rd Year",
        semester="6th Semester"
    )
    assert created.id is not None
    assert created.name == "Alex Mercer"
    assert created.course == "B.Tech Computer Science"

    # Fetch profile
    fetched = get_student_profile(db_session)
    assert fetched is not None
    assert fetched.name == "Alex Mercer"
    assert fetched.branch == "Computer Science & Engineering"

    # Update profile
    updated = create_or_update_student_profile(
        db=db_session,
        name="Alex Mercer",
        course="B.Tech AI & Data Science",
        branch="AI & DS",
        year="4th Year",
        semester="7th Semester"
    )
    assert updated.id == created.id
    assert updated.course == "B.Tech AI & Data Science"
    assert updated.year == "4th Year"

def test_subject_crud(db_session):
    # Initially empty
    subjects = get_subjects(db_session)
    assert len(subjects) == 0

    # Create subjects
    sub1 = create_subject(
        db=db_session,
        name="Database Management Systems",
        code="CS601",
        semester="6th Semester",
        description="Core relational databases and SQL."
    )
    sub2 = create_subject(
        db=db_session,
        name="Operating Systems",
        code="CS602",
        semester="6th Semester",
        description="Processes, threads, and memory management."
    )

    assert sub1.id is not None
    assert sub2.id is not None
    assert sub1.code == "CS601"

    # List subjects
    all_subs = get_subjects(db_session)
    assert len(all_subs) == 2

    # Get by ID
    found_by_id = get_subject_by_id(db_session, sub1.id)
    assert found_by_id is not None
    assert found_by_id.name == "Database Management Systems"

    # Get by Code (case-insensitive)
    found_by_code = get_subject_by_code(db_session, "cs601")
    assert found_by_code is not None
    assert found_by_code.id == sub1.id

    # Update subject
    updated = update_subject(
        db=db_session,
        subject_id=sub1.id,
        name="Advanced Database Systems",
        code="CS601-A",
        semester="6th Semester",
        description="Updated description."
    )
    assert updated.name == "Advanced Database Systems"
    assert updated.code == "CS601-A"

    # Delete subject
    deleted = delete_subject(db_session, sub2.id)
    assert deleted is True
    assert len(get_subjects(db_session)) == 1

def test_syllabus_topics_and_cascade_delete(db_session):
    # Create subject
    subject = create_subject(
        db=db_session,
        name="Computer Networks",
        code="CS603",
        semester="6th Semester"
    )

    # Add single topic
    t1 = add_topic(db_session, subject_id=subject.id, unit_number=1, topic_name="OSI & TCP/IP Reference Models")
    assert t1.id is not None
    assert t1.is_completed is False

    # Bulk add topics
    topics_to_add = [
        {"unit_number": 1, "topic_name": "Physical Layer and Transmission Media"},
        {"unit_number": 2, "topic_name": "Data Link Layer & Error Detection"},
        {"unit_number": 3, "topic_name": "Routing Algorithms & IP Addressing"},
    ]
    bulk_add_topics(db_session, subject_id=subject.id, topics_data=topics_to_add)

    # Retrieve topics
    topics = get_topics_by_subject(db_session, subject.id)
    assert len(topics) == 4
    assert topics[0].topic_name == "OSI & TCP/IP Reference Models"

    # Toggle completion
    t_toggle = toggle_topic_completion(db_session, t1.id)
    assert t_toggle.is_completed is True

    # Delete single topic
    del_ok = delete_topic(db_session, t1.id)
    assert del_ok is True
    assert len(get_topics_by_subject(db_session, subject.id)) == 3

    # Test cascade delete: deleting the subject must delete all its topics
    delete_subject(db_session, subject.id)
    assert len(get_topics_by_subject(db_session, subject.id)) == 0

def test_dashboard_summary(db_session):
    # Empty state
    summary = get_dashboard_summary(db_session)
    assert summary["student_name"] is None
    assert summary["total_subjects"] == 0
    assert summary["total_topics"] == 0
    assert summary["study_progress"] == 0.0

    # Populate profile and subject with topics
    create_or_update_student_profile(
        db=db_session,
        name="Taylor Swift",
        course="B.Sc Computer Science",
        branch="Information Technology",
        year="2nd Year",
        semester="4th Semester"
    )
    subj = create_subject(
        db=db_session,
        name="Discrete Mathematics",
        code="MA401",
        semester="4th Semester"
    )
    t1 = add_topic(db_session, subj.id, 1, "Set Theory")
    t2 = add_topic(db_session, subj.id, 1, "Graph Theory")
    toggle_topic_completion(db_session, t1.id)

    summary = get_dashboard_summary(db_session)
    assert summary["student_name"] == "Taylor Swift"
    assert summary["total_subjects"] == 1
    assert summary["total_topics"] == 2
    assert summary["completed_topics"] == 1
    assert summary["study_progress"] == 50.0

def test_physical_sqlite_persistence():
    """Verifies that data written to a physical SQLite database persists across engine/connection restarts."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    try:
        db_url = f"sqlite:///{tmp_db_path}"
        
        # Instance 1: Create table and save subject
        engine1 = create_engine(db_url)
        Base.metadata.create_all(bind=engine1)
        Session1 = sessionmaker(bind=engine1)
        with Session1() as s1:
            create_subject(s1, name="Machine Learning", code="CS701", semester="7th Semester")
            s1.commit()
        engine1.dispose()

        # Instance 2: Connect with fresh engine and verify data is present
        engine2 = create_engine(db_url)
        Session2 = sessionmaker(bind=engine2)
        with Session2() as s2:
            subjects = get_subjects(s2)
            assert len(subjects) == 1
            assert subjects[0].name == "Machine Learning"
            assert subjects[0].code == "CS701"
        engine2.dispose()

    finally:
        if os.path.exists(tmp_db_path):
            os.remove(tmp_db_path)
