from __future__ import annotations

import hashlib
import logging
import re
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.domain.knowledge.models import Document, DocumentChunk, DocumentStatus, DocumentType
from app.domain.learning.services.qdrant_service import chunk_text, ingest_document
from app.services.document_text_extractor import extract_document_text

logger = logging.getLogger(__name__)

SREYAS_SOURCE_PAGES: dict[str, str] = {
    "CSE": "https://sreyas.ac.in/departments/cse/course-content",
    "AIML": "https://sreyas.ac.in/departments/aiml/course-content",
    "ECE": "https://sreyas.ac.in/departments/ece/course-content",
}

SREYAS_CHUNK_SIZE = 3500
SREYAS_CHUNK_OVERLAP = 350


@dataclass(slots=True)
class CrawledDocument:
    title: str
    source_page_url: str
    resource_url: str
    source: str
    department: str
    semester: str | None
    subject: str
    unit: str | None
    resource_label: str
    document_type: DocumentType
    content: str
    google_drive_file_id: str | None = None
    page_number: int | None = None
    metadata: dict[str, Any] | None = None

    def signature(self) -> str:
        digest = hashlib.sha256()
        digest.update((self.source_page_url or "").encode("utf-8"))
        digest.update((self.resource_url or "").encode("utf-8"))
        digest.update((self.title or "").encode("utf-8"))
        digest.update((self.content or "").encode("utf-8"))
        return digest.hexdigest()


@dataclass(slots=True)
class CrawlFailure:
    url: str
    department: str
    subject: str | None
    reason: str
    retry_attempts: int
    final_status: str


def _normalize(text: str | None) -> str:
    return " ".join((text or "").split())


def _page_title(html: str, fallback: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:
        return _normalize(soup.title.string)
    return fallback


def _extract_drive_file_id(url: str) -> str | None:
    match = re.search(r"(?:/d/|/folders/)([A-Za-z0-9_-]+)", url or "")
    return match.group(1) if match else None


def _drive_file_url(file_id: str) -> str:
    return f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"


def _drive_folder_url(folder_id: str) -> str:
    return f"https://drive.google.com/drive/folders/{folder_id}?usp=drive_link"


def _is_drive_folder_url(url: str) -> bool:
    return "/drive/folders/" in (url or "").lower()


def _is_drive_file_url(url: str) -> bool:
    url_lower = (url or "").lower()
    return any(
        marker in url_lower
        for marker in (
            "drive.google.com/file/d/",
            "docs.google.com/document/d/",
            "docs.google.com/presentation/d/",
            "docs.google.com/spreadsheets/d/",
        )
    )


def _classify_failure(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
        return f"{exc.response.status_code} {exc.response.reason_phrase}"
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    message = str(exc).lower()
    if "ssl" in message:
        return "ssl"
    if "quota" in message:
        return "quota"
    return exc.__class__.__name__.lower()


def _retry_delay(attempt: int) -> float:
    return 0.5 * (2 ** (attempt - 1))


def _fetch_text(url: str, *, timeout: float = 60.0) -> str:
    last_error: Exception | None = None
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for attempt in range(1, 4):
            try:
                response = client.get(url)
                response.raise_for_status()
                return response.text
            except Exception as exc:
                last_error = exc
                if attempt < 3:
                    time.sleep(_retry_delay(attempt))
                    continue
    raise RuntimeError(f"Failed to fetch {url}: {last_error}") from last_error


def _fetch_bytes(url: str, *, timeout: float = 60.0) -> httpx.Response:
    last_error: Exception | None = None
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for attempt in range(1, 4):
            try:
                response = client.get(url)
                response.raise_for_status()
                return response
            except Exception as exc:
                last_error = exc
                if attempt < 3:
                    time.sleep(_retry_delay(attempt))
                    continue
    raise RuntimeError(f"Failed to fetch {url}: {last_error}") from last_error


def _html_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
        element.decompose()
    text = soup.get_text(separator="\n")
    lines = (line.strip() for line in text.splitlines())
    chunks = (piece.strip() for line in lines for piece in line.split("  "))
    return "\n".join(chunk for chunk in chunks if chunk)


def _filename_from_disposition(disposition: str | None) -> str | None:
    if not disposition:
        return None
    match = re.search(r'filename="?([^";]+)"?', disposition, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _content_type_to_doc_type(filename: str | None, content_type: str | None, fallback: DocumentType = DocumentType.WEBPAGE) -> DocumentType:
    ext = Path(filename or "").suffix.lower().lstrip(".")
    mapping = {
        "pdf": DocumentType.PDF,
        "docx": DocumentType.DOCX,
        "pptx": DocumentType.PPTX,
        "txt": DocumentType.TXT,
        "md": DocumentType.MD,
        "csv": DocumentType.TXT,
        "json": DocumentType.TXT,
        "log": DocumentType.TXT,
        "xlsx": DocumentType.TXT,
        "zip": DocumentType.TXT,
        "png": DocumentType.TXT,
        "jpg": DocumentType.TXT,
        "jpeg": DocumentType.TXT,
        "webp": DocumentType.TXT,
        "tiff": DocumentType.TXT,
        "bmp": DocumentType.TXT,
    }
    if ext in mapping:
        return mapping[ext]
    if content_type:
        lowered = content_type.lower()
        if "pdf" in lowered:
            return DocumentType.PDF
        if "word" in lowered or "docx" in lowered:
            return DocumentType.DOCX
        if "presentation" in lowered or "ppt" in lowered:
            return DocumentType.PPTX
        if "text" in lowered:
            return DocumentType.TXT
        if "sheet" in lowered or "excel" in lowered:
            return DocumentType.TXT
    return fallback


def _download_google_doc_text(resource_url: str, *, kind: str, file_id: str) -> tuple[str, DocumentType]:
    if kind == "document":
        export_url = f"https://docs.google.com/document/d/{file_id}/export?format=txt"
    else:
        export_url = f"https://docs.google.com/presentation/d/{file_id}/export/txt"

    try:
        response = _fetch_bytes(export_url)
        if "text/plain" in (response.headers.get("content-type") or "").lower():
            return response.text, DocumentType.TXT
        if response.text.strip():
            return _html_text(response.text), DocumentType.WEBPAGE
    except Exception as exc:
        logger.debug("Google export failed for %s: %s", resource_url, exc)
    return "", DocumentType.WEBPAGE


def _download_drive_file(resource_url: str, file_id: str) -> tuple[str, DocumentType]:
    response = _fetch_bytes(f"https://drive.google.com/uc?export=download&id={file_id}")
    filename = _filename_from_disposition(response.headers.get("content-disposition")) or Path(resource_url).name
    doc_type = _content_type_to_doc_type(filename, response.headers.get("content-type"))
    suffix = Path(filename or resource_url).suffix.lower() or ".bin"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    try:
        extracted = extract_document_text(tmp_path).strip()
        if extracted:
            return extracted, doc_type

        content_type = (response.headers.get("content-type") or "").lower()
        if "text/html" in content_type and response.text.strip():
            return _html_text(response.text), DocumentType.WEBPAGE

        if doc_type in {DocumentType.TXT, DocumentType.MD}:
            try:
                return response.text, doc_type
            except Exception:
                return response.content.decode("utf-8", errors="ignore"), doc_type

        return response.content.decode("utf-8", errors="ignore"), doc_type
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _download_resource(resource_url: str) -> tuple[str, DocumentType, str | None]:
    file_id = _extract_drive_file_id(resource_url)
    url_lower = resource_url.lower()

    if "/drive/folders/" in url_lower:
        html = _fetch_text(resource_url)
        return _html_text(html), DocumentType.WEBPAGE, file_id

    if "docs.google.com/document" in url_lower and file_id:
        text, doc_type = _download_google_doc_text(resource_url, kind="document", file_id=file_id)
        return text, doc_type, file_id

    if "docs.google.com/presentation" in url_lower and file_id:
        text, doc_type = _download_google_doc_text(resource_url, kind="presentation", file_id=file_id)
        return text, doc_type, file_id

    if "drive.google.com/file/d/" in url_lower and file_id:
        text, doc_type = _download_drive_file(resource_url, file_id)
        return text, doc_type, file_id

    html = _fetch_text(resource_url)
    return _html_text(html), DocumentType.WEBPAGE, file_id


def _drive_row_title(row: Any) -> str:
    title_node = row.find("strong")
    if title_node and title_node.get_text(strip=True):
        return _normalize(title_node.get_text(" ", strip=True))
    tooltip_node = row.select_one("[data-tooltip]")
    if tooltip_node and tooltip_node.get("data-tooltip"):
        tooltip = _normalize(tooltip_node.get("data-tooltip"))
        if tooltip:
            return tooltip.split(" PDF", 1)[0].split(" DOCX", 1)[0].split(" PPTX", 1)[0].strip()
    return _normalize(row.get_text(" ", strip=True))


def _drive_row_kind(row: Any) -> str:
    data_target = (row.get("data-target") or "").lower()
    if data_target:
        return data_target
    icon_title = row.select_one("svg title")
    if icon_title and icon_title.get_text(strip=True).lower() == "folder":
        return "folder"
    if "folder" in _drive_row_title(row).lower():
        return "folder"
    return "doc"


def _parse_drive_listing_entries(folder_url: str, base_entry: dict[str, Any], html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    base_metadata = dict(base_entry.get("metadata") or {})

    for row in soup.select("tr[data-id]"):
        item_id = row.get("data-id")
        if not item_id or item_id.startswith("_") or item_id in seen_ids:
            continue
        seen_ids.add(item_id)

        item_kind = _drive_row_kind(row)
        item_title = _drive_row_title(row)
        if not item_title:
            continue

        resource_url = _drive_folder_url(item_id) if item_kind == "folder" else _drive_file_url(item_id)
        entries.append(
            {
                "title": item_title if base_entry.get("subject") is None else f"{base_entry.get('subject')} - {item_title}",
                "source_page_url": base_entry.get("source_page_url") or folder_url,
                "resource_url": resource_url,
                "source": base_entry.get("source") or f"SREYAS_{base_entry.get('department', '')}",
                "department": base_entry.get("department"),
                "semester": base_entry.get("semester"),
                "subject": base_entry.get("subject"),
                "unit": base_entry.get("unit"),
                "resource_label": base_entry.get("resource_label") or item_kind.title(),
                "document_type": DocumentType.WEBPAGE,
                "content": "",
                "google_drive_file_id": item_id,
                "page_number": base_entry.get("page_number") or 1,
                "metadata": {
                    **base_metadata,
                    "parent_folder_url": folder_url,
                    "parent_resource_label": base_entry.get("resource_label"),
                    "drive_item_id": item_id,
                    "drive_item_kind": item_kind,
                    "drive_row_text": _normalize(row.get_text(" ", strip=True)),
                    "drive_row_title": item_title,
                },
            }
        )

    return entries


def _expand_resource_tree(entry: dict[str, Any], visited: set[str], failures: list[CrawlFailure], depth: int = 0) -> list[dict[str, Any]]:
    resource_url = entry.get("resource_url") or ""
    canonical_key = f"folder:{_extract_drive_file_id(resource_url)}" if _is_drive_folder_url(resource_url) else (
        f"file:{_extract_drive_file_id(resource_url)}" if _extract_drive_file_id(resource_url) else resource_url
    )

    if canonical_key in visited:
        return []
    visited.add(canonical_key)

    if depth > 8:
        failures.append(
            CrawlFailure(
                url=resource_url,
                department=entry.get("department") or "",
                subject=entry.get("subject"),
                reason="max recursion depth reached",
                retry_attempts=0,
                final_status="skipped",
            )
        )
        return []

    if _is_drive_folder_url(resource_url):
        try:
            html = _fetch_text(resource_url)
        except Exception as exc:
            failures.append(
                CrawlFailure(
                    url=resource_url,
                    department=entry.get("department") or "",
                    subject=entry.get("subject"),
                    reason=_classify_failure(exc),
                    retry_attempts=3,
                    final_status="failed",
                )
            )
            return []

        child_entries = _parse_drive_listing_entries(resource_url, entry, html)
        if child_entries:
            expanded: list[dict[str, Any]] = []
            for child in child_entries:
                expanded.extend(_expand_resource_tree(child, visited, failures, depth + 1))
            return expanded

        fallback_content = _html_text(html)
        if len(_normalize(fallback_content)) >= 20:
            fallback_entry = dict(entry)
            fallback_entry["content"] = fallback_content
            fallback_entry["document_type"] = DocumentType.WEBPAGE
            fallback_entry.setdefault("metadata", {})
            fallback_entry["metadata"] = {
                **(entry.get("metadata") or {}),
                "drive_folder_fallback": True,
            }
            failures.append(
                CrawlFailure(
                    url=resource_url,
                    department=entry.get("department") or "",
                    subject=entry.get("subject"),
                    reason="folder listing returned no child rows",
                    retry_attempts=3,
                    final_status="fallback",
                )
            )
            return [fallback_entry]

        failures.append(
            CrawlFailure(
                url=resource_url,
                department=entry.get("department") or "",
                subject=entry.get("subject"),
                reason="folder listing empty",
                retry_attempts=3,
                final_status="failed",
            )
        )
        return []

    return [entry]


def _resource_entries(page_url: str, department: str, html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    page_title = _page_title(html, f"Sreyas {department} Course Content")
    entries: list[dict[str, Any]] = [
        {
            "title": page_title,
            "source_page_url": page_url,
            "resource_url": page_url,
            "source": f"SREYAS_{department}",
            "department": department,
            "semester": None,
            "subject": department,
            "unit": None,
            "resource_label": "course content page",
            "document_type": DocumentType.WEBPAGE,
            "content": _html_text(html),
            "google_drive_file_id": None,
            "page_number": 1,
            "metadata": {"source_page_title": page_title},
        }
    ]

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        headers = [_normalize(cell.get_text(" ", strip=True)).lower() for cell in rows[0].find_all(["th", "td"])]
        if not headers:
            continue

        is_course_table = any("course name" in header for header in headers)
        is_ece_table = any("year & semester" in header for header in headers) and any("subject" in header for header in headers)

        for row in rows[1:]:
            cells = row.find_all("td")
            if not cells:
                continue

            cell_texts = [_normalize(cell.get_text(" ", strip=True)) for cell in cells]

            if is_course_table:
                course_name = cell_texts[1] if len(cell_texts) > 1 else ""
                if not course_name:
                    continue
                for index, cell in enumerate(cells[2:], start=2):
                    links = cell.find_all("a", href=True)
                    if not links:
                        continue
                    resource_label = _normalize(headers[index]).replace("�", "").replace("'", "").title() if index < len(headers) else "Resource"
                    for link in links:
                        href = urljoin(page_url, link["href"])
                        entries.append(
                            {
                                "title": f"{course_name} - {resource_label}",
                                "source_page_url": page_url,
                                "resource_url": href,
                                "source": f"SREYAS_{department}",
                                "department": department,
                                "semester": None,
                                "subject": course_name,
                                "unit": None,
                                "resource_label": resource_label,
                                "document_type": DocumentType.WEBPAGE,
                                "content": "",
                                "google_drive_file_id": _extract_drive_file_id(href),
                                "page_number": 1,
                                "metadata": {
                                    "course_name": course_name,
                                    "row_index": cell_texts[0] if cell_texts else None,
                                    "resource_type": resource_label,
                                },
                            }
                        )
            elif is_ece_table:
                semester = cell_texts[2] if len(cell_texts) > 2 else None
                subject = cell_texts[3] if len(cell_texts) > 3 else ""
                subject_code = cell_texts[1] if len(cell_texts) > 1 else None
                if not subject:
                    continue
                links = cells[-1].find_all("a", href=True)
                for link in links:
                    href = urljoin(page_url, link["href"])
                    entries.append(
                        {
                            "title": f"{subject} - {subject_code or 'resource'}",
                            "source_page_url": page_url,
                            "resource_url": href,
                            "source": f"SREYAS_{department}",
                            "department": department,
                            "semester": semester,
                            "subject": subject,
                            "unit": None,
                            "resource_label": "Link",
                            "document_type": DocumentType.WEBPAGE,
                            "content": "",
                            "google_drive_file_id": _extract_drive_file_id(href),
                            "page_number": 1,
                            "metadata": {
                                "subject_code": subject_code,
                                "row_index": cell_texts[0] if cell_texts else None,
                                "year_semester": semester,
                            },
                        }
                    )

    return entries


def _materialize_record(page_url: str, department: str, entry: dict[str, Any]) -> tuple[CrawledDocument | None, CrawlFailure | None]:
    content = entry.get("content") or ""
    document_type = entry.get("document_type", DocumentType.WEBPAGE)
    resource_url = entry.get("resource_url") or page_url

    if not content.strip() and resource_url != page_url:
        try:
            content, document_type, file_id = _download_resource(resource_url)
            entry["content"] = content
            entry["document_type"] = document_type
            entry["google_drive_file_id"] = entry.get("google_drive_file_id") or file_id
        except Exception as exc:
            logger.warning("Failed to download Sreyas resource %s: %s", resource_url, exc)
            return None, CrawlFailure(
                url=resource_url,
                department=department,
                subject=entry.get("subject"),
                reason=_classify_failure(exc),
                retry_attempts=3,
                final_status="failed",
            )

    normalized_content = _normalize(content)
    if len(normalized_content) < 20:
        return None, CrawlFailure(
            url=resource_url,
            department=department,
            subject=entry.get("subject"),
            reason="empty or too short after cleanup",
            retry_attempts=0,
            final_status="skipped",
        )

    return CrawledDocument(
        title=entry["title"],
        source_page_url=entry["source_page_url"],
        resource_url=resource_url,
        source=entry["source"],
        department=department,
        semester=entry.get("semester"),
        subject=entry["subject"],
        unit=entry.get("unit"),
        resource_label=entry["resource_label"],
        document_type=document_type,
        content=content,
        google_drive_file_id=entry.get("google_drive_file_id"),
        page_number=entry.get("page_number"),
        metadata=entry.get("metadata") or {},
    ), None


def crawl_sreyas_course_content() -> tuple[list[CrawledDocument], list[CrawlFailure]]:
    records: list[CrawledDocument] = []
    failures: list[CrawlFailure] = []
    seen_signatures: set[str] = set()
    seen_resources: set[str] = set()

    seed_entries: list[dict[str, Any]] = []
    for department, page_url in SREYAS_SOURCE_PAGES.items():
        try:
            html = _fetch_text(page_url)
        except Exception as exc:
            logger.warning("Failed to fetch Sreyas page %s: %s", page_url, exc)
            failures.append(
                CrawlFailure(
                    url=page_url,
                    department=department,
                    subject=None,
                    reason=_classify_failure(exc),
                    retry_attempts=3,
                    final_status="failed",
                )
            )
            continue

        seed_entries.extend(_resource_entries(page_url, department, html))

    expanded_entries: list[dict[str, Any]] = []
    for entry in seed_entries:
        expanded_entries.extend(_expand_resource_tree(entry, seen_resources, failures))

    # ponytail: 8 workers is still conservative for Drive but keeps a large corpus from crawling forever.
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_materialize_record, entry["source_page_url"], entry["department"], entry) for entry in expanded_entries]
        for future in as_completed(futures):
            record, failure = future.result()
            if failure is not None:
                failures.append(failure)
            if record is None:
                continue
            signature = record.signature()
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            records.append(record)

    return records, failures


def _persist_crawled_record(db: Session, record: CrawledDocument) -> dict[str, int]:
    summary = {
        "documents": 0,
        "chunks": 0,
        "embeddings": 0,
        "duplicates": 0,
        "failed": 0,
    }
    content = _normalize(record.content)
    if len(content) < 20:
        return summary

    file_hash = hashlib.sha256(
        f"{record.source_page_url}|{record.resource_url}|{record.title}|{content}".encode("utf-8")
    ).hexdigest()

    existing = db.query(Document).filter(Document.file_hash == file_hash).first()
    if existing:
        summary["duplicates"] += 1
        return summary

    keywords = list(
        dict.fromkeys(
            [
                record.department,
                record.subject,
                record.resource_label,
                record.google_drive_file_id or "",
                record.title,
                record.metadata.get("subject_code") if record.metadata else "",
            ]
        )
    )
    keywords = [keyword for keyword in keywords if keyword]

    document = Document(
        title=record.title,
        url=record.resource_url,
        source=record.source,
        department=record.department,
        semester=record.semester,
        subject=record.subject,
        unit=record.unit,
        module=record.resource_label,
        academic_year=None,
        keywords=keywords,
        language="en",
        version=1,
        doc_type=record.document_type,
        file_hash=file_hash,
        status=DocumentStatus.PROCESSING,
        uploaded_by=None,
    )
    db.add(document)
    db.flush()

    chunks = chunk_text(content, chunk_size=SREYAS_CHUNK_SIZE, overlap=SREYAS_CHUNK_OVERLAP)
    for index, chunk in enumerate(chunks):
        db.add(
            DocumentChunk(
                id=f"{document.id}{index:04d}",
                document_id=document.id,
                heading=record.resource_label,
                page_number=record.page_number or 1,
                section=record.resource_label,
                chunk_index=index,
                char_count=len(chunk),
                token_count=max(len(chunk) // 4, 1),
            )
        )

    db.commit()

    try:
        ingest_document(
            document_id=document.id,
            title=record.title,
            text_content=content,
            source_type=record.document_type.value,
            subject=record.subject,
            unit=record.unit,
            semester=record.semester,
            topic=record.subject,
            keywords=keywords,
            extra_metadata={
                "department": record.department,
                "source": record.source,
                "source_page_url": record.source_page_url,
                "resource_url": record.resource_url,
                "google_drive_file_id": record.google_drive_file_id,
                "document_title": record.title,
                "resource_label": record.resource_label,
                "page_number": record.page_number or 1,
                "embedding_id": None,
                "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": record.metadata or {},
            },
            chunk_size=SREYAS_CHUNK_SIZE,
            overlap=SREYAS_CHUNK_OVERLAP,
        )
        document.status = DocumentStatus.COMPLETED
        db.commit()
        summary["documents"] += 1
        summary["chunks"] += len(chunks)
        summary["embeddings"] += len(chunks)
    except Exception as exc:
        logger.warning("Failed to index Sreyas document %s: %s", record.title, exc)
        document.status = DocumentStatus.FAILED
        document.error_message = str(exc)
        db.commit()
        summary["failed"] += 1

    return summary


def persist_crawled_documents(db: Session, records: Iterable[CrawledDocument]) -> dict[str, Any]:
    summary = {
        "documents": 0,
        "chunks": 0,
        "embeddings": 0,
        "duplicates": 0,
        "failed": 0,
    }

    for record in records:
        delta = _persist_crawled_record(db, record)
        for key in summary:
            summary[key] += delta.get(key, 0)

    return summary


def sync_sreyas_course_content(db: Session) -> dict[str, Any]:
    summary = {
        "documents": 0,
        "chunks": 0,
        "embeddings": 0,
        "duplicates": 0,
        "failed": 0,
        "records": 0,
        "pages": len(SREYAS_SOURCE_PAGES),
        "failures": 0,
        "failed_downloads": [],
    }
    failures: list[CrawlFailure] = []
    seen_signatures: set[str] = set()
    seen_resources: set[str] = set()

    seed_entries: list[dict[str, Any]] = []
    for department, page_url in SREYAS_SOURCE_PAGES.items():
        try:
            html = _fetch_text(page_url)
        except Exception as exc:
            logger.warning("Failed to fetch Sreyas page %s: %s", page_url, exc)
            failures.append(
                CrawlFailure(
                    url=page_url,
                    department=department,
                    subject=None,
                    reason=_classify_failure(exc),
                    retry_attempts=3,
                    final_status="failed",
                )
            )
            continue
        seed_entries.extend(_resource_entries(page_url, department, html))

    expanded_entries: list[dict[str, Any]] = []
    for entry in seed_entries:
        expanded_entries.extend(_expand_resource_tree(entry, seen_resources, failures))

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_materialize_record, entry["source_page_url"], entry["department"], entry) for entry in expanded_entries]
        for future in as_completed(futures):
            record, failure = future.result()
            if failure is not None:
                failures.append(failure)
            if record is None:
                continue
            signature = record.signature()
            if signature in seen_signatures:
                summary["duplicates"] += 1
                continue
            seen_signatures.add(signature)
            delta = _persist_crawled_record(db, record)
            for key in ("documents", "chunks", "embeddings", "duplicates", "failed"):
                summary[key] += delta.get(key, 0)
            summary["records"] += 1

    summary["failures"] = len(failures)
    summary["failed_downloads"] = [
        {
            "url": failure.url,
            "department": failure.department,
            "subject": failure.subject,
            "reason": failure.reason,
            "retry_attempts": failure.retry_attempts,
            "final_status": failure.final_status,
        }
        for failure in failures
    ]
    return summary
