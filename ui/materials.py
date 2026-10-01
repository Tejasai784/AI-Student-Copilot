import streamlit as st
from database.database import get_db
from database.crud import get_subjects, get_documents, get_topics_by_subject, get_document_chunks
from services.document_service import save_and_process_document, retry_document_processing, delete_document_with_files
from rag.vector_store import get_vector_store
from utils.helpers import format_datetime, format_file_size
from ui.components import render_header, render_empty_state, render_metric_card

def render_materials_page():
    """Renders the Study Materials management and upload screen."""
    render_header(
        title="Study Materials",
        subtitle="Upload and manage course syllabi, lecture notes, textbook chapters, and question papers.",
        badge="Documents & RAG Index"
    )

    with get_db() as db:
        subjects = get_subjects(db)

    if not subjects:
        st.warning("⚠️ You have not registered any subjects yet. Please add at least one subject in **Subjects & Syllabus** before uploading study materials.")
        return

    tab1, tab2, tab3 = st.tabs(["📤 Upload PDF", "📚 Document Library", "🔍 Vector Store Status"])

    # ------------------------------------------------------------------------
    # TAB 1: UPLOAD DOCUMENT
    # ------------------------------------------------------------------------
    with tab1:
        st.subheader("Upload Academic Document")
        
        # Subject selection
        subject_options = {f"{s.name} ({s.code})": s.id for s in subjects}
        selected_subject_label = st.selectbox("Select Subject *", options=list(subject_options.keys()))
        selected_subject_id = subject_options[selected_subject_label]

        # Fetch topics for selected subject
        with get_db() as db:
            subject_topics = get_topics_by_subject(db, selected_subject_id)

        c1, c2 = st.columns(2)
        with c1:
            unit_choices = ["Whole Subject / General"] + [f"Unit {i}" for i in range(1, 11)]
            selected_unit_label = st.selectbox("Assign to Unit (Optional)", options=unit_choices)
            unit_number = int(selected_unit_label.split()[1]) if selected_unit_label.startswith("Unit ") else None

        with c2:
            doc_type = st.selectbox(
                "Document Type *",
                options=["Lecture Notes", "Syllabus", "Previous Question Paper", "Textbook Chapter", "Reference Material"]
            )

        uploaded_file = st.file_uploader(
            "Choose a Study Document *",
            type=["pdf", "docx", "txt", "md", "csv"],
            help="Accepted formats: PDF, Word (DOCX), Text (TXT, MD), CSV. Maximum size: 25MB."
        )

        if uploaded_file is not None:
            st.caption(f"Selected file: **{uploaded_file.name}** ({format_file_size(len(uploaded_file.getvalue()))})")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Upload & Index Document", type="primary", use_container_width=True, disabled=(uploaded_file is None)):
            if uploaded_file is None:
                st.error("Please select a document file to upload.")
            else:
                with st.spinner("Processing document: extracting text, chunking, generating embeddings, and indexing..."):
                    try:
                        file_bytes = uploaded_file.getvalue()
                        with get_db() as db:
                            doc = save_and_process_document(
                                db=db,
                                file_bytes=file_bytes,
                                original_filename=uploaded_file.name,
                                subject_id=selected_subject_id,
                                unit_number=unit_number,
                                document_type=doc_type
                            )
                            doc_status = doc.status
                            doc_pages = doc.total_pages
                            doc_chunks = doc.total_chunks
                            doc_err = doc.error_message

                        if doc_status == "COMPLETED":
                            st.success(f"✅ Successfully processed and indexed **{uploaded_file.name}**! ({doc_pages} pages, {doc_chunks} semantic chunks)")
                            st.rerun()
                        else:
                            st.error(f"❌ Document processing failed: {doc_err}")
                    except Exception as e:
                        st.error(f"Upload error: {str(e)}")

    # ------------------------------------------------------------------------
    # TAB 2: DOCUMENT LIBRARY
    # ------------------------------------------------------------------------
    with tab2:
        with get_db() as db:
            docs = get_documents(db)

        if not docs:
            render_empty_state(
                message="No study materials uploaded yet.",
                action_text="Use the 'Upload PDF' tab to upload lecture notes or syllabus documents.",
                icon="📄"
            )
        else:
            st.write(f"Total study materials: **{len(docs)}**")
            
            for doc in docs:
                status_color = {
                    "COMPLETED": "#10B981",
                    "READY": "#10B981",
                    "INDEXING": "#8B5CF6",
                    "PROCESSING": "#3B82F6",
                    "UPLOADING": "#F59E0B",
                    "FAILED": "#EF4444",
                    "PENDING": "#F59E0B"
                }.get(doc.status, "#64748B")

                status_badge = f'<span style="background-color: {status_color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: 600;">{doc.status}</span>'
                unit_str = f"Unit {doc.unit_number}" if doc.unit_number else "General"
                
                with st.expander(f"📄 **{doc.filename}** ({doc.document_type}) — {doc.subject.code if doc.subject else ''}", expanded=False):
                    c_meta1, c_meta2 = st.columns([3, 1])
                    with c_meta1:
                        st.markdown(f"**Status:** {status_badge}", unsafe_allow_html=True)
                        st.markdown(f"**Subject:** {doc.subject.name if doc.subject else 'N/A'} ({doc.subject.code if doc.subject else 'N/A'})")
                        st.markdown(f"**Unit:** {unit_str} | **Type:** {doc.document_type}")
                        st.markdown(f"**Size:** {format_file_size(doc.file_size)} | **Uploaded:** {format_datetime(doc.created_at)}")
                        if doc.status in ("COMPLETED", "READY"):
                            st.markdown(f"**Pages Extracted:** {doc.total_pages} | **Vector Chunks:** {doc.total_chunks}")
                        elif doc.status == "FAILED":
                            st.error(f"Error details: {doc.error_message}")

                    with c_meta2:
                        if doc.status == "FAILED":
                            if st.button("🔄 Retry Processing", key=f"retry_{doc.id}", type="primary"):
                                with st.spinner("Retrying document indexing..."):
                                    with get_db() as db:
                                        retry_document_processing(db, doc.id)
                                st.rerun()

                        if st.button("🗑️ Delete Document", key=f"del_doc_{doc.id}", type="secondary"):
                            with get_db() as db:
                                delete_document_with_files(db, doc.id)
                            st.success(f"Document '{doc.filename}' deleted.")
                            st.rerun()

                    # Chunk Inspector
                    if doc.status in ("COMPLETED", "READY") and doc.total_chunks > 0:
                        st.markdown("---")
                        st.markdown("###### 🔍 Extracted Chunks Preview")
                        with get_db() as db:
                            chunks = get_document_chunks(db, doc.id)

                        preview_count = min(3, len(chunks))
                        st.caption(f"Showing first {preview_count} of {len(chunks)} indexed chunks:")
                        
                        for chk in chunks[:preview_count]:
                            with st.container():
                                st.markdown(
                                    f"""
                                    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 0.6rem; margin-bottom: 0.5rem; font-size: 0.85rem;">
                                        <strong>Chunk #{chk.chunk_index + 1} (Page {chk.page_number}, {chk.char_count} chars):</strong><br>
                                        <span style="color: #334155; font-family: monospace;">{chk.content[:250]}...</span>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

    # ------------------------------------------------------------------------
    # TAB 3: VECTOR STORE STATUS
    # ------------------------------------------------------------------------
    with tab3:
        st.subheader("Vector Store Diagnostics")
        v_store = get_vector_store()
        total_indexed_chunks = v_store.count()

        c_v1, c_v2 = st.columns(2)
        with c_v1:
            render_metric_card(
                title="Indexed Chunks in Vector Store",
                value=str(total_indexed_chunks),
                subtitle="Embedded semantic segments",
                border_color="#8B5CF6"
            )
        with c_v2:
            render_metric_card(
                title="Storage Location",
                value="Local Disk",
                subtitle=str(v_store.store_dir),
                border_color="#3B82F6"
            )

        if total_indexed_chunks > 0:
            st.markdown("##### Chunks Breakdown by Subject")
            # Group by subject from in-memory metadata
            sub_counts = {}
            for m in v_store.metadata:
                sid = m.get("subject_id")
                sub_counts[sid] = sub_counts.get(sid, 0) + 1

            for sid, count in sub_counts.items():
                with get_db() as db:
                    s_obj = next((s for s in subjects if s.id == sid), None)
                s_name = f"{s_obj.name} ({s_obj.code})" if s_obj else f"Subject ID {sid}"
                st.write(f"- **{s_name}**: {count} indexed chunks")
        else:
            st.info("The vector index is currently empty. Upload PDF study materials in the 'Upload PDF' tab to build the index.")
