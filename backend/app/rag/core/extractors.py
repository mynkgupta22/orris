from __future__ import annotations

from typing import Dict, List, Optional
from pathlib import Path
import io
import zipfile


def extract_pdf_images(pdf_path: str, out_dir: str) -> Dict[int, List[str]]:
    """Extract images from a PDF file into out_dir.

    Returns a mapping: page_number (1-based) -> list of image file paths in reading order.
    Requires PyMuPDF (fitz).
    """
    try:
        import fitz  # type: ignore
    except Exception as e:
        raise RuntimeError("PyMuPDF (fitz) is required for PDF image extraction") from e

    pdf = fitz.open(pdf_path)
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    page_to_paths: Dict[int, List[str]] = {}
    for page_index in range(len(pdf)):
        page = pdf.load_page(page_index)
        images = page.get_images(full=True)
        if not images:
            continue
        page_no = page_index + 1
        saved: List[str] = []
        for idx, img in enumerate(images):
            xref = img[0]
            base = f"p{page_no:03d}_img{idx:03d}"
            pix = fitz.Pixmap(pdf, xref)
            # choose extension
            ext = "png" if not pix.alpha else "png"
            out_path = out_root / f"{base}.{ext}"
            if pix.n >= 5:  # CMYK or other
                pix = fitz.Pixmap(fitz.csRGB, pix)
            pix.save(str(out_path))
            saved.append(str(out_path))
            pix = None  # free
        if saved:
            page_to_paths[page_no] = saved
    pdf.close()
    return page_to_paths


def extract_docx_images(docx_path: str, out_dir: str) -> List[str]:
    """Extract embedded images from a DOCX into out_dir.

    Returns a list of file paths in approximate document order (as stored in /word/media).
    """
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    paths: List[str] = []
    with zipfile.ZipFile(docx_path) as z:
        for name in z.namelist():
            if name.startswith("word/media/") and not name.endswith("/"):
                data = z.read(name)
                filename = Path(name).name
                out_path = out_root / filename
                with open(out_path, "wb") as f:
                    f.write(data)
                paths.append(str(out_path))
    return paths


