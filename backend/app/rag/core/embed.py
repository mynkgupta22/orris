from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import os
import httpx
import numpy as np
from app.core.config import get_settings

settings = get_settings()


try:
    import torch  # type: ignore
except Exception:  # pragma: no cover
    torch = None  # type: ignore

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception as _e:  # pragma: no cover
    SentenceTransformer = None  # type: ignore


DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")


@dataclass
class EmbeddingInfo:
    model_name: str
    dimension: int


class EmbeddingClient:
    """Thin wrapper over SentenceTransformers for text embeddings.

    - Loads the model lazily on first use
    - Produces L2-normalized float32 numpy arrays
    """

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL):
        if SentenceTransformer is None:
            raise RuntimeError(
                "sentence-transformers not available. Please install it to use embeddings."
            )
        self._model_name = model_name
        self._model: Optional[SentenceTransformer] = None
        self._dimension: Optional[int] = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            # ensure model is loaded
            _ = self._get_model()
        assert self._dimension is not None
        return self._dimension

    def _get_model(self) -> SentenceTransformer:
        if self._model is not None:
            return self._model
        device = "cuda" if (torch is not None and hasattr(torch, "cuda") and torch.cuda.is_available()) else "cpu"
        self._model = SentenceTransformer(self._model_name, device=device)
        # probe dimension by encoding a tiny sample
        vec = self._model.encode(["test"], normalize_embeddings=True)
        self._dimension = int(vec.shape[1])
        return self._model

    def encode_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        model = self._get_model()
        vectors: np.ndarray = model.encode(
            texts,
            batch_size=int(os.getenv("EMBED_BATCH_SIZE", "32")),
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        # Ensure dtype float32
        if vectors.dtype != np.float32:
            vectors = vectors.astype(np.float32, copy=False)
        return vectors


_singleton_client: Optional[EmbeddingClient] = None


def get_embedding_client(model_name: Optional[str] = None) -> EmbeddingClient:
    global _singleton_client
    if _singleton_client is None:
        _singleton_client = EmbeddingClient(model_name or DEFAULT_EMBEDDING_MODEL)
    return _singleton_client


