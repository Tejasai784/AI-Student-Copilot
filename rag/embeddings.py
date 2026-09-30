import math
import re
import numpy as np
from typing import List
from backend.config import settings
from backend.logging_config import logger

class EmbeddingGenerator:
    """Base interface for embedding generators."""
    def embed_text(self, text: str) -> List[float]:
        raise NotImplementedError

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError


STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "at", "by",
    "for", "with", "about", "against", "between", "into", "through", "during",
    "before", "after", "above", "below", "to", "from", "up", "down", "in", "out",
    "on", "off", "over", "under", "again", "further", "once", "here", "there",
    "why", "how", "all", "any", "both", "each", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than",
    "too", "very", "can", "will", "just", "should", "now", "is", "it", "its",
    "are", "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "of"
}

class LocalSemanticEmbeddingGenerator(EmbeddingGenerator):
    """
    High-speed, offline deterministic semantic embedding generator.
    Uses token hashing, stop-word elimination, root prefix stems, and TF-IDF weighting
    with L2 normalization to produce 1024-dimensional dense vectors.
    """
    def __init__(self, dimension: int = 1024):
        self.dimension = dimension

    def _hash_token(self, token: str) -> int:
        """Computes a deterministic 32-bit FNV-1a hash index."""
        h = 2166136261
        for char in token:
            h = (h ^ ord(char)) * 16777619
            h &= 0xFFFFFFFF
        return h % self.dimension

    def embed_text(self, text: str) -> List[float]:
        vec = np.zeros(self.dimension, dtype=np.float32)
        if not text:
            return vec.tolist()

        raw_tokens = re.findall(r'\b[a-zA-Z0-9_-]+\b', text.lower())
        tokens = [t for t in raw_tokens if t not in STOP_WORDS and len(t) > 1]
        if not tokens:
            return vec.tolist()

        # 1. Content unigrams with logarithmic length weight
        for token in tokens:
            idx = self._hash_token(token)
            weight = 1.0 + math.log(1.0 + len(token))
            vec[idx] += weight

            # Root prefix (stem approximation)
            if len(token) >= 5:
                stem_idx = self._hash_token(token[:5])
                vec[stem_idx] += 0.8

        # 2. Informative bigrams
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]}_{tokens[i+1]}"
            idx = self._hash_token(bigram)
            vec[idx] += 2.0

        # L2 normalization so dot product == cosine similarity
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


class OpenAIEmbeddingGenerator(EmbeddingGenerator):
    """OpenAI API Embedding Generator with automatic fallback to local."""
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.api_key = api_key
        self.model = model
        self.fallback = LocalSemanticEmbeddingGenerator()
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}. Falling back to local embeddings.")
            self.client = None

    def embed_text(self, text: str) -> List[float]:
        if not self.client or not self.api_key:
            return self.fallback.embed_text(text)
        try:
            resp = self.client.embeddings.create(input=[text], model=self.model)
            return resp.data[0].embedding
        except Exception as e:
            logger.warning(f"OpenAI embedding call failed: {e}. Using local fallback.")
            return self.fallback.embed_text(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self.client or not self.api_key:
            return self.fallback.embed_batch(texts)
        try:
            batch_size = 64
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                resp = self.client.embeddings.create(input=batch, model=self.model)
                all_embeddings.extend([item.embedding for item in resp.data])
            return all_embeddings
        except Exception as e:
            logger.warning(f"OpenAI batch embedding call failed: {e}. Using local fallback.")
            return self.fallback.embed_batch(texts)


def get_embedding_generator() -> EmbeddingGenerator:
    """Factory returning configured embedding generator (OpenAI or local offline)."""
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
        logger.info(f"Using OpenAI Embedding Generator (Model: {settings.EMBEDDING_MODEL})")
        return OpenAIEmbeddingGenerator(api_key=settings.OPENAI_API_KEY, model=settings.EMBEDDING_MODEL)
    else:
        logger.info("Using Local Semantic Embedding Generator (Offline mode)")
        return LocalSemanticEmbeddingGenerator()
