from __future__ import annotations

import logging
from typing import Any, Dict, List

from .base import BaseKnowledgeAdapter
from app.domain.learning.services.institutional_content import (
    SREYAS_SOURCE_PAGES,
    crawl_sreyas_course_content,
)

logger = logging.getLogger(__name__)


class SreyasKnowledgeAdapter(BaseKnowledgeAdapter):
    def discover(self) -> List[str]:
        return list(SREYAS_SOURCE_PAGES.values())

    def fetch(self, url: str) -> str:
        from app.domain.learning.services.institutional_content import _fetch_text

        return _fetch_text(url)

    def clean(self, raw_content: str) -> str:
        from app.domain.learning.services.institutional_content import _html_text

        return _html_text(raw_content)

    def extract_metadata(self, url: str, raw_content: str) -> Dict[str, Any]:
        return {
            "title": url,
            "source": "SREYAS",
            "department": "Unknown",
            "language": "en",
            "doc_type": "webpage",
        }

    def sync(self) -> List[Dict[str, Any]]:
        records, _failures = crawl_sreyas_course_content()
        return [
            {
                "url": record.resource_url,
                "raw_content": record.content,
                "cleaned_content": record.content,
                "metadata": {
                    **(record.metadata or {}),
                    "title": record.title,
                    "source": record.source,
                    "department": record.department,
                    "semester": record.semester,
                    "subject": record.subject,
                    "unit": record.unit,
                    "page_number": record.page_number,
                    "source_page_url": record.source_page_url,
                    "resource_url": record.resource_url,
                    "google_drive_file_id": record.google_drive_file_id,
                },
            }
            for record in records
        ]
