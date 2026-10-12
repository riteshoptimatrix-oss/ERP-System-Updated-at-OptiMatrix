from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.user import ManufacturingUnit
from app.schemas.hr import ShiftConfigResponse, AttendanceEntryResponse, LeaveApplicationResponse, LeaveType, AttendanceStatus
from app.schemas.notification import NotificationResponse, AnnouncementResponse
from app.schemas.payroll import SalaryStructureResponse, PayslipResponse


class EmployeeShiftSummary(BaseModel):
    shift_code: str
    name: str
    start_time: str
    end_time: str
    grace_period_minutes: int = 15
    standard_work_hours: float = 8.0
    unit_id: str = "BOTH"


class EmployeeAttendanceToday(BaseModel):
    record_id: Optional[str] = None
    date: str
    status: str
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    hours_worked: float = 0.0
    overtime_hours: float = 0.0
    shift_code: Optional[str] = None
    is_checked_in: bool = False
    is_checked_out: bool = False


class LeaveBalanceItem(BaseModel):
    leave_type: str
    name: str
    quota_days: float
    used_days: float
    pending_days: float
    remaining_balance: float


class EmployeeDashboardResponse(BaseModel):
    employee_code: str
    full_name: str
    email: str
    department: str
    designation: str
    job_roles: List[str]
    unit_id: str
    allowed_units: List[str]
    today_attendance: Optional[EmployeeAttendanceToday] = None
    current_shift: Optional[EmployeeShiftSummary] = None
    leave_balances: List[LeaveBalanceItem] = []
    pending_tasks_count: int = 0
    upcoming_deadlines_count: int = 0
    pending_leaves_count: int = 0
    unread_notifications_count: int = 0
    recent_notifications: List[NotificationResponse] = []
    announcements: List[AnnouncementResponse] = []
    authorized_modules: List[str] = []


class EmployeeProfileResponse(BaseModel):
    user_id: str
    employee_id: Optional[str] = None
    employee_code: str
    full_name: str
    email: str
    phone: Optional[str] = None
    department: str
    designation: str
    job_role: Optional[str] = None
    job_roles: List[str] = []
    reporting_officer_id: Optional[str] = None
    reporting_officer_name: Optional[str] = None
    unit_id: str
    allowed_units: List[str] = []
    account_type: str
    role: str
    status: str = "ACTIVE"
    joining_date: Optional[str] = None
    emergency_contact: Optional[str] = None
    is_active: bool = True
    must_change_password: bool = False
    created_at: Optional[datetime] = None
    permissions: List[str] = []


class ProfileCorrectionRequestCreate(BaseModel):
    field_name: str = Field(..., min_length=2, max_length=50)
    requested_value: str = Field(..., min_length=1, max_length=200)
    reason: str = Field(..., min_length=5, max_length=500)


class ProfileCorrectionRequestResponse(BaseModel):
    id: str
    request_number: str
    employee_id: str
    employee_code: str
    employee_name: str
    field_name: str
    requested_value: str
    reason: str
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime


class AttendanceCheckInOutRequest(BaseModel):
    unit_id: Optional[str] = None
    remarks: Optional[str] = Field(None, max_length=300)


class AttendanceCorrectionSubmission(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    requested_check_in: Optional[str] = Field(None, description="HH:MM format e.g. 09:15")
    requested_check_out: Optional[str] = Field(None, description="HH:MM format e.g. 18:30")
    requested_status: Optional[str] = Field(None, description="PRESENT, HALF_DAY, ON_LEAVE")
    reason: str = Field(..., min_length=5, max_length=500)


class AttendanceCorrectionResponse(BaseModel):
    id: str
    request_number: str
    employee_id: str
    employee_code: str
    employee_name: str
    date: str
    requested_check_in: Optional[str] = None
    requested_check_out: Optional[str] = None
    requested_status: Optional[str] = None
    reason: str
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime


class EmployeeLeaveApplicationCreate(BaseModel):
    leave_type: LeaveType = Field(default=LeaveType.CASUAL_LEAVE)
    start_date: str = Field(..., description="YYYY-MM-DD")
    end_date: str = Field(..., description="YYYY-MM-DD")
    days_count: float = Field(..., gt=0.0, description="Total days requested")
    reason: str = Field(..., min_length=3, max_length=500)


class EmployeeTaskResponse(BaseModel):
    id: str
    task_number: str
    title: str
    description: str
    source_module: str  # inventory, production, qc, sales, power
    priority: str = "MEDIUM"  # LOW, MEDIUM, HIGH, URGENT
    status: str = "PENDING"   # PENDING, IN_PROGRESS, COMPLETED, CANCELLED
    due_date: Optional[str] = None
    related_record: Optional[str] = None
    related_link: Optional[str] = None
    unit_id: str = "Unit_1"
    notes: Optional[str] = None
    completion_evidence: Optional[str] = None
    supervisor_feedback: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class EmployeeTaskUpdate(BaseModel):
    status: Optional[str] = Field(None, description="IN_PROGRESS, COMPLETED, PENDING")
    notes: Optional[str] = Field(None, max_length=500)
    completion_evidence: Optional[str] = Field(None, max_length=500)
