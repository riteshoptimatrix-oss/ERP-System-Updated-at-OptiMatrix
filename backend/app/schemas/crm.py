from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, model_validator
from app.models.user import ManufacturingUnit
from app.schemas.master import AuditBase, PaginatedResponse

class LeadStatus(str, Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUALIFIED = "QUALIFIED"
    PROPOSAL_SENT = "PROPOSAL_SENT"
    NEGOTIATION = "NEGOTIATION"
    CONVERTED = "CONVERTED"
    LOST = "LOST"

class LeadPriority(str, Enum):
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"

class LeadSource(str, Enum):
    DIRECT_INQUIRY = "DIRECT_INQUIRY"
    TRADE_EXPO = "TRADE_EXPO"
    WEBSITE = "WEBSITE"
    REFERRAL = "REFERRAL"
    COLD_CALL = "COLD_CALL"
    EXISTING_CLIENT = "EXISTING_CLIENT"

class ActivityType(str, Enum):
    CALL = "CALL"
    EMAIL = "EMAIL"
    MEETING = "MEETING"
    SITE_VISIT = "SITE_VISIT"
    NOTE = "NOTE"
    STATUS_CHANGE = "STATUS_CHANGE"


# ----------------------------------------------------
# Lead Activity Models
# ----------------------------------------------------
class LeadActivityCreate(BaseModel):
    activity_type: ActivityType
    summary: str = Field(..., min_length=2, max_length=200)
    details: Optional[str] = Field(None, max_length=1000)
    next_follow_up: Optional[datetime] = None

class LeadActivityResponse(LeadActivityCreate):
    id: str
    lead_id: str
    created_at: datetime
    created_by: str


# ----------------------------------------------------
# Lead CRUD Models
# ----------------------------------------------------
class LeadCreate(BaseModel):
    code: Optional[str] = Field(None, description="Optional custom code; auto-generated if omitted")
    company_name: str = Field(..., min_length=2, max_length=150)
    contact_person: str = Field(..., min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: str = Field(..., min_length=5, max_length=25)
    source: LeadSource = Field(default=LeadSource.DIRECT_INQUIRY)
    status: LeadStatus = Field(default=LeadStatus.NEW)
    priority: LeadPriority = Field(default=LeadPriority.WARM)
    assigned_to: Optional[str] = Field(None, max_length=100, description="Assigned sales representative email/badge")
    estimated_value: float = Field(default=0.0, ge=0.0, description="Estimated deal value in INR")
    machine_interest: Optional[str] = Field(None, max_length=200, description="e.g. 500 Ton Hydraulic Press")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.BOTH)
    next_follow_up: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=1000)

class LeadUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=2, max_length=150)
    contact_person: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=5, max_length=25)
    source: Optional[LeadSource] = None
    status: Optional[LeadStatus] = None
    priority: Optional[LeadPriority] = None
    assigned_to: Optional[str] = None
    estimated_value: Optional[float] = Field(None, ge=0.0)
    machine_interest: Optional[str] = Field(None, max_length=200)
    unit_id: Optional[ManufacturingUnit] = None
    next_follow_up: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=1000)

class LeadResponse(BaseModel):
    id: str
    code: str
    company_name: str
    contact_person: str
    email: Optional[str] = None
    phone: str
    source: LeadSource
    status: LeadStatus
    priority: LeadPriority
    assigned_to: Optional[str] = None
    estimated_value: float = 0.0
    machine_interest: Optional[str] = None
    unit_id: ManufacturingUnit
    next_follow_up: Optional[datetime] = None
    notes: Optional[str] = None
    converted_customer_id: Optional[str] = None
    converted_at: Optional[datetime] = None
    created_at: datetime
    created_by: str
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


# ----------------------------------------------------
# Lead Conversion Model
# ----------------------------------------------------
class LeadConvertRequest(BaseModel):
    customer_code: Optional[str] = Field(default=None, max_length=50, description="Optional custom customer code e.g. CUST-101; auto-generated if omitted")
    gstin: Optional[str] = Field(None, max_length=15)
    pan: Optional[str] = Field(None, max_length=10)
    billing_address: Optional[str] = Field(None, max_length=500)
    shipping_address: Optional[str] = Field(None, max_length=500)
    credit_limit: float = Field(default=0.0, ge=0.0)
    payment_terms_days: int = Field(default=30, ge=0)
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.BOTH)

    @model_validator(mode="before")
    @classmethod
    def sanitize_empty_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            for field in ["customer_code", "gstin", "pan", "billing_address", "shipping_address"]:
                if values.get(field) == "":
                    values[field] = None
        return values


# ----------------------------------------------------
# Dashboard Summary Model
# ----------------------------------------------------
class CrmDashboardSummary(BaseModel):
    total_leads: int
    active_leads: int
    hot_leads: int
    converted_leads: int
    conversion_rate_percentage: float
    pipeline_by_status: Dict[str, int]
    follow_ups_due_today: int
    follow_ups_overdue: int
