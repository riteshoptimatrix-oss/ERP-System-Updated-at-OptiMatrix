from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class SessionDocument(BaseModel):
    token_hash: str = Field(..., description="SHA-256 hash of random session token")
    user_id: str = Field(..., description="ID of authenticated user")
    email: str = Field(..., description="User corporate email")
    role: str = Field(..., description="User role at login time")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(..., description="Absolute session expiry time")
    last_activity_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_revoked: bool = Field(default=False, description="Flag for manual or system session revocation")
    csrf_token: str = Field(..., description="Active CSRF token bound to this session")


class AuditLogDocument(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    action: str = Field(..., description="E.g. AUTH_LOGIN, AUTH_LOGOUT, USER_CREATE, UNIT_ACCESS")
    resource: str = Field(..., description="Target module or document ID")
    unit_id: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="SUCCESS", description="SUCCESS or FAILED")
    details: Dict[str, Any] = Field(default_factory=dict)
