import json
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from backend.config import settings
from backend.logging_config import logger

class LocalVectorStore:
    """
    Lightweight, fast, file-persisted vector store.
    Stores normalized vector embeddings in a .npy array and chunk metadata in JSON.
    Performs cosine similarity search using vectorized dot products.
    """
    def __init__(self, store_dir: Optional[Path] = None):
        self.store_dir = Path(store_dir) if store_dir else settings.VECTOR_STORE_PATH
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.meta_file = self.store_dir / "index_metadata.json"
        self.vectors_file = self.store_dir / "index_vectors.npy"
        
        self.metadata: List[Dict[str, Any]] = []
        self.vectors: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        
        self.load()

    def load(self) -> None:
        """Loads index from disk if files exist."""
        with self._lock:
            if self.meta_file.exists() and self.vectors_file.exists():
                try:
                    with open(self.meta_file, "r", encoding="utf-8") as f:
                        self.metadata = json.load(f)
                    self.vectors = np.load(self.vectors_file)
                    logger.info(f"Loaded vector store with {len(self.metadata)} chunks from {self.store_dir}")
                except Exception as e:
                    logger.error(f"Error loading vector store from disk: {e}. Resetting index.", exc_info=True)
                    self.metadata = []
                    self.vectors = None
            else:
                self.metadata = []
                self.vectors = None

    def save(self) -> None:
        """Saves current index and metadata to disk."""
        with self._lock:
            try:
                # Write metadata atomically
                temp_meta = self.store_dir / "index_metadata.tmp"
                with open(temp_meta, "w", encoding="utf-8") as f:
                    json.dump(self.metadata, f, ensure_ascii=False, indent=2)
                temp_meta.replace(self.meta_file)

                # Write vectors
                if self.vectors is not None and len(self.vectors) > 0:
                    np.save(self.vectors_file, self.vectors)
                elif self.vectors_file.exists():
                    self.vectors_file.unlink()

            except Exception as e:
                logger.error(f"Failed to save vector store to disk: {e}", exc_info=True)
                raise

    def add_chunks(self, items: List[Dict[str, Any]]) -> int:
        """
        Adds chunks with precomputed embeddings to the index.

        Each item must contain:
        {
            "vector_id": str,
            "document_id": int,
            "subject_id": int,
            "unit_number": Optional[int],
            "topic_name": Optional[str],
            "page_number": int,
            "chunk_index": int,
            "content": str,
            "char_count": int,
            "embedding": List[float]
        }
        """
        if not items:
            return 0

        with self._lock:
            new_meta = []
            new_vecs = []

            for it in items:
                embedding = it.get("embedding")
                if embedding is None:
                    continue
                
                # Copy metadata without the raw embedding vector
                meta = {k: v for k, v in it.items() if k != "embedding"}
                new_meta.append(meta)
                new_vecs.append(embedding)

            if not new_vecs:
                return 0

            new_vecs_arr = np.array(new_vecs, dtype=np.float32)
            
            # Ensure L2 normalized
            norms = np.linalg.norm(new_vecs_arr, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            new_vecs_arr = new_vecs_arr / norms

            if self.vectors is None or len(self.vectors) == 0:
                self.vectors = new_vecs_arr
                self.metadata = new_meta
            else:
                self.vectors = np.vstack([self.vectors, new_vecs_arr])
                self.metadata.extend(new_meta)

        self.save()
        logger.info(f"Successfully indexed {len(new_meta)} chunks into local vector store.")
        return len(new_meta)

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_subject_id: Optional[int] = None,
        filter_unit: Optional[int] = None,
        filter_user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Performs cosine similarity search against indexed chunks with optional subject,
        unit, and user_id filtering.
        """
        with self._lock:
            if self.vectors is None or len(self.vectors) == 0 or len(self.metadata) == 0:
                return []

            q_vec = np.array(query_embedding, dtype=np.float32)
            q_norm = np.linalg.norm(q_vec)
            if q_norm > 0:
                q_vec = q_vec / q_norm

            # Filter indices based on subject_id, unit_number, and user_id
            valid_indices = []
            for idx, meta in enumerate(self.metadata):
                if filter_subject_id is not None and meta.get("subject_id") != filter_subject_id:
                    continue
                if filter_unit is not None and meta.get("unit_number") != filter_unit:
                    continue
                if filter_user_id is not None:
                    chunk_user = meta.get("user_id")
                    if chunk_user is not None and chunk_user != filter_user_id:
                        continue
                    elif chunk_user is None and filter_user_id != 1:
                        continue
                valid_indices.append(idx)

            if not valid_indices:
                return []

            filtered_vectors = self.vectors[valid_indices]
            # Dot product computes cosine similarity for L2 normalized vectors
            scores = np.dot(filtered_vectors, q_vec)

            # Get top-k
            k = min(top_k, len(valid_indices))
            top_local_indices = np.argsort(-scores)[:k]

            results = []
            for loc_idx in top_local_indices:
                global_idx = valid_indices[loc_idx]
                item = dict(self.metadata[global_idx])
                item["score"] = float(round(float(scores[loc_idx]), 4))
                results.append(item)

            return results

    def delete_by_document_id(self, document_id: int) -> int:
        """Deletes all chunks associated with a specific document_id."""
        with self._lock:
            if not self.metadata or self.vectors is None:
                return 0

            keep_indices = [i for i, meta in enumerate(self.metadata) if meta.get("document_id") != document_id]
            removed_count = len(self.metadata) - len(keep_indices)

            if removed_count == 0:
                return 0

            if not keep_indices:
                self.metadata = []
                self.vectors = None
            else:
                self.metadata = [self.metadata[i] for i in keep_indices]
                self.vectors = self.vectors[keep_indices]

        self.save()
        logger.info(f"Removed {removed_count} chunks for document_id={document_id} from vector store.")
        return removed_count

    def count(self) -> int:
        """Returns total number of chunks currently indexed."""
        with self._lock:
            return len(self.metadata)

    def clear(self) -> None:
        """Resets the vector store."""
        with self._lock:
            self.metadata = []
            self.vectors = None
        self.save()


# Singleton instance
_vector_store_instance: Optional[LocalVectorStore] = None

def get_vector_store() -> LocalVectorStore:
    """Returns the application vector store instance."""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = LocalVectorStore()
    return _vector_store_instance
