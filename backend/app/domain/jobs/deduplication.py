from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Mapping


def normalize_text(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip().lower()
    return text


def _value(data: Mapping[str, Any] | Any, key: str, default: Any = None) -> Any:
    if isinstance(data, Mapping):
        return data.get(key, default)
    return getattr(data, key, default)


def job_fingerprint(data: Mapping[str, Any] | Any) -> str:
    parts = [
        normalize_text(_value(data, "title")),
        normalize_text(_value(data, "company")),
        normalize_text(_value(data, "location")),
        normalize_text(_value(data, "apply_url") or _value(data, "apply_link")),
    ]
    digest = hashlib.sha256(" | ".join(parts).encode("utf-8")).hexdigest()
    return digest


def job_similarity(left: Mapping[str, Any] | Any, right: Mapping[str, Any] | Any) -> float:
    left_text = " ".join(
        normalize_text(_value(left, field))
        for field in ("title", "company", "location", "description", "raw_description")
    )
    right_text = " ".join(
        normalize_text(_value(right, field))
        for field in ("title", "company", "location", "description", "raw_description")
    )
    if not left_text or not right_text:
        return 0.0
    return SequenceMatcher(None, left_text, right_text).ratio()


def _source_priority(value: Any) -> int:
    source = normalize_text(value)
    order = {
        "company_page": 6,
        "amazon_careers": 6,
        "google_careers": 6,
        "workday_careers": 6,
        "configured_company_feed": 6,
        "greenhouse": 5,
        "lever": 5,
        "workday": 4,
        "adzuna": 4,
        "serpapi": 3,
        "serper": 3,
        "google_cse": 3,
        "arbeitnow": 2,
        "remoteok": 2,
        "manual": 1,
        "local_cache": 0,
    }
    return order.get(source, 1)


def _quality_score(job: Mapping[str, Any] | Any) -> tuple[int, int, int]:
    source_score = _source_priority(_value(job, "source") or _value(job, "provider"))
    posted_date = _value(job, "posted_date")
    recency_score = 0
    if isinstance(posted_date, datetime):
        if posted_date.tzinfo is None:
            posted_date = posted_date.replace(tzinfo=timezone.utc)
        age_days = max((datetime.now(timezone.utc) - posted_date).days, 0)
        recency_score = max(0, 60 - age_days)
    description = str(_value(job, "description") or _value(job, "raw_description") or "")
    return source_score, recency_score, len(description)


def should_replace(existing: Mapping[str, Any] | Any, candidate: Mapping[str, Any] | Any) -> bool:
    if not existing:
        return True
    candidate_score = _quality_score(candidate)
    existing_score = _quality_score(existing)
    if candidate_score != existing_score:
        return candidate_score > existing_score
    return job_similarity(existing, candidate) > 0.85 and _quality_score(candidate)[2] > _quality_score(existing)[2]
