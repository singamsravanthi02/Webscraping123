import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from app.db.session import SessionLocal
from app.domain.users.models import User, UserRole
from app.domain.jobs.models import Job
from app.domain.job_discovery.models import StudentSearchProfile
from app.core.security import get_password_hash

def seed_test_data():
    db = SessionLocal()
    try:
        # Create a test student
        test_email = "job_test@example.com"
        user = db.query(User).filter(User.email == test_email).first()
        if not user:
            print("Creating test user...")
            user = User(
                full_name="Job Test Student",
                email=test_email,
                password_hash=get_password_hash("password123"),
                role=UserRole.STUDENT,
                college="Test Institute",
                department="Computer Science",
                branch="B.Tech",
                cgpa=8.5,
                skills=["Python", "React", "SQL", "FastAPI"],
                career_goal="Full Stack Developer",
                is_active=True,
                profile_completed=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            print("Test user already exists. Updating...")
            user.skills = ["Python", "React", "SQL", "FastAPI"]
            user.career_goal = "Full Stack Developer"
            db.commit()

        # Create or update StudentSearchProfile
        profile = db.query(StudentSearchProfile).filter(StudentSearchProfile.user_id == user.id).first()
        if not profile:
            print("Creating test student search profile...")
            profile = StudentSearchProfile(
                user_id=user.id,
                preferred_roles=["Full Stack Developer", "Backend Developer", "Frontend Developer"],
                preferred_locations=["Remote", "Hyderabad", "Bengaluru"],
                keywords=["Python", "React", "SQL", "FastAPI", "Full Stack Developer", "Backend Developer", "Frontend Developer"],
                resume_keywords=["Python", "React", "SQL", "FastAPI", "Job Test Student", "Full Stack Developer"],
                interview_scores={"confidence_score": 8, "communication_score": 7, "technical_score": 9, "problem_solving_score": 8, "overall_grade": 8},
                learning_progress={"sessions": 5, "messages": 120},
                search_context={"education": "B.Tech Computer Science at Test Institute", "role": "student", "profile_completed": True},
                cgpa=8.5,
                career_goal="Full Stack Developer"
            )
            db.add(profile)
            db.commit()
        else:
            print("Test profile already exists. Updating...")
            profile.interview_scores = {"confidence_score": 8, "communication_score": 7, "technical_score": 9, "problem_solving_score": 8, "overall_grade": 8}
            profile.learning_progress = {"sessions": 5, "messages": 120}
            db.commit()

        print(f"Seed complete. Use '{test_email}' and 'password123' to test.")

    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_test_data()
