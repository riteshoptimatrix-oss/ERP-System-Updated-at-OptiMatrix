from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class AudienceType(str, Enum):
    ALL = "all"
    SPECIFIC = "specific"
    DEPARTMENT = "department"
    ROLE = "role"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_lower = value.strip().lower()
            for member in cls:
                if member.value == val_lower:
                    return member
        return cls.ALL


class AnnouncementPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_upper = value.strip().upper()
            for member in cls:
                if member.value == val_upper:
                    return member
        return cls.NORMAL


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=150, description="Headline of the announcement")
    message: str = Field(..., min_length=5, max_length=5000, description="Full body text of the announcement")
    content: Optional[str] = Field(None, description="Alias for message for backwards compatibility")
    priority: AnnouncementPriority = AnnouncementPriority.NORMAL
    unit_id: str = Field(default="BOTH", description="Unit_1, Unit_2, or BOTH")
    audience_type: AudienceType = AudienceType.ALL
    recipients: List[str] = Field(default_factory=list, description="Targeted recipient IDs, codes, or emails when specific")
    recipient_names: Optional[List[str]] = Field(default_factory=list, description="Human-readable names of targeted recipients")
    expires_at: Optional[datetime] = None


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=150)
    message: Optional[str] = Field(None, min_length=5, max_length=5000)
    content: Optional[str] = None
    priority: Optional[AnnouncementPriority] = None
    unit_id: Optional[str] = None
    audience_type: Optional[AudienceType] = None
    recipients: Optional[List[str]] = None
    recipient_names: Optional[List[str]] = None
    expires_at: Optional[datetime] = None


class AnnouncementResponse(BaseModel):
    id: str
    title: str
    message: str
    content: str
    priority: str = "NORMAL"
    unit_id: str = "BOTH"
    audience_type: str = "all"
    recipients: List[str] = []
    recipient_names: List[str] = []
    author_id: Optional[str] = None
    author_name: str = "Management"
    author_role: str = "SUPER_ADMIN"
    is_read: bool = False
    read_at: Optional[datetime] = None
    read_count: int = 0
    created_at: datetime
    published_at: datetime
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class UnreadCountResponse(BaseModel):
    unread_count: int


class RecipientOption(BaseModel):
    id: str
    code: str
    name: str
    email: str
    department: Optional[str] = "General"
    role: Optional[str] = "EMPLOYEE"
    unit_id: Optional[str] = "BOTH"
