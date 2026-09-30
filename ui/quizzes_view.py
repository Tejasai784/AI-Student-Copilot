"""Quizzes & Mock Exams View.
Interactive quiz generation, mock assessments, automated answer grading, and rubric evaluation.
"""
import streamlit as st
from database.database import get_db
from database.crud import get_subjects
from tools.registry import get_tool_registry
from ui.components import render_header, render_metric_card


def render_quizzes_page():
    render_header(
        title="📝 Quizzes & Mock Exams",
        subtitle="Generate mock questions, practice under exam conditions, and receive automated diagnostic evaluation.",
        badge="Exam & Assessment Engine"
    )

    with get_db() as db:
        subjects = get_subjects(db)

    # Quiz Generator Form
    with st.expander("✨ Generate Practice Quiz or Mock Exam", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            subj_opts = {f"{s.name} ({s.code})": s.name for s in subjects} if subjects else {"Python Programming": "Python"}
            chosen_subj_label = st.selectbox("Select Subject", list(subj_opts.keys()))
            subject_name = subj_opts[chosen_subj_label]
        with c2:
            num_q = st.number_input("Number of Questions", min_value=1, max_value=10, value=3)
        with c3:
            difficulty = st.selectbox("Difficulty Level", ["easy", "medium", "hard"], index=1)

        custom_topic = st.text_input("Specific Topic Focus (Optional)", placeholder="e.g. Normalization & BCNF, Python Dictionaries, Loops")

        if st.button("Generate Assessment", type="primary", use_container_width=True):
            topic_query = custom_topic if custom_topic.strip() else subject_name
            with st.spinner("Exam Agent generating questions and evaluation rubrics..."):
                reg = get_tool_registry()
                q_tool = reg.get_tool("quiz_generator")
                quiz_data = q_tool.execute(topic=topic_query, num_questions=int(num_q), difficulty=difficulty)
                st.session_state["active_quiz"] = quiz_data

    # Display Active Quiz
    active_quiz = st.session_state.get("active_quiz")
    if active_quiz and active_quiz.get("ok"):
        questions = active_quiz.get("questions", [])
        st.markdown(f"### 📋 Active Quiz: {active_quiz.get('topic')} ({len(questions)} Questions)")

        user_responses = {}
        for idx, q in enumerate(questions, start=1):
            with st.container():
                st.markdown(f"**Question {idx} [{q.get('question_type')} &bull; {q.get('max_marks', 1.0)} Marks]:**")
                st.markdown(f"> {q.get('question_text')}")

                if q.get("question_type") == "MCQ" and q.get("options"):
                    resp = st.radio(f"Select your answer for Q{idx}:", q.get("options"), key=f"quiz_q_{idx}")
                    user_responses[idx] = resp
                else:
                    resp = st.text_area(f"Your answer for Q{idx}:", key=f"quiz_q_{idx}", height=80)
                    user_responses[idx] = resp
                st.markdown("---")

        if st.button("Submit Assessment for AI Evaluation", type="primary"):
            st.session_state["submitted_quiz"] = True
            st.success("✅ Answers submitted! Here is your AI Diagnostic Evaluation:")

            total_score = 0.0
            max_score = sum(q.get("max_marks", 1.0) for q in questions)

            for idx, q in enumerate(questions, start=1):
                ans = user_responses.get(idx, "").strip()
                correct_ans = q.get("correct_answer", "")
                is_correct = (ans.lower() == correct_ans.lower()) or (ans and ans in correct_ans)

                score = q.get("max_marks", 1.0) if is_correct else 0.0
                total_score += score

                with st.expander(f"Question {idx} Result: {'✅ Correct' if is_correct else '❌ Needs Review'} ({score}/{q.get('max_marks', 1.0)})", expanded=True):
                    st.write(f"**Your Answer:** {ans or '_No answer provided_'}")
                    st.write(f"**Model Answer / Key:** {correct_ans}")
                    if q.get("explanation"):
                        st.info(f"💡 **Explanation:** {q.get('explanation')}")

            accuracy = round((total_score / max_score * 100.0), 1) if max_score > 0 else 0.0
            st.markdown(f"### 🎯 Final Assessment Score: **{total_score}/{max_score} ({accuracy}%)**")
            if accuracy >= 70:
                st.balloons()
                st.success("Great job! You have demonstrated solid concept mastery.")
            else:
                st.warning("Recommended: Review the explanations above and schedule a follow-up revision session.")
    else:
        st.info("No active quiz. Generate a quiz above to start your practice session.")
