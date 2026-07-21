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

def seed_users(db: Session):
    logger.info("Seeding Users...")
    users_seeded = 0
    
    # 1 Super Admin
    admin_email = "admin@spip.com"
    if not db.query(User).filter(User.email == admin_email).first():
        admin = User(
            full_name="System Admin",
            email=admin_email,
            password_hash=get_password_hash("Admin@123"),
            role=UserRole.ADMIN,
            is_verified=True,
            is_active=True,
            profile_completed=True
        )
        db.add(admin)
        users_seeded += 1
        
    # 5 Faculty
    for i in range(1, 6):
        faculty_email = f"faculty{i}@spip.com"
        if not db.query(User).filter(User.email == faculty_email).first():
            faculty = User(
                full_name=f"Faculty {i}",
                email=faculty_email,
                password_hash=get_password_hash("Faculty@123"),
                role=UserRole.FACULTY,
                is_verified=True,
                is_active=True,
                department="Computer Science",
                profile_completed=True
            )
            db.add(faculty)
            users_seeded += 1
            
    # 30 Students
    colleges = ["JNTUH", "Osmania University", "CBIT", "VNR VJIET", "MGIT"]
    departments = ["Computer Science", "Information Technology", "Electronics"]
    branches = ["CSE", "IT", "ECE"]
    career_goals = ["Software Engineer", "Data Scientist", "Product Manager", "Cloud Architect", "Frontend Developer"]
    
    existing_students = db.query(User).filter(User.role == UserRole.STUDENT).count()
    if existing_students < 30:
        for i in range(existing_students + 1, 31):
            student_email = f"student{i}@spip.com"
            if not db.query(User).filter(User.email == student_email).first():
                student = User(
                    full_name=f"Student {i}",
                    email=student_email,
                    phone=f"98765432{i:02d}",
                    password_hash=get_password_hash("Student@123"),
                    role=UserRole.STUDENT,
                    college=random.choice(colleges),
                    department=random.choice(departments),
                    branch=random.choice(branches),
                    semester=random.randint(1, 8),
                    cgpa=round(random.uniform(6.5, 9.8), 2),
                    skills=["Python", "Java", "React", "SQL", "Machine Learning", "C++", "AWS"][:random.randint(2, 6)],
                    career_goal=random.choice(career_goals),
                    github_url=f"https://github.com/student{i}",
                    linkedin_url=f"https://linkedin.com/in/student{i}",
                    portfolio_url=f"https://student{i}.dev",
                    resume_url=f"https://s3.amazonaws.com/spip/resumes/student{i}.pdf",
                    is_verified=True,
                    is_active=True,
                    profile_completed=True
                )
                db.add(student)
                users_seeded += 1
                
    db.commit()
    logger.info("Users Seeded: %s", users_seeded)
    return db.query(User).filter(User.role == UserRole.STUDENT).all()

def seed_jobs(db: Session):
    logger.info("Seeding Jobs...")
    existing = db.query(Job).count()
    if existing >= 100:
        logger.info("Jobs already seeded.")
        return db.query(Job).all()
        
    companies = ["Google", "Microsoft", "Amazon", "TCS", "Infosys", "Wipro", "Cognizant", "Accenture", "IBM", "Oracle"]
    titles = ["Software Engineer", "Frontend Developer", "Backend Engineer", "Data Scientist", "Full Stack Developer", "Cloud Architect"]
    locations = ["Hyderabad, India", "Bengaluru, India", "Remote", "Pune, India", "Chennai, India"]
    
    jobs = []
    for i in range(existing, 100):
        job = Job(
            title=random.choice(titles) + f" {i}",
            company=random.choice(companies),
            location=random.choice(locations),
            salary_range=f"₹{random.randint(5, 20)}L - ₹{random.randint(21, 50)}L",
            experience_required=random.choice(["Fresher", "0-2 Years", "2+ Years", "1-3 Years"]),
            raw_description="Work on scalable systems.",
            apply_link="https://careers.example.com",
            source=JobSource.MANUAL,
            extracted_skills=["Python", "C++", "System Design", "React", "Java", "AWS"][:random.randint(2, 5)],
            eligibility="B.Tech/BE in CS",
            deadline=datetime.now() + timedelta(days=random.randint(10, 60)),
            ai_summary="Great software engineering role.",
            status=JobStatus.ACTIVE
        )
        db.add(job)
        jobs.append(job)
    db.commit()
    logger.info("Jobs Seeded.")
    return jobs

def seed_assessments(db: Session):
    logger.info("Seeding Assessments...")
    existing = db.query(Assessment).count()
    if existing >= 25:
        logger.info("Assessments already seeded.")
        return db.query(Assessment).all()
        
    for i in range(existing, 25):
        a = Assessment(
            title=f"Assessment Mock {i}",
            type=random.choice(list(AssessmentType)),
            duration_minutes=random.choice([30, 45, 60, 90]),
            is_proctored=random.choice([True, False]),
            total_marks=random.choice([10.0, 20.0, 50.0])
        )
        db.add(a)
    db.commit()
    logger.info("Assessments Seeded.")
    return db.query(Assessment).all()

def seed_notifications(db: Session, students):
    logger.info("Seeding Notifications...")
    templates = ["welcome", "assessment_reminder", "job_recommendation", "interview_reminder"]
    for student in students:
        existing = db.query(NotificationLog).filter(NotificationLog.user_id == student.id).count()
        if existing < 3:
            for _ in range(3 - existing):
                notification = NotificationLog(
                    user_id=student.id,
                    template_name=random.choice(templates),
                    channel=NotificationChannel.EMAIL,
                    status=NotificationStatus.SENT if random.choice([True, False]) else NotificationStatus.PENDING,
                    context_data={"message": f"Hello {student.full_name}, this is a test notification."},
                    created_at=datetime.now() - timedelta(days=random.randint(0, 10))
                )
                db.add(notification)
    db.commit()
    logger.info("Notifications Seeded.")

def seed_learning_and_interviews(db: Session, students):
    logger.info("Seeding Learning & Interviews...")
    for student in students:
        if db.query(LearningSession).filter(LearningSession.user_id == student.id).count() == 0:
            ls = LearningSession(
                user_id=student.id,
                title=f"Learning DS for {student.full_name}",
                subject="Data Structures",
                is_active=True
            )
            db.add(ls)
            
            lr = LearningResource(
                title=f"Notes for {student.full_name}",
                type=ResourceType.PDF,
                uploaded_by=student.id,
                file_path=f"s3://spip/resources/{student.id}.pdf",
                is_processed=True
            )
            db.add(lr)

        if db.query(InterviewSession).filter(InterviewSession.user_id == student.id).count() == 0:
            interview = InterviewSession(
                user_id=student.id,
                title=f"Mock Tech Interview for {student.full_name}",
                type=InterviewType.TECHNICAL,
                status=InterviewStatus.COMPLETED,
                start_time=datetime.now() - timedelta(days=random.randint(1, 5)),
                end_time=datetime.now() - timedelta(days=random.randint(1, 5)) + timedelta(hours=1)
            )
            db.add(interview)
            db.flush()
            
            result = InterviewResult(
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
                learning_plan="Read OS book.",
                placement_readiness_contribution=round(random.uniform(10, 25), 1)
            )
            db.add(result)
            
    db.commit()
    logger.info("Learning & Interviews Seeded.")

def seed_assessment_attempts(db: Session, students, assessments):
    logger.info("Seeding Assessment Attempts...")
    for student in students:
        if db.query(AssessmentAttempt).filter(AssessmentAttempt.user_id == student.id).count() == 0:
            for assessment in random.sample(assessments, k=min(2, len(assessments))):
                attempt = AssessmentAttempt(
                    user_id=student.id,
                    assessment_id=assessment.id,
                    status=AttemptStatus.SUBMITTED,
                    start_time=datetime.now() - timedelta(days=random.randint(1, 10)),
                    end_time=datetime.now() - timedelta(days=random.randint(1, 10)) + timedelta(hours=1),
                    score=round(random.uniform(1.0, assessment.total_marks), 1)
                )
                db.add(attempt)
    db.commit()
    logger.info("Assessment Attempts Seeded.")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        logger.info("Starting comprehensive database seeding...")
        students = seed_users(db)
        jobs = seed_jobs(db)
        assessments = seed_assessments(db)
        
        if students:
            seed_notifications(db, students)
            seed_learning_and_interviews(db, students)
            seed_assessment_attempts(db, students, assessments)
            
        logger.info("Database seeding entirely completed.")
    except Exception as e:
        logger.error("Error seeding database: %s", e)
    finally:
        db.close()
