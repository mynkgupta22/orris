from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import os
import httpx
import numpy as np
import sys
from app.core.config import get_settings

settings = get_settings()

# Set the desired model as the default and only option.
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"

# Empty the fallback list to ensure only the default model is used.
FALLBACK_MODELS = []


@dataclass
class EmbeddingInfo:
    model_name: str
    dimension: int


class EmbeddingClient:
    """Client for Hugging Face Inference API text embeddings.
    
    - Uses HF Inference API to avoid loading models locally
    - Produces L2-normalized float32 numpy arrays
    - Memory efficient for deployment on limited instances
    - Includes automatic fallback for unsupported models
    """

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL):
        self._original_model_name = model_name
        self._model_name = model_name
        self._dimension: Optional[int] = None
        self._api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        self._client: Optional[httpx.Client] = None
        self._api_key: Optional[str] = None
        self._model_tested = False
        self._model_works = False
        # Set numpy print options to see the full array in the console
        np.set_printoptions(threshold=sys.maxsize)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            # Probe dimension with a test encoding
            test_embedding = self._encode_single_text("test")
            self._dimension = len(test_embedding)
        return self._dimension

    def _get_client_and_headers(self):
        """Lazy initialization of HTTP client and headers."""
        if self._client is None:
            # Check for API key only when actually needed
            self._api_key = getattr(settings, 'huggingface_api_key', None)
            if not self._api_key:
                raise RuntimeError(
                    "huggingface_api_key environment variable is required for Hugging Face Inference API. "
                    "Please add it to your .env file or settings."
                )
            
            self._client = httpx.Client(
                timeout=90.0,  # Long timeout for model loading
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        
        headers = {"Authorization": f"Bearer {self._api_key}"}
        return self._client, headers

    def _try_model(self, model_name: str, text: str) -> np.ndarray:
        """Try to encode text with a specific model."""
        client, headers = self._get_client_and_headers()
        api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        
        # Try the standard feature extraction format
        payload = {
            "inputs": text,
            "options": {
                "wait_for_model": True,
                "use_cache": False
            }
        }
        
        response = client.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        # Handle different response formats
        if isinstance(result, list):
            if len(result) > 0 and isinstance(result[0], list):
                # Nested list format [[embedding]] - take first embedding
                embedding = np.array(result[0], dtype=np.float32)
            else:
                # Simple list format [embedding]
                embedding = np.array(result, dtype=np.float32)
        else:
            raise RuntimeError(f"Unexpected API response format: {type(result)}")
        
        # Flatten if needed
        if embedding.ndim > 1:
            embedding = embedding.flatten()
        
        # L2 normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def _encode_single_text(self, text: str) -> np.ndarray:
        """Encode a single text and return normalized embedding."""
        
        # If we haven't tested the model yet, try the original model first
        if not self._model_tested:
            try:
                print(f"Testing model: {self._original_model_name}")
                embedding = self._try_model(self._original_model_name, text)
                self._model_tested = True
                self._model_works = True
                print(f"✅ {self._original_model_name} works! Using it for embeddings.")
                return embedding
                
            except httpx.HTTPStatusError as e:
                print(f"❌ {self._original_model_name} failed: {e.response.status_code}")
                self._model_tested = True
                self._model_works = False
                
                # Try fallback models (this list is now empty)
                for fallback_model in FALLBACK_MODELS:
                    try:
                        print(f"Trying fallback model: {fallback_model}")
                        embedding = self._try_model(fallback_model, text)
                        
                        # Switch to working model
                        print(f"✅ Switched to {fallback_model}")
                        self._model_name = fallback_model
                        self._api_url = f"https://api-inference.huggingface.co/models/{fallback_model}"
                        return embedding
                        
                    except Exception as fallback_error:
                        print(f"❌ {fallback_model} also failed: {fallback_error}")
                        continue
                
                # If all models fail, raise the original error
                if e.response.status_code == 503:
                    raise RuntimeError(
                        f"Model {self._original_model_name} is loading on HF servers. This can take 1-2 minutes. Please wait and retry."
                    )
                elif e.response.status_code == 401:
                    raise RuntimeError("Invalid Hugging Face API key")
                elif e.response.status_code == 400:
                    raise RuntimeError(
                        f"Model {self._original_model_name} doesn't support feature extraction."
                    )
                else:
                    raise RuntimeError(f"Model {self._original_model_name} failed. Error: {e.response.status_code} - {e.response.text}")
                    
            except Exception as e:
                raise RuntimeError(f"Failed to encode text: {str(e)}")
        
        # Model already tested and working
        elif self._model_works:
            return self._try_model(self._model_name, text)
        
        # Model tested but not working, use current fallback
        else:
            return self._try_model(self._model_name, text)

    def _encode_batch(self, texts: List[str]) -> np.ndarray:
        """Encode multiple texts in a single API call."""
        client, headers = self._get_client_and_headers()
        
        payload = {
            "inputs": texts,
            "options": {
                "wait_for_model": True,
                "use_cache": False
            }
        }
        
        try:
            response = client.post(
                self._api_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Convert to numpy array
            embeddings = np.array(result, dtype=np.float32)
            
            # Handle different response formats
            if embeddings.ndim == 3:  # [batch, 1, dim] -> [batch, dim]
                embeddings = embeddings.squeeze(axis=1)
            elif embeddings.ndim == 1:  # Single embedding returned as 1D
                embeddings = embeddings.reshape(1, -1)
            
            # Validate shapes
            if len(texts) != embeddings.shape[0]:
                raise RuntimeError(f"Expected {len(texts)} embeddings, got {embeddings.shape[0]}")
            
            # L2 normalize each embedding
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms = np.where(norms > 0, norms, 1)  # Avoid division by zero
            embeddings = embeddings / norms           
            return embeddings
            
        except httpx.HTTPStatusError as e:
            # For batch requests, fall back to individual encoding if batch fails
            if not self._model_tested:
                # Test with single text first
                _ = self._encode_single_text(texts[0])
                # Then try batch again with the working model
                return self._encode_batch(texts)
            else:
                raise RuntimeError(f"Batch encoding failed: {e.response.status_code} - {e.response.text}")
                
        except Exception as e:
            raise RuntimeError(f"Failed to encode texts: {str(e)}")

    def encode_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            # The dimension might not be probed yet if input is empty
            if self._dimension is None:
                self._dimension = 1024 # Manually set dimension for the chosen model
            return np.zeros((0, self.dimension), dtype=np.float32)
        
        batch_size = getattr(settings, 'EMBED_BATCH_SIZE', 16)  # Smaller batch for API
        if isinstance(batch_size, str):
            batch_size = int(batch_size)
        
        # For small batches, try batch API first
        if len(texts) <= batch_size:
            try:
                return self._encode_batch(texts)
            except:
                # Fall back to individual encoding
                print(f"Batch encoding failed, falling back to individual encoding")
                embeddings = []
                for text in texts:
                    embedding = self._encode_single_text(text)
                    embeddings.append(embedding)
                return np.vstack(embeddings)
        
        # For larger requests, split into batches
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            try:
                batch_embeddings = self._encode_batch(batch_texts)
                all_embeddings.append(batch_embeddings)
            except:
                # Fall back to individual encoding for this batch
                batch_embeddings = []
                for text in batch_texts:
                    embedding = self._encode_single_text(text)
                    batch_embeddings.append(embedding)
                all_embeddings.append(np.vstack(batch_embeddings))
        
        final_embeddings = np.vstack(all_embeddings)

        # --- Added for debugging ---
        print("--- Final Embeddings from encode_texts ---")
        print(f"Total number of embeddings: {final_embeddings.shape[0]}")
        print(f"Final embeddings (shape: {final_embeddings.shape}):\n{final_embeddings}")
        print("-------------------------------------------")
        
        return final_embeddings

    def __del__(self):
        """Clean up HTTP client on deletion."""
        if hasattr(self, '_client') and self._client is not None:
            self._client.close()


_singleton_client: Optional[EmbeddingClient] = None


def get_embedding_client(model_name: Optional[str] = None) -> EmbeddingClient:
    global _singleton_client
    # Ensure the singleton always uses the hardcoded default unless explicitly overridden
    if model_name is None:
        model_name = DEFAULT_EMBEDDING_MODEL
        
    if _singleton_client is None or _singleton_client.model_name != model_name:
        _singleton_client = EmbeddingClient(model_name)
        
    return _singleton_client
