from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from app.models.user import ManufacturingUnit


class PayrollRunStatus(str, Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    POSTED = "POSTED"


# -------------------------------------------------------------
# Salary Structure Models
# -------------------------------------------------------------
class SalaryStructureInput(BaseModel):
    employee_id: str = Field(..., description="Employee Master ID or Code")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    base_monthly_salary: float = Field(..., gt=0.0, description="Monthly CTC base")
    basic_salary: float = Field(..., gt=0.0, description="Basic salary component")
    hra: float = Field(default=0.0, ge=0.0, description="House Rent Allowance")
    conveyance_allowance: float = Field(default=0.0, ge=0.0)
    special_allowance: float = Field(default=0.0, ge=0.0)
    overtime_hourly_rate: float = Field(default=0.0, ge=0.0, description="Hourly overtime pay rate")
    pf_applicable: bool = Field(default=True, description="Provident Fund deduction")
    pf_percentage: float = Field(default=12.0, ge=0.0, le=20.0)
    esi_applicable: bool = Field(default=False, description="Employee State Insurance")
    esi_percentage: float = Field(default=0.75, ge=0.0, le=10.0)
    professional_tax: float = Field(default=200.0, ge=0.0, description="Standard State Professional Tax")
    tds_monthly: float = Field(default=0.0, ge=0.0, description="Monthly TDS / Tax withholding")
    bank_name: Optional[str] = Field(None, max_length=100)
    bank_account_number: Optional[str] = Field(None, max_length=50)
    bank_ifsc: Optional[str] = Field(None, max_length=20)


class SalaryStructureResponse(SalaryStructureInput):
    id: str
    employee_code: str
    employee_name: str
    department: str
    designation: str
    gross_monthly_standard: float
    created_at: datetime
    updated_at: Optional[datetime] = None


# -------------------------------------------------------------
# Payroll Run & Processing Models
# -------------------------------------------------------------
class PayrollRunCreate(BaseModel):
    period: str = Field(..., description="YYYY-MM e.g. 2026-10")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    working_days_in_month: int = Field(default=26, gt=0, le=31, description="Standard working days in month")
    notes: Optional[str] = Field(None, max_length=500)


class PayrollItemResponse(BaseModel):
    id: str
    payroll_run_id: str
    employee_id: str
    employee_code: str
    employee_name: str
    department: str
    designation: str
    period: str
    unit_id: str
    # Attendance metrics
    standard_working_days: int
    present_days: float
    paid_leave_days: float
    unpaid_leave_days: float  # Loss of Pay
    overtime_hours: float
    # Calculated Earnings
    basic: float
    hra: float
    conveyance: float
    special_allowance: float
    overtime_pay: float
    gross_earnings: float
    # Calculated Deductions
    lop_deduction: float
    pf_deduction: float
    esi_deduction: float
    professional_tax: float
    tds_deduction: float
    total_deductions: float
    # Net Pay
    net_pay: float
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None


class PayrollRunResponse(BaseModel):
    id: str
    run_number: str
    period: str
    unit_id: str
    working_days_in_month: int
    total_employees: int
    total_gross_payout: float
    total_deductions: float
    total_net_payout: float
    status: str
    notes: Optional[str] = None
    created_at: datetime
    created_by: str
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    posted_at: Optional[datetime] = None
    posted_by: Optional[str] = None


# -------------------------------------------------------------
# Payslip Model
# -------------------------------------------------------------
class PayslipResponse(BaseModel):
    payslip_number: str
    period: str
    unit_id: str
    employee_id: str
    employee_code: str
    employee_name: str
    department: str
    designation: str
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    # Attendance
    standard_working_days: int
    present_days: float
    paid_leave_days: float
    lop_days: float
    overtime_hours: float
    # Earnings breakdown
    basic: float
    hra: float
    conveyance: float
    special_allowance: float
    overtime_pay: float
    total_earnings: float
    # Deductions breakdown
    lop_deduction: float
    pf_deduction: float
    esi_deduction: float
    professional_tax: float
    tds_deduction: float
    total_deductions: float
    net_salary_payable: float
    generated_at: datetime


# -------------------------------------------------------------
# Accounting Integration Models
# -------------------------------------------------------------
class JournalEntryLine(BaseModel):
    account_code: str
    account_name: str
    debit: float
    credit: float
    description: str


class PayrollJournalEntryResponse(BaseModel):
    voucher_number: str
    payroll_run_id: str
    period: str
    unit_id: str
    posting_date: str
    lines: List[JournalEntryLine]
    total_debit: float
    total_credit: float
    is_balanced: bool


# -------------------------------------------------------------
# Summary / KPI Models
# -------------------------------------------------------------
class PayrollSummary(BaseModel):
    unit_id: Optional[str] = None
    active_payroll_runs: int
    latest_period: Optional[str] = None
    total_gross_payout: float
    total_net_payout: float
    total_statutory_deductions: float
    configured_salary_structures_count: int
