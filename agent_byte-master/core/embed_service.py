"""GhostGoat Embedding Service — Real vector embeddings with offline fallback."""
import hashlib, json, logging, subprocess
from typing import List, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

_EMBEDDING_MODEL = "nomic-embed-text"
_EMBEDDING_DIM = 768


@lru_cache(maxsize=128)
def embed(text: str, model: Optional[str] = None) -> List[float]:
    """Return a real embedding vector. Falls back to deterministic SHA if Ollama is offline."""
    model = model or _EMBEDDING_MODEL
    try:
        r = subprocess.run(
            ["ollama", "embeddings", "-m", model, text],
            capture_output=True, text=True, timeout=10, check=True
        )
        vec = json.loads(r.stdout).get("embedding", [])
        if vec and len(vec) == _EMBEDDING_DIM:
            return vec
    except Exception as e:
        logger.debug("Ollama embed fallback: %s", e)
    return _deterministic_embed(text)


def _deterministic_embed(text: str, dim: int = _EMBEDDING_DIM) -> List[float]:
    h = hashlib.sha512(text.encode()).hexdigest()
    vec = []
    for i in range(dim):
        chunk = h[(i * 2) % len(h):((i * 2) + 4) % len(h) + 1]
        val = int(chunk, 16) / 65535.0 if chunk else 0.5
        vec.append(val)
    return vec


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)

