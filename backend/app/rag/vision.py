from __future__ import annotations

"""
Minimal image/graph summarization via LLaVA 1.6 7B.

This module exposes a single function `summarize_image_llava(image_path: str) -> str`
that returns a short textual summary. It loads the model lazily on first call.

Notes:
- Requires a compatible environment (GPU recommended). If unavailable,
  this function will raise at import/model load time.
- For strict MVP, callers should handle exceptions and fall back gracefully.
"""

from typing import Optional
import torch

try:
    from transformers import AutoProcessor, AutoModelForVision2Seq
except Exception as _e:  # pragma: no cover
    AutoProcessor = None  # type: ignore
    AutoModelForVision2Seq = None  # type: ignore

_MODEL_ID = "llava-hf/llava-1.6-7b-hf"
_processor: Optional[AutoProcessor] = None
_model: Optional[AutoModelForVision2Seq] = None


def _load_model_if_needed():
    global _processor, _model
    if _processor is not None and _model is not None:
        return
    if AutoProcessor is None or AutoModelForVision2Seq is None:
        raise RuntimeError(
            "transformers is not available; please install it to use LLaVA summarization."
        )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    _processor = AutoProcessor.from_pretrained(_MODEL_ID)
    _model = AutoModelForVision2Seq.from_pretrained(
        _MODEL_ID,
        torch_dtype=torch.float16 if device == "cuda" else None,
        low_cpu_mem_usage=True,
    ).to(device)


def summarize_image_llava(image_path: str) -> str:
    """Return a concise description/summary for graphs or images using LLaVA 1.6 7B.

    Keep the output short and informative for indexing.
    """
    _load_model_if_needed()
    assert _processor is not None and _model is not None

    device = next(_model.parameters()).device
    prompt = (
        "You are an analyst. Briefly summarize the key trend(s), axes, and notable points in this chart."
        " Keep it under 2 sentences."
    )
    inputs = _processor(images=image_path, text=prompt, return_tensors="pt").to(device)
    with torch.no_grad():
        output_ids = _model.generate(**inputs, max_new_tokens=80)
    summary = _processor.batch_decode(output_ids, skip_special_tokens=True)[0]
    return summary.strip()


