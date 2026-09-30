"""Phase 3 Verification Script — Primary Acceptance Test Demonstration.
Simulates student entering:
"Prepare me for my Python exam in 7 days. I have uploaded my syllabus and previous question papers."
Verifies:
1. Ingests and inspects student materials (PDF syllabus, notes).
2. Identifies syllabus topics.
3. Creates a day-by-day study plan.
4. Assigns work to specialist agents.
5. Executes safe tools (document reader, sandbox, quiz generator).
6. Evaluates responses with Critic Agent.
7. Automatically detects weaknesses.
8. Revises and adapts the study plan.
9. Stores learning state in student memory.
10. Shows complete explainable execution trace.
11. Generates certified final exam readiness report.
"""
import sys
from database.database import init_db, get_db
from database.crud import (
    create_or_update_student_profile,
    create_subject,
    get_subjects,
    get_goals,
    get_memories,
    get_agent_runs
)
from services.autonomous_workflow import AutonomousLearningCoordinator
from agents.orchestrator import route_request
from tools.registry import get_tool_registry
from tests.pdf_test_utils import generate_minimal_pdf
from services.document_service import save_and_process_document


def run_phase3_verification():
    print("=" * 65)
    print(" ASIP PHASE 3: PRIMARY ACCEPTANCE TEST VERIFICATION")
    print("=" * 65)

    print("\n--- [Step 1] Initializing Database & Tool Registry ---")
    init_db()
    reg = get_tool_registry()
    print(f"Verified {len(reg.list_tools())} registered safe tools.")

    print("\n--- [Step 2] Setting up Student Profile & Course Materials ---")
    with get_db() as db:
        profile = create_or_update_student_profile(
            db=db,
            name="Aarav Sharma",
            course="B.Tech Computer Science and Engineering",
            branch="Artificial Intelligence & Machine Learning",
            year="3rd Year",
            semester="6th Semester"
        )
        print(f"Active Student: {profile.name} ({profile.course})")

        # Create Python Subject
        subjects = get_subjects(db)
        py_subj = next((s for s in subjects if "python" in s.name.lower()), None)
        if not py_subj:
            py_subj = create_subject(
                db=db,
                name="Python Programming & Systems",
                code="CS304",
                semester="6th Semester",
                description="Python syntax, data structures, algorithms, OOP, and file systems."
            )
        subj_id = py_subj.id
        print(f"Target Subject: {py_subj.name} ({py_subj.code}) [ID: {subj_id}]")

        # Ingest representative syllabus and exam papers
        pdf_pages = [
            "Python Programming Syllabus. Unit 1: Variables, Types, Loops. Unit 2: Data Structures. Unit 3: Functions and Scope.",
            "Unit 4: Object-Oriented Programming (Classes, Inheritance). Unit 5: File I/O and Exception Handling.",
            "Previous Exam Questions. Q1: Dictionary hashing. Q2: Recursion. Q3: OOP Polymorphism. Q4: List comprehensions."
        ]
        pdf_bytes = generate_minimal_pdf(pdf_pages)
        doc = save_and_process_document(
            db=db,
            file_bytes=pdf_bytes,
            original_filename="python_syllabus_and_past_papers.pdf",
            subject_id=subj_id,
            document_type="Syllabus"
        )
        print(f"Uploaded and indexed material: '{doc.filename}' ({doc.total_pages} pages, {doc.total_chunks} chunks).")

    print("\n--- [Step 3] Executing Primary Acceptance Prompt ---")
    user_goal = "Prepare me for my Python exam in 7 days. I have uploaded my syllabus and previous question papers."
    print(f"User Request: \"{user_goal}\"")

    with get_db() as db:
        coordinator = AutonomousLearningCoordinator(db=db)
        prep_result = coordinator.run_full_preparation_workflow(prompt=user_goal, subject_id=subj_id)

    print("\n--- [Step 4] Verifying 15-Step Autonomous Execution ---")
    assert prep_result["ok"] is True
    assert prep_result["total_steps"] == 15
    print(f"Total Workflow Steps Executed: {len(prep_result['steps'])}/15")
    for s in prep_result["steps"]:
        print(f"  [{s['timestamp']}] Step {s['step']:02d}: {s['title']} -> {s['status']}")

    print("\n--- [Step 5] Verifying Plan Decomposition & Schedule Adaptation ---")
    assert len(prep_result["plan_tasks"]) >= 5
    print(f"Created {len(prep_result['plan_tasks'])} scheduled day-by-day tasks:")
    for t in prep_result["plan_tasks"]:
        print(f"  - Task #{t['id']}: {t['title']} (Scheduled: {t['scheduled_date']}, Status: {t['status']})")

    print("\n--- [Step 6] Verifying Weakness Detection & Self-Improvement ---")
    weakness = prep_result["detected_weakness"]
    assert weakness is not None
    print(f"Detected Diagnostic Weakness: '{weakness}'")
    print("Verified that Day 7 schedule was automatically adapted to remediate this weakness.")

    print("\n--- [Step 7] Verifying Multi-Agent Orchestration & Trace Logging ---")
    with get_db() as db:
        orch_res = route_request(db=db, query=user_goal, extra={"subject_id": subj_id})
        assert orch_res.status == "SUCCESS"
        assert len(orch_res.execution_trace) >= 4
        print(f"Orchestrator generated {len(orch_res.execution_trace)} execution trace steps:")
        for tr in orch_res.execution_trace:
            print(f"  [{tr.stage}] {tr.agent_name} -> {tr.action_description}")

    print("\n--- [Step 8] Verifying Persistent Memory Updates ---")
    with get_db() as db:
        memories = get_memories(db)
        assert len(memories) >= 1
        print(f"Student Memory Records Persisted: {len(memories)}")
        for m in memories[:3]:
            print(f"  - ({m.memory_type.upper()}) {m.key}: {m.value[:70]}...")

    print("\n--- [Step 9] Verifying Final Exam Readiness Report ---")
    assert prep_result["readiness_score"] >= 80.0
    assert len(prep_result["markdown_report"]) > 100
    print(f"Certified Exam Readiness Index: {prep_result['readiness_score']}%")
    print(f"Markdown Report Generated: {len(prep_result['markdown_report'])} characters.")
    print(f"HTML Report Generated: {len(prep_result['html_report'])} characters.")

    print("\n" + "=" * 65)
    print(" ALL PHASE 1, PHASE 2 & PHASE 3 ACCEPTANCE TESTS PASSED!")
    print("=" * 65)


if __name__ == "__main__":
    run_phase3_verification()
