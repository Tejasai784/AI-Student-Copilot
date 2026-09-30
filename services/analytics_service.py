"""Performance analytics and weak-topic detection."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from database.academic_crud import get_exam_attempts
from database.models import ExamAnswer, ExamAttempt, ExamQuestion, Subject

MIN_EVIDENCE = 2  # do not label weak from a single question


def _topic_key(question: ExamQuestion) -> Tuple[int, str]:
    subject_id = int(question.subject_id or 0)
    topic = (question.topic_name or "General").strip() or "General"
    return subject_id, topic


def compute_performance(db: Session) -> Dict[str, Any]:
    attempts = [
        a
        for a in get_exam_attempts(db)
        if a.status in {"SUBMITTED", "EXPIRED"}
    ]
    subject_names = {s.id: f"{s.name} ({s.code})" for s in db.query(Subject).all()}

    overall_score = 0.0
    overall_max = 0.0
    by_subject = defaultdict(lambda: {"score": 0.0, "max": 0.0, "attempts": 0})
    by_topic = defaultdict(lambda: {"score": 0.0, "max": 0.0, "n": 0, "correct": 0})
    by_type = defaultdict(lambda: {"score": 0.0, "max": 0.0, "n": 0})
    by_diff = defaultdict(lambda: {"score": 0.0, "max": 0.0, "n": 0})
    history = []

    for attempt in sorted(attempts, key=lambda a: a.submitted_at or a.created_at):
        overall_score += float(attempt.total_score or 0)
        overall_max += float(attempt.max_score or 0)
        sid = attempt.subject_id or 0
        by_subject[sid]["score"] += float(attempt.total_score or 0)
        by_subject[sid]["max"] += float(attempt.max_score or 0)
        by_subject[sid]["attempts"] += 1
        history.append(
            {
                "id": attempt.id,
                "title": attempt.title,
                "accuracy": float(attempt.accuracy or 0),
                "score": float(attempt.total_score or 0),
                "max_score": float(attempt.max_score or 0),
                "kind": attempt.exam_kind,
                "difficulty": attempt.difficulty,
                "submitted_at": attempt.submitted_at,
                "subject": subject_names.get(attempt.subject_id, "General"),
            }
        )
        for q in attempt.questions or []:
            ans = next((a for a in (attempt.answers or []) if a.question_id == q.id), None)
            score = float(ans.score) if ans else 0.0
            max_m = float(q.max_marks or 1)
            key = _topic_key(q)
            by_topic[key]["score"] += score
            by_topic[key]["max"] += max_m
            by_topic[key]["n"] += 1
            if ans and ans.is_correct:
                by_topic[key]["correct"] += 1
            by_type[q.question_type]["score"] += score
            by_type[q.question_type]["max"] += max_m
            by_type[q.question_type]["n"] += 1
            diff = (q.difficulty or attempt.difficulty or "medium").lower()
            by_diff[diff]["score"] += score
            by_diff[diff]["max"] += max_m
            by_diff[diff]["n"] += 1

    def acc(score, mx):
        return round((score / mx) * 100, 1) if mx else 0.0

    subjects_out = []
    for sid, data in by_subject.items():
        subjects_out.append(
            {
                "subject_id": sid,
                "name": subject_names.get(sid, "General"),
                "accuracy": acc(data["score"], data["max"]),
                "attempts": data["attempts"],
            }
        )

    types_out = [
        {"question_type": k, "accuracy": acc(v["score"], v["max"]), "n": v["n"]}
        for k, v in sorted(by_type.items())
    ]
    diff_out = [
        {"difficulty": k, "accuracy": acc(v["score"], v["max"]), "n": v["n"]}
        for k, v in sorted(by_diff.items())
    ]

    topics_out = []
    for (sid, topic), data in by_topic.items():
        topics_out.append(
            {
                "subject_id": sid,
                "subject": subject_names.get(sid, "General"),
                "topic_name": topic,
                "accuracy": acc(data["score"], data["max"]),
                "n": data["n"],
                "correct": data["correct"],
            }
        )

    quizzes = [h for h in history if h["kind"] == "quiz"]
    exams = [h for h in history if h["kind"] != "quiz"]

    return {
        "overall_accuracy": acc(overall_score, overall_max),
        "total_attempts": len(attempts),
        "quiz_count": len(quizzes),
        "exam_count": len(exams),
        "subject_performance": sorted(subjects_out, key=lambda x: x["accuracy"]),
        "topic_mastery": sorted(topics_out, key=lambda x: x["accuracy"]),
        "question_type_performance": types_out,
        "difficulty_performance": diff_out,
        "history": history,
        "recent": history[-8:],
    }


def detect_weak_topics(db: Session) -> List[Dict[str, Any]]:
    """
    Weak topics require at least MIN_EVIDENCE graded questions AND
    (accuracy < 50% or recent accuracy < 45% with n>=2).
    """
    stats = compute_performance(db)
    weak = []
    for topic in stats["topic_mastery"]:
        if topic["n"] < MIN_EVIDENCE:
            continue
        if topic["accuracy"] < 50.0:
            weak.append({**topic, "reason": "Low accuracy across multiple questions"})
    # Repeated recent mistakes
    attempts = [
        a
        for a in get_exam_attempts(db)
        if a.status in {"SUBMITTED", "EXPIRED"}
    ]
    recent = sorted(attempts, key=lambda a: a.submitted_at or a.created_at)[-3:]
    recent_topic = defaultdict(lambda: {"score": 0.0, "max": 0.0, "n": 0})
    for attempt in recent:
        for q in attempt.questions or []:
            ans = next((a for a in (attempt.answers or []) if a.question_id == q.id), None)
            key = _topic_key(q)
            recent_topic[key]["n"] += 1
            recent_topic[key]["max"] += float(q.max_marks or 1)
            recent_topic[key]["score"] += float(ans.score) if ans else 0.0
    already = {(w["subject_id"], w["topic_name"]) for w in weak}
    for (sid, name), data in recent_topic.items():
        if data["n"] < MIN_EVIDENCE:
            continue
        acc = (data["score"] / data["max"] * 100) if data["max"] else 0
        if acc < 45 and (sid, name) not in already:
            weak.append(
                {
                    "subject_id": sid,
                    "topic_name": name,
                    "accuracy": round(acc, 1),
                    "n": data["n"],
                    "reason": "Repeated low scores in recent attempts",
                }
            )
    return sorted(weak, key=lambda w: w.get("accuracy", 0))


def strong_topics(db: Session) -> List[Dict[str, Any]]:
    stats = compute_performance(db)
    return [
        t
        for t in stats["topic_mastery"]
        if t["n"] >= MIN_EVIDENCE and t["accuracy"] >= 75.0
    ]


def generate_knowledge_map(db: Session, subject_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Constructs a topic graph / knowledge map:
    Returns nodes (subject, unit, topic, mastery level) and relationships/edges.
    """
    from database.crud import get_subjects
    subjects = get_subjects(db)
    if subject_id:
        subjects = [s for s in subjects if s.id == subject_id]

    nodes = []
    edges = []
    perf = compute_performance(db)
    topic_acc = {t["topic_name"].lower(): t["accuracy"] for t in perf.get("topic_mastery", [])}

    for s in subjects:
        s_node_id = f"subj_{s.id}"
        nodes.append({
            "id": s_node_id,
            "label": s.name,
            "type": "subject",
            "code": s.code,
            "mastery": 80.0
        })

        prev_topic_id = None
        for t in s.topics:
            t_node_id = f"topic_{t.id}"
            accuracy = topic_acc.get(t.topic_name.lower(), 75.0 if t.is_completed else 40.0)
            mastery_tier = "Mastered" if accuracy >= 75 else ("Developing" if accuracy >= 50 else "Weak")

            nodes.append({
                "id": t_node_id,
                "label": t.topic_name,
                "unit": t.unit_number,
                "type": "topic",
                "completed": t.is_completed,
                "accuracy": accuracy,
                "tier": mastery_tier
            })

            # Edge from subject to topic
            edges.append({
                "source": s_node_id,
                "target": t_node_id,
                "relation": "contains"
            })

            # Sequential prerequisite edge between topics within a subject
            if prev_topic_id:
                edges.append({
                    "source": prev_topic_id,
                    "target": t_node_id,
                    "relation": "prerequisite"
                })
            prev_topic_id = t_node_id

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges)
    }
