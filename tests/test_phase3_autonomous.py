"""Tests for Phase 3: Autonomous AGI-Inspired Learning Platform.
- 15-Step Autonomous Exam Preparation Pipeline
- Automatic Weakness Detection & Schedule Adaptation
- Knowledge Map / Topic Graph Generation
- Certified Exam Readiness Report Generation
"""
import pytest
from database.crud import create_subject, add_topic
from services.autonomous_workflow import AutonomousLearningCoordinator
from services.analytics_service import generate_knowledge_map, detect_weak_topics
from services.report_service import generate_exam_readiness_report


def test_15_step_autonomous_exam_prep_workflow(db_session):
    subj = create_subject(db_session, "Python Programming", "CS204", "4th Semester")
    add_topic(db_session, subj.id, 1, "Variables and Data Types")
    add_topic(db_session, subj.id, 2, "Control Flow and Loops")
    add_topic(db_session, subj.id, 3, "Data Structures: Lists and Dictionaries")

    coord = AutonomousLearningCoordinator(db=db_session)
    prompt = "Prepare me for my Python exam in 7 days. I have uploaded my syllabus and previous question papers."
    
    result = coord.run_full_preparation_workflow(prompt=prompt, subject_id=subj.id)

    assert result["ok"] is True
    assert result["total_steps"] == 15
    assert len(result["steps"]) == 15
    assert result["readiness_score"] >= 80.0
    assert result["detected_weakness"] is not None
    assert len(result["plan_tasks"]) >= 5
    assert "# Academic Exam Readiness Report" in result["markdown_report"]
    assert "Exam Readiness Report" in result["html_report"]

    # Verify all 15 steps are recorded
    step_titles = [s["title"] for s in result["steps"]]
    assert any("Understand Request" in t for t in step_titles)
    assert any("Inspect Uploaded Syllabus" in t for t in step_titles)
    assert any("Build Day-by-Day Study Plan" in t for t in step_titles)
    assert any("Detect Weaknesses" in t for t in step_titles)
    assert any("Adapt Study Plan" in t for t in step_titles)
    assert any("Final Readiness Report" in t for t in step_titles)


def test_knowledge_map_and_topic_graph(db_session):
    subj = create_subject(db_session, "Database Systems", "CS301", "5th Semester")
    t1 = add_topic(db_session, subj.id, 1, "Relational Algebra")
    t2 = add_topic(db_session, subj.id, 2, "Normalization & BCNF")

    kmap = generate_knowledge_map(db_session, subject_id=subj.id)
    assert kmap["total_nodes"] >= 3  # 1 subject + 2 topics
    assert kmap["total_edges"] >= 2

    node_types = [n["type"] for n in kmap["nodes"]]
    assert "subject" in node_types
    assert "topic" in node_types


def test_readiness_report_service(db_session):
    subj = create_subject(db_session, "Operating Systems", "CS302", "5th Semester")
    report = generate_exam_readiness_report(db_session, subject_id=subj.id)
    
    assert report["ok"] is True
    assert "Operating Systems" in report["subject"]
    assert "markdown_report" in report
    assert "html_report" in report
    assert "Readiness Score" in report["markdown_report"]
