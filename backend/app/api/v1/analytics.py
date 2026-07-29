from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from statistics import fmean
from typing import Any, Dict, Iterable, List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user
from app.db.session import get_db
from app.domain.ai_orchestration.models import StudentAIMemory
from app.domain.audit_logs.models import AITokenUsageLog
from app.domain.assessments.models import AssessmentAttempt, AttemptDetail, AttemptStatus, QuestionBank
from app.domain.interviews.models import InterviewSession
from app.domain.job_discovery.models import JobRanking, JobSearchHistory, RecommendedJob
from app.domain.jobs.models import Job, JobBookmark, JobStatus
from app.domain.knowledge.models import Document
from app.domain.learning.models import LearningMessage, LearningSession
from app.domain.notifications.models import NotificationLog, NotificationStatus
from app.domain.users.models import User, UserRole, UserSession

router = APIRouter()
logger = logging.getLogger(__name__)


def _today_utc() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc_date(value: datetime | None):
    if not value:
        return None
    if value.tzinfo is None:
        return value.date()
    return value.astimezone(timezone.utc).date()


def _mean(values: Iterable[float]) -> float:
    numbers = [float(v) for v in values if v is not None]
    return round(fmean(numbers), 1) if numbers else 0.0


def _daily_counts(events: Iterable[datetime], days: int) -> List[Dict[str, Any]]:
    now = _today_utc().date()
    start = now - timedelta(days=days - 1)
    buckets = {(start + timedelta(days=i)).isoformat(): 0 for i in range(days)}
    for event in events:
        day = _to_utc_date(event)
        if day is None:
            continue
        key = day.isoformat()
        if key in buckets:
            buckets[key] += 1
    return [{"date": date_key, "count": count} for date_key, count in buckets.items()]


def _weekly_averages(scored_events: Iterable[tuple[datetime, float]], weeks: int = 5) -> List[Dict[str, Any]]:
    today = _today_utc().date()
    current_week_start = today - timedelta(days=today.weekday())
    buckets: Dict[str, List[float]] = {}
    labels: List[str] = []
    for offset in range(weeks - 1, -1, -1):
        week_start = current_week_start - timedelta(weeks=offset)
        key = week_start.isoformat()
        buckets[key] = []
        labels.append(key)
    for created_at, score in scored_events:
        day = _to_utc_date(created_at)
        if day is None:
            continue
        week_start = day - timedelta(days=day.weekday())
        key = week_start.isoformat()
        if key in buckets:
            buckets[key].append(float(score))
    return [
        {"week": week_key, "avg": round(fmean(values), 1) if values else 0.0}
        for week_key, values in buckets.items()
    ]


def _score_distribution(scores: Iterable[float]) -> List[Dict[str, Any]]:
    buckets = Counter({"0-40": 0, "41-60": 0, "61-75": 0, "76-90": 0, "91-100": 0})
    for raw_score in scores:
        score = float(raw_score or 0)
        if score <= 40:
            buckets["0-40"] += 1
        elif score <= 60:
            buckets["41-60"] += 1
        elif score <= 75:
            buckets["61-75"] += 1
        elif score <= 90:
            buckets["76-90"] += 1
        else:
            buckets["91-100"] += 1
    return [{"range": label, "count": buckets[label]} for label in ["0-40", "41-60", "61-75", "76-90", "91-100"]]


def _skill_scores(primary: Iterable[str], fallback: Iterable[str], strong: Iterable[str], weak: Iterable[str]) -> List[Dict[str, Any]]:
    strong_set = {item.lower() for item in strong if item}
    weak_set = {item.lower() for item in weak if item}
    scores: Dict[str, float] = {}
    for skill in list(primary) + list(fallback):
        label = skill.strip()
        if not label:
            continue
        normalized = label.lower()
        if normalized in scores:
            continue
        if normalized in strong_set:
            scores[label] = 88.0
        elif normalized in weak_set:
            scores[label] = 48.0
        else:
            scores[label] = 68.0
    return [{"subject": skill, "A": score, "fullMark": 100} for skill, score in scores.items()]


def _heatmap_from_events(events: Iterable[datetime], days: int = 140) -> List[Dict[str, Any]]:
    return _daily_counts(events, days)


@router.get("/overview")
def analytics_overview(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        student_memory = db.query(StudentAIMemory).filter(StudentAIMemory.user_id == current_user.id).first()
    except Exception as exc:
        db.rollback()
        logger.warning("Student analytics memory unavailable for user %s: %s", current_user.id, exc)
        student_memory = None
    resume_analysis = student_memory.resume_analysis if student_memory and student_memory.resume_analysis else {}
    test_performance = student_memory.test_performance if student_memory and student_memory.test_performance else {}
    strong_topics = list(student_memory.strong_topics or []) if student_memory else []
    weak_topics = list(student_memory.weak_topics or []) if student_memory else []
    technical_skills = list(resume_analysis.get("technical_skills", []))
    profile_skills = list(current_user.skills or [])

    student_events = []
    student_events.extend(
        [row.created_at for row in db.query(AssessmentAttempt).filter(AssessmentAttempt.user_id == current_user.id).all() if row.created_at]
    )
    student_events.extend(
        [row.created_at for row in db.query(InterviewSession).filter(InterviewSession.user_id == current_user.id).all() if row.created_at]
    )
    student_events.extend(
        [
            row.created_at
            for row in db.query(JobSearchHistory).filter(JobSearchHistory.user_id == current_user.id).all()
            if row.created_at
        ]
    )
    student_events.extend(
        [row.created_at for row in db.query(LearningSession).filter(LearningSession.user_id == current_user.id).all() if row.created_at]
    )
    student_events.extend(
        [row.created_at for row in db.query(LearningMessage).join(LearningSession).filter(LearningSession.user_id == current_user.id).all() if row.created_at]
    )
    try:
        student_events.extend(
            [row.created_at for row in db.query(AITokenUsageLog).filter(AITokenUsageLog.user_id == current_user.id).all() if row.created_at]
        )
    except Exception as exc:
        db.rollback()
        logger.warning("AI token usage history unavailable for user %s: %s", current_user.id, exc)

    student_test_data = []
    if isinstance(test_performance, dict):
        for key, value in sorted(test_performance.items()):
            student_test_data.append({"name": key.replace("_", " ").title(), "score": float(value or 0)})

    if not student_test_data and student_memory and student_memory.interview_feedback:
        student_test_data = [
            {"name": f"Interview {index + 1}", "score": float((entry or {}).get("overall_grade", 0) * 10)}
            for index, entry in enumerate(student_memory.interview_feedback[:5])
        ]

    if isinstance(test_performance, dict) and test_performance:
        student_subject_strengths = [{"subject": key.replace("_", " ").title(), "score": float(value or 0)} for key, value in test_performance.items()]
    elif strong_topics or weak_topics:
        subject_scores: Dict[str, float] = {}
        for topic in strong_topics:
            subject_scores[topic] = 84.0
        for topic in weak_topics:
            subject_scores.setdefault(topic, 44.0)
        student_subject_strengths = [{"subject": topic, "score": score} for topic, score in subject_scores.items()]
    else:
        student_subject_strengths = []

    student = {
        "readiness_score": round(student_memory.placement_readiness_score or 0.0, 1) if student_memory else 0.0,
        "resume_score": float(
            resume_analysis.get("overall_score")
            or resume_analysis.get("ats_score")
            or resume_analysis.get("score")
            or 0
        ),
        "ai_recommendation": (
            f"Focus on {', '.join(weak_topics[:3])} next."
            if weak_topics
            else (
                f"Build on {', '.join(strong_topics[:3])} to raise your placement readiness."
                if strong_topics
                else (current_user.career_goal or "Complete your profile to unlock deeper recommendations.")
            )
        ),
        "test_performance": student_test_data,
        "subject_strengths": student_subject_strengths,
        "skills_breakdown": _skill_scores(profile_skills, technical_skills, strong_topics, weak_topics),
        "activity_heatmap": _heatmap_from_events(student_events),
    }

    submitted_attempts = (
        db.query(AssessmentAttempt)
        .filter(AssessmentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED]))
        .all()
    )
    attempt_scores = [float(attempt.score) for attempt in submitted_attempts if attempt.score is not None]
    attempts_by_user: Dict[int, List[float]] = defaultdict(list)
    for attempt in submitted_attempts:
        if attempt.score is not None:
            attempts_by_user[attempt.user_id].append(float(attempt.score))

    faculty = {
        "total_students": db.query(User).filter(User.role == UserRole.STUDENT).count(),
        "class_average": _mean(attempt_scores),
        "at_risk_students": sum(1 for scores in attempts_by_user.values() if _mean(scores) < 60.0),
        "top_performers": sum(1 for scores in attempts_by_user.values() if _mean(scores) >= 80.0),
        "grade_distribution": _score_distribution(attempt_scores),
        "class_performance": _weekly_averages(
            ((attempt.created_at, float(attempt.score or 0.0)) for attempt in submitted_attempts if attempt.created_at),
            weeks=5,
        ),
    }

    subject_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"correct": 0, "incorrect": 0, "total": 0})
    topic_rows = (
        db.query(QuestionBank.subject, AttemptDetail.is_correct)
        .join(QuestionBank, QuestionBank.id == AttemptDetail.question_id)
        .join(AssessmentAttempt, AssessmentAttempt.id == AttemptDetail.attempt_id)
        .filter(AssessmentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED]))
        .all()
    )
    for subject, is_correct in topic_rows:
        key = subject or "General"
        subject_stats[key]["total"] += 1
        if is_correct:
            subject_stats[key]["correct"] += 1
        else:
            subject_stats[key]["incorrect"] += 1

    faculty["topic_mastery"] = [
        {"topic": subject, **stats}
        for subject, stats in sorted(subject_stats.items(), key=lambda item: item[1]["total"], reverse=True)[:6]
    ]

    active_jobs = db.query(Job).filter(Job.status == JobStatus.ACTIVE).count()
    job_bookmarks = db.query(JobBookmark).count()
    job_searches = db.query(JobSearchHistory).count()
    recommendations = db.query(RecommendedJob).filter(RecommendedJob.is_current == True).count()
    ranking_scores = [row.rank_score for row in db.query(JobRanking).all() if row.rank_score is not None]
    jobs_today = db.query(Job).filter(Job.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)).count()
    source_mix_counter = Counter()
    for row in db.query(Job.source).all():
        source = row[0]
        if source is None:
            continue
        source_mix_counter[getattr(source, "value", str(source))] += 1
    placement = {
        "active_drives": active_jobs,
        "recommendations": recommendations,
        "avg_match_score": round(_mean(ranking_scores), 1),
        "bookmarks": job_bookmarks,
        "funnel": [
            {"stage": "Searches", "count": job_searches},
            {"stage": "Bookmarks", "count": job_bookmarks},
            {"stage": "Recommendations", "count": recommendations},
            {"stage": "Active Jobs", "count": active_jobs},
        ],
        "source_mix": [{"name": source, "value": count} for source, count in source_mix_counter.most_common(5)],
    }

    active_users = db.query(User).filter(User.is_active == True).count()
    try:
        token_logs = db.query(AITokenUsageLog).all()
    except Exception as exc:
        db.rollback()
        logger.warning("AI token usage summary unavailable: %s", exc)
        token_logs = []
    token_log_counts = [row.created_at for row in token_logs if row.created_at]
    assessment_count = (
        db.query(AssessmentAttempt)
        .filter(AssessmentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED]))
        .count()
    )
    session_activity = []
    sessions = db.query(UserSession).all()
    hour_buckets = Counter()
    for session in sessions:
        created = session.created_at
        if not created:
            continue
        hour = created.astimezone(timezone.utc).hour if created.tzinfo else created.hour
        label = f"{(hour // 4) * 4:02d}:00"
        hour_buckets[label] += 1
    for label in sorted(hour_buckets.keys()):
        session_activity.append({"time": label, "users": hour_buckets[label]})

    admin = {
        "system_status": "Operational",
        "active_users": active_users,
        "jobs": db.query(Job).count(),
        "jobs_today": jobs_today,
        "job_searches": job_searches,
        "job_recommendations": recommendations,
        "avg_job_match_score": round(_mean(ranking_scores), 1),
        "documents": db.query(Document).count(),
        "pending_notifications": db.query(NotificationLog).filter(NotificationLog.status == NotificationStatus.PENDING).count(),
        "ai_requests": len(token_logs),
        "assessments_taken": assessment_count,
        "job_source_mix": [{"name": source, "value": count} for source, count in source_mix_counter.most_common(5)],
        "ai_usage": [
            {"day": row["date"], "calls": row["count"]}
            for row in _daily_counts(token_log_counts, 7)
        ],
        "concurrent_users": session_activity,
    }

    return {
        "student": student,
        "faculty": faculty,
        "placement": placement,
        "admin": admin,
    }
