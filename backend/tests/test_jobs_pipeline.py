import pytest
import uuid
from unittest.mock import patch, MagicMock
from app.worker.tasks import aggregate_and_process_jobs_task
from app.domain.jobs.models import Job, JobSource
from app.domain.users.models import User

@patch('app.worker.scrapers.arbeitnow.httpx.Client.get')
@patch('app.worker.ai_pipeline.AIGateway.chat_session')
@patch('app.domain.ai_orchestration.agents.jobs.JobMatchingAgent.match_jobs')
def test_job_aggregation_pipeline(mock_match, mock_chat_session, mock_http_get, db_session):
    initial_count = db_session.query(Job).count()

    # Mock Arbeitnow API Response
    mock_response = MagicMock()
    unique_slug = f"software-engineer-{uuid.uuid4().hex[:8]}"
    mock_response.json.return_value = {
        "data": [
            {
                "title": "Software Engineer",
                "company_name": f"Tech Inc {unique_slug}",
                "location": "Remote",
                "url": "https://example.com/apply",
                "description": "Python and React",
                "created_at": "2026-07-09T00:00:00Z",
                "slug": unique_slug
            }
        ]
    }
    mock_http_get.return_value = mock_response

    # Mock Gemini extraction
    mock_chat_mock = MagicMock()
    mock_chat_mock.send_message.return_value.text = '''{"skills": ["Python", "React"], "eligibility": "Bachelors", "ai_summary": "Great role"}'''
    mock_chat_session.return_value = mock_chat_mock
    
    # Mock Match Agent
    mock_match.return_value = [{"job_id": 1, "match_score": 85, "missing_skills": ["SQL"], "ai_summary": "Good match"}]
    
    # Run task
    # To test deduplication, we run it twice
    aggregate_and_process_jobs_task()
    
    # Verify Job was inserted
    jobs = db_session.query(Job).all()
    assert len(jobs) == initial_count + 1
    inserted_job = next(job for job in jobs if job.company == f"Tech Inc {unique_slug}")
    assert "Python" in inserted_job.extracted_skills
    
    # Run again to test deduplication
    aggregate_and_process_jobs_task()
    jobs_after = db_session.query(Job).all()
    assert len(jobs_after) == len(jobs)
