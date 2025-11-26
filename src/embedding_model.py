# src/embedding_model.py
from typing import List
import math
import re
from .config import PG_DIM

TOKEN_RE = re.compile(r"\w+", re.UNICODE)

def _text_to_vector(text: str, dim: int) -> List[float]:
    """
    Very lightweight embedding:
    - tokenize text into words
    - hash each token into one of `dim` buckets
    - count frequencies
    - L2-normalize the vector
    """
    vec = [0.0] * dim
    tokens = TOKEN_RE.findall(text.lower())

    for tok in tokens:
        idx = hash(tok) % dim
        vec[idx] += 1.0

    # L2 normalization
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]

    return vec

def embed_texts(texts: List[str], batch_size: int = 64) -> List[List[float]]:
    """
    Embed a list of texts into vectors of length PG_DIM.
    Pure Python, very light on memory.
    """
    return [_text_to_vector(t, PG_DIM) for t in texts]
