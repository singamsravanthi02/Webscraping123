from .celery_app import celery_app
import logging
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.domain.notifications.models import NotificationLog, NotificationStatus

logger = logging.getLogger(__name__)

# Basic celery task setup with retries
@celery_app.task(name="app.worker.tasks.dispatch_notification_task", bind=True, max_retries=3, default_retry_delay=30)
def dispatch_notification_task(self, log_id: int):
    """
    Worker task to actually process and send the notification via the correct channel.
    Uses robust retries (up to 3 times, with 30s delay).
    """
    db: Session = SessionLocal()
    try:
        log = db.query(NotificationLog).filter(NotificationLog.id == log_id).first()
        if not log:
            logger.error(f"Notification log {log_id} not found.")
            return

        # Mark as processing
        log.status = NotificationStatus.PROCESSING
        db.commit()

        # Simulate network latency and sending logic based on channel
        logger.info(f"Preparing to send {log.channel} to User ID {log.user_id} using template '{log.template_name}'")
        time.sleep(1) # Simulate delay
        
        # In a real app, this is where we call Twilio/SendGrid/FCM SDKs
        # For SMS: client.messages.create(to=user.phone, from_=our_phone, body=rendered_body)
        # Best-effort dispatch; retries and failure handling happen in the notification service.
        success = True 
        
        if success:
            log.status = NotificationStatus.SENT
            log.sent_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Successfully sent {log.channel} to User ID {log.user_id}")
            return True
        else:
            raise Exception("Simulated network failure")
            
    except Exception as exc:
        logger.error(f"Failed to send notification {log_id}: {str(exc)}")
        db.rollback()
        try:
            # Mark as failed in DB if we maxed out retries
            if self.request.retries >= self.max_retries:
                db_log = db.query(NotificationLog).filter(NotificationLog.id == log_id).first()
                if db_log:
                    db_log.status = NotificationStatus.FAILED
                    db_log.error_message = str(exc)
                    db.commit()
            
            # Retry
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for notification {log_id}")
    finally:
        db.close()

@celery_app.task(name="app.worker.tasks.send_email")
def send_email_task(email_address: str, template: str, context: dict):
    from app.services.email_service import email_service

    payload = context or {}
    logger.info("Sending %s email to %s", template, email_address)

    if template in {"welcome", "send_welcome_email"}:
        email_service.send_welcome_email(email_address, payload.get("full_name", "there"))
        return True
    if template in {"password_reset", "reset_password", "send_password_reset_email"}:
        token = payload.get("reset_token") or payload.get("otp") or payload.get("token")
        if token:
            email_service.send_password_reset_email(email_address, str(token))
            return True
    if template in {"otp", "verification", "send_otp_email"}:
        otp = payload.get("otp") or payload.get("token")
        if otp:
            email_service.send_otp_email(email_address, str(otp))
            return True

    logger.warning("Unsupported email template %s for %s", template, email_address)
    return False

@celery_app.task(name="app.worker.tasks.generate_embeddings")
def generate_embeddings_task(resource_id: str, resource_type: str):
    from app.db.session import SessionLocal
    from app.domain.ai_orchestration.gateway import gateway
    from app.domain.jobs.models import Job
    from app.worker.ai_pipeline import AIPipeline

    logger.info("Generating embeddings for %s %s", resource_type, resource_id)

    if resource_type.lower() != "job":
        logger.warning("Embedding task only supports job resources for now: %s", resource_type)
        return False

    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == int(resource_id)).first()
        if not job:
            logger.warning("Job %s not found for embedding generation", resource_id)
            return False

        text = " ".join(part for part in [job.title, job.company, job.location or "", job.raw_description or ""] if part).strip()
        if not text:
            logger.warning("Job %s has no text to embed", resource_id)
            return False

        embedding = gateway.embed_text(text, feature="job_embedding")
        pipeline = AIPipeline()
        metadata = {
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "source": getattr(job.source, "value", job.source),
        }
        pipeline.upsert_to_qdrant(job.id, embedding, metadata)
        return True
    except Exception as exc:
        logger.error("Failed to generate embeddings for %s %s: %s", resource_type, resource_id, exc)
        return False
    finally:
        db.close()

@celery_app.task(name="app.worker.tasks.process_knowledge_document")
def process_knowledge_document(document_id: int, file_path: str):
    """
    Parses an uploaded document, chunks it, generates local embeddings, 
    stores in Qdrant, and flags for Question Generation.
    """
    from app.domain.knowledge.models import Document, DocumentStatus, DocumentChunk
    from app.worker.ai_pipeline import AIPipeline
    import os
    import uuid
    
    logger.info(f"Processing knowledge document ID: {document_id}")
    db: Session = SessionLocal()
    pipeline = AIPipeline()
    
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return
            
        doc.status = DocumentStatus.PROCESSING
        db.commit()
        
        from app.services.document_text_extractor import extract_document_text

        raw_text = extract_document_text(file_path)
        ext = file_path.split('.')[-1].lower()
        if not raw_text.strip():
            raise ValueError(f"No text could be extracted from {file_path}")
                        
        # 2 & 3. Generate Embeddings & Store in Qdrant (Centralized)
        from app.domain.learning.services.qdrant_service import ingest_document, chunk_text
        
        chunks = chunk_text(raw_text)
        
        # This uses Gemini text-embedding-004 and stores in learning_materials
        ingest_document(
            document_id=doc.id,
            title=doc.title,
            text_content=raw_text,
            source_type=ext,
            subject=doc.subject,
            unit=doc.unit,
            semester=doc.semester
        )
        
        # Store metadata in PostgreSQL
        for idx, text_chunk in enumerate(chunks):
            db_chunk = DocumentChunk(
                id=f"{doc.id}{idx:04d}",
                document_id=doc.id,
                chunk_index=idx,
                char_count=len(text_chunk)
            )
            db.add(db_chunk)
            
        doc.status = DocumentStatus.COMPLETED
        db.commit()
        
        # Cleanup temp file
        if os.path.exists(file_path):
            os.remove(file_path)
            
        logger.info(f"Successfully processed document {document_id} into {len(chunks)} chunks.")
        
        # 4. Trigger Question/Content Generation
        generate_ai_content_for_document.delay(document_id)
        
    except Exception as e:
        logger.error(f"Failed to process document {document_id}: {e}")
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            db.commit()
    finally:
        db.close()

@celery_app.task(name="app.worker.tasks.generate_ai_content_for_document")
def generate_ai_content_for_document(document_id: int):
    """
    Takes a processed document and generates Questions and Learning Resources via AI Agents.
    """
    from app.domain.knowledge.models import Document, GeneratedResource, LearningResourceType
    from app.domain.assessments.models import QuestionBank, QuestionType
    from app.domain.ai_orchestration.agents.content import QuestionGenerationAgent, ContentGenerationAgent
    
    logger.info(f"Generating AI content for document ID: {document_id}")
    db: Session = SessionLocal()
    
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc or not doc.chunks:
            return
            
        from app.domain.learning.services.qdrant_service import get_document_text
        doc_text = get_document_text(document_id)
        if not doc_text:
            logger.error("No text retrieved from Qdrant for document")
            return
            
        # Keep the context compact so structured output stays reliable.
        sample_text = doc_text[:12000]
        context_text = f"Document Title: {doc.title}\nSource: {doc.source}\nSubject: {doc.subject}\n\n{sample_text}"
        
        metadata = {
            "title": doc.title,
            "department": doc.department,
            "subject": doc.subject,
            "unit": doc.unit
        }
        
        # We need a system user ID for orchestration logging, usually ID 1 (Admin)
        admin_user_id = 1 
        
        q_agent = QuestionGenerationAgent()
        c_agent = ContentGenerationAgent()
        
        # 1. Generate Questions
        questions_data = q_agent.generate_questions(admin_user_id, context_text, metadata)
        for qd in questions_data:
            q_type = QuestionType.MCQ if qd.get("type") == "mcq" else QuestionType.SUBJECTIVE
            question = QuestionBank(
                topic=qd.get("topic", doc.title),
                subject=qd.get("subject", doc.subject),
                difficulty=qd.get("difficulty", 5),
                type=q_type,
                content=qd.get("content", ""),
                options=qd.get("options"),
                correct_answer=qd.get("correct_answer"),
                detailed_explanation=qd.get("detailed_explanation"),
                hints=qd.get("hints", []),
                common_mistakes=qd.get("common_mistakes", []),
                company_tags=qd.get("company_tags", []),
                bloom_level=qd.get("bloom_level"),
                placement_relevance=qd.get("placement_relevance"),
                interview_difficulty=qd.get("interview_difficulty"),
                company_difficulty=qd.get("company_difficulty"),
                estimated_time=qd.get("estimated_time"),
                marks=qd.get("marks", 1.0),
                points=qd.get("marks", 1.0)
            )
            db.add(question)
            
        # 2. Generate Resources
        resources_data = c_agent.generate_learning_resources(admin_user_id, context_text, metadata)
        
        if "flashcards" in resources_data:
            db.add(GeneratedResource(
                document_id=doc.id,
                resource_type=LearningResourceType.FLASHCARD,
                content=resources_data["flashcards"],
                topic=doc.title
            ))
            
        if "revision_notes" in resources_data:
            db.add(GeneratedResource(
                document_id=doc.id,
                resource_type=LearningResourceType.REVISION_NOTE,
                content={"markdown": resources_data["revision_notes"]},
                topic=doc.title
            ))
            
        if "cheat_sheet" in resources_data:
            db.add(GeneratedResource(
                document_id=doc.id,
                resource_type=LearningResourceType.CHEAT_SHEET,
                content={"markdown": resources_data["cheat_sheet"]},
                topic=doc.title
            ))
            
        db.commit()
        logger.info(f"Successfully generated AI content for document {document_id}")
        
    except Exception as e:
        logger.error(f"Failed to generate AI content for document {document_id}: {e}")
        db.rollback()
    finally:
        db.close()

@celery_app.task(name="app.worker.tasks.parse_resume")
def parse_resume_task(user_id: str, resume_url: str):
    from app.domain.ai_orchestration.agents.resume import ResumeAgent
    from app.domain.ai_orchestration.agents.jobs import JobMatchingAgent
    from app.domain.ai_orchestration.placement_engine import placement_engine
    from app.domain.ai_orchestration.models import StudentAIMemory
    from app.domain.users.models import User
    from app.domain.jobs.models import Job
    import os
    
    logger.info(f"Parsing resume for user {user_id}")
    db: Session = SessionLocal()
    
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            return
            
        # Get local file path from url (url starts with /uploads)
        file_path = f".{resume_url}"
        if not os.path.exists(file_path):
            logger.error(f"Resume file not found: {file_path}")
            return
            
        from app.services.document_text_extractor import extract_document_text

        raw_text = extract_document_text(file_path)
        if not raw_text.strip():
            logger.error("No text extracted from resume")
            return
            
        # 1. Resume Agent -> Extract Skills
        agent = ResumeAgent()
        analysis = agent.analyze_resume(user.id, raw_text)
        
        # 2. Store Skills in User
        extracted_skills = list(dict.fromkeys(
            (analysis.get("technical_skills") or [])
            + (analysis.get("soft_skills") or [])
        ))
        if extracted_skills:
            # Merge with existing skills avoiding duplicates
            existing = set(user.skills or [])
            existing.update(extracted_skills)
            user.skills = list(existing)
            db.commit()
            
        # 3. Update Student AI Memory
        memory = db.query(StudentAIMemory).filter(StudentAIMemory.user_id == user.id).first()
        if not memory:
            memory = StudentAIMemory(user_id=user.id)
            db.add(memory)
            
        # Update memory context with resume details
        memory.resume_analysis = analysis
        db.commit()
        
        # 4. Recalculate Placement Readiness
        score = placement_engine.calculate_score(user.id)
        logger.info(f"Updated readiness score for user {user.id}: {score}")
        
        # 5. Trigger Job Matching Agent -> Generate Initial Recommendations
        try:
            jobs = db.query(Job).all()
            job_desc_list = [{"id": j.id, "title": j.title, "skills": j.extracted_skills} for j in jobs]
            
            if job_desc_list:
                matching_agent = JobMatchingAgent()
                profile = f"Email: {user.email}. User ID: {user.id}. Skills: {', '.join(user.skills or [])}. Goal: {user.career_goal}"
                scores = matching_agent.match_jobs(user.id, profile, job_desc_list)
                
                # Just log them for now or create notifications (the aggregate jobs task already creates notifications)
                logger.info(f"Generated {len(scores)} job recommendations for user {user.id}")
        except Exception as job_exc:
            logger.warning("Job matching skipped for user %s after resume parse: %s", user.id, job_exc)
            
    except Exception as e:
        logger.error(f"Error parsing resume for user {user_id}: {e}")
        db.rollback()
    finally:
        db.close()

@celery_app.task(name="app.worker.tasks.daily_recommendation_scheduler")
def daily_recommendation_scheduler():
    """
    Runs every night via celery-beat to update readiness scores and generate adaptive plans.
    """
    from app.domain.users.models import User
    from app.domain.ai_orchestration.placement_engine import placement_engine
    from app.domain.ai_orchestration.agents.career import CareerCoachAgent
    from app.domain.ai_orchestration.models import StudentAIMemory
    
    logger.info("Starting Daily Recommendation Scheduler...")
    db: Session = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        coach = CareerCoachAgent()
        
        for user in users:
            # 1. Update Readiness Score
            score = placement_engine.calculate_score(user.id)
            logger.info(f"Updated readiness score for user {user.id}: {score}")
            
            # 2. Generate Adaptive Plan
            memory = db.query(StudentAIMemory).filter(StudentAIMemory.user_id == user.id).first()
            if memory:
                # Converting ORM object to dict for the prompt
                mem_dict = {
                    "weak_topics": memory.weak_topics,
                    "career_goals": memory.career_goals,
                    "score": score
                }
                # Generate and log plan silently
                coach.generate_weekly_plan(user.id, mem_dict)
                logger.info(f"Generated adaptive plan for user {user.id}")
                
        db.commit()
    except Exception as e:
        logger.error(f"Error in daily scheduler: {e}")
        db.rollback()
    finally:
        db.close()

@celery_app.task(name="app.worker.tasks.aggregate_and_process_jobs_task")
def aggregate_and_process_jobs_task():
    """
    Refresh live job recommendations through the production Job Discovery engine.
    """
    return refresh_ai_job_recommendations_task()


@celery_app.task(name="app.worker.tasks.refresh_ai_job_recommendations_task")
def refresh_ai_job_recommendations_task(user_id: int | None = None):
    """
    Periodically refreshes AI job discovery queries and rankings.
    When user_id is omitted, refreshes all active student users.
    Also cleans up expired queries.
    """
    from app.domain.job_discovery.services import RecommendationEngine
    from app.domain.job_discovery.models import AIJobQuery
    from app.domain.users.models import User, UserRole
    from datetime import datetime, timezone

    db: Session = SessionLocal()
    try:
        # Cleanup expired queries
        deleted = db.query(AIJobQuery).filter(AIJobQuery.expires_at < datetime.now(timezone.utc)).delete()
        if deleted > 0:
            db.commit()
            logger.info("Deleted %s expired AI job queries", deleted)

        query = db.query(User).filter(User.is_active == True)  # noqa: E712
        if user_id:
            query = query.filter(User.id == user_id)
        else:
            query = query.filter(User.role == UserRole.STUDENT)

        users = query.all()
        refreshed = 0
        for user in users:
            try:
                engine = RecommendationEngine(db)
                engine.refresh_recommendations(user)
                refreshed += 1
            except Exception as exc:
                logger.warning("Failed to refresh AI jobs for user %s: %s", user.id, exc)
        logger.info("AI job discovery refresh completed for %s user(s)", refreshed)
        return {"refreshed": refreshed, "deleted_expired_queries": deleted}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.update_dashboard_analytics_task")
def update_dashboard_analytics_task():
    from app.domain.ai_orchestration.models import StudentAIMemory
    from app.domain.jobs.models import Job
    from app.domain.knowledge.models import Document
    from app.domain.notifications.models import NotificationLog, NotificationStatus
    from app.domain.users.models import User

    db: Session = SessionLocal()
    try:
        active_users = db.query(User).filter(User.is_active == True).count()
        job_count = db.query(Job).count()
        document_count = db.query(Document).count()
        pending_notifications = db.query(NotificationLog).filter(NotificationLog.status == NotificationStatus.PENDING).count()
        scores = [
            memory.placement_readiness_score
            for memory in db.query(StudentAIMemory).all()
            if memory.placement_readiness_score is not None
        ]
        average_score = round(sum(scores) / len(scores), 2) if scores else 0.0
        summary = {
            "active_users": active_users,
            "jobs": job_count,
            "documents": document_count,
            "pending_notifications": pending_notifications,
            "average_placement_readiness": average_score,
        }
        logger.info("Dashboard analytics refreshed: %s", summary)
        return summary
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.send_notification_digest_task")
def send_notification_digest_task():
    from datetime import datetime, timedelta, timezone

    from app.domain.notifications.models import NotificationChannel, NotificationLog, NotificationStatus
    from app.domain.users.models import User

    db: Session = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        users = db.query(User).filter(User.is_active == True).all()
        queued = 0
        for user in users:
            recent_count = (
                db.query(NotificationLog)
                .filter(NotificationLog.user_id == user.id, NotificationLog.created_at >= cutoff)
                .count()
            )
            if not recent_count:
                continue

            digest = NotificationLog(
                user_id=user.id,
                template_name="notification_digest",
                channel=NotificationChannel.IN_APP,
                context_data={"recent_notifications": recent_count},
                status=NotificationStatus.PENDING,
            )
            db.add(digest)
            db.flush()
            dispatch_notification_task.delay(digest.id)
            queued += 1

        db.commit()
        logger.info("Queued %s notification digest(s)", queued)
        return {"queued": queued}
    except Exception as exc:
        db.rollback()
        logger.error("Notification digest task failed: %s", exc)
        raise
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.reanalyze_resumes_task")
def reanalyze_resumes_task():
    from app.domain.users.models import User

    db: Session = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True, User.resume_url.isnot(None)).all()
        queued = 0
        for user in users:
            parse_resume_task.delay(str(user.id), user.resume_url)
            queued += 1
        logger.info("Queued resume reanalysis for %s user(s)", queued)
        return {"queued": queued}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.refresh_career_dna_task")
def refresh_career_dna_task():
    from app.domain.ai_orchestration.placement_engine import placement_engine
    from app.domain.users.models import User

    db: Session = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        refreshed = 0
        for user in users:
            placement_engine.calculate_score(user.id)
            refreshed += 1
        logger.info("Career DNA refreshed for %s user(s)", refreshed)
        return {"refreshed": refreshed}
    finally:
        db.close()
