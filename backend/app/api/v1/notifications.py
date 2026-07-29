from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.api.dependencies.auth import get_current_active_user, get_current_active_superuser
from app.domain.users.models import User
from app.domain.notifications import schemas, models
from app.domain.notifications.services import NotificationService

router = APIRouter()


@router.get("/me", response_model=List[schemas.NotificationInboxResponse])
def get_my_notifications(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(models.NotificationLog).filter(models.NotificationLog.user_id == current_user.id)
    if unread_only:
        query = query.filter(models.NotificationLog.is_read.is_(False))
    return query.order_by(models.NotificationLog.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/me/{notification_id}/read", response_model=dict)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    notification = (
        db.query(models.NotificationLog)
        .filter(models.NotificationLog.id == notification_id, models.NotificationLog.user_id == current_user.id)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.commit()
    return {"message": "Notification marked as read"}


@router.post("/me/read-all", response_model=dict)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    db.query(models.NotificationLog).filter(
        models.NotificationLog.user_id == current_user.id,
        models.NotificationLog.is_read.is_(False),
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}


@router.delete("/me/{notification_id}", response_model=dict)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    notification = (
        db.query(models.NotificationLog)
        .filter(models.NotificationLog.id == notification_id, models.NotificationLog.user_id == current_user.id)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(notification)
    db.commit()
    return {"message": "Notification deleted"}

@router.get("/logs", response_model=List[schemas.NotificationLogResponse])
def get_notification_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """
    Admin only: Get all notification logs to monitor queue and delivery status.
    """
    logs = db.query(models.NotificationLog).order_by(models.NotificationLog.created_at.desc()).offset(skip).limit(limit).all()
    return logs

@router.post("/broadcast")
def send_admin_broadcast(
    request: schemas.BroadcastRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """
    Admin only: Send a broadcast message via Email, SMS, or Push.
    """
    service = NotificationService(db)
    count = service.broadcast_message(
        admin_id=current_user.id,
        subject=request.subject,
        message=request.message,
        channel=request.channel,
        user_ids=request.user_ids
    )
    return {"status": "success", "messages_queued": count}

@router.get("/templates", response_model=List[schemas.NotificationTemplateResponse])
def get_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """
    Admin only: Get notification templates.
    """
    templates = db.query(models.NotificationTemplate).all()
    return templates
