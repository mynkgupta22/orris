from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
import os

# NOTE: We import unstructured partitioners lazily inside functions to provide
# clearer error messages and to allow partial environments.

import pandas as pd


SUPPORTED_TYPES = {"pdf", "docx", "txt", "xlsx", "image"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def detect_type(path: str) -> str:
    """Detect a supported source type from file extension.

    Returns one of: "pdf" | "docx" | "txt" | "xlsx" | "image".
    Raises ValueError for unsupported extensions.
    """

    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext == ".docx":
        return "docx"
    if ext in {".txt", ".log"}:
        return "txt"
    if ext in {".xlsx", ".xls"}:
        return "xlsx"
    if ext in IMAGE_EXTS:
        return "image"
    raise ValueError(f"Unsupported file extension: {ext}")


def _normalize_element(
    *,
    text: str,
    base_meta: Dict[str, Any],
    is_table: bool = False,
    is_image: bool = False,
    source_page: Optional[int] = None,
) -> Dict[str, Any]:
    meta = dict(base_meta)
    meta.update(
        {
            "is_table": bool(is_table),
            "is_image": bool(is_image),
            "source_page": source_page,
        }
    )
    return {"text": text, "meta": meta}


def load_pdf(
    path: str,
    base_meta: Dict[str, Any],
    *,
    summarize_image_fn: Optional[Callable[[str], str]] = None,
    image_lookup: Optional[Callable[[int], List[str]]] = None,
) -> List[Dict[str, Any]]:
    try:
        from unstructured.partition.pdf import partition_pdf  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "unstructured.partition.pdf import failed. Install 'unstructured[pdf]' or 'unstructured[all-docs]'. "
            f"Underlying error: {e}"
        )

    elements = partition_pdf(
        filename=path,
        strategy="fast",
        chunking_strategy="by_title",
        max_characters=2000,
        new_after_n_chars=1800,
        overlap=200,
        combine_text_under_n_chars=200,
        infer_table_structure=True,
    )

    normalized: List[Dict[str, Any]] = []
    for el in elements:
        category = getattr(el, "category", "") or getattr(el, "type", "")
        page_number = getattr(el, "page_number", None)
        text = getattr(el, "text", "") or ""
        is_table = category == "Table"
        is_image = category in {"Image", "Figure"}

        if is_image:
            summary: Optional[str] = None
            if summarize_image_fn is not None:
                try:
                    # Prefer extracted image if available for this page
                    img_paths = image_lookup(page_number) if (image_lookup and page_number) else []
                    target_img = img_paths[0] if img_paths else path
                    summary = summarize_image_fn(target_img)
                except Exception:
                    summary = None
            if summary and summary.strip():
                text = summary
            elif not text.strip():
                # Fallback placeholder for images without text
                text = f"Image: {base_meta.get('source_doc_name', Path(path).name)}"

        if not text.strip() and not is_table and not is_image:
            continue

        elem = _normalize_element(
            text=text,
            base_meta=base_meta,
            is_table=is_table,
            is_image=is_image,
            source_page=page_number,
        )
        if is_image:
            meta_with_summary = dict(elem["meta"])  # shallow copy
            meta_with_summary["image_summary"] = text
            # record the first extracted image path, if any
            if image_lookup and page_number:
                img_paths = image_lookup(page_number)
                if img_paths:
                    meta_with_summary["image_url"] = img_paths[0]
            elem["meta"] = meta_with_summary
        normalized.append(elem)
    return normalized


def load_docx(path: str, base_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        from unstructured.partition.docx import partition_docx  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "unstructured.partition.docx import failed. Install 'unstructured[docx]' or 'unstructured[all-docs]'. "
            f"Underlying error: {e}"
        )

    try:
        elements = partition_docx(filename=path)
    except Exception as e:
        raise RuntimeError(
            "Failed to parse DOCX with unstructured. Consider installing 'unstructured[docx]' or 'all-docs'. "
            f"Error: {e}"
        )
    normalized: List[Dict[str, Any]] = []
    for el in elements:
        category = getattr(el, "category", "") or getattr(el, "type", "")
        text = getattr(el, "text", "") or ""
        is_table = category == "Table"

        if not text.strip() and not is_table:
            continue

        normalized.append(
            _normalize_element(
                text=text,
                base_meta=base_meta,
                is_table=is_table,
                is_image=False,
                source_page=None,
            )
        )
    return normalized


def load_txt(path: str, base_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = p.read_text(encoding="latin-1")

    if not text.strip():
        return []
    return [
        _normalize_element(
            text=text,
            base_meta=base_meta,
            is_table=False,
            is_image=False,
            source_page=None,
        )
    ]


def load_xlsx(path: str, base_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Minimal approach: use pandas to read each sheet and serialize to CSV-like text
    book = pd.read_excel(path, sheet_name=None)  # dict of sheet_name -> DataFrame
    normalized: List[Dict[str, Any]] = []
    for sheet_name, df in book.items():
        if df.empty:
            continue
        # Convert to CSV-like text for MVP (markdown optional later)
        csv_text = df.to_csv(index=False)
        text = f"Sheet: {sheet_name}\n{csv_text}"
        meta = dict(base_meta)
        meta.update({"is_table": True, "is_image": False, "source_page": None, "sheet_name": sheet_name})
        normalized.append({"text": text, "meta": meta})
    return normalized


def load_image(
    path: str,
    base_meta: Dict[str, Any],
    *,
    summarize_image_fn: Optional[Callable[[str], str]] = None,
) -> List[Dict[str, Any]]:
    # Summarize via callback if provided; otherwise placeholder text
    name = base_meta.get("source_doc_name", Path(path).name)
    summary: Optional[str] = None
    if summarize_image_fn is not None:
        try:
            summary = summarize_image_fn(path)
        except Exception:
            summary = None
    text = summary if (summary and summary.strip()) else f"Image: {name}"
    elem = _normalize_element(
        text=text,
        base_meta=base_meta,
        is_table=False,
        is_image=True,
        source_page=None,
    )
    meta_with_summary = dict(elem["meta"])  # shallow copy
    meta_with_summary["image_summary"] = text
    meta_with_summary["image_url"] = str(Path(path))
    elem["meta"] = meta_with_summary
    return [elem]


def load_file_to_elements(
    path: str,
    base_meta: Dict[str, Any],
    *,
    summarize_image_fn: Optional[Callable[[str], str]] = None,
    image_lookup: Optional[Callable[[int], List[str]]] = None,
) -> List[Dict[str, Any]]:
    """Route a file to the proper loader and return normalized elements.

    The returned list items have shape: {"text": str, "meta": dict}
    where meta minimally contains flags: is_table, is_image, source_page, and
    inherits keys from base_meta.
    """

    dtype = detect_type(path)
    if dtype == "pdf":
        return load_pdf(path, base_meta, summarize_image_fn=summarize_image_fn, image_lookup=image_lookup)
    if dtype == "docx":
        return load_docx(path, base_meta)
    if dtype == "txt":
        return load_txt(path, base_meta)
    if dtype == "xlsx":
        return load_xlsx(path, base_meta)
    if dtype == "image":
        return load_image(path, base_meta, summarize_image_fn=summarize_image_fn)
    raise ValueError(f"Unsupported detected type: {dtype}")


