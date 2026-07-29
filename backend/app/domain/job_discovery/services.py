from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import func, tuple_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.ai_orchestration.gateway import gateway
from app.domain.interviews.models import InterviewResult, InterviewSession
from app.domain.jobs.models import Job, JobSource, JobStatus
from app.domain.jobs.deduplication import should_replace
from app.domain.jobs.providers import JobListing, JobProviderHub, normalize_job_item
from app.domain.learning.models import LearningMessage, LearningSession
from app.domain.users.models import User
from app.services.cache_service import cache
from app.domain.ai_orchestration.prompts import job_query_prompt, PROMPT_VERSION_JOB_QUERY
from app.domain.ai_orchestration.schemas import JobQuerySchema

from .models import (
    AIJobQuery,
    JobRanking,
    JobRecommendationEvent,
    JobSearchHistory,
    JobSearchSource,
    RecommendedJob,
    StudentSearchProfile,
)

logger = logging.getLogger(__name__)


CAREER_PROVIDER_NAMES = {
    "company_page",
    "amazon_careers",
    "google_careers",
    "workday_careers",
    "configured_company_feed",
}

NON_PRODUCTION_JOB_MARKERS = ("placeholder", "fake job", "demo job", "tech inc", "example.com", "remote-jobs/example")


def _json_loads(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)


def _tokenize(text: str) -> List[str]:
    return [part.lower() for part in re.split(r"[^a-zA-Z0-9+.#-]+", text or "") if len(part) > 1]


def _dedupe_keep_order(items: Sequence[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _looks_non_production_job(job: Job) -> bool:
    text = " ".join([job.title or "", job.company or "", job.raw_description or "", job.apply_link or ""]).lower()
    return any(marker in text for marker in NON_PRODUCTION_JOB_MARKERS)


def _latest_interview_scores(db: Session, user_id: int) -> Dict[str, Any]:
    result = (
        db.query(InterviewResult)
        .join(InterviewSession, InterviewResult.interview_id == InterviewSession.id)
        .filter(InterviewSession.user_id == user_id)
        .order_by(InterviewResult.created_at.desc())
        .first()
    )
    if not result:
        return {}
    return {
        "confidence_score": result.confidence_score,
        "communication_score": result.communication_score,
        "technical_score": result.technical_score,
        "problem_solving_score": result.problem_solving_score,
        "overall_grade": result.overall_grade,
    }


def _learning_progress(db: Session, user_id: int) -> Dict[str, Any]:
    sessions = db.query(LearningSession).filter(LearningSession.user_id == user_id).count()
    messages = (
        db.query(func.count(LearningMessage.id))
        .join(LearningSession, LearningMessage.session_id == LearningSession.id)
        .filter(LearningSession.user_id == user_id)
        .scalar()
    ) or 0
    return {
        "sessions": sessions,
        "messages": int(messages),
    }


def _seed_query_variants(query: str) -> List[str]:
    seed = (query or "").strip()
    if not seed:
        return []
    text = seed.lower()
    variants: List[str] = []
    if any(token in text for token in ["ai engineer", "machine learning", "ml engineer", "llm", "generative ai", "deep learning", "nlp", "computer vision"]):
        variants.extend([
            "machine learning engineer",
            "ml engineer",
            "ai software engineer",
            "llm engineer",
            "generative ai engineer",
            "nlp engineer",
            "computer vision engineer",
            "rag engineer",
            "mlops engineer",
            "python ai engineer",
            "deep learning engineer",
        ])
    elif any(token in text for token in ["data scientist", "data engineer", "analytics"]):
        variants.extend([
            "data scientist",
            "data engineer",
            "analytics engineer",
            "business intelligence engineer",
            "data analyst",
        ])
    elif any(token in text for token in ["frontend", "react", "ui", "ux"]):
        variants.extend([
            "frontend developer",
            "react developer",
            "ui engineer",
            "ui developer",
            "next.js developer",
        ])
    elif any(token in text for token in ["backend", "api", "python", "fastapi", "django", "flask"]):
        variants.extend([
            "backend engineer",
            "api engineer",
            "python developer",
            "fastapi developer",
            "django developer",
        ])
    else:
        variants.extend([
            f"{seed} jobs",
            f"{seed} internship",
            f"{seed} remote jobs",
            f"{seed} fresher jobs",
        ])
    variants.extend([
        f"{variant} jobs" for variant in list(variants) if not variant.endswith("jobs")
    ])
    return _dedupe_keep_order(variants)


class GeminiQueryGenerator:
    def generate(self, profile: StudentSearchProfile, user: User, seed_query: str | None = None, use_ai: bool = True) -> List[str]:
        prompt_profile = {
            "skills": profile.keywords or [],
            "education": profile.search_context.get("education", "Not specified"),
            "preferred_roles": profile.preferred_roles or [],
            "preferred_locations": profile.preferred_locations or [],
            "career_goal": profile.career_goal or user.career_goal or "Not specified",
            "interview_scores": profile.interview_scores or {},
            "learning_progress": profile.learning_progress or {},
        }
        if seed_query:
            prompt_profile["career_goal"] = seed_query
            prompt_profile["preferred_roles"] = _dedupe_keep_order([seed_query] + list(profile.preferred_roles or []) + _seed_query_variants(seed_query))
        prompt = job_query_prompt(
            prompt_profile,
            seed_query=seed_query,
        )
        if use_ai and settings.GEMINI_API_KEY:
            try:
                response = gateway.generate_structured_response(
                    prompt,
                    JobQuerySchema,
                    use_pro=False,
                    user_id=user.id,
                    feature="job_query_generation",
                    prompt_version=PROMPT_VERSION_JOB_QUERY,
                )
                queries = _dedupe_keep_order(response.queries)
                if seed_query:
                    seed_l = seed_query.strip().lower()
                    queries = [query for query in queries if query.strip().lower() != seed_l]
                return queries[:20]
            except Exception as exc:
                logger.warning("Gemini query generation failed, using heuristic fallback: %s", exc)
        return self._heuristic_queries(profile, seed_query=seed_query)

    def _heuristic_queries(self, profile: StudentSearchProfile, seed_query: str | None = None) -> List[str]:
        skills = list(profile.keywords or [])[:8]
        roles = list(profile.preferred_roles or [])[:6] or ["Software Engineer", "Backend Developer", "Frontend Developer"]
        locations = list(profile.preferred_locations or [])[:4] or ["Remote", "India", "Hyderabad"]

        queries: List[str] = []
        seed_variants = _seed_query_variants(seed_query or "")
        for variant in seed_variants[:8]:
            for location in locations[:3]:
                queries.append(f"{variant} {location}".strip())
        if seed_query:
            for location in locations[:3]:
                queries.append(f"{seed_query} jobs {location}".strip())
                queries.append(f"{seed_query} internship {location}".strip())
        for role in roles[:4]:
            for location in locations[:3]:
                queries.append(f"{role} jobs {location}".strip())
        for skill in skills[:6]:
            queries.append(f"{skill} jobs {locations[0]}")
            queries.append(f"{skill} internship {locations[0]}")
        if profile.career_goal:
            queries.append(f"{profile.career_goal} jobs {locations[0]}")
        queries.extend(
            [
                "software engineer fresher jobs India",
                "remote software engineer jobs",
                "entry level backend developer jobs",
                "graduate engineer trainee jobs",
            ]
        )
        return _dedupe_keep_order(queries)[:20]


@dataclass
class SearchResultBundle:
    jobs: List[Job]
    queries: List[str]
    history_id: Optional[int] = None


class JobRankingService:
    def __init__(self) -> None:
        self._embedding_enabled = True
        self._embedding_cache: Dict[str, List[float]] = {}
        self._semantic_budget = 0

    def set_embedding_budget(self, value: int) -> None:
        self._semantic_budget = max(0, value)

    def _embed_cached(self, text: str, user_id: int) -> List[float] | None:
        if not self._embedding_enabled:
            return None
        key = hashlib.sha256(text[:4000].encode("utf-8")).hexdigest()
        if key in self._embedding_cache:
            return self._embedding_cache[key]
        try:
            from app.domain.ai_orchestration.gateway import gateway

            embedding = gateway.embed_text(text[:4000], user_id=user_id, feature="job_matching_embedding")
            self._embedding_cache[key] = embedding
            return embedding
        except Exception as exc:
            self._embedding_enabled = False
            logger.debug("Job embedding match disabled for this request: %s", exc)
            return None

    def _semantic_similarity(self, user: User, profile: StudentSearchProfile, job: Job) -> float:
        if self._semantic_budget <= 0:
            return 0.0
        self._semantic_budget -= 1
        profile_text = " ".join(
            [
                user.career_goal or "",
                " ".join(user.skills or []),
                " ".join(profile.keywords or []),
                " ".join(profile.preferred_roles or []),
                " ".join(profile.resume_keywords or []),
            ]
        )
        job_text = " ".join([job.title or "", job.company or "", job.raw_description or "", " ".join(job.extracted_skills or [])])
        left = self._embed_cached(profile_text, user.id)
        right = self._embed_cached(job_text, user.id)
        if not left or not right:
            return 0.0
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = sum(a * a for a in left) ** 0.5
        right_norm = sum(b * b for b in right) ** 0.5
        if not left_norm or not right_norm:
            return 0.0
        return max(0.0, min(dot / (left_norm * right_norm), 1.0))

    def score_job(self, user: User, profile: StudentSearchProfile, job: Job) -> Dict[str, Any]:
        user_skills = {skill.strip().lower() for skill in (user.skills or []) if skill}
        job_skills = {skill.strip().lower() for skill in (job.extracted_skills or []) if skill}
        title_tokens = set(_tokenize(job.title))
        desc_tokens = set(_tokenize(job.raw_description or ""))
        skill_overlap = len(user_skills.intersection(job_skills))
        token_overlap = len(user_skills.intersection(title_tokens.union(desc_tokens)))

        role_tokens = set(_tokenize(" ".join(profile.preferred_roles or []))) | set(_tokenize(user.career_goal or ""))
        role_overlap = len(role_tokens.intersection(title_tokens.union(desc_tokens)))

        location_score = 0
        preferred_locations = [loc.lower() for loc in (profile.preferred_locations or []) if loc]
        if preferred_locations:
            job_location = (job.location or "").lower()
            if any(loc in job_location for loc in preferred_locations):
                location_score = 10
            elif "remote" in preferred_locations and "remote" in job_location:
                location_score = 10

        interview_scores = profile.interview_scores or {}
        interview_bonus = float(interview_scores.get("overall_grade") or 0) * 2
        learning_bonus = min(float((profile.learning_progress or {}).get("sessions", 0)) * 1.5, 8.0)
        cgpa_bonus = min((profile.cgpa or 0) * 2.5, 12.5) if profile.cgpa else 0

        semantic_bonus = self._semantic_similarity(user, profile, job) * 35
        raw_score = (skill_overlap * 12) + (token_overlap * 4) + (role_overlap * 5) + location_score + interview_bonus + learning_bonus + cgpa_bonus + semantic_bonus
        match_score = max(0, min(int(round(raw_score)), 100))

        missing_skills = list((job_skills - user_skills) or set(_tokenize(job.title)) - user_skills)
        missing_skills = _dedupe_keep_order([skill.title() for skill in missing_skills])[:6]
        suggested_improvements = []
        if missing_skills:
            suggested_improvements.append(f"Strengthen {', '.join(missing_skills[:3])}")
        if not location_score:
            suggested_improvements.append("Add preferred locations to your profile")
        suggested_improvements.append("Keep your resume keywords current")

        learning_recommendations = []
        if "docker" not in user_skills and any(token in {"backend", "full", "stack", "api"} for token in title_tokens):
            learning_recommendations.append("Docker Essentials")
        if "sql" not in user_skills and any(token in {"data", "database", "backend"} for token in title_tokens):
            learning_recommendations.append("SQL and Database Fundamentals")
        if any(token in {"react", "frontend", "ui"} for token in title_tokens):
            learning_recommendations.append("React component architecture")
        learning_recommendations = _dedupe_keep_order(learning_recommendations)[:4]

        if match_score >= 85:
            recommendation = "Apply Immediately"
            difficulty = "Medium"
        elif match_score >= 65:
            recommendation = "Apply Soon"
            difficulty = "Medium"
        elif match_score >= 45:
            recommendation = "Prepare First"
            difficulty = "Hard"
        else:
            recommendation = "Build Skills First"
            difficulty = "Hard"

        reason = f"Strong {', '.join(sorted(job_skills.intersection(user_skills))[:4]) or 'profile'} match with {job.company}."
        if semantic_bonus >= 20:
            reason = f"Strong semantic fit between your profile and {job.title} at {job.company}."
        if role_overlap:
            reason = f"Excellent role alignment for {job.title}."

        return {
            "rank_score": match_score,
            "reason": reason,
            "missing_skills": missing_skills,
            "suggested_improvements": suggested_improvements,
            "learning_recommendations": learning_recommendations,
            "expected_difficulty": difficulty,
            "ai_recommendation": recommendation,
        }


class RecommendationEngine:
    def __init__(self, db: Session):
        self.db = db
        self.query_generator = GeminiQueryGenerator()
        self.provider_hub = JobProviderHub()
        self.ranking_service = JobRankingService()
        self._last_job_monitor: Dict[str, Any] = {}

    def build_profile(self, user: User, refresh: bool = False) -> StudentSearchProfile:
        profile = self.db.query(StudentSearchProfile).filter(StudentSearchProfile.user_id == user.id).first()
        if not profile:
            profile = StudentSearchProfile(user_id=user.id)
            self.db.add(profile)

        resume_hash = hashlib.sha256((user.resume_url or "").encode("utf-8")).hexdigest() if user.resume_url else None
        education = f"{user.branch or ''} {user.department or ''} at {user.college or ''}".strip()
        search_context = {
            "education": education,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "profile_completed": user.profile_completed,
        }

        profile.preferred_roles = _dedupe_keep_order(
            list((profile.preferred_roles or []))
            + [user.career_goal or ""]
            + [user.role.value.title().replace("_", " ") if hasattr(user.role, "value") else str(user.role).title()]
            + [self._goal_to_role(user.career_goal)]
        )
        profile.preferred_locations = _dedupe_keep_order(
            list((profile.preferred_locations or []))
            + list(user.profile_data.get("preferred_locations", []) if isinstance(user.profile_data, dict) else [])
            + ["Remote", "India", "Hyderabad"]
        )
        profile.keywords = _dedupe_keep_order(
            list(user.skills or [])
            + self._extract_keywords(user.career_goal or "")
            + self._extract_keywords(education)
        )
        profile.resume_keywords = _dedupe_keep_order(
            list((user.skills or []))
            + self._extract_keywords(user.full_name)
            + self._extract_keywords(user.career_goal or "")
        )
        profile.interview_scores = _latest_interview_scores(self.db, user.id)
        profile.learning_progress = _learning_progress(self.db, user.id)
        profile.search_context = search_context
        profile.cgpa = user.cgpa
        profile.career_goal = user.career_goal
        profile.last_resume_url = user.resume_url
        profile.profile_hash = resume_hash
        profile.last_generated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(profile)
        return profile

    def generate_queries(self, profile: StudentSearchProfile, user: User, force: bool = False, use_ai: bool = True) -> List[AIJobQuery]:
        if not force:
            cached_queries = (
                self.db.query(AIJobQuery)
                .filter(
                    AIJobQuery.profile_id == profile.id,
                    AIJobQuery.expires_at.isnot(None),
                    AIJobQuery.expires_at > datetime.now(timezone.utc),
                )
                .order_by(AIJobQuery.created_at.desc())
                .all()
            )
            if cached_queries:
                return cached_queries
        queries = self.query_generator.generate(profile, user, use_ai=use_ai)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=6)
        results: List[AIJobQuery] = []
        for idx, query in enumerate(queries):
            record = AIJobQuery(
                user_id=user.id,
                profile_id=profile.id,
                query_text=query,
                query_payload={
                    "preferred_roles": profile.preferred_roles or [],
                    "preferred_locations": profile.preferred_locations or [],
                    "keywords": profile.keywords or [],
                    "index": idx,
                },
                source=JobSearchSource.GEMINI.value if settings.GEMINI_API_KEY else JobSearchSource.LOCAL_CACHE.value,
                expires_at=expires_at,
                cache_key=hashlib.sha256(f"{user.id}:{query}".encode("utf-8")).hexdigest(),
            )
            self.db.add(record)
            results.append(record)
        self.db.commit()
        for record in results:
            self.db.refresh(record)
        return results

    def _run_async(self, coro):
        try:
            return asyncio.run(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

    def _fetch_live_job_listings(self, queries: Sequence[str], location: Optional[str], limit: int) -> List[JobListing]:
        cache_key = hashlib.sha256(
            f"jobs:live:v2:{location or ''}:{limit}:{'|'.join(queries[:10])}".encode("utf-8")
        ).hexdigest()
        cached = cache.get(cache_key)
        cached_items = cached.get("listings") if isinstance(cached, dict) else cached
        cached_monitor = cached.get("monitor") if isinstance(cached, dict) else None
        if isinstance(cached_items, list) and cached_items:
            try:
                listings = [
                    JobListing(
                        **{
                            **item,
                            "posted_date": self._parse_datetime(item.get("posted_date")),
                        }
                    )
                    for item in cached_items
                    if isinstance(item, dict)
                ]
                monitor = dict(cached_monitor or {})
                monitor.update({
                    "cached": True,
                    "queries": list(queries[:10]),
                    "jobs_fetched": len(listings),
                    "status": "cached",
                })
                self._last_job_monitor = monitor
                return listings
            except Exception as exc:
                logger.debug("Ignoring stale cached job listings: %s", exc)
        try:
            start = time.perf_counter()
            listings = self._run_async(self.provider_hub.search(queries, location=location, limit=min(limit, settings.JOB_MAX_RESULTS)))
            logger.info("Fetched %s live job listings for %s query(s)", len(listings), len(queries))
            run = getattr(self.provider_hub, "last_run", {}) or {}
            self._last_job_monitor = {
                "cached": False,
                "queries": list(queries[:10]),
                "jobs_fetched": len(listings),
                "candidate_count": int(run.get("candidate_count", len(listings)) or len(listings)),
                "duplicates_removed": int(run.get("duplicates_removed", 0) or 0),
                "latency_ms": round(float(run.get("latency_ms") or ((time.perf_counter() - start) * 1000)), 1),
                "failures": int(run.get("failures", 0) or 0),
                "provider_counts": dict(run.get("provider_counts") or {}),
                "provider_status": list(run.get("provider_status") or []),
                "status": "healthy" if listings else "empty",
            }
            cache.set(
                cache_key,
                {
                    "listings": [listing.to_dict() for listing in listings],
                    "monitor": self._last_job_monitor,
                },
                expiration=settings.JOB_CACHE_TTL_MINUTES * 60,
            )
            return listings
        except Exception as exc:
            logger.warning("Live job provider search failed: %s", exc)
            return []

    def _listing_to_job(self, listing: JobListing, query_id: Optional[int] = None) -> Job:
        source_map = {
            "arbeitnow": JobSource.ARBEITNOW,
            "remoteok": JobSource.REMOTEOK,
            "adzuna": JobSource.ADZUNA,
            **{name: JobSource.COMPANY_PAGE for name in CAREER_PROVIDER_NAMES},
        }
        source = source_map.get(listing.provider, JobSource.MANUAL)
        return Job(
            title=listing.title,
            company=listing.company,
            location=listing.location,
            salary_range=listing.salary,
            experience_required=listing.experience or listing.employment_type,
            employment_type=listing.employment_type,
            posted_date=listing.posted_date,
            raw_description=listing.description or listing.summary or listing.title,
            apply_link=listing.apply_url or listing.provider_url or "",
            source=source,
            external_id=listing.fingerprint,
            extracted_skills=list(listing.skills or []),
            eligibility=None,
            ai_summary=listing.summary or listing.description or listing.title,
            match_score=listing.ai_match_score or 0,
            missing_skills=list(listing.missing_skills or []),
            recommended_topics=[],
            status=JobStatus.ACTIVE,
        )

    def search_jobs(self, user: User, query: str, location: Optional[str] = None, limit: int = 20, refresh: bool = False) -> SearchResultBundle:
        profile = self.build_profile(user, refresh=refresh)
        query_record = AIJobQuery(
            user_id=user.id,
            profile_id=profile.id,
            query_text=query,
            query_payload={"location": location, "limit": limit, "refresh": refresh},
            source=JobSearchSource.MANUAL.value,
            results_count=0,
            cache_key=hashlib.sha256(f"{user.id}:{query}:{location or ''}".encode("utf-8")).hexdigest(),
        )
        self.db.add(query_record)
        self.db.commit()
        self.db.refresh(query_record)

        planned_queries = [record.query_text for record in self.generate_queries(profile, user, force=refresh, use_ai=True)]
        expanded_queries = self.query_generator.generate(profile, user, seed_query=query, use_ai=True)
        normalized_queries = _dedupe_keep_order([query] + expanded_queries + planned_queries)[:10]

        self.ranking_service.set_embedding_budget(5)
        jobs = self._collect_jobs_for_queries(normalized_queries, location=location, limit=limit, user=user, profile=profile, query_id=query_record.id)
        query_record.results_count = len(jobs)
        self.db.commit()

        history = JobSearchHistory(
            user_id=user.id,
            query_text=query,
            filters={
                "location": location,
                "limit": limit,
                "refresh": refresh,
                "job_monitor": self._last_job_monitor,
            },
            results_count=len(jobs),
            source=JobSearchSource.MANUAL.value,
            used_queries=normalized_queries,
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)

        return SearchResultBundle(jobs=jobs, queries=normalized_queries, history_id=history.id)

    def refresh_recommendations(self, user: User, limit: int = 100) -> Dict[str, Any]:
        profile = self.build_profile(user, refresh=True)
        query_records = self.generate_queries(profile, user, force=True, use_ai=False)
        self.ranking_service.set_embedding_budget(0)
        jobs = self._collect_jobs_for_queries(
            [q.query_text for q in query_records], 
            location=None, 
            limit=limit,
            user=user, 
            profile=profile, 
            query_id=None
        )
        return self._materialize_recommendations(user, profile, query_records, jobs)

    def get_recommendations(self, user: User, limit: int = 100) -> List[Job]:
        recommended = (
            self.db.query(RecommendedJob)
            .filter(RecommendedJob.user_id == user.id, RecommendedJob.is_current == True)  # noqa: E712
            .order_by(RecommendedJob.rank_score.desc(), RecommendedJob.refreshed_at.desc())
            .limit(limit)
            .all()
        )
        jobs: List[Job] = []
        seen_job_ids: set[int] = set()
        job_ids = [rec.job_id for rec in recommended]
        jobs_by_id = {job.id: job for job in self.db.query(Job).filter(Job.id.in_(job_ids)).all()} if job_ids else {}
        ranking_ids = [rec.ranking_id for rec in recommended if rec.ranking_id]
        rankings_by_id = {
            ranking.id: ranking
            for ranking in self.db.query(JobRanking).filter(JobRanking.id.in_(ranking_ids)).all()
        } if ranking_ids else {}
        for rec in recommended:
            job = jobs_by_id.get(rec.job_id)
            if job and job.id not in seen_job_ids:
                ranking = rankings_by_id.get(rec.ranking_id) if rec.ranking_id else None
                job.match_score = rec.rank_score
                job.missing_skills = list((ranking.missing_skills or []) if ranking else [])
                job.recommended_topics = list((ranking.learning_recommendations or []) if ranking else [])
                job.extracted_skills = job.extracted_skills or []
                job.ai_summary = rec.reason or job.ai_summary
                jobs.append(job)
                seen_job_ids.add(job.id)
        if jobs:
            return jobs
        try:
            refreshed = self.refresh_recommendations(user, limit=limit)
            refreshed_jobs = refreshed.get("jobs") or []
            if refreshed_jobs:
                return refreshed_jobs[:limit]
        except Exception as exc:
            logger.warning("Live recommendation refresh failed for %s: %s", user.id, exc)
        return []

    def get_history(self, user: User, limit: int = 50) -> List[JobSearchHistory]:
        return (
            self.db.query(JobSearchHistory)
            .filter(JobSearchHistory.user_id == user.id)
            .order_by(JobSearchHistory.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_trending(self, limit: int = 20) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(
                Job.id.label("job_id"),
                func.count(RecommendedJob.id).label("hits"),
                func.avg(RecommendedJob.rank_score).label("avg_score"),
            )
            .join(RecommendedJob, RecommendedJob.job_id == Job.id)
            .filter(RecommendedJob.is_current == True)  # noqa: E712
            .group_by(Job.id)
            .order_by(func.count(RecommendedJob.id).desc(), func.avg(RecommendedJob.rank_score).desc())
            .limit(limit)
            .all()
        )
        job_ids = [row.job_id for row in rows]
        jobs = {job.id: job for job in self.db.query(Job).filter(Job.id.in_(job_ids)).all()}
        results = []
        for row in rows:
            job = jobs.get(row.job_id)
            if not job:
                continue
            results.append({
                "job": job,
                "hits": int(row.hits or 0),
                "avg_score": int(round(float(row.avg_score or 0))),
            })
        return results

    def record_action(self, user: User, job_id: int, action: str, note: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> JobRecommendationEvent:
        event = JobRecommendationEvent(
            user_id=user.id,
            job_id=job_id,
            action=action,
            note=note,
            payload=payload or {},
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        if action == "applied":
            self.db.query(RecommendedJob).filter(RecommendedJob.user_id == user.id, RecommendedJob.job_id == job_id).update({"is_current": False})
            self.db.commit()
        return event

    def _materialize_recommendations(
        self,
        user: User,
        profile: StudentSearchProfile,
        query_records: Sequence[AIJobQuery],
        jobs: Sequence[Job],
    ) -> Dict[str, Any]:
        self.db.query(RecommendedJob).filter(RecommendedJob.user_id == user.id).update({"is_current": False})

        ranked_jobs: List[Dict[str, Any]] = []
        ranking_rows: List[JobRanking] = []
        recommendation_rows: List[RecommendedJob] = []
        for index, job in enumerate(jobs):
            if not job.id:
                continue
            ranking = self.ranking_service.score_job(user, profile, job)
            ranking_rows.append(
                JobRanking(
                    user_id=user.id,
                    job_id=job.id,
                    query_id=query_records[0].id if query_records else None,
                    rank_score=ranking["rank_score"],
                    reason=ranking["reason"],
                    missing_skills=ranking["missing_skills"],
                    suggested_improvements=ranking["suggested_improvements"],
                    learning_recommendations=ranking["learning_recommendations"],
                    expected_difficulty=ranking["expected_difficulty"],
                    ai_recommendation=ranking["ai_recommendation"],
                    rank_index=index + 1,
                )
            )
            recommendation_rows.append(
                RecommendedJob(
                    user_id=user.id,
                    job_id=job.id,
                    rank_score=ranking["rank_score"],
                    reason=ranking["reason"],
                    ai_recommendation=ranking["ai_recommendation"],
                    is_current=True,
                    source_query=query_records[0].query_text if query_records else None,
                )
            )
            ranked_jobs.append({
                "job": job,
                **ranking,
                "rank_index": index + 1,
            })
        if ranking_rows:
            self.db.bulk_save_objects(ranking_rows)
        if recommendation_rows:
            self.db.bulk_save_objects(recommendation_rows)

        refresh_event = JobRecommendationEvent(
            user_id=user.id,
            job_id=jobs[0].id if jobs else 0,
            action=JobSearchSource.MANUAL.value,
            payload={
                "queries": [q.query_text for q in query_records],
                "count": len(jobs),
                "job_monitor": self._last_job_monitor,
            },
            note="Recommendation refresh",
        )
        self.db.add(refresh_event)
        self.db.commit()
        for row in ranked_jobs:
            job = row["job"]
            job.match_score = row["rank_score"]
            job.missing_skills = row["missing_skills"]
            job.recommended_topics = row["learning_recommendations"]
            job.ai_summary = row["reason"]

        return {
            "profile": profile,
            "queries": list(query_records),
            "rankings": ranked_jobs,
            "jobs": [row["job"] for row in ranked_jobs],
        }

    def _collect_jobs_for_queries(
        self,
        queries: Sequence[str],
        location: Optional[str],
        limit: int,
        user: User,
        profile: StudentSearchProfile,
        query_id: Optional[int],
    ) -> List[Job]:
        self._expire_non_production_jobs()
        collected: List[Job] = []
        seen_external: set[str] = set()
        seen_fingerprints: set[str] = set()
        query_tokens = set(_tokenize(" ".join(queries)))
        skills = set(_tokenize(" ".join(profile.keywords or [])))

        live_listings = self._fetch_live_job_listings(queries, location, limit)
        fingerprints = [listing.fingerprint for listing in live_listings if listing.fingerprint]
        existing_by_external = {
            job.external_id: job
            for job in self.db.query(Job).filter(Job.external_id.in_(fingerprints)).all()
        } if fingerprints else {}
        title_keys = {
            (listing.title, listing.company)
            for listing in live_listings
            if listing.title and listing.company
        }
        existing_by_title = {
            (job.title, job.company): job
            for job in self.db.query(Job)
            .filter(tuple_(Job.title, Job.company).in_(title_keys))
            .all()
        } if title_keys else {}
        for listing in live_listings:
            job = self._persist_search_job(
                listing,
                user,
                profile,
                query_id,
                seen_external,
                seen_fingerprints,
                existing_by_external,
                existing_by_title,
            )
            if job:
                collected.append(job)
                seen_external.add(job.external_id or f"job-{job.id}")
                seen_fingerprints.add(job.fingerprint)
            if len(collected) >= limit:
                break

        if collected:
            self.db.flush()

        if len(collected) < limit:
            active_jobs = (
                self.db.query(Job)
                .filter(Job.status == JobStatus.ACTIVE, Job.source != JobSource.MANUAL)
                .order_by(Job.created_at.desc())
                .limit(max(limit * 4, 200))
                .all()
            )
            for job in active_jobs:
                if _looks_non_production_job(job):
                    continue
                if job.fingerprint in seen_fingerprints:
                    continue
                if location and job.location and location.lower() not in job.location.lower() and "remote" not in (job.location or "").lower():
                    continue
                haystack = " ".join([job.title or "", job.company or "", job.location or "", job.raw_description or ""])
                hay_tokens = set(_tokenize(haystack))
                if query_tokens and not hay_tokens.intersection(query_tokens) and not hay_tokens.intersection(skills):
                    continue
                collected.append(job)
                seen_external.add(job.external_id or f"job-{job.id}")
                seen_fingerprints.add(job.fingerprint)
                if len(collected) >= limit:
                    break

        ranked: List[Tuple[int, Job]] = []
        for job in collected:
            score = self.ranking_service.score_job(user, profile, job)["rank_score"]
            score += self._query_relevance_score(job, query_tokens, skills)
            ranked.append((score, job))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [job for _, job in ranked[:limit]]

    def _query_relevance_score(self, job: Job, query_tokens: set[str], skills: set[str]) -> int:
        wanted = query_tokens | skills
        if not wanted:
            return 0
        title_tokens = set(_tokenize(job.title or ""))
        text_tokens = set(_tokenize(" ".join([job.company or "", job.location or "", job.raw_description or ""])))
        score = (len(title_tokens & wanted) * 12) + (len(text_tokens & wanted) * 4)
        if "remote" in wanted and job.remote:
            score += 6
        return min(score, 60)

    def _expire_non_production_jobs(self) -> None:
        bad_jobs = (
            self.db.query(Job)
            .filter(Job.status == JobStatus.ACTIVE)
            .order_by(Job.id.desc())
            .limit(1000)
            .all()
        )
        changed = False
        for job in bad_jobs:
            if _looks_non_production_job(job):
                job.status = JobStatus.EXPIRED
                changed = True
        if changed:
            self.db.commit()

    def _persist_search_job(
        self,
        item: JobListing | Dict[str, Any],
        user: User,
        profile: StudentSearchProfile,
        query_id: Optional[int],
        seen_external: set[str],
        seen_fingerprints: set[str],
        existing_by_external: Optional[Dict[str, Job]] = None,
        existing_by_title: Optional[Dict[Tuple[str, str], Job]] = None,
    ) -> Optional[Job]:
        listing = item if isinstance(item, JobListing) else normalize_job_item(
            item,
            provider=str(item.get("source") or item.get("provider") or "manual"),
            provider_url=item.get("provider_url"),
            company_url=item.get("company_url"),
        )
        if listing.fingerprint in seen_fingerprints:
            existing = (existing_by_external or {}).get(listing.fingerprint)
            return existing

        existing = (existing_by_external or {}).get(listing.fingerprint)
        if not existing and listing.title and listing.company:
            existing = (existing_by_title or {}).get((listing.title, listing.company))
        if existing:
            if should_replace(existing, listing):
                source_map = {
                    "arbeitnow": JobSource.ARBEITNOW,
                    "remoteok": JobSource.REMOTEOK,
                    "adzuna": JobSource.ADZUNA,
                    **{name: JobSource.COMPANY_PAGE for name in CAREER_PROVIDER_NAMES},
                }
                existing.title = listing.title
                existing.company = listing.company
                existing.location = listing.location
                existing.salary_range = listing.salary
                existing.experience_required = listing.experience or listing.employment_type
                existing.employment_type = listing.employment_type
                existing.posted_date = listing.posted_date
                existing.raw_description = listing.description or listing.summary or listing.title
                existing.apply_link = listing.apply_url or listing.provider_url or existing.apply_link
                existing.source = source_map.get(listing.provider, JobSource.MANUAL)
                existing.external_id = listing.fingerprint
                existing.extracted_skills = list(listing.skills or [])
                existing.ai_summary = listing.summary or listing.description or listing.title
                existing.match_score = listing.ai_match_score or existing.match_score
            seen_external.add(existing.external_id or listing.fingerprint)
            seen_fingerprints.add(listing.fingerprint)
            if existing_by_external is not None:
                existing_by_external[existing.external_id or listing.fingerprint] = existing
            if existing_by_title is not None:
                existing_by_title[(existing.title, existing.company)] = existing
            return existing

        job = Job(
            title=listing.title,
            company=listing.company,
            location=listing.location,
            salary_range=listing.salary,
            experience_required=listing.experience or listing.employment_type,
            employment_type=listing.employment_type,
            posted_date=listing.posted_date,
            raw_description=listing.description or listing.summary or listing.title,
            apply_link=listing.apply_url or listing.provider_url or "",
            source=JobSource.ARBEITNOW if listing.provider == "arbeitnow" else (
                JobSource.REMOTEOK if listing.provider == "remoteok" else (
                    JobSource.ADZUNA if listing.provider == "adzuna" else JobSource.COMPANY_PAGE
                )
            ),
            external_id=listing.fingerprint,
            extracted_skills=list(listing.skills or []),
            eligibility=None,
            ai_summary=listing.summary or listing.description or listing.title,
            match_score=listing.ai_match_score or 0,
            missing_skills=list(listing.missing_skills or []),
            recommended_topics=[],
            status=JobStatus.ACTIVE,
        )
        self.db.add(job)
        seen_external.add(job.external_id or listing.fingerprint)
        seen_fingerprints.add(listing.fingerprint)
        if existing_by_external is not None:
            existing_by_external[job.external_id or listing.fingerprint] = job
        if existing_by_title is not None:
            existing_by_title[(job.title, job.company)] = job
        return job

    def _infer_skills_from_text(self, text: str) -> List[str]:
        text_l = text.lower()
        candidates = [
            "Python",
            "JavaScript",
            "TypeScript",
            "React",
            "FastAPI",
            "Django",
            "Flask",
            "SQL",
            "AWS",
            "Docker",
            "Kubernetes",
            "Machine Learning",
            "Communication",
            "System Design",
            "Node.js",
        ]
        return [skill for skill in candidates if skill.lower() in text_l][:6]

    def _goal_to_role(self, goal: Optional[str]) -> str:
        if not goal:
            return ""
        goal_l = goal.lower()
        if "backend" in goal_l:
            return "Backend Developer"
        if "frontend" in goal_l:
            return "Frontend Developer"
        if "machine learning" in goal_l or "ml" in goal_l or "ai" in goal_l:
            return "ML Engineer"
        if "data" in goal_l:
            return "Data Scientist"
        if "full stack" in goal_l:
            return "Full Stack Developer"
        return goal.title()

    def _extract_keywords(self, text: str) -> List[str]:
        tokens = _tokenize(text)
        important = [token.title() for token in tokens if token not in {"and", "the", "for", "with", "from", "into"}]
        return important[:12]

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None


class AIJobDiscoveryService:
    def __init__(self, db: Session):
        self.db = db
        self.engine = RecommendationEngine(db)

    def refresh_user(self, user: User) -> Dict[str, Any]:
        return self.engine.refresh_recommendations(user)

    def recommended_jobs(self, user: User, limit: int = 20) -> List[Job]:
        return self.engine.get_recommendations(user, limit=limit)

    def get_history(self, user: User, limit: int = 50) -> List[JobSearchHistory]:
        return self.engine.get_history(user, limit=limit)

    def search(self, user: User, query: str, location: Optional[str] = None, limit: int = 20, refresh: bool = False) -> Dict[str, Any]:
        result = self.engine.search_jobs(user, query=query, location=location, limit=limit, refresh=refresh)
        ranked = []
        profile = self.engine.build_profile(user)
        query_tokens = set(_tokenize(" ".join([query] + list(result.queries))))
        skills = set(_tokenize(" ".join(profile.keywords or [])))
        for job in result.jobs:
            ranking = self.engine.ranking_service.score_job(user, profile, job)
            ranking["rank_score"] = min(100, ranking["rank_score"] + self.engine._query_relevance_score(job, query_tokens, skills))
            job.match_score = ranking["rank_score"]
            job.missing_skills = ranking["missing_skills"]
            job.recommended_topics = ranking["learning_recommendations"]
            ranked.append({"job": job, **ranking})
        return {
            "queries": result.queries,
            "jobs": result.jobs,
            "rankings": ranked,
            "history_id": result.history_id,
            "profile": profile,
        }

    def chat(self, user: User, message: str, location: Optional[str] = None, limit: int = 12) -> Dict[str, Any]:
        profile = self.engine.build_profile(user)
        search = self.search(user, message, location=location, limit=limit, refresh=False)
        return {
            "assistant_message": self._assistant_message(message, search["jobs"]),
            "queries": search["queries"],
            "jobs": search["jobs"],
            "rankings": search["rankings"],
            "profile": profile,
        }

    def _assistant_message(self, message: str, jobs: Sequence[Job]) -> str:
        if not jobs:
            return "I couldn't find strong matches right now, but I can widen the search or try a different role/location."
        top_job = jobs[0]
        return f"I found a strong match: {top_job.title} at {top_job.company}. If you'd like, I can refine for remote roles, fresher roles, or a higher salary band."
