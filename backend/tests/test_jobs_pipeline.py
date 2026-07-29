from app.domain.jobs.deduplication import job_fingerprint
from app.domain.jobs.providers import JobListing, JobProviderHub, normalize_job_item
def test_job_fingerprint_ignores_description_noise():
    left = {
        "title": "Software Engineer",
        "company": "NVIDIA",
        "location": "India, Hyderabad",
        "apply_url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/abc",
        "description": "short",
    }
    right = {**left, "description": "much richer job description from another source"}

    assert job_fingerprint(left) == job_fingerprint(right)


def test_provider_hub_keeps_richer_duplicate():
    hub = JobProviderHub()
    lean = JobListing(
        title="Software Engineer",
        company="NVIDIA",
        location="India, Hyderabad",
        apply_url="https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/abc",
        provider="remoteok",
        description="Python",
        fingerprint=job_fingerprint(
            {
                "title": "Software Engineer",
                "company": "NVIDIA",
                "location": "India, Hyderabad",
                "apply_url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/abc",
            }
        ),
    )
    rich = JobListing(
        title=lean.title,
        company=lean.company,
        location=lean.location,
        apply_url=lean.apply_url,
        provider="workday_careers",
        description="Python, CUDA, Linux, distributed systems, and GPU infrastructure",
        fingerprint=lean.fingerprint,
    )

    deduped = hub._dedupe([lean, rich])

    assert len(deduped) == 1
    assert deduped[0].provider == "workday_careers"


def test_normalize_rejects_non_job_placeholder_urls():
    listing = normalize_job_item(
        {
            "title": "Software Engineer",
            "company_name": "NVIDIA",
            "location": "India",
            "apply_link": "not-a-url",
            "raw_description": "Python role",
        },
        provider="workday_careers",
    )

    assert listing.apply_url == ""
