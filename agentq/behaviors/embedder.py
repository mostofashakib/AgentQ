# agentq/behaviors/embedder.py
from __future__ import annotations
from functools import lru_cache
import numpy as np
from agentq.db.models import SpanRecord

_DIM = 384  # all-MiniLM-L6-v2 output dimension


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")


def compute_composite(spans: list[SpanRecord]) -> list[float]:
    if not spans:
        return [0.0] * _DIM

    sorted_spans = sorted(spans, key=lambda s: s.start_time_unix_nano)

    # Structural: operation→tool sequence
    ops = []
    for s in sorted_spans:
        part = s.gen_ai_operation or s.name
        if s.gen_ai_tool_name:
            part = f"{part}:{s.gen_ai_tool_name}"
        ops.append(part)
    structural_str = "→".join(ops)

    # Semantic: concatenated prompt + completion content
    parts = []
    for s in sorted_spans:
        prompt = str(s.attributes.get("gen_ai.prompt", ""))
        completion = str(s.attributes.get("gen_ai.completion", ""))
        if prompt:
            parts.append(prompt[:200])
        if completion:
            parts.append(completion[:200])
    semantic_str = " ".join(parts)[:512] if parts else structural_str

    model = _get_model()
    vecs = model.encode([structural_str, semantic_str], normalize_embeddings=True)
    composite = 0.4 * np.array(vecs[0]) + 0.6 * np.array(vecs[1])
    norm = float(np.linalg.norm(composite))
    if norm > 0:
        composite = composite / norm
    return composite.tolist()
