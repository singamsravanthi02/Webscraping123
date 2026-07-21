import logging
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
import app.db.base

from app.core.security import get_password_hash
from app.domain.users.models import User, UserRole
from app.domain.jobs.models import Job, JobSource, JobStatus
from app.domain.assessments.models import Assessment, QuestionBank, AssessmentQuestionMap, AssessmentType, QuestionType, AssessmentAttempt, AttemptStatus, AttemptDetail
from app.domain.interviews.models import InterviewSession, InterviewType, InterviewStatus, InterviewResult
from app.domain.learning.models import LearningSession, LearningResource, ResourceType
from app.domain.notifications.models import NotificationLog, NotificationChannel, NotificationStatus

logger = logging.getLogger(__name__)

def run_expansion():
    db = SessionLocal()
    try:
        logger.info("Expanding DB...")
        # Add 30 more students
        colleges = ["JNTUH", "Osmania University", "CBIT", "VNR VJIET", "MGIT"]
        departments = ["Computer Science", "Information Technology", "Electronics"]
        branches = ["CSE", "IT", "ECE"]
        career_goals = ["Software Engineer", "Data Scientist", "Product Manager", "Cloud Architect", "Frontend Developer"]
        
        current_students = db.query(User).filter(User.role == UserRole.STUDENT).count()
        new_students = []
        for i in range(current_students + 1, current_students + 31):
            student_email = f"student_ext_{i}@spip.com"
            if not db.query(User).filter(User.email == student_email).first():
                student = User(
                    full_name=f"Demo Student {i}",
                    email=student_email,
                    phone=f"9876543{i:03d}",
                    password_hash=get_password_hash("Student@123"),
                    role=UserRole.STUDENT,
                    college=random.choice(colleges),
                    department=random.choice(departments),
                    branch=random.choice(branches),
                    semester=random.randint(1, 8),
                    cgpa=round(random.uniform(5.5, 9.8), 2),
                    skills=["Python", "Java", "React", "SQL", "Machine Learning", "C++", "AWS"][:random.randint(2, 6)],
                    career_goal=random.choice(career_goals),
                    is_verified=True,
                    is_active=True,
                    profile_completed=True
                )
                db.add(student)
                new_students.append(student)
        db.commit()
        logger.info("Added %s new students", len(new_students))
        
        # Add 10 more Jobs
        companies = ["Accenture", "Wipro", "Capgemini", "Cognizant", "Deloitte", "Oracle", "IBM"]
        titles = ["Software Engineer", "Data Analyst", "Cloud Engineer", "System Administrator", "Backend Developer"]
        new_jobs = []
        for i in range(10):
            job = Job(
                title=f"{random.choice(titles)} - Level {i}",
                company=random.choice(companies),
                location=random.choice(["Hyderabad", "Bangalore", "Chennai", "Pune", "Remote"]),
                salary_range=f"₹{random.randint(4, 15)}L - ₹{random.randint(16, 25)}L",
                experience_required="Fresher" if i % 2 == 0 else "1-3 Years",
                raw_description="A great opportunity to work in a fast-paced environment.",
                apply_link="https://careers.example.com",
                source=JobSource.MANUAL,
                extracted_skills=["Python", "SQL"] if i % 2 == 0 else ["Java", "Spring"],
                eligibility="B.Tech",
                deadline=datetime.now() + timedelta(days=random.randint(5, 60)),
                ai_summary="Excellent role for growth.",
                status=JobStatus.ACTIVE
            )
            db.add(job)
            new_jobs.append(job)
        db.commit()
        logger.info("Added 10 new jobs")

        all_students = db.query(User).filter(User.role == UserRole.STUDENT).all()
        # Ensure notifications are populated for all students to simulate activity
        for student in all_students:
            for _ in range(3):
                notification = NotificationLog(
                    user_id=student.id,
                    template_name="system_alert",
                    channel=NotificationChannel.EMAIL,
                    status=NotificationStatus.SENT,
                    context_data={"message": "Please review your dashboard for new updates."},
                    created_at=datetime.now() - timedelta(hours=random.randint(1, 100))
                )
                db.add(notification)
        db.commit()
        logger.info("Expanded notifications")

    except Exception as e:
        logger.error("Error expanding db: %s", e)
    finally:
        db.close()

if __name__ == "__main__":
    run_expansion()
