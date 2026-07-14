from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from app.domain.notifications.models import NotificationTemplate, NotificationLog, NotificationChannel, NotificationStatus
from app.domain.users.models import User
from app.worker.tasks import dispatch_notification_task

class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def get_template(self, template_name: str) -> Optional[NotificationTemplate]:
        return self.db.query(NotificationTemplate).filter(NotificationTemplate.name == template_name).first()

    def send_notification(self, user_id: int, template_name: str, channel: NotificationChannel, context_data: Dict[str, Any] = None):
        """
        Creates a notification log entry and queues the task for background processing via Celery.
        """
        # Create a log entry indicating it is pending
        log_entry = NotificationLog(
            user_id=user_id,
            template_name=template_name,
            channel=channel,
            context_data=context_data,
            status=NotificationStatus.PENDING
        )
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)

        # Dispatch Celery Task
        dispatch_notification_task.delay(log_entry.id)
        
        return log_entry

    def broadcast_message(self, admin_id: int, subject: str, message: str, channel: NotificationChannel, user_ids: Optional[List[int]] = None):
        """
        Sends an ad-hoc broadcast message to specific users or all users.
        """
        # If no users specified, broadcast to all active users
        if not user_ids:
            users = self.db.query(User).filter(User.is_active == True).all()
            user_ids = [u.id for u in users]
            
        logs = []
        for uid in user_ids:
            log_entry = NotificationLog(
                user_id=uid,
                template_name="admin_broadcast",
                channel=channel,
                context_data={"subject": subject, "message": message, "sender_admin_id": admin_id},
                status=NotificationStatus.PENDING
            )
            self.db.add(log_entry)
            logs.append(log_entry)
            
        self.db.commit()
        
        # Dispatch tasks
        for log in logs:
            self.db.refresh(log)
            dispatch_notification_task.delay(log.id)
            
        return len(logs)
