from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ALERT = "ALERT"
    LEAVE = "LEAVE"
    ATTENDANCE = "ATTENDANCE"
    TASK = "TASK"
    PAYROLL = "PAYROLL"
    ANNOUNCEMENT = "ANNOUNCEMENT"
    CHAT = "CHAT"

    @classmethod
    def _missing_(cls, value: object):
        return cls.INFO


class NotificationResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    employee_code: Optional[str] = None
    title: str
    message: str
    notification_type: NotificationType = NotificationType.INFO
    is_read: bool = False
    link: Optional[str] = None
    created_at: datetime
    read_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class AnnouncementResponse(BaseModel):
    id: str
    title: str
    content: str
    priority: str = "NORMAL"  # LOW, NORMAL, HIGH, URGENT
    unit_id: str = "BOTH"     # Unit_1, Unit_2, BOTH
    author_name: str
    author_role: str
    published_at: datetime
    expires_at: Optional[datetime] = None
