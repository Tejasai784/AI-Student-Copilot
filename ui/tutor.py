from __future__ import annotations

import streamlit as st
from database.crud import get_documents, get_subjects
from database.database import get_db
from services.tutor_service import ANSWER_MODES, DEFAULT_ANSWER_MODE, get_tutor_response


def render_tutor():
    st.title("🤖 AI Tutor")
    st.caption("Ask questions grounded in your uploaded study material, with exam-ready answer formats.")

    with get_db() as db:
        subjects = get_subjects(db)
        docs = get_documents(db)
        doc_map = {d.id: d for d in docs}

    if not subjects:
        st.info("Add at least one subject before using the tutor.")
        return

    subject_options = {"All subjects": None, **{f"{s.code} — {s.name}": s.id for s in subjects}}
    selected_label = st.selectbox("Subject filter", list(subject_options.keys()))
    subject_id = subject_options[selected_label]

    units = []
    if subject_id:
        with get_db() as db:
            subject = next((s for s in get_subjects(db) if s.id == subject_id), None)
            if subject:
                units = sorted({t.unit_number for t in (subject.topics or []) if t.unit_number is not None})

    unit_value = st.selectbox("Unit filter", ["All units"] + [f"Unit {u}" for u in units])
    unit_number = None if unit_value == "All units" else int(unit_value.split()[-1])

    mode = st.selectbox("Answer format", list(ANSWER_MODES.keys()), index=list(ANSWER_MODES.keys()).index(DEFAULT_ANSWER_MODE))
    top_k = st.slider("Retrieved passages", min_value=2, max_value=10, value=5)

    question = st.text_area(
        "Your question",
        placeholder="Example: Explain the PN junction diode in simple English for a 5-mark answer.",
        height=130,
    )

    if st.button("✨ Ask AI Tutor", type="primary", use_container_width=True):
        if not question.strip():
            st.warning("Enter a question first.")
            return
        with st.spinner("Searching your material and preparing the answer..."):
            response = get_tutor_response(
                query=question.strip(),
                subject_id=subject_id,
                unit_number=unit_number,
                answer_mode=mode,
                top_k=top_k,
                db_docs=doc_map,
            )
        if response.error:
            st.error(response.error)
            return

        source_labels = {
            "material": "📚 Grounded in your study material",
            "general": "🌐 General academic explanation",
            "no_material": "ℹ️ No matching uploaded material",
            "offline": "💾 Offline mode",
        }
        st.success(source_labels.get(response.source_mode, response.source_mode))
        st.markdown(response.answer)
        st.caption(f"Model: {response.model_used} • Retrieval score: {response.retrieval_score:.3f}")

        if response.sources:
            with st.expander("📖 Sources and retrieved passages", expanded=False):
                for i, src in enumerate(response.sources, 1):
                    st.markdown(
                        f"**{i}. {src.get('filename', 'Document')}** — "
                        f"page {src.get('page_number', '?')} • score {src.get('score', 0):.3f}"
                    )
                    st.caption(src.get("excerpt", ""))
                    st.divider()