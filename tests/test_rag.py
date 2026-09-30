import tempfile
import numpy as np
from pathlib import Path
from rag.embeddings import LocalSemanticEmbeddingGenerator
from rag.vector_store import LocalVectorStore

def test_local_embeddings():
    embedder = LocalSemanticEmbeddingGenerator(dimension=1024)
    
    vec1 = embedder.embed_text("Normalization in database management systems")
    vec2 = embedder.embed_text("Database Boyce-Codd normal forms and functional dependencies")
    vec3 = embedder.embed_text("Quantum mechanics wave function in physics")

    assert len(vec1) == 1024
    # Check L2 unit length
    assert abs(np.linalg.norm(vec1) - 1.0) < 1e-4

    # Related database texts should have higher cosine similarity than unrelated physics text
    sim_db = np.dot(vec1, vec2)
    sim_physics = np.dot(vec1, vec3)
    assert sim_db > sim_physics

def test_vector_store_persistence_and_search():
    with tempfile.TemporaryDirectory() as tmp_dir:
        store_path = Path(tmp_dir)
        store = LocalVectorStore(store_dir=store_path)
        embedder = LocalSemanticEmbeddingGenerator()

        # Add 3 chunks across 2 documents and 2 subjects
        c1_text = "Relational database schema and primary keys."
        c2_text = "Normalization and third normal form."
        c3_text = "Process control block and CPU scheduling algorithms."

        chunks = [
            {
                "vector_id": "v1",
                "document_id": 101,
                "subject_id": 1,
                "unit_number": 1,
                "topic_name": "Relational Models",
                "page_number": 1,
                "chunk_index": 0,
                "content": c1_text,
                "char_count": len(c1_text),
                "embedding": embedder.embed_text(c1_text)
            },
            {
                "vector_id": "v2",
                "document_id": 101,
                "subject_id": 1,
                "unit_number": 2,
                "topic_name": "Normalization",
                "page_number": 2,
                "chunk_index": 1,
                "content": c2_text,
                "char_count": len(c2_text),
                "embedding": embedder.embed_text(c2_text)
            },
            {
                "vector_id": "v3",
                "document_id": 102,
                "subject_id": 2,
                "unit_number": 1,
                "topic_name": "Processes",
                "page_number": 1,
                "chunk_index": 0,
                "content": c3_text,
                "char_count": len(c3_text),
                "embedding": embedder.embed_text(c3_text)
            }
        ]

        store.add_chunks(chunks)
        assert store.count() == 3

        # Test reload from disk in a fresh store instance
        fresh_store = LocalVectorStore(store_dir=store_path)
        assert fresh_store.count() == 3

        # Search for database normalization
        q_emb = embedder.embed_text("Explain 3NF normalization")
        results = fresh_store.search(q_emb, top_k=2)
        assert len(results) == 2
        assert results[0]["vector_id"] == "v2"  # Normalization chunk should rank top
        assert results[0]["score"] > 0

        # Search with subject filter (only OS subject_id=2)
        filtered_results = fresh_store.search(q_emb, top_k=2, filter_subject_id=2)
        assert len(filtered_results) == 1
        assert filtered_results[0]["subject_id"] == 2

        # Search with unit filter
        unit2_results = fresh_store.search(q_emb, top_k=2, filter_subject_id=1, filter_unit=2)
        assert len(unit2_results) == 1
        assert unit2_results[0]["unit_number"] == 2

        # Test deletion by document ID
        fresh_store.delete_by_document_id(101)
        assert fresh_store.count() == 1
        
        # Verify persistence of deletion
        reloaded_after_del = LocalVectorStore(store_dir=store_path)
        assert reloaded_after_del.count() == 1
        assert reloaded_after_del.metadata[0]["document_id"] == 102
