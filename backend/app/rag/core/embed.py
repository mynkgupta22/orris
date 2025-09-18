from typing import List, Optional
import httpx
import numpy as np
from app.core.config import get_settings

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"


class EmbeddingClient:
    """Simple client for Hugging Face Inference API text embeddings."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL):
        self.model_name = model_name
        self._api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        self._client = None
        self._headers = None

    def _get_client_and_headers(self):
        """Initialize HTTP client and headers."""
        if self._client is None:
            settings = get_settings()
            api_key = getattr(settings, 'huggingface_api_key', None)
            if not api_key:
                raise RuntimeError("huggingface_api_key is required")
            
            self._client = httpx.Client(timeout=60.0)
            self._headers = {"Authorization": f"Bearer {api_key}"}
        
        return self._client, self._headers

    def _encode_request(self, inputs) -> np.ndarray:
        """Send encoding request to HuggingFace API."""
        client, headers = self._get_client_and_headers()
        
        payload = {
            "inputs": inputs,
            "options": {"wait_for_model": True}
        }
        
        response = client.post(self._api_url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        # Convert to numpy array and handle different response formats
        embeddings = np.array(result, dtype=np.float32)
        
        # Handle nested list format [[embedding]] -> [embedding]
        if embeddings.ndim == 3 and embeddings.shape[1] == 1:
            embeddings = embeddings.squeeze(axis=1)
        
        # Single embedding case
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        
        # L2 normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms > 0, norms, 1)
        embeddings = embeddings / norms
        
        return embeddings

    def encode_texts(self, texts: List[str]) -> np.ndarray:
        """Encode list of texts and return L2-normalized embeddings."""
        if not texts:
            return np.zeros((0, 1024), dtype=np.float32)  # Default dimension
        
        return self._encode_request(texts)

    def __del__(self):
        """Clean up HTTP client."""
        if self._client is not None:
            self._client.close()


_singleton_client: Optional[EmbeddingClient] = None


def get_embedding_client(model_name: Optional[str] = None) -> EmbeddingClient:
    """Get singleton embedding client."""
    global _singleton_client
    
    if model_name is None:
        model_name = DEFAULT_EMBEDDING_MODEL
        
    if _singleton_client is None or _singleton_client.model_name != model_name:
        _singleton_client = EmbeddingClient(model_name)
        
    return _singleton_client
