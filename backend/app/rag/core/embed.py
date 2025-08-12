from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import os
import httpx
import numpy as np
from app.core.config import get_settings

settings = get_settings()

DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")
HF_API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/{}"

@dataclass
class EmbeddingInfo:
    model_name: str
    dimension: int

class EmbeddingClient:
    """Thin wrapper over Hugging Face Inference API for text embeddings."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL):
        self._model_name = model_name
        self._api_key = settings.hugging_face_api_key
        if not self._api_key:
            raise ValueError("Hugging Face API key is not set.")
        # Dimension for BAAI/bge-m3 is 1024
        self._dimension = 1024

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def encode_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)

        headers = {"Authorization": f"Bearer {self._api_key}"}
        api_url = HF_API_URL.format(self._model_name)
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    api_url,
                    headers=headers,
                    json={"inputs": texts, "options": {"wait_for_model": True}},
                    timeout=30.0,
                )
                response.raise_for_status()
                embeddings = response.json()

        except httpx.HTTPStatusError as e:
            # Log the error or handle it as needed
            print(f"HTTP error occurred: {e}")
            raise
        except Exception as e:
            print(f"An error occurred: {e}")
            raise

        # Ensure the output is a numpy array of float32
        vectors = np.array(embeddings, dtype=np.float32)
        
        # L2 normalization
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / norms
        
        return vectors

_singleton_client: Optional[EmbeddingClient] = None

def get_embedding_client(model_name: Optional[str] = None) -> EmbeddingClient:
    global _singleton_client
    if _singleton_client is None:
        _singleton_client = EmbeddingClient(model_name or DEFAULT_EMBEDDING_MODEL)
    return _singleton_client



