from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from app.models.user import ManufacturingUnit


class ShiftType(str, Enum):
    GENERAL = "GENERAL"
    SHIFT_1 = "SHIFT_1"
    SHIFT_2 = "SHIFT_2"
    NIGHT = "NIGHT"


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    HALF_DAY = "HALF_DAY"
    ABSENT = "ABSENT"
    ON_LEAVE = "ON_LEAVE"
    HOLIDAY = "HOLIDAY"


class LeaveType(str, Enum):
    CASUAL_LEAVE = "CASUAL_LEAVE"
    SICK_LEAVE = "SICK_LEAVE"
    EARNED_LEAVE = "EARNED_LEAVE"
    UNPAID_LEAVE = "UNPAID_LEAVE"


class LeaveStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


# -------------------------------------------------------------
# Shift Configuration Models
# -------------------------------------------------------------
class ShiftConfigCreate(BaseModel):
    shift_code: str = Field(..., min_length=2, max_length=50, description="Code e.g. SHIFT-GEN, SHIFT-MORN")
    name: str = Field(..., min_length=2, max_length=100)
    shift_type: ShiftType = Field(default=ShiftType.GENERAL)
    start_time: str = Field(..., description="HH:MM format e.g. 09:00")
    end_time: str = Field(..., description="HH:MM format e.g. 18:00")
    break_duration_minutes: int = Field(default=60, ge=0)
    grace_period_minutes: int = Field(default=15, ge=0)
    standard_work_hours: float = Field(default=8.0, gt=0.0)
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.BOTH)
    is_active: bool = True


class ShiftConfigResponse(ShiftConfigCreate):
    id: str
    created_at: datetime
    created_by: str


# -------------------------------------------------------------
# Attendance Models
# -------------------------------------------------------------
class AttendanceEntryCreate(BaseModel):
    employee_id: str = Field(..., description="Employee Master ID")
    employee_code: str = Field(..., description="Employee Code e.g. EMP-001")
    date: str = Field(..., description="YYYY-MM-DD")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    shift_code: Optional[str] = Field("SHIFT-GEN", description="Shift code")
    check_in: Optional[str] = Field(None, description="ISO timestamp or HH:MM")
    check_out: Optional[str] = Field(None, description="ISO timestamp or HH:MM")
    status: AttendanceStatus = Field(default=AttendanceStatus.PRESENT)
    hours_worked: float = Field(default=8.0, ge=0.0)
    overtime_hours: float = Field(default=0.0, ge=0.0)
    remarks: Optional[str] = Field(None, max_length=300)


class AttendanceCorrectionRequest(BaseModel):
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    status: Optional[AttendanceStatus] = None
    hours_worked: Optional[float] = Field(None, ge=0.0)
    overtime_hours: Optional[float] = Field(None, ge=0.0)
    correction_reason: str = Field(..., min_length=3, max_length=500)


class AttendanceEntryResponse(BaseModel):
    id: str
    employee_id: str
    employee_code: str
    employee_name: str
    department: str
    designation: str
    date: str
    unit_id: str
    shift_code: str
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    status: str
    hours_worked: float
    overtime_hours: float
    is_corrected: bool = False
    correction_reason: Optional[str] = None
    corrected_by: Optional[str] = None
    created_at: datetime
    created_by: str


# -------------------------------------------------------------
# Leave Application Models
# -------------------------------------------------------------
class LeaveApplicationCreate(BaseModel):
    employee_id: str = Field(..., description="Employee Master ID")
    leave_type: LeaveType = Field(default=LeaveType.CASUAL_LEAVE)
    start_date: str = Field(..., description="YYYY-MM-DD")
    end_date: str = Field(..., description="YYYY-MM-DD")
    days_count: float = Field(..., gt=0.0, description="Total days requested")
    reason: str = Field(..., min_length=3, max_length=500)


class LeaveApprovalRequest(BaseModel):
    status: LeaveStatus = Field(..., description="APPROVED or REJECTED")
    rejection_reason: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=300)


class LeaveApplicationResponse(BaseModel):
    id: str
    application_number: str
    employee_id: str
    employee_code: str
    employee_name: str
    department: str
    unit_id: str
    leave_type: str
    start_date: str
    end_date: str
    days_count: float
    reason: str
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    created_by: str


# -------------------------------------------------------------
# Attendance Summary / KPI Models
# -------------------------------------------------------------
class HRAttendanceSummary(BaseModel):
    unit_id: Optional[str] = None
    total_active_employees: int
    present_today: int
    on_leave_today: int
    absent_today: int
    total_overtime_hours_month: float
    pending_leave_requests: int
