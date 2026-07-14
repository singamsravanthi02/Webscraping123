from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import httpx
from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.ai_orchestration.gateway import gateway
from app.domain.interviews.models import InterviewResult, InterviewSession
from app.domain.jobs.models import Job, JobBookmark, JobSource, JobStatus
from app.domain.learning.models import LearningMessage, LearningSession
from app.domain.users.models import User
from app.worker.scrapers.factory import get_all_scrapers

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


class GeminiQueryGenerator:
    def generate(self, profile: StudentSearchProfile, user: User) -> List[str]:
        prompt = f"""
Student Profile:
Skills:
{chr(10).join(profile.keywords or [])}

Education:
{profile.search_context.get('education', 'Not specified')}

Preferred Roles:
{chr(10).join(profile.preferred_roles or [])}

Preferred Locations:
{chr(10).join(profile.preferred_locations or [])}

Career Goal:
{profile.career_goal or user.career_goal or 'Not specified'}

Interview Scores:
{json.dumps(profile.interview_scores or {})}

Learning Progress:
{json.dumps(profile.learning_progress or {})}

Generate the best Google Job Search queries for this student.
Return valid JSON only in this exact format:
{{
  "queries": ["query 1", "query 2"]
}}

Generate 10-20 search queries. Focus on internships, fresher roles, remote roles, and location-aware roles when relevant.
"""
        if settings.GEMINI_API_KEY:
            try:
                response_text = gateway.generate_content(prompt, use_pro=False, user_id=user.id, feature="job_query_generation")
                payload = _json_loads(response_text)
                queries = payload.get("queries") or []
                return _dedupe_keep_order(queries)[:20]
            except Exception as exc:
                logger.warning("Gemini query generation failed, using heuristic fallback: %s", exc)
        return self._heuristic_queries(profile)

    def _heuristic_queries(self, profile: StudentSearchProfile) -> List[str]:
        skills = list(profile.keywords or [])[:8]
        roles = list(profile.preferred_roles or [])[:6] or ["Software Engineer", "Backend Developer", "Frontend Developer"]
        locations = list(profile.preferred_locations or [])[:4] or ["Remote", "India", "Hyderabad"]

        queries: List[str] = []
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


class GoogleJobSearchProvider:
    def search(self, query: str, location: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        if settings.SERPAPI_KEY:
            try:
                return self._search_serpapi(query, location, limit)
            except Exception as exc:
                logger.warning("SerpAPI search failed, falling back to local search: %s", exc)
        if settings.SERPER_API_KEY:
            try:
                return self._search_serper(query, location, limit)
            except Exception as exc:
                logger.warning("Serper search failed, falling back to local search: %s", exc)
        if settings.GOOGLE_CSE_API_KEY and settings.GOOGLE_CSE_ID:
            try:
                return self._search_google_cse(query, location, limit)
            except Exception as exc:
                logger.warning("Google CSE search failed, falling back to local search: %s", exc)
        return []

    def _search_serpapi(self, query: str, location: Optional[str], limit: int) -> List[Dict[str, Any]]:
        params = {
            "engine": "google_jobs",
            "q": query,
            "hl": "en",
            "api_key": settings.SERPAPI_KEY,
            "num": limit,
        }
        if location:
            params["location"] = location
        response = httpx.get("https://serpapi.com/search.json", params=params, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        jobs = []
        for item in data.get("jobs_results", [])[:limit]:
            jobs.append({
                "title": item.get("title"),
                "company": item.get("company_name") or item.get("company"),
                "location": item.get("location"),
                "salary_range": item.get("detected_extensions", {}).get("salary"),
                "experience_required": item.get("detected_extensions", {}).get("posted_at") or item.get("job_type"),
                "employment_type": item.get("detected_extensions", {}).get("schedule_type"),
                "posted_date": item.get("detected_extensions", {}).get("posted_at"),
                "raw_description": item.get("description") or item.get("snippet") or item.get("title") or "",
                "apply_link": item.get("apply_options", [{}])[0].get("link") or item.get("related_links", [{}])[0].get("link") or item.get("share_link") or item.get("link") or "",
                "company_logo": item.get("thumbnail"),
                "external_id": f"serpapi_{item.get('job_id') or item.get('title')}_{item.get('company_name')}",
                "source": JobSearchSource.SERPAPI.value,
            })
        return jobs

    def _search_serper(self, query: str, location: Optional[str], limit: int) -> List[Dict[str, Any]]:
        payload = {"q": f"{query} {location or ''}".strip(), "num": limit}
        headers = {"X-API-KEY": settings.SERPER_API_KEY or "", "Content-Type": "application/json"}
        response = httpx.post("https://google.serper.dev/jobs", json=payload, headers=headers, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        jobs = []
        for item in data.get("jobs", [])[:limit]:
            jobs.append({
                "title": item.get("title"),
                "company": item.get("company"),
                "location": item.get("location"),
                "salary_range": item.get("salary"),
                "experience_required": item.get("employmentType"),
                "employment_type": item.get("employmentType"),
                "posted_date": item.get("postedAt"),
                "raw_description": item.get("description") or item.get("snippet") or "",
                "apply_link": item.get("jobUrl") or item.get("link") or "",
                "company_logo": item.get("companyLogo"),
                "external_id": f"serper_{item.get('jobId') or item.get('title')}_{item.get('company')}",
                "source": JobSearchSource.SERPER.value,
            })
        return jobs

    def _search_google_cse(self, query: str, location: Optional[str], limit: int) -> List[Dict[str, Any]]:
        params = {
            "key": settings.GOOGLE_CSE_API_KEY,
            "cx": settings.GOOGLE_CSE_ID,
            "q": f"{query} jobs {location or ''}".strip(),
            "num": min(limit, 10),
        }
        response = httpx.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        jobs = []
        for item in data.get("items", [])[:limit]:
            jobs.append({
                "title": item.get("title"),
                "company": item.get("displayLink"),
                "location": location,
                "salary_range": None,
                "experience_required": None,
                "employment_type": None,
                "posted_date": None,
                "raw_description": item.get("snippet") or item.get("title") or "",
                "apply_link": item.get("link") or "",
                "company_logo": None,
                "external_id": f"googlecse_{item.get('cacheId') or item.get('link')}",
                "source": JobSearchSource.GOOGLE_CSE.value,
            })
        return jobs


class JobRankingService:
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

        raw_score = (skill_overlap * 12) + (token_overlap * 4) + (role_overlap * 5) + location_score + interview_bonus + learning_bonus + cgpa_bonus
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
        self.provider = GoogleJobSearchProvider()
        self.ranking_service = JobRankingService()

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

    def generate_queries(self, profile: StudentSearchProfile, user: User, force: bool = False) -> List[AIJobQuery]:
        queries = self.query_generator.generate(profile, user)
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

        normalized_queries = self.query_generator._heuristic_queries(profile)
        normalized_queries.insert(0, query)
        normalized_queries = _dedupe_keep_order(normalized_queries)[:10]

        jobs = self._collect_jobs_for_queries(normalized_queries, location=location, limit=limit, user=user, profile=profile, query_id=query_record.id)
        query_record.results_count = len(jobs)
        self.db.commit()

        history = JobSearchHistory(
            user_id=user.id,
            query_text=query,
            filters={"location": location, "limit": limit, "refresh": refresh},
            results_count=len(jobs),
            source=JobSearchSource.MANUAL.value,
            used_queries=normalized_queries,
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)

        return SearchResultBundle(jobs=jobs, queries=normalized_queries, history_id=history.id)

    def refresh_recommendations(self, user: User) -> Dict[str, Any]:
        profile = self.build_profile(user, refresh=True)
        query_records = self.generate_queries(profile, user, force=True)
        jobs = self._collect_jobs_for_queries([q.query_text for q in query_records], user=user, profile=profile, query_id=None)
        return self._materialize_recommendations(user, profile, query_records, jobs)

    def get_recommendations(self, user: User, limit: int = 20) -> List[Job]:
        recommended = (
            self.db.query(RecommendedJob)
            .filter(RecommendedJob.user_id == user.id, RecommendedJob.is_current == True)  # noqa: E712
            .order_by(RecommendedJob.rank_score.desc(), RecommendedJob.refreshed_at.desc())
            .limit(limit)
            .all()
        )
        jobs: List[Job] = []
        for rec in recommended:
            job = self.db.query(Job).filter(Job.id == rec.job_id).first()
            if job:
                ranking = self.db.query(JobRanking).filter(JobRanking.id == rec.ranking_id).first() if rec.ranking_id else None
                job.match_score = rec.rank_score
                job.missing_skills = list((ranking.missing_skills or []) if ranking else [])
                job.recommended_topics = list((ranking.learning_recommendations or []) if ranking else [])
                job.extracted_skills = job.extracted_skills or []
                job.ai_summary = rec.reason or job.ai_summary
                jobs.append(job)
        if jobs:
            return jobs
        return self.db.query(Job).filter(Job.status == JobStatus.ACTIVE).order_by(Job.created_at.desc()).limit(limit).all()

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
        self.db.commit()

        ranked_jobs: List[Dict[str, Any]] = []
        for index, job in enumerate(jobs):
            ranking = self.ranking_service.score_job(user, profile, job)
            ranking_record = JobRanking(
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
            self.db.add(ranking_record)
            self.db.flush()
            self.db.add(
                RecommendedJob(
                    user_id=user.id,
                    job_id=job.id,
                    ranking_id=ranking_record.id,
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
        self.db.commit()

        refresh_event = JobRecommendationEvent(
            user_id=user.id,
            job_id=jobs[0].id if jobs else 0,
            action=JobSearchSource.MANUAL.value,
            payload={"queries": [q.query_text for q in query_records], "count": len(jobs)},
            note="Recommendation refresh",
        )
        self.db.add(refresh_event)
        self.db.commit()

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
        collected: List[Job] = []
        seen_external: set[str] = set()
        active_jobs = self.db.query(Job).filter(Job.status == JobStatus.ACTIVE).all()
        query_tokens = _tokenize(" ".join(queries))
        skills = set(_tokenize(" ".join(profile.keywords or [])))
        for job in active_jobs:
            if location and job.location and location.lower() not in job.location.lower() and "remote" not in (job.location or "").lower():
                continue
            haystack = " ".join([job.title or "", job.company or "", job.location or "", job.raw_description or ""])
            hay_tokens = set(_tokenize(haystack))
            if query_tokens and not hay_tokens.intersection(query_tokens) and not hay_tokens.intersection(skills):
                continue
            collected.append(job)
            seen_external.add(job.external_id or f"job-{job.id}")

        if len(collected) < limit:
            for scraper in get_all_scrapers():
                for query in queries[:5]:
                    try:
                        for item in scraper.scrape(keyword=query, location=location or ""):
                            normalized = self._persist_search_job(item, user, profile, query_id, seen_external)
                            if normalized:
                                collected.append(normalized)
                                seen_external.add(normalized.external_id or f"job-{normalized.id}")
                                if len(collected) >= limit:
                                    break
                    except Exception as exc:
                        logger.warning("Job scraper %s failed for query %s: %s", scraper.__class__.__name__, query, exc)
                if len(collected) >= limit:
                    break

        ranked: List[Tuple[int, Job]] = []
        for job in collected:
            score = self.ranking_service.score_job(user, profile, job)["rank_score"]
            ranked.append((score, job))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [job for _, job in ranked[:limit]]

    def _persist_search_job(
        self,
        item: Dict[str, Any],
        user: User,
        profile: StudentSearchProfile,
        query_id: Optional[int],
        seen_external: set[str],
    ) -> Optional[Job]:
        title = item.get("title") or item.get("position") or "Untitled Role"
        company = item.get("company") or item.get("company_name") or "Unknown Company"
        external_id = item.get("external_id") or f"{company}_{title}".replace(" ", "_").lower()
        if external_id in seen_external:
            return self.db.query(Job).filter(Job.external_id == external_id).first()
        existing = self.db.query(Job).filter(Job.external_id == external_id).first()
        if existing:
            return existing
        job = Job(
            title=title,
            company=company,
            location=item.get("location"),
            salary_range=item.get("salary_range"),
            experience_required=item.get("experience_required") or item.get("employment_type"),
            employment_type=item.get("employment_type"),
            posted_date=self._parse_datetime(item.get("posted_date")),
            raw_description=item.get("raw_description") or item.get("description") or title,
            apply_link=item.get("apply_link") or item.get("url") or "",
            source=JobSource(item.get("source") or JobSource.MANUAL.value) if item.get("source") in {s.value for s in JobSource} else JobSource.MANUAL,
            external_id=external_id,
            extracted_skills=item.get("extracted_skills") or self._infer_skills_from_text(item.get("raw_description") or item.get("description") or title),
            eligibility=item.get("eligibility"),
            ai_summary=item.get("ai_summary") or item.get("description") or title,
            match_score=0,
            missing_skills=[],
            recommended_topics=[],
            status=JobStatus.ACTIVE,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
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

    def search(self, user: User, query: str, location: Optional[str] = None, limit: int = 20, refresh: bool = False) -> Dict[str, Any]:
        result = self.engine.search_jobs(user, query=query, location=location, limit=limit, refresh=refresh)
        ranked = []
        profile = self.engine.build_profile(user)
        for job in result.jobs:
            ranking = self.engine.ranking_service.score_job(user, profile, job)
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
        query_bundle = self.engine.query_generator.generate(profile, user)
        chat_prompt = f"""
User message: {message}
Location: {location or 'Any'}
Profile keywords: {', '.join(profile.keywords or [])}
Preferred roles: {', '.join(profile.preferred_roles or [])}
Convert the message into job search queries. Return valid JSON only:
{{"queries":["..."]}}
"""
        if settings.GEMINI_API_KEY:
            try:
                response = gateway.generate_content(chat_prompt, user_id=user.id, feature="job_chat")
                parsed = _json_loads(response)
                chat_queries = _dedupe_keep_order(parsed.get("queries") or [])
            except Exception as exc:
                logger.warning("AI chat query generation failed, using fallback: %s", exc)
                chat_queries = []
        else:
            chat_queries = []
        queries = _dedupe_keep_order([message] + chat_queries + query_bundle)[:10]
        search = self.search(user, queries[0], location=location, limit=limit, refresh=False)
        return {
            "assistant_message": self._assistant_message(message, search["jobs"]),
            "queries": queries,
            "jobs": search["jobs"],
            "rankings": search["rankings"],
            "profile": profile,
        }

    def _assistant_message(self, message: str, jobs: Sequence[Job]) -> str:
        if not jobs:
            return "I couldn't find strong matches right now, but I can widen the search or try a different role/location."
        top_job = jobs[0]
        return f"I found a strong match: {top_job.title} at {top_job.company}. If you'd like, I can refine for remote roles, fresher roles, or a higher salary band."
