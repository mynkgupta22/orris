from __future__ import annotations

"""
Minimal image/graph summarization via OpenAI GPT-4o-mini.

This module exposes a single function `summarize_image_llava(image_path: str) -> str`
that returns a short textual summary using OpenAI's vision API.

Notes:
- Requires OPENAI_API_KEY environment variable to be set
- For strict MVP, callers should handle exceptions and fall back gracefully.
"""

import os
import base64
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent.parent.parent / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

try:
    from openai import OpenAI
except ImportError as _e:
    OpenAI = None  # type: ignore

_client: Optional[OpenAI] = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    
    if OpenAI is None:
        raise RuntimeError("openai library is not available; please install it.")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is required.")
    
    _client = OpenAI(api_key=api_key)
    return _client


def _encode_image(image_path: str) -> str:
    """Encode image to base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def summarize_image_llava(image_path: str) -> str:
    """Return a concise description/summary for graphs or images using GPT-4o-mini.

    Keep the output short and informative for indexing.
    """
    client = _get_client()
    
    # Encode image to base64
    base64_image = _encode_image(image_path)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "You are an analyst. Examine the chart or image and, in no more than 4 sentences, concisely describe the key trends, axes (including units, scales, and categories), and all notable features (if any), including subtle or distinct details that may be easily overlooked. Focus on insights and patterns rather than restating obvious labels, and ensure every sentence adds unique, non-redundant information."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        max_tokens=150
    )
    
    return response.choices[0].message.content.strip() if response.choices[0].message.content else ""


def summarize_image_with_base64(image_path: str) -> tuple[str, str]:
    """Return both summary and base64 encoding for images.
    
    Returns:
        tuple: (summary, base64_encoding)
    """
    client = _get_client()
    
    # Encode image to base64
    base64_image = _encode_image(image_path)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "You are an analyst. Examine the chart or image and, in no more than 4 sentences, concisely describe the key trends, axes (including units, scales, and categories), and all notable features (if any), including subtle or distinct details that may be easily overlooked. Focus on insights and patterns rather than restating obvious labels, and ensure every sentence adds unique, non-redundant information."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        max_tokens=150
    )
    
    summary = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
    return summary, base64_image


