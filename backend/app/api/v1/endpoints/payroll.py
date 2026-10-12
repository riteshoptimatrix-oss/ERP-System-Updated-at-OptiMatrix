from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from app.database.mongodb import mongodb_manager
from app.api.deps import get_current_active_user, require_permission, verify_csrf_token
from app.models.user import RoleName
from app.repositories.payroll_repository import PayrollRepository
from app.schemas.payroll import (
    SalaryStructureInput,
    SalaryStructureResponse,
    PayrollRunCreate,
    PayrollRunResponse,
    PayrollItemResponse,
    PayslipResponse,
    PayrollJournalEntryResponse,
    PayrollSummary,
)
from app.schemas.master import PaginatedResponse

router = APIRouter(prefix="/payroll", tags=["Payroll & Compensation"])


def is_regular_employee(user: Dict[str, Any]) -> bool:
    return user.get("role") == RoleName.EMPLOYEE.value or user.get("account_type") == "EMPLOYEE"


def get_payroll_repo() -> PayrollRepository:
    db = mongodb_manager.get_database()
    return PayrollRepository(db)


def serialize_salary_structure(doc: Dict[str, Any]) -> SalaryStructureResponse:
    return SalaryStructureResponse(
        id=str(doc["_id"]),
        employee_id=doc["employee_id"],
        employee_code=doc.get("employee_code", ""),
        employee_name=doc.get("employee_name", ""),
        department=doc.get("department", "Operations"),
        designation=doc.get("designation", "Staff"),
        unit_id=doc.get("unit_id", "Unit_1"),
        base_monthly_salary=doc["base_monthly_salary"],
        basic_salary=doc["basic_salary"],
        hra=doc.get("hra", 0.0),
        conveyance_allowance=doc.get("conveyance_allowance", 0.0),
        special_allowance=doc.get("special_allowance", 0.0),
        overtime_hourly_rate=doc.get("overtime_hourly_rate", 0.0),
        gross_monthly_standard=doc.get("gross_monthly_standard", 0.0),
        pf_applicable=doc.get("pf_applicable", True),
        pf_percentage=doc.get("pf_percentage", 12.0),
        esi_applicable=doc.get("esi_applicable", False),
        esi_percentage=doc.get("esi_percentage", 0.75),
        professional_tax=doc.get("professional_tax", 200.0),
        tds_monthly=doc.get("tds_monthly", 0.0),
        bank_name=doc.get("bank_name"),
        bank_account_number=doc.get("bank_account_number"),
        bank_ifsc=doc.get("bank_ifsc"),
        created_at=doc["created_at"],
        updated_at=doc.get("updated_at"),
    )


def serialize_payroll_run(doc: Dict[str, Any]) -> PayrollRunResponse:
    return PayrollRunResponse(
        id=str(doc["_id"]),
        run_number=doc["run_number"],
        period=doc["period"],
        unit_id=doc["unit_id"],
        working_days_in_month=doc.get("working_days_in_month", 26),
        total_employees=doc.get("total_employees", 0),
        total_gross_payout=doc.get("total_gross_payout", 0.0),
        total_deductions=doc.get("total_deductions", 0.0),
        total_net_payout=doc.get("total_net_payout", 0.0),
        status=doc["status"],
        notes=doc.get("notes"),
        created_at=doc["created_at"],
        created_by=doc["created_by"],
        reviewed_at=doc.get("reviewed_at"),
        reviewed_by=doc.get("reviewed_by"),
        approved_at=doc.get("approved_at"),
        approved_by=doc.get("approved_by"),
        posted_at=doc.get("posted_at"),
        posted_by=doc.get("posted_by"),
    )


def serialize_payroll_item(doc: Dict[str, Any]) -> PayrollItemResponse:
    return PayrollItemResponse(
        id=str(doc["_id"]),
        payroll_run_id=doc["payroll_run_id"],
        employee_id=doc["employee_id"],
        employee_code=doc.get("employee_code", ""),
        employee_name=doc.get("employee_name", ""),
        department=doc.get("department", "Operations"),
        designation=doc.get("designation", "Staff"),
        period=doc["period"],
        unit_id=doc["unit_id"],
        standard_working_days=doc.get("standard_working_days", 26),
        present_days=doc.get("present_days", 0.0),
        paid_leave_days=doc.get("paid_leave_days", 0.0),
        unpaid_leave_days=doc.get("unpaid_leave_days", 0.0),
        overtime_hours=doc.get("overtime_hours", 0.0),
        basic=doc.get("basic", 0.0),
        hra=doc.get("hra", 0.0),
        conveyance=doc.get("conveyance", 0.0),
        special_allowance=doc.get("special_allowance", 0.0),
        overtime_pay=doc.get("overtime_pay", 0.0),
        gross_earnings=doc.get("gross_earnings", 0.0),
        lop_deduction=doc.get("lop_deduction", 0.0),
        pf_deduction=doc.get("pf_deduction", 0.0),
        esi_deduction=doc.get("esi_deduction", 0.0),
        professional_tax=doc.get("professional_tax", 0.0),
        tds_deduction=doc.get("tds_deduction", 0.0),
        total_deductions=doc.get("total_deductions", 0.0),
        net_pay=doc.get("net_pay", 0.0),
        bank_account_number=doc.get("bank_account_number"),
        bank_ifsc=doc.get("bank_ifsc"),
    )


# -------------------------------------------------------------
# Summary & Analytics
# -------------------------------------------------------------
@router.get(
    "/summary",
    response_model=PayrollSummary,
    dependencies=[Depends(require_permission("payroll", "read"))],
)
async def get_payroll_summary(
    unit_id: Optional[str] = Query(None, description="Unit_1 or Unit_2"),
    repo: PayrollRepository = Depends(get_payroll_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Retrieve payroll processing KPIs and statutory liability totals."""
    if is_regular_employee(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Corporate payroll KPIs are restricted to HR and Management."
        )
    return await repo.get_payroll_summary(unit_id=unit_id)


# -------------------------------------------------------------
# Salary Structures
# -------------------------------------------------------------
@router.post(
    "/structures",
    response_model=SalaryStructureResponse,
    dependencies=[Depends(require_permission("payroll", "update")), Depends(verify_csrf_token)],
)
async def upsert_salary_structure(
    payload: SalaryStructureInput,
    repo: PayrollRepository = Depends(get_payroll_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Configure or update employee compensation package."""
    try:
        doc = await repo.upsert_salary_structure(payload, updated_by=current_user["email"])
        return serialize_salary_structure(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/structures",
    response_model=List[SalaryStructureResponse],
    dependencies=[Depends(require_permission("payroll", "read"))],
)
async def list_salary_structures(
    unit_id: Optional[str] = Query(None),
    repo: PayrollRepository = Depends(get_payroll_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """List configured salary structures."""
    if is_regular_employee(current_user):
        my_code = current_user.get("employee_code")
        my_id = str(current_user.get("_id"))
        doc = await repo.get_salary_structure(my_code) if my_code else None
        if not doc:
            doc = await repo.get_salary_structure(my_id)
        return [serialize_salary_structure(doc)] if doc else []

    docs = await repo.list_salary_structures(unit_id=unit_id)
    return [serialize_salary_structure(d) for d in docs]


@router.get(
    "/structures/{employee_id}",
    response_model=SalaryStructureResponse,
    dependencies=[Depends(require_permission("payroll", "read"))],
)
async def get_salary_structure(
    employee_id: str = Path(..., description="Employee Code or ID"),
    repo: PayrollRepository = Depends(get_payroll_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Get salary structure for specific employee with strict ownership verification."""
    if is_regular_employee(current_user):
        my_code = current_user.get("employee_code")
        my_id = str(current_user.get("_id"))
        if employee_id != my_code and employee_id != my_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are only authorized to view your own salary structure."
            )

    doc = await repo.get_salary_structure(employee_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salary structure not found.")
    return serialize_salary_structure(doc)


# -------------------------------------------------------------
# Payroll Runs & Processing
# -------------------------------------------------------------
@router.post(
    "/runs",
    response_model=PayrollRunResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("payroll", "create")), Depends(verify_csrf_token)],
)
async def create_payroll_run(
    payload: PayrollRunCreate,
    repo: PayrollRepository = Depends(get_payroll_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Calculate and generate a monthly payroll run based on attendance and LOP."""
    try:
        doc = await repo.create_and_calculate_payroll_run(payload, created_by=current_user["email"])
        return serialize_payroll_run(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/runs",
    response_model=PaginatedResponse[PayrollRunResponse],
    dependencies=[Depends(require_permission("payroll", "read"))],
)
async def list_payroll_runs(
    unit_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    period: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    repo: PayrollRepository = Depends(get_payroll_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """List payroll runs with status and period filters."""
    if is_regular_employee(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Administrative payroll run listing is restricted to HR and Finance managers."
        )

    items, total = await repo.list_payroll_runs(
        unit_id=unit_id,
        status=status_filter,
        period=period,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[serialize_payroll_run(it) for it in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if page_size else 1,
    )


@router.get(
    "/runs/{run_id}",
    response_model=PayrollRunResponse,
    dependencies=[Depends(require_permission("payroll", "read"))],
)
async def get_payroll_run(
    run_id: str = Path(...),
    repo: PayrollRepository = Depends(get_payroll_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    if is_regular_employee(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Administrative payroll run details are restricted to HR and Finance managers."
        )

    doc = await repo.get_payroll_run_by_id(run_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll run not found.")
    return serialize_payroll_run(doc)


@router.get(
    "/runs/{run_id}/items",
    response_model=List[PayrollItemResponse],
    dependencies=[Depends(require_permission("payroll", "read"))],
)
async def list_payroll_items(
    run_id: str = Path(...),
    repo: PayrollRepository = Depends(get_payroll_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    if is_regular_employee(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Company-wide payroll items are restricted to HR and Finance managers."
        )

    items = await repo.list_payroll_items(run_id)
    return [serialize_payroll_item(it) for it in items]


# -------------------------------------------------------------
# Review, Approve, and Post Actions
# -------------------------------------------------------------
@router.post(
    "/runs/{run_id}/review",
    response_model=PayrollRunResponse,
    dependencies=[Depends(require_permission("payroll", "update")), Depends(verify_csrf_token)],
)
async def review_payroll_run(
    run_id: str = Path(...),
    repo: PayrollRepository = Depends(get_payroll_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Submit a draft payroll run for management review."""
    try:
        doc = await repo.review_payroll_run(run_id, reviewer=current_user["email"])
        return serialize_payroll_run(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/runs/{run_id}/approve",
    response_model=PayrollRunResponse,
    dependencies=[Depends(require_permission("payroll", "approve")), Depends(verify_csrf_token)],
)
async def approve_payroll_run(
    run_id: str = Path(...),
    repo: PayrollRepository = Depends(get_payroll_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Approve a reviewed payroll run."""
    try:
        doc = await repo.approve_payroll_run(run_id, approver=current_user["email"])
        return serialize_payroll_run(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/runs/{run_id}/post",
    response_model=PayrollRunResponse,
    dependencies=[Depends(require_permission("payroll", "post")), Depends(verify_csrf_token)],
)
async def post_payroll_run(
    run_id: str = Path(...),
    repo: PayrollRepository = Depends(get_payroll_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Final posting: locks records and prevents duplicate runs or post-approval tampering."""
    try:
        doc = await repo.post_payroll_run(run_id, poster=current_user["email"])
        return serialize_payroll_run(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# Payslip & Accounting Exports
# -------------------------------------------------------------
@router.get(
    "/payslips/{employee_id}/{period}",
    response_model=PayslipResponse,
    dependencies=[Depends(require_permission("payroll", "read"))],
)
async def get_payslip(
    employee_id: str = Path(..., description="Employee Code or ID"),
    period: str = Path(..., description="YYYY-MM"),
    repo: PayrollRepository = Depends(get_payroll_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Retrieve itemized payslip breakdown for employee with strict ownership validation."""
    if is_regular_employee(current_user):
        my_code = current_user.get("employee_code")
        my_id = str(current_user.get("_id"))
        if employee_id != my_code and employee_id != my_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are only authorized to view your own payslip."
            )

    slip = await repo.get_payslip(employee_id, period)
    if not slip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payslip record not found for this period.")
    return slip


@router.get(
    "/runs/{run_id}/accounting-export",
    response_model=PayrollJournalEntryResponse,
    dependencies=[Depends(require_permission("payroll", "export"))],
)
async def get_accounting_export(
    run_id: str = Path(...),
    repo: PayrollRepository = Depends(get_payroll_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Export double-entry general ledger journal entry for the payroll run."""
    try:
        return await repo.get_accounting_export(run_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
