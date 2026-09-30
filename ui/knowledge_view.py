"""Knowledge Base & Semantic Vector Index Inspector View."""
import streamlit as st
from database.database import get_db
from database.crud import get_documents, get_subjects
from rag.vector_store import get_vector_store
from rag.embeddings import get_embedding_generator
from ui.components import render_header, render_metric_card


def render_knowledge_base_page():
    render_header(
        title="🧠 Knowledge Base & Vector Index",
        subtitle="Inspect segmented knowledge chunks, test semantic similarity retrieval, and verify grounded citations.",
        badge="RAG Vector Engine"
    )

    v_store = get_vector_store()
    chunk_count = v_store.count()

    col1, col2, col3 = st.columns(3)
    with col1:
        render_metric_card("Indexed Chunks", str(chunk_count), "Normalized vectors on disk", border_color="#3B82F6")
    with col2:
        render_metric_card("Similarity Metric", "Cosine Dot-Product", "L2-normalized vectors", border_color="#10B981")
    with col3:
        embedder = get_embedding_generator()
        render_metric_card("Embedding Generator", type(embedder).__name__, "Deterministic 128-dim", border_color="#8B5CF6")

    st.markdown("### 🔍 Semantic Retrieval Playground")
    st.caption("Test how the platform retrieves relevant academic passages from your uploaded documents.")

    query = st.text_input("Enter search query or exam concept:", placeholder="e.g. Normalization BCNF superkey, Python dictionaries, ACID properties")
    top_k = st.slider("Top Results to Fetch", min_value=1, max_value=10, value=3)

    if st.button("Run Semantic Search", type="primary"):
        if not query.strip():
            st.warning("Please enter a search query.")
        elif chunk_count == 0:
            st.info("No documents have been indexed yet. Please upload study files in 'Uploaded Materials'.")
        else:
            with st.spinner("Embedding query and computing cosine similarities..."):
                q_vec = embedder.embed_text(query.strip())
                hits = v_store.search(q_vec, top_k=top_k)

            if not hits:
                st.info("No matching passages found.")
            else:
                st.success(f"Retrieved {len(hits)} matching passages:")
                for idx, h in enumerate(hits, start=1):
                    with st.expander(f"Hit #{idx}: Score {h.get('score', 0.0):.4f} (Doc #{h.get('document_id')}, Page {h.get('page_number', 1)})", expanded=True):
                        st.markdown(f"**Content:**\n> {h.get('content')}")
                        st.caption(f"Chunk Index: {h.get('chunk_index')} | Unit: {h.get('unit_number')} | Character Count: {h.get('char_count')}")

    st.markdown("---")
    st.markdown("### 📑 Indexed Knowledge Chunks Overview")
    if chunk_count > 0:
        meta_sample = v_store.metadata[:15]
        for m in meta_sample:
            with st.container():
                st.markdown(f"**Doc #{m.get('document_id')} (Page {m.get('page_number')}, Chunk {m.get('chunk_index')})**: {m.get('content')[:120]}...")
    else:
        st.info("Vector index is empty. Upload documents in 'Uploaded Materials' to populate chunks.")
