import uuid

from app.core.config import settings
from app.core.security import get_password_hash
from app.domain.job_discovery.services import RecommendationEngine
from app.domain.jobs.models import Job, JobSource, JobStatus
from app.domain.users.models import User, UserRole


def _student() -> User:
    return User(
        full_name="Job Search Student",
        email=f"job-search-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=get_password_hash("password123"),
        role=UserRole.STUDENT,
        is_active=True,
        is_verified=True,
        terms_accepted=True,
        skills=["Python", "TensorFlow", "FastAPI"],
        career_goal="AI Engineer",
        profile_completed=True,
        profile_data={"preferred_locations": ["Remote"]},
    )


def test_keyword_expansion_removes_raw_seed_query(db_session, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None, raising=False)

    user = _student()
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    engine = RecommendationEngine(db_session)
    profile = engine.build_profile(user)
    queries = engine.query_generator.generate(profile, user, seed_query="AI Engineer")
    normalized = [query.strip().lower() for query in queries]

    assert "ai engineer" not in normalized
    assert any(
        phrase in " ".join(normalized)
        for phrase in ["machine learning engineer", "ml engineer", "llm engineer", "rag engineer"]
    )


def test_fallback_expires_fake_jobs_and_skips_manual_rows(db_session, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None, raising=False)

    user = _student()
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    fake = Job(
        title="Software Engineer",
        company="Tech Inc fake-job",
        location="Remote",
        raw_description="Placeholder fake job",
        apply_link="https://example.com/fake",
        source=JobSource.ARBEITNOW,
        external_id="fake-row",
        extracted_skills=["Python"],
        status=JobStatus.ACTIVE,
    )
    manual = Job(
        title="Python Backend Engineer",
        company="Manual Company",
        location="Remote",
        raw_description="Python API role",
        apply_link="https://example.com/manual",
        source=JobSource.MANUAL,
        external_id="manual-row",
        extracted_skills=["Python"],
        status=JobStatus.ACTIVE,
    )
    real = Job(
        title="Python Backend Engineer",
        company="NVIDIA",
        location="Remote",
        raw_description="Python API role",
        apply_link="https://remoteok.com/remote-jobs/remote-python-backend-engineer-nvidia-123456",
        source=JobSource.REMOTEOK,
        external_id=f"real-row-{uuid.uuid4().hex}",
        extracted_skills=["Python"],
        status=JobStatus.ACTIVE,
    )
    fake.external_id = f"fake-row-{uuid.uuid4().hex}"
    manual.external_id = f"manual-row-{uuid.uuid4().hex}"
    db_session.add_all([fake, manual, real])
    db_session.commit()

    try:
        engine = RecommendationEngine(db_session)
        profile = engine.build_profile(user)
        monkeypatch.setattr(engine, "_fetch_live_job_listings", lambda *args, **kwargs: [])

        jobs = engine._collect_jobs_for_queries(["python backend"], None, 10, user, profile, None)

        db_session.refresh(fake)
        job_ids = {job.id for job in jobs}
        assert fake.status == JobStatus.EXPIRED
        assert real.id in job_ids
        assert fake.id not in job_ids
        assert manual.id not in job_ids
    finally:
        for row in (fake, manual, real):
            db_session.delete(row)
        db_session.commit()
