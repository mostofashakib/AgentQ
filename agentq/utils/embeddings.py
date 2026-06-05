from __future__ import annotations
from functools import lru_cache
import numpy as np


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")


def cosine_similarity(text_a: str, text_b: str) -> float:
    model = _get_model()
    embeddings = model.encode([text_a, text_b], normalize_embeddings=True)
    return float(np.dot(embeddings[0], embeddings[1]))
