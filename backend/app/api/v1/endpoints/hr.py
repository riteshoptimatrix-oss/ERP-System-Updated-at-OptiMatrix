from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from app.database.mongodb import mongodb_manager
from app.api.deps import get_current_active_user, require_permission, verify_csrf_token
from app.repositories.hr_repository import HRRepository
from app.schemas.hr import (
    ShiftConfigCreate,
    ShiftConfigResponse,
    AttendanceEntryCreate,
    AttendanceCorrectionRequest,
    AttendanceEntryResponse,
    LeaveApplicationCreate,
    LeaveApprovalRequest,
    LeaveApplicationResponse,
    HRAttendanceSummary,
)
from app.schemas.master import PaginatedResponse

router = APIRouter(prefix="/hr", tags=["HR & Attendance Management"])


def get_hr_repo() -> HRRepository:
    db = mongodb_manager.get_database()
    return HRRepository(db)


def serialize_shift(doc: Dict[str, Any]) -> ShiftConfigResponse:
    return ShiftConfigResponse(
        id=str(doc["_id"]),
        shift_code=doc["shift_code"],
        name=doc["name"],
        shift_type=doc["shift_type"],
        start_time=doc["start_time"],
        end_time=doc["end_time"],
        break_duration_minutes=doc.get("break_duration_minutes", 60),
        grace_period_minutes=doc.get("grace_period_minutes", 15),
        standard_work_hours=doc.get("standard_work_hours", 8.0),
        unit_id=doc.get("unit_id", "BOTH"),
        is_active=doc.get("is_active", True),
        created_at=doc["created_at"],
        created_by=doc.get("created_by", "SYSTEM"),
    )


def serialize_attendance(doc: Dict[str, Any]) -> AttendanceEntryResponse:
    return AttendanceEntryResponse(
        id=str(doc["_id"]),
        employee_id=doc["employee_id"],
        employee_code=doc.get("employee_code", ""),
        employee_name=doc.get("employee_name", ""),
        department=doc.get("department", "Operations"),
        designation=doc.get("designation", "Staff"),
        date=doc["date"],
        unit_id=doc.get("unit_id", "Unit_1"),
        shift_code=doc.get("shift_code", "SHIFT-GEN"),
        check_in=doc.get("check_in"),
        check_out=doc.get("check_out"),
        status=doc["status"],
        hours_worked=doc.get("hours_worked", 8.0),
        overtime_hours=doc.get("overtime_hours", 0.0),
        is_corrected=doc.get("is_corrected", False),
        correction_reason=doc.get("correction_reason"),
        corrected_by=doc.get("corrected_by"),
        created_at=doc["created_at"],
        created_by=doc.get("created_by", "SYSTEM"),
    )


def serialize_leave(doc: Dict[str, Any]) -> LeaveApplicationResponse:
    return LeaveApplicationResponse(
        id=str(doc["_id"]),
        application_number=doc["application_number"],
        employee_id=doc["employee_id"],
        employee_code=doc.get("employee_code", ""),
        employee_name=doc.get("employee_name", ""),
        department=doc.get("department", "Operations"),
        unit_id=doc.get("unit_id", "Unit_1"),
        leave_type=doc["leave_type"],
        start_date=doc["start_date"],
        end_date=doc["end_date"],
        days_count=doc.get("days_count", 1.0),
        reason=doc.get("reason", ""),
        status=doc["status"],
        approved_by=doc.get("approved_by"),
        approved_at=doc.get("approved_at"),
        rejection_reason=doc.get("rejection_reason"),
        created_at=doc["created_at"],
        created_by=doc.get("created_by", "SYSTEM"),
    )


# -------------------------------------------------------------
# Summary & Metrics
# -------------------------------------------------------------
@router.get(
    "/summary",
    response_model=HRAttendanceSummary,
    dependencies=[Depends(require_permission("attendance", "read"))],
)
async def get_hr_summary(
    unit_id: Optional[str] = Query(None, description="Unit_1 or Unit_2"),
    repo: HRRepository = Depends(get_hr_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Retrieve workforce attendance metrics, today's presence, and pending leaves."""
    if current_user.get("role") == "EMPLOYEE" or current_user.get("account_type") == "EMPLOYEE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Workforce summary metrics are restricted to HR and Management."
        )
    return await repo.get_hr_summary(unit_id=unit_id)


# -------------------------------------------------------------
# Shifts Management
# -------------------------------------------------------------
@router.post(
    "/shifts",
    response_model=ShiftConfigResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("hr", "create")), Depends(verify_csrf_token)],
)
async def create_shift(
    payload: ShiftConfigCreate,
    repo: HRRepository = Depends(get_hr_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Configure a manufacturing facility work shift."""
    try:
        doc = await repo.create_shift(payload, created_by=current_user["email"])
        return serialize_shift(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/shifts",
    response_model=List[ShiftConfigResponse],
    dependencies=[Depends(require_permission("hr", "read"))],
)
async def list_shifts(
    unit_id: Optional[str] = Query(None, description="Unit_1 or Unit_2"),
    repo: HRRepository = Depends(get_hr_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """List configured shifts for the unit."""
    docs = await repo.list_shifts(unit_id=unit_id)
    return [serialize_shift(d) for d in docs]


# -------------------------------------------------------------
# Attendance Recording & Corrections
# -------------------------------------------------------------
@router.post(
    "/attendance",
    response_model=AttendanceEntryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("attendance", "create")), Depends(verify_csrf_token)],
)
async def record_attendance(
    payload: AttendanceEntryCreate,
    repo: HRRepository = Depends(get_hr_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Record daily attendance with duplicate submission protection."""
    try:
        doc = await repo.record_attendance(payload, created_by=current_user["email"])
        return serialize_attendance(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/attendance",
    response_model=PaginatedResponse[AttendanceEntryResponse],
    dependencies=[Depends(require_permission("attendance", "read"))],
)
async def list_attendance(
    date: Optional[str] = Query(None, description="Specific date YYYY-MM-DD"),
    employee_id: Optional[str] = Query(None, description="Employee code or ID"),
    unit_id: Optional[str] = Query(None, description="Unit_1 or Unit_2"),
    attendance_status: Optional[str] = Query(None, alias="status"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    repo: HRRepository = Depends(get_hr_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Search and filter attendance records."""
    if current_user.get("role") == "EMPLOYEE" or current_user.get("account_type") == "EMPLOYEE":
        my_code = current_user.get("employee_code") or str(current_user["_id"])
        if employee_id and employee_id != my_code and employee_id != str(current_user["_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are only authorized to view your own attendance records."
            )
        employee_id = my_code

    items, total = await repo.list_attendance(
        date=date,
        employee_id=employee_id,
        unit_id=unit_id,
        status=attendance_status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[serialize_attendance(it) for it in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if page_size else 1,
    )


@router.put(
    "/attendance/{record_id}/correct",
    response_model=AttendanceEntryResponse,
    dependencies=[Depends(require_permission("attendance", "update")), Depends(verify_csrf_token)],
)
async def correct_attendance(
    record_id: str = Path(..., description="Attendance Record ID"),
    payload: AttendanceCorrectionRequest = ...,
    repo: HRRepository = Depends(get_hr_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Authorized supervisor correction of attendance timing or status."""
    try:
        doc = await repo.correct_attendance(
            record_id=record_id,
            correction=payload,
            corrected_by=current_user["email"],
        )
        return serialize_attendance(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# Leave Applications & Approval
# -------------------------------------------------------------
@router.post(
    "/leaves",
    response_model=LeaveApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("attendance", "create")), Depends(verify_csrf_token)],
)
async def apply_leave(
    payload: LeaveApplicationCreate,
    repo: HRRepository = Depends(get_hr_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Submit a leave application."""
    try:
        doc = await repo.apply_leave(payload, applied_by=current_user["email"])
        return serialize_leave(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/leaves",
    response_model=PaginatedResponse[LeaveApplicationResponse],
    dependencies=[Depends(require_permission("attendance", "read"))],
)
async def list_leaves(
    employee_id: Optional[str] = Query(None),
    unit_id: Optional[str] = Query(None),
    leave_status: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    repo: HRRepository = Depends(get_hr_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """List leave applications with status filter."""
    if current_user.get("role") == "EMPLOYEE" or current_user.get("account_type") == "EMPLOYEE":
        my_code = current_user.get("employee_code") or str(current_user["_id"])
        if employee_id and employee_id != my_code and employee_id != str(current_user["_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are only authorized to view your own leave applications."
            )
        employee_id = my_code

    items, total = await repo.list_leaves(
        employee_id=employee_id,
        unit_id=unit_id,
        status=leave_status,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[serialize_leave(it) for it in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if page_size else 1,
    )


@router.put(
    "/leaves/{leave_id}/review",
    response_model=LeaveApplicationResponse,
    dependencies=[Depends(require_permission("attendance", "approve")), Depends(verify_csrf_token)],
)
async def review_leave(
    leave_id: str = Path(..., description="Leave Application ID or Number"),
    payload: LeaveApprovalRequest = ...,
    repo: HRRepository = Depends(get_hr_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Review, approve, or reject an employee leave request."""
    try:
        doc = await repo.review_leave(
            leave_id=leave_id,
            review=payload,
            reviewer=current_user["email"],
        )
        return serialize_leave(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
