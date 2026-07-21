from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from .models import NotificationChannel, NotificationStatus

class NotificationTemplateBase(BaseModel):
    name: str
    channel: NotificationChannel
    subject_template: Optional[str] = None
    body_template: str
    is_active: bool = True

class NotificationTemplateCreate(NotificationTemplateBase):
    ...

class NotificationTemplateResponse(NotificationTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime

class NotificationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    template_name: str
    channel: NotificationChannel
    status: NotificationStatus
    error_message: Optional[str] = None
    created_at: datetime
    sent_at: Optional[datetime] = None

class BroadcastRequest(BaseModel):
    subject: str
    message: str
    channel: NotificationChannel
    user_ids: Optional[List[int]] = None # If None, broadcast to all users
