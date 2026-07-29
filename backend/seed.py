import logging
import random
from datetime import datetime, timedelta

import app.db.base
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.domain.assessments.models import Assessment, AssessmentAttempt, AssessmentType, AttemptStatus
from app.domain.interviews.models import InterviewResult, InterviewSession, InterviewStatus, InterviewType
from app.domain.jobs.models import Job, JobStatus
from app.domain.learning.models import LearningResource, LearningSession, ResourceType
from app.domain.notifications.models import NotificationChannel, NotificationLog, NotificationStatus
from app.domain.users.models import User, UserRole

logger = logging.getLogger(__name__)


def seed_users(db: Session):
    logger.info("Seeding users...")
    users_seeded = 0

    if not db.query(User).filter(User.email == "admin@spip.com").first():
        db.add(
            User(
                full_name="System Admin",
                email="admin@spip.com",
                password_hash=get_password_hash("Admin@123"),
                role=UserRole.ADMIN,
                is_verified=True,
                is_active=True,
                profile_completed=True,
            )
        )
        users_seeded += 1

    for i in range(1, 6):
        email = f"faculty{i}@spip.com"
        if not db.query(User).filter(User.email == email).first():
            db.add(
                User(
                    full_name=f"Faculty {i}",
                    email=email,
                    password_hash=get_password_hash("Faculty@123"),
                    role=UserRole.FACULTY,
                    is_verified=True,
                    is_active=True,
                    department="Computer Science",
                    profile_completed=True,
                )
            )
            users_seeded += 1

    colleges = ["JNTUH", "Osmania University", "CBIT", "VNR VJIET", "MGIT"]
    departments = ["Computer Science", "Information Technology", "Electronics"]
    branches = ["CSE", "IT", "ECE"]
    career_goals = ["Software Engineer", "Data Scientist", "Product Manager", "Cloud Architect", "Frontend Developer"]

    existing_students = db.query(User).filter(User.role == UserRole.STUDENT).count()
    if existing_students < 30:
        for i in range(existing_students + 1, 31):
            email = f"student{i}@spip.com"
            if db.query(User).filter(User.email == email).first():
                continue
            db.add(
                User(
                    full_name=f"Student {i}",
                    email=email,
                    phone=f"98765432{i:02d}",
                    password_hash=get_password_hash("Student@123"),
                    role=UserRole.STUDENT,
                    college=random.choice(colleges),
                    department=random.choice(departments),
                    branch=random.choice(branches),
                    semester=random.randint(1, 8),
                    cgpa=round(random.uniform(6.5, 9.8), 2),
                    skills=["Python", "Java", "React", "SQL", "Machine Learning", "C++", "AWS"][: random.randint(2, 6)],
                    career_goal=random.choice(career_goals),
                    github_url=f"https://github.com/student{i}",
                    linkedin_url=f"https://linkedin.com/in/student{i}",
                    portfolio_url=f"https://student{i}.dev",
                    resume_url=f"https://storage.example.invalid/spip/resumes/student{i}.pdf",
                    is_verified=True,
                    is_active=True,
                    profile_completed=True,
                )
            )
            users_seeded += 1

    db.commit()
    logger.info("Users seeded: %s", users_seeded)
    return db.query(User).filter(User.role == UserRole.STUDENT).all()


def seed_jobs(db: Session):
    logger.info("Skipping job seeding; Job Discovery populates live provider data on first refresh/search.")
    return db.query(Job).filter(Job.status == JobStatus.ACTIVE).all()


def seed_assessments(db: Session):
    logger.info("Seeding assessments...")
    existing = db.query(Assessment).count()
    if existing >= 25:
        return db.query(Assessment).all()

    for i in range(existing, 25):
        db.add(
            Assessment(
                title=f"Assessment {i}",
                type=random.choice(list(AssessmentType)),
                duration_minutes=random.choice([30, 45, 60, 90]),
                is_proctored=random.choice([True, False]),
                total_marks=random.choice([10.0, 20.0, 50.0]),
            )
        )
    db.commit()
    return db.query(Assessment).all()


def seed_notifications(db: Session, students):
    templates = ["welcome", "assessment_reminder", "job_recommendation", "interview_reminder"]
    for student in students:
        existing = db.query(NotificationLog).filter(NotificationLog.user_id == student.id).count()
        for _ in range(max(0, 3 - existing)):
            db.add(
                NotificationLog(
                    user_id=student.id,
                    template_name=random.choice(templates),
                    channel=NotificationChannel.EMAIL,
                    status=random.choice([NotificationStatus.SENT, NotificationStatus.PENDING]),
                    context_data={"message": f"Hello {student.full_name}, please review your dashboard."},
                    created_at=datetime.now() - timedelta(days=random.randint(0, 10)),
                )
            )
    db.commit()


def seed_learning_and_interviews(db: Session, students):
    for student in students:
        if db.query(LearningSession).filter(LearningSession.user_id == student.id).count() == 0:
            db.add(LearningSession(user_id=student.id, title=f"Learning DS for {student.full_name}", subject="Data Structures", is_active=True))
            db.add(
                LearningResource(
                    title=f"Notes for {student.full_name}",
                    type=ResourceType.PDF,
                    uploaded_by=student.id,
                    file_path=f"seed://resources/{student.id}.pdf",
                    is_processed=True,
                )
            )

        if db.query(InterviewSession).filter(InterviewSession.user_id == student.id).count() == 0:
            interview = InterviewSession(
                user_id=student.id,
                title=f"Technical Interview for {student.full_name}",
                type=InterviewType.TECHNICAL,
                status=InterviewStatus.COMPLETED,
                start_time=datetime.now() - timedelta(days=random.randint(1, 5)),
                end_time=datetime.now() - timedelta(days=random.randint(1, 5)) + timedelta(hours=1),
            )
            db.add(interview)
            db.flush()
            db.add(
                InterviewResult(
                    interview_id=interview.id,
                    confidence_score=round(random.uniform(6.0, 9.5), 1),
                    communication_score=round(random.uniform(6.0, 9.5), 1),
                    technical_score=round(random.uniform(6.0, 9.5), 1),
                    problem_solving_score=round(random.uniform(6.0, 9.5), 1),
                    overall_grade=round(random.uniform(6.0, 9.5), 1),
                    feedback_summary="Good performance.",
                    strengths=["Data Structures"],
                    weaknesses=["Networking"],
                    recommended_topics=["TCP/IP"],
                    learning_plan="Review OS and networking fundamentals.",
                    placement_readiness_contribution=round(random.uniform(10, 25), 1),
                )
            )
    db.commit()


def seed_assessment_attempts(db: Session, students, assessments):
    for student in students:
        if db.query(AssessmentAttempt).filter(AssessmentAttempt.user_id == student.id).count() == 0:
            for assessment in random.sample(assessments, k=min(2, len(assessments))):
                db.add(
                    AssessmentAttempt(
                        user_id=student.id,
                        assessment_id=assessment.id,
                        status=AttemptStatus.SUBMITTED,
                        start_time=datetime.now() - timedelta(days=random.randint(1, 10)),
                        end_time=datetime.now() - timedelta(days=random.randint(1, 10)) + timedelta(hours=1),
                        score=round(random.uniform(1.0, assessment.total_marks), 1),
                    )
                )
    db.commit()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        logging.basicConfig(level=logging.INFO)
        students = seed_users(db)
        seed_jobs(db)
        assessments = seed_assessments(db)
        if students:
            seed_notifications(db, students)
            seed_learning_and_interviews(db, students)
            seed_assessment_attempts(db, students, assessments)
        logger.info("Database seeding completed.")
    except Exception as exc:
        logger.error("Error seeding database: %s", exc)
    finally:
        db.close()
