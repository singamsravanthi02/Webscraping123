from __future__ import annotations

import logging
from pathlib import Path

from docx import Document
from pypdf import PdfReader

logger = logging.getLogger(__name__)

try:
    from pdf2image import convert_from_path
    from PIL import Image, ImageFilter, ImageOps
    import pytesseract
except Exception:  # pragma: no cover - optional runtime dependency guard
    convert_from_path = None
    Image = None
    ImageFilter = None
    ImageOps = None
    pytesseract = None


def _ocr_image(image) -> str:
    if pytesseract is None or ImageOps is None:
        return ""

    processed = ImageOps.grayscale(image)
    processed = ImageOps.autocontrast(processed)
    if ImageFilter is not None:
        processed = processed.filter(ImageFilter.SHARPEN)
    return pytesseract.image_to_string(processed)


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="ignore")


def extract_document_text(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        return ""

    ext = path.suffix.lower().lstrip(".")

    try:
        if ext in {"txt", "md", "csv", "json", "log"}:
            return _read_text_file(path)

        if ext == "docx":
            document = Document(str(path))
            paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
            return "\n".join(paragraphs)

        if ext == "pptx":
            from pptx import Presentation

            presentation = Presentation(str(path))
            text_parts: list[str] = []
            for slide in presentation.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        text_parts.append(shape.text)
            return "\n".join(text_parts)

        if ext == "pdf":
            reader = PdfReader(str(path))
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text)

            extracted = "\n".join(text_parts).strip()
            if extracted:
                return extracted

            if convert_from_path is None or pytesseract is None:
                return ""

            ocr_parts: list[str] = []
            for page_image in convert_from_path(str(path), dpi=220):
                ocr_parts.append(_ocr_image(page_image))
            return "\n".join(part for part in ocr_parts if part.strip())

        if ext in {"png", "jpg", "jpeg", "webp", "tiff", "bmp"}:
            if pytesseract is None or Image is None:
                return ""
            with Image.open(str(path)) as image:
                return _ocr_image(image)

    except Exception as exc:
        logger.warning("Document text extraction failed for %s: %s", file_path, exc)
        return ""

    return ""
