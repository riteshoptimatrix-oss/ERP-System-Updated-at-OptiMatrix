from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, model_validator
from enum import Enum


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED_FOR_REVIEW = "SUBMITTED_FOR_REVIEW"
    COMPLETED = "COMPLETED"
    REVISIONS_REQUIRED = "REVISIONS_REQUIRED"


class ReportingOfficerOption(BaseModel):
    id: str
    user_id: Optional[str] = None
    name: str
    email: str
    designation: str
    department: str
    role: str


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, description="Task Title")
    description: str = Field(..., min_length=5, max_length=4000, description="Detailed task description")
    due_date: Optional[str] = Field(None, description="ISO date or YYYY-MM-DD")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    reporting_officer_id: str = Field(..., description="ID or Email of the assigned reporting officer")
    attachments: Optional[List[str]] = Field(default_factory=list, description="List of attachment links or names")
    unit_id: Optional[str] = Field(default="Unit_1", description="Manufacturing Unit")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=5, max_length=4000)
    due_date: Optional[str] = None
    priority: Optional[TaskPriority] = None
    reporting_officer_id: Optional[str] = None
    status: Optional[TaskStatus] = None
    notes: Optional[str] = None
    attachments: Optional[List[str]] = None


class TaskSubmitForReview(BaseModel):
    completion_note: str = Field(default="Work completed and submitted for review.", min_length=1, max_length=3000, description="Detailed explanation of work accomplished")
    completion_evidence: Optional[str] = Field(None, max_length=1000, description="Reference link, job card, or sign-off identifier")
    attachments: Optional[List[str]] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def sanitize(cls, values: Any) -> Any:
        if isinstance(values, dict):
            note = values.get("completion_note") or values.get("note") or values.get("notes") or ""
            note_str = str(note).strip()
            if not note_str:
                note_str = "Work completed and submitted for review."
            values["completion_note"] = note_str

            evidence = values.get("completion_evidence") or values.get("evidence")
            if evidence == "" or evidence is None:
                values["completion_evidence"] = None
            else:
                values["completion_evidence"] = str(evidence).strip()

            if values.get("attachments") is None:
                values["attachments"] = []
        return values


class TaskReviewDecision(BaseModel):
    decision: str = Field(..., description="APPROVED or REVISIONS_REQUIRED")
    feedback_note: str = Field(default="Review completed.", min_length=1, max_length=3000, description="Officer review feedback")

    @model_validator(mode="before")
    @classmethod
    def sanitize(cls, values: Any) -> Any:
        if isinstance(values, dict):
            decision = str(values.get("decision", "APPROVED")).upper().strip()
            values["decision"] = decision
            feedback = values.get("feedback_note") or values.get("feedback") or values.get("notes") or ""
            feedback_str = str(feedback).strip()
            if not feedback_str:
                feedback_str = "Approved by reporting officer." if "APPR" in decision else "Please review and revise the submitted work."
            values["feedback_note"] = feedback_str
        return values


class TaskMessageCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=3000, description="Message text")


class TaskMessageResponse(BaseModel):
    id: str
    task_id: str
    sender_id: str
    sender_name: str
    sender_email: str
    sender_role: str  # EMPLOYEE, REPORTING_OFFICER, SUPER_ADMIN
    message: str
    created_at: datetime


class TaskResponse(BaseModel):
    id: str
    task_number: str
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    due_date: Optional[str] = None
    
    # Reporting Officer
    reporting_officer_id: Optional[str] = None
    reporting_officer_name: Optional[str] = None
    reporting_officer_email: Optional[str] = None
    
    # Creator
    created_by_id: str
    created_by_code: Optional[str] = None
    created_by_name: str
    created_by_email: str
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Submission details
    submitted_at: Optional[datetime] = None
    submitted_by: Optional[str] = None
    completion_note: Optional[str] = None
    completion_evidence: Optional[str] = None
    
    # Review details
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    review_feedback: Optional[str] = None
    
    # Extras
    attachments: List[str] = []
    source_module: str = "tasks"
    unit_id: str = "Unit_1"
    message_count: int = 0
