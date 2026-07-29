from __future__ import annotations

import asyncio
import html
import logging
import re
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from app.core.config import settings

from .deduplication import job_fingerprint, job_similarity, normalize_text, should_replace

logger = logging.getLogger(__name__)

USER_AGENT = "SPIP-JobDiscovery/1.0"
_ROBOTS_CACHE: dict[str, robotparser.RobotFileParser | None] = {}


class RobotsDisallowed(RuntimeError):
    pass


@dataclass(slots=True)
class JobListing:
    id: Optional[int] = None
    title: str = ""
    company: str = ""
    location: str = ""
    country: Optional[str] = None
    remote: bool = False
    salary: Optional[str] = None
    currency: Optional[str] = None
    skills: list[str] = field(default_factory=list)
    description: str = ""
    experience: Optional[str] = None
    employment_type: Optional[str] = None
    posted_date: Optional[datetime] = None
    provider: str = ""
    provider_url: Optional[str] = None
    company_url: Optional[str] = None
    apply_url: str = ""
    ai_match_score: Optional[int] = None
    missing_skills: list[str] = field(default_factory=list)
    summary: Optional[str] = None
    fingerprint: str = ""
    freshness_score: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.posted_date is not None:
            data["posted_date"] = self.posted_date.isoformat()
        return data


def _clean_url(value: Any) -> str:
    url = str(value or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return url


def _strip_html(value: Any) -> str:
    text = html.unescape(str(value or ""))
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _parse_posted_date(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    text = str(value).strip()
    relative = re.search(r"posted\s+(\d+)\s+day", text, re.IGNORECASE)
    if relative:
        return datetime.now(timezone.utc) - timedelta(days=int(relative.group(1)))
    if re.search(r"posted\s+today|today", text, re.IGNORECASE):
        return datetime.now(timezone.utc)
    if re.search(r"yesterday", text, re.IGNORECASE):
        return datetime.now(timezone.utc) - timedelta(days=1)
    if re.search(r"30\+\s+days", text, re.IGNORECASE):
        return datetime.now(timezone.utc) - timedelta(days=31)

    try:
        parsed = date_parser.parse(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _infer_country(location: str | None) -> Optional[str]:
    text = (location or "").lower()
    for token, country in {
        "india": "India",
        "hyderabad": "India",
        "bengaluru": "India",
        "bangalore": "India",
        "pune": "India",
        "remote": "Remote",
        "united states": "United States",
        "usa": "United States",
        "us": "United States",
        "uk": "United Kingdom",
        "london": "United Kingdom",
        "germany": "Germany",
        "europe": "Europe",
    }.items():
        if token in text:
            return country
    return None


def _infer_adzuna_country(location: str | None) -> str:
    text = (location or "").lower()
    if any(token in text for token in ["united states", "usa", "us", "new york", "california", "texas", "san francisco"]):
        return "us"
    if any(token in text for token in ["united kingdom", "uk", "london", "manchester"]):
        return "gb"
    if any(token in text for token in ["germany", "berlin", "munich"]):
        return "de"
    if any(token in text for token in ["canada", "toronto", "vancouver"]):
        return "ca"
    return "in"


def _infer_remote(location: str | None, employment_type: str | None, description: str | None = None) -> bool:
    text = " ".join(part for part in [location, employment_type, description] if part).lower()
    return any(token in text for token in ["remote", "work from home", "wfh", "hybrid", "virtual"])


def _infer_currency(salary: str | None) -> Optional[str]:
    text = (salary or "").upper()
    if "INR" in text or "LPA" in text:
        return "INR"
    if "$" in text or "USD" in text:
        return "USD"
    if "EUR" in text:
        return "EUR"
    if "GBP" in text:
        return "GBP"
    return None


def _infer_skills(text: str) -> list[str]:
    haystack = text.lower()
    candidates = [
        "Python",
        "Java",
        "JavaScript",
        "TypeScript",
        "React",
        "Next.js",
        "FastAPI",
        "Django",
        "Flask",
        "Node.js",
        "Go",
        "Rust",
        "C++",
        "SQL",
        "PostgreSQL",
        "Redis",
        "Docker",
        "Kubernetes",
        "AWS",
        "Azure",
        "GCP",
        "Machine Learning",
        "Deep Learning",
        "NLP",
        "LLM",
        "RAG",
        "MLOps",
        "Data Structures",
        "System Design",
    ]
    return [skill for skill in candidates if skill.lower() in haystack][:10]


def _freshness_score(posted_date: Optional[datetime]) -> int:
    if not posted_date:
        return 0
    if posted_date.tzinfo is None:
        posted_date = posted_date.replace(tzinfo=timezone.utc)
    age_days = max((datetime.now(timezone.utc) - posted_date).days, 0)
    return max(0, 100 - min(age_days * 10, 100))


def _salary_range(min_value: Any, max_value: Any, currency: str | None = None) -> str | None:
    if not min_value and not max_value:
        return None
    parts = [str(value) for value in [min_value, max_value] if value]
    prefix = f"{currency} " if currency else ""
    return prefix + " - ".join(parts)


def normalize_job_item(item: dict[str, Any], provider: str, provider_url: str | None = None, company_url: str | None = None) -> JobListing:
    title = str(item.get("title") or item.get("position") or item.get("job_title") or "").strip()
    company = str(item.get("company") or item.get("company_name") or item.get("employer") or "").strip()
    location = str(item.get("location") or item.get("city") or item.get("region") or "Remote").strip()
    salary = item.get("salary_range") or item.get("salary")
    apply_url = _clean_url(item.get("apply_link") or item.get("apply_url") or item.get("url") or item.get("jobUrl") or item.get("link"))
    description = _strip_html(item.get("raw_description") or item.get("description") or item.get("snippet") or title)
    posted_date = _parse_posted_date(item.get("posted_date") or item.get("created_at") or item.get("date") or item.get("published_at"))
    experience = item.get("experience_required") or item.get("experience") or item.get("seniority")
    employment_type = item.get("employment_type") or item.get("job_type") or item.get("schedule_type")
    remote = bool(item.get("remote")) if item.get("remote") is not None else _infer_remote(location, str(employment_type or ""), description)
    skills = list(item.get("skills") or item.get("extracted_skills") or _infer_skills(description))
    currency = item.get("currency") or _infer_currency(str(salary or ""))
    country = item.get("country") or _infer_country(location)
    provider_url = _clean_url(provider_url or item.get("provider_url") or apply_url)
    company_url = _clean_url(company_url or item.get("company_url") or provider_url or apply_url)
    summary = _strip_html(item.get("summary") or item.get("ai_summary") or description[:320])
    ai_match_score = item.get("ai_match_score")

    listing = JobListing(
        id=item.get("id"),
        title=title,
        company=company,
        location=location,
        country=country,
        remote=remote,
        salary=str(salary).strip() if salary else None,
        currency=currency,
        skills=skills,
        description=description,
        experience=str(experience).strip() if experience else None,
        employment_type=str(employment_type).strip() if employment_type else None,
        posted_date=posted_date,
        provider=provider,
        provider_url=provider_url,
        company_url=company_url,
        apply_url=apply_url,
        ai_match_score=int(ai_match_score) if ai_match_score is not None else None,
        missing_skills=list(item.get("missing_skills") or []),
        summary=summary,
        fingerprint=job_fingerprint(
            {
                "title": title,
                "company": company,
                "location": location,
                "apply_url": apply_url,
            }
        ),
        freshness_score=_freshness_score(posted_date),
    )
    return listing


def _configured_company_feeds() -> list[tuple[str, str]]:
    raw = (settings.JOB_COMPANY_CAREER_URLS or "").strip()
    if not raw:
        return []
    feeds: list[tuple[str, str]] = []
    for chunk in re.split(r"[,\n;]+", raw):
        entry = chunk.strip()
        if not entry:
            continue
        if "|" in entry:
            name, url = entry.split("|", 1)
        elif "=" in entry:
            name, url = entry.split("=", 1)
        else:
            name, url = entry, entry
        url = _clean_url(url)
        if url:
            feeds.append((name.strip() or urlparse(url).netloc, url))
    return feeds


def _extract_job_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("jobs", "data", "results", "items", "positions", "content", "jobPostings"):
        items = payload.get(key)
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    return []


def _company_key(job: JobListing) -> str:
    return "|".join(
        [
            normalize_text(job.company),
            normalize_text(job.title),
            normalize_text(job.location),
        ]
    )


def _valid_listing(job: JobListing) -> bool:
    if not job.title or not job.company or not job.apply_url:
        return False
    host = urlparse(job.apply_url).netloc.lower()
    if host in {"example.com", "www.example.com", "localhost", "127.0.0.1"}:
        return False
    text = f"{job.title} {job.company} {job.apply_url}".lower()
    return not any(marker in text for marker in ["placeholder", "fake job", "demo job", "tech inc "])


def _failure_count(status: dict[str, Any]) -> int:
    total = int(status.get("failures", 0) or 0)
    for child in status.get("children") or []:
        if isinstance(child, dict):
            total += _failure_count(child)
    return total


def _robots_allowed_sync(url: str) -> bool:
    parsed = urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    parser = _ROBOTS_CACHE.get(root)
    if root not in _ROBOTS_CACHE:
        try:
            response = httpx.get(f"{root}/robots.txt", timeout=5.0, headers={"User-Agent": USER_AGENT})
            parser = robotparser.RobotFileParser()
            if response.status_code < 400:
                parser.parse(response.text.splitlines())
            else:
                parser = None
        except Exception:
            parser = None
        _ROBOTS_CACHE[root] = parser
    return True if parser is None else parser.can_fetch(USER_AGENT, url)


async def _robots_allowed(url: str) -> bool:
    return await asyncio.to_thread(_robots_allowed_sync, url)


class HTTPJobProvider:
    name = "provider"
    rate_limit_seconds = 0.25
    respect_robots = True

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._last_request = 0.0
        self.status: dict[str, Any] = {
            "name": self.name,
            "status": "idle",
            "requests": 0,
            "failures": 0,
            "jobs": 0,
            "latency_ms": 0.0,
            "last_error": None,
        }

    async def _throttle(self) -> None:
        async with self._lock:
            wait = self.rate_limit_seconds - (time.perf_counter() - self._last_request)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request = time.perf_counter()

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        if self.respect_robots and not await _robots_allowed(url):
            raise RobotsDisallowed(f"robots.txt disallows {url}")

        await self._throttle()
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(
                    timeout=settings.JOB_PROVIDER_TIMEOUT,
                    follow_redirects=True,
                    headers={"User-Agent": USER_AGENT, **(headers or {})},
                ) as client:
                    response = await client.request(method, url, params=params, json=json_body)
                    response.raise_for_status()
                    return response
            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.TransportError) as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(0.5 * (2**attempt))
        raise last_error or RuntimeError("provider request failed")

    async def _json(self, method: str, url: str, **kwargs: Any) -> Any:
        response = await self._request(method, url, **kwargs)
        return response.json()

    async def _text(self, url: str, **kwargs: Any) -> str:
        response = await self._request("GET", url, **kwargs)
        return response.text

    async def _safe_search(self, query: str, location: str | None, limit: int) -> list[JobListing]:
        start = time.perf_counter()
        self.status["requests"] += 1
        try:
            jobs = [job for job in await self.search(query, location=location, limit=limit) if _valid_listing(job)]
            self.status.update(
                {
                    "status": "healthy" if jobs else "empty",
                    "jobs": len(jobs),
                    "latency_ms": round((time.perf_counter() - start) * 1000, 1),
                    "last_error": None,
                }
            )
            return jobs
        except RobotsDisallowed as exc:
            self.status.update(
                {
                    "status": "skipped",
                    "latency_ms": round((time.perf_counter() - start) * 1000, 1),
                    "last_error": str(exc)[:240],
                }
            )
            logger.info("%s job provider skipped: %s", self.name, exc)
            return []
        except Exception as exc:
            self.status.update(
                {
                    "status": "failed",
                    "failures": int(self.status.get("failures", 0)) + 1,
                    "latency_ms": round((time.perf_counter() - start) * 1000, 1),
                    "last_error": str(exc)[:240],
                }
            )
            logger.warning("%s job provider failed: %s", self.name, exc)
            return []

    async def search(self, query: str, location: str | None = None, limit: int = 20) -> list[JobListing]:
        raise NotImplementedError

    async def health_check(self) -> dict[str, Any]:
        return dict(self.status)


class ArbeitNowProvider(HTTPJobProvider):
    name = "arbeitnow"

    async def search(self, query: str, location: str | None = None, limit: int = 20) -> list[JobListing]:
        data = await self._json("GET", "https://www.arbeitnow.com/api/job-board-api")
        raw_jobs = []
        query_tokens = set(normalize_text(query).split())
        location_text = normalize_text(location)
        for item in data.get("data", []):
            title = item.get("title", "")
            haystack = normalize_text(" ".join([title, item.get("company_name", ""), item.get("location", ""), item.get("description", "")]))
            if query_tokens and not query_tokens.intersection(haystack.split()):
                continue
            if location_text and location_text not in haystack and "remote" not in haystack:
                continue
            raw_jobs.append(
                {
                    "title": title,
                    "company": item.get("company_name"),
                    "location": item.get("location"),
                    "salary_range": None,
                    "apply_link": item.get("url"),
                    "raw_description": item.get("description"),
                    "employment_type": "Full-time",
                    "posted_date": item.get("created_at"),
                }
            )
        return [
            normalize_job_item(item, provider=self.name, provider_url="https://www.arbeitnow.com/api/job-board-api")
            for item in raw_jobs[:limit]
        ]


class RemoteOKProvider(HTTPJobProvider):
    name = "remoteok"

    async def search(self, query: str, location: str | None = None, limit: int = 20) -> list[JobListing]:
        data = await self._json("GET", "https://remoteok.com/api", headers={"User-Agent": USER_AGENT})
        raw_jobs = []
        query_tokens = set(normalize_text(query).split())
        location_text = normalize_text(location)
        for item in data[1:] if isinstance(data, list) else []:
            title = item.get("position", "")
            haystack = normalize_text(" ".join([title, item.get("company", ""), item.get("location", ""), item.get("description", "")]))
            if query_tokens and not query_tokens.intersection(haystack.split()):
                continue
            if location_text and location_text not in haystack and "remote" not in haystack:
                continue
            raw_jobs.append(
                {
                    "title": title,
                    "company": item.get("company"),
                    "location": item.get("location") or "Remote",
                    "salary_range": _salary_range(item.get("salary_min"), item.get("salary_max"), "USD"),
                    "apply_link": item.get("apply_url") or item.get("url"),
                    "raw_description": item.get("description"),
                    "employment_type": "Full-time",
                    "posted_date": item.get("date"),
                }
            )
        return [
            normalize_job_item(item, provider=self.name, provider_url="https://remoteok.com/api")
            for item in raw_jobs[:limit]
        ]


class AdzunaProvider(HTTPJobProvider):
    name = "adzuna"
    respect_robots = False

    async def search(self, query: str, location: str | None = None, limit: int = 20) -> list[JobListing]:
        if not settings.ADZUNA_APP_ID or not settings.ADZUNA_APP_KEY:
            return []
        country = _infer_adzuna_country(location)
        params = {
            "app_id": settings.ADZUNA_APP_ID,
            "app_key": settings.ADZUNA_APP_KEY,
            "results_per_page": min(limit, 50),
            "what": query,
        }
        if location:
            params["where"] = location
        data = await self._json("GET", f"https://api.adzuna.com/v1/api/jobs/{country}/search/1", params=params)
        results = []
        for item in (data.get("results") or [])[:limit]:
            company = item.get("company", {})
            location_data = item.get("location", {})
            salary = _salary_range(item.get("salary_min"), item.get("salary_max"), item.get("salary_currency"))
            results.append(
                normalize_job_item(
                    {
                        "title": item.get("title"),
                        "company_name": company.get("display_name") if isinstance(company, dict) else company,
                        "location": location_data.get("display_name") if isinstance(location_data, dict) else location_data,
                        "salary_range": salary,
                        "raw_description": item.get("description") or item.get("title"),
                        "employment_type": item.get("contract_time") or item.get("contract_type"),
                        "posted_date": item.get("created"),
                        "apply_link": item.get("redirect_url"),
                        "provider_url": item.get("redirect_url"),
                    },
                    provider=self.name,
                    provider_url="https://api.adzuna.com",
                )
            )
        return results


class AmazonCareersProvider(HTTPJobProvider):
    name = "amazon_careers"

    async def search(self, query: str, location: str | None = None, limit: int = 20) -> list[JobListing]:
        data = await self._json(
            "GET",
            "https://www.amazon.jobs/en/search.json",
            params={
                "base_query": query,
                "loc_query": location or "",
                "result_limit": min(limit, 100),
                "sort": "recent",
            },
            headers={"Accept-Encoding": "identity"},
        )
        jobs = []
        for item in (data.get("jobs") or [])[:limit]:
            description = " ".join(
                _strip_html(item.get(key))
                for key in ("description", "basic_qualifications", "preferred_qualifications")
                if item.get(key)
            )
            apply_url = item.get("url_next_step") or urljoin("https://www.amazon.jobs", item.get("job_path") or "")
            jobs.append(
                normalize_job_item(
                    {
                        "title": item.get("title"),
                        "company_name": item.get("company_name") or "Amazon",
                        "location": item.get("normalized_location") or item.get("location"),
                        "raw_description": description,
                        "employment_type": item.get("job_schedule_type"),
                        "posted_date": item.get("posted_date"),
                        "apply_link": apply_url,
                        "company_url": urljoin("https://www.amazon.jobs", item.get("job_path") or ""),
                    },
                    provider=self.name,
                    provider_url="https://www.amazon.jobs/en/search.json",
                    company_url="https://www.amazon.jobs",
                )
            )
        return jobs


@dataclass(frozen=True)
class WorkdaySource:
    company: str
    host: str
    tenant: str
    site: str

    @property
    def search_url(self) -> str:
        return f"{self.host}/wday/cxs/{self.tenant}/{self.site}/jobs"

    def external_url(self, external_path: str) -> str:
        return f"{self.host}/{self.site}{external_path}"


WORKDAY_SOURCES = [
    WorkdaySource("NVIDIA", "https://nvidia.wd5.myworkdayjobs.com", "nvidia", "NVIDIAExternalCareerSite"),
    WorkdaySource("Adobe", "https://adobe.wd5.myworkdayjobs.com", "adobe", "external_experienced"),
    WorkdaySource("Intel", "https://intel.wd1.myworkdayjobs.com", "intel", "External"),
    WorkdaySource("Salesforce", "https://salesforce.wd12.myworkdayjobs.com", "salesforce", "External_Career_Site"),
]


class WorkdayCareersProvider(HTTPJobProvider):
    name = "workday_careers"

    async def search(self, query: str, location: str | None = None, limit: int = 20) -> list[JobListing]:
        per_company = max(5, min(20, limit // max(len(WORKDAY_SOURCES), 1) + 3))
        tasks = [self._fetch_company(source, query, location, per_company) for source in WORKDAY_SOURCES]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        jobs: list[JobListing] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Workday source failed: %s", result)
                continue
            jobs.extend(result)
        return jobs[:limit]

    async def _fetch_company(self, source: WorkdaySource, query: str, location: str | None, limit: int) -> list[JobListing]:
        search_text = " ".join(part for part in [query, location] if part)
        data = await self._json(
            "POST",
            source.search_url,
            json_body={"appliedFacets": {}, "limit": limit, "offset": 0, "searchText": search_text},
            headers={"Content-Type": "application/json"},
        )
        jobs = []
        for item in (data.get("jobPostings") or [])[:limit]:
            external_path = item.get("externalPath")
            if not external_path:
                continue
            title = item.get("title") or ""
            bullets = ", ".join(str(value) for value in item.get("bulletFields") or [] if value)
            jobs.append(
                normalize_job_item(
                    {
                        "title": title,
                        "company_name": source.company,
                        "location": item.get("locationsText"),
                        "raw_description": f"{title}. {bullets}".strip(),
                        "employment_type": "Full-time",
                        "posted_date": item.get("postedOn"),
                        "apply_link": source.external_url(external_path),
                        "company_url": source.external_url(external_path),
                    },
                    provider=self.name,
                    provider_url=source.search_url,
                    company_url=source.host,
                )
            )
        return jobs


class GoogleCareersProvider(HTTPJobProvider):
    name = "google_careers"

    async def search(self, query: str, location: str | None = None, limit: int = 20) -> list[JobListing]:
        text = await self._text(
            "https://www.google.com/about/careers/applications/jobs/results/",
            params={"q": query, "location": location or "India"},
        )
        jobs: list[JobListing] = []
        pattern = re.compile(
            r'\["(?P<id>\d{8,})","(?P<title>[^"]+)","(?P<url>https://www\.google\.com/about/careers/applications/signin\?jobId[^"]+)"',
            re.DOTALL,
        )
        for match in pattern.finditer(text):
            window = text[match.start() : match.start() + 5000]
            locations = re.findall(r'\[\["([^"]+)"', window)
            description_match = re.search(r'\[null,"(?P<body><p>.*?)(?:",\[|\]\])', window, re.DOTALL)
            raw_url = match.group("url").replace("\\u003d", "=").replace("\\u0026", "&")
            jobs.append(
                normalize_job_item(
                    {
                        "title": html.unescape(match.group("title")),
                        "company_name": "Google",
                        "location": html.unescape(locations[0]) if locations else (location or "Global"),
                        "raw_description": _strip_html(description_match.group("body")) if description_match else match.group("title"),
                        "employment_type": "Full-time",
                        "apply_link": raw_url,
                        "company_url": "https://www.google.com/about/careers/applications/",
                    },
                    provider=self.name,
                    provider_url="https://www.google.com/about/careers/applications/jobs/results/",
                    company_url="https://www.google.com/about/careers/applications/",
                )
            )
            if len(jobs) >= limit:
                break
        return jobs


class ConfiguredCompanyFeedProvider(HTTPJobProvider):
    name = "configured_company_feed"

    async def search(self, query: str, location: str | None = None, limit: int = 20) -> list[JobListing]:
        feeds = _configured_company_feeds()
        if not feeds:
            return []
        tasks = [self._fetch_feed(feed_name, url, query, location, limit) for feed_name, url in feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        jobs: list[JobListing] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Configured company feed failed: %s", result)
                continue
            jobs.extend(result)
        return jobs[:limit]

    async def _fetch_feed(self, feed_name: str, url: str, query: str, location: str | None, limit: int) -> list[JobListing]:
        payload = await self._json("GET", url, params={"q": query, "query": query, "keywords": query, "location": location or ""})
        return [
            normalize_job_item(
                {**item, "company_name": item.get("company_name") or feed_name, "provider_url": url, "company_url": url},
                provider=self.name,
                provider_url=url,
                company_url=url,
            )
            for item in _extract_job_items(payload)
        ][:limit]


class CompanyCareerProvider(HTTPJobProvider):
    name = "company_page"

    def __init__(self) -> None:
        super().__init__()
        self.providers = [
            AmazonCareersProvider(),
            WorkdayCareersProvider(),
            GoogleCareersProvider(),
            ConfiguredCompanyFeedProvider(),
        ]

    async def search(self, query: str, location: str | None = None, limit: int = 20) -> list[JobListing]:
        if not settings.JOB_ENABLE_COMPANY_SCRAPERS:
            return []
        per_provider = max(10, min(limit, 100))
        results = await asyncio.gather(
            *(provider._safe_search(query, location, per_provider) for provider in self.providers),
            return_exceptions=True,
        )
        jobs: list[JobListing] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Company provider failed: %s", result)
                continue
            jobs.extend(result)
        return jobs[:limit]

    async def health_check(self) -> dict[str, Any]:
        status = dict(self.status)
        status["children"] = [dict(provider.status) for provider in self.providers]
        return status


class JobProviderHub:
    def __init__(self) -> None:
        self.providers: list[HTTPJobProvider] = [
            AdzunaProvider(),
            CompanyCareerProvider(),
            ArbeitNowProvider(),
            RemoteOKProvider(),
        ]
        self.last_run: dict[str, Any] = {}

    async def search(self, queries: Iterable[str], location: str | None = None, limit: int = 20) -> list[JobListing]:
        normalized_queries = [query.strip() for query in queries if query and query.strip()]
        if not normalized_queries:
            self.last_run = self._empty_run()
            return []

        per_query_limit = max(20, min(limit, settings.JOB_MAX_RESULTS))
        start = time.perf_counter()
        tasks = []
        for provider in self.providers:
            query_count = 3 if isinstance(provider, CompanyCareerProvider) else 5
            for query in normalized_queries[:query_count]:
                tasks.append(provider._safe_search(query, location=location, limit=per_query_limit))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        candidates: list[JobListing] = []
        provider_counts: Counter[str] = Counter()
        failures = 0
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Job provider search failed: %s", result)
                failures += 1
                continue
            candidates.extend(result)
            for job in result:
                provider_counts[job.provider or "unknown"] += 1

        deduped = self._dedupe(candidates)[:limit]
        statuses = [await provider.health_check() for provider in self.providers]
        self.last_run = {
            "query_count": len(normalized_queries),
            "candidate_count": len(candidates),
            "deduped_count": len(deduped),
            "duplicates_removed": max(len(candidates) - len(deduped), 0),
            "latency_ms": round((time.perf_counter() - start) * 1000, 1),
            "failures": failures + sum(_failure_count(status) for status in statuses),
            "provider_counts": dict(provider_counts),
            "provider_status": statuses,
        }
        return deduped

    def _empty_run(self) -> dict[str, Any]:
        return {
            "query_count": 0,
            "candidate_count": 0,
            "deduped_count": 0,
            "duplicates_removed": 0,
            "latency_ms": 0.0,
            "failures": 0,
            "provider_counts": {},
            "provider_status": [],
        }

    def _dedupe(self, jobs: Iterable[JobListing]) -> list[JobListing]:
        deduped: list[JobListing] = []
        by_fingerprint: dict[str, int] = {}
        by_company_key: dict[str, int] = {}
        for job in jobs:
            if not _valid_listing(job):
                continue
            key = _company_key(job)
            match_index = by_fingerprint.get(job.fingerprint)
            if match_index is None:
                match_index = by_company_key.get(key)
            if match_index is None:
                for index, existing in enumerate(deduped):
                    if normalize_text(existing.company) == normalize_text(job.company) and job_similarity(existing, job) >= 0.86:
                        match_index = index
                        break
            if match_index is None:
                deduped.append(job)
                by_fingerprint[job.fingerprint] = len(deduped) - 1
                by_company_key[key] = len(deduped) - 1
                continue
            existing = deduped[match_index]
            if should_replace(existing, job):
                deduped[match_index] = job
                by_fingerprint[job.fingerprint] = match_index
                by_company_key[key] = match_index
        deduped.sort(key=lambda item: (item.freshness_score, len(item.description)), reverse=True)
        return deduped


__all__ = [
    "JobListing",
    "JobProviderHub",
    "normalize_job_item",
]
