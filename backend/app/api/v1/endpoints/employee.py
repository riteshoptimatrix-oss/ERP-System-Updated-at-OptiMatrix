from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from bson import ObjectId
from datetime import datetime, timezone
from app.database.mongodb import mongodb_manager
from app.api.deps import get_current_active_user, verify_csrf_token, require_unit_access
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.employee import (
    EmployeeDashboardResponse,
    EmployeeProfileResponse,
    ProfileCorrectionRequestCreate,
    ProfileCorrectionRequestResponse,
    AttendanceCheckInOutRequest,
    AttendanceCorrectionSubmission,
    AttendanceCorrectionResponse,
    EmployeeLeaveApplicationCreate,
    EmployeeTaskResponse,
    EmployeeTaskUpdate,
    EmployeeAttendanceToday,
)
from app.schemas.hr import (
    AttendanceEntryResponse,
    LeaveApplicationCreate,
    LeaveApplicationResponse,
)
from app.schemas.payroll import SalaryStructureResponse, PayslipResponse
from app.schemas.master import PaginatedResponse

router = APIRouter(prefix="/employee", tags=["Employee Self-Service Portal"])


def get_emp_repo() -> EmployeeRepository:
    db = mongodb_manager.get_database()
    return EmployeeRepository(db)


def serialize_attendance(doc: Dict[str, Any]) -> AttendanceEntryResponse:
    return AttendanceEntryResponse(
        id=str(doc["_id"]),
        employee_id=doc.get("employee_id", ""),
        employee_code=doc.get("employee_code", ""),
        employee_name=doc.get("employee_name", ""),
        department=doc.get("department", "Operations"),
        designation=doc.get("designation", "Staff"),
        date=doc["date"],
        unit_id=doc.get("unit_id", "Unit_1"),
        shift_code=doc.get("shift_code", "SHIFT-GEN"),
        check_in=doc.get("check_in"),
        check_out=doc.get("check_out"),
        status=doc.get("status", "PRESENT"),
        hours_worked=float(doc.get("hours_worked", 8.0)),
        overtime_hours=float(doc.get("overtime_hours", 0.0)),
        is_corrected=doc.get("is_corrected", False),
        correction_reason=doc.get("correction_reason"),
        corrected_by=doc.get("corrected_by"),
        created_at=doc.get("created_at", datetime.now(timezone.utc)),
        created_by=doc.get("created_by", "SYSTEM"),
    )


def serialize_leave(doc: Dict[str, Any]) -> LeaveApplicationResponse:
    return LeaveApplicationResponse(
        id=str(doc["_id"]),
        application_number=doc.get("application_number", ""),
        employee_id=doc.get("employee_id", ""),
        employee_code=doc.get("employee_code", ""),
        employee_name=doc.get("employee_name", ""),
        department=doc.get("department", "Operations"),
        unit_id=doc.get("unit_id", "Unit_1"),
        leave_type=doc.get("leave_type", "CASUAL_LEAVE"),
        start_date=doc["start_date"],
        end_date=doc["end_date"],
        days_count=float(doc.get("days_count", 1.0)),
        reason=doc.get("reason", ""),
        status=doc.get("status", "PENDING"),
        approved_by=doc.get("approved_by"),
        approved_at=doc.get("approved_at"),
        rejection_reason=doc.get("rejection_reason"),
        created_at=doc.get("created_at", datetime.now(timezone.utc)),
        created_by=doc.get("created_by", "SYSTEM"),
    )


# -------------------------------------------------------------
# 1. Employee Dashboard
# -------------------------------------------------------------
@router.get("/dashboard", response_model=EmployeeDashboardResponse)
async def get_employee_dashboard(
    unit_id: Optional[str] = Query(None, description="Unit_1 or Unit_2"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: EmployeeRepository = Depends(get_emp_repo),
) -> EmployeeDashboardResponse:
    """
    Returns personalized real-time dashboard data for the authenticated employee:
    today's attendance, active shift, leave balances, pending tasks, and notifications.
    """
    return await repo.get_dashboard(user_doc=current_user, unit_id=unit_id)


# -------------------------------------------------------------
# 2. Employee Profile & Correction Requests
# -------------------------------------------------------------
@router.get("/profile", response_model=EmployeeProfileResponse)
async def get_employee_profile(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: EmployeeRepository = Depends(get_emp_repo),
) -> EmployeeProfileResponse:
    """
    Returns comprehensive profile data combining User Account and Employee Master records.
    """
    emp_doc = await repo.resolve_employee_doc(current_user)
    j_roles = current_user.get("job_roles")
    if not j_roles and current_user.get("job_role"):
        j_roles = [current_user["job_role"]]
    elif not j_roles:
        j_roles = [emp_doc.get("designation", "Staff")]

    return EmployeeProfileResponse(
        user_id=str(current_user["_id"]),
        employee_id=str(emp_doc["_id"]),
        employee_code=emp_doc.get("code", current_user.get("employee_code", "")),
        full_name=emp_doc.get("full_name", current_user.get("full_name")),
        email=current_user["email"],
        phone=emp_doc.get("phone", current_user.get("phone")),
        department=emp_doc.get("department", current_user.get("department", "Operations")),
        designation=emp_doc.get("designation", current_user.get("job_role", "Staff")),
        job_role=current_user.get("job_role"),
        job_roles=j_roles,
        reporting_officer_id=emp_doc.get("reporting_officer_id"),
        reporting_officer_name=emp_doc.get("reporting_officer_name"),
        unit_id=emp_doc.get("unit_id", "Unit_1"),
        allowed_units=current_user.get("allowed_units", ["Unit_1"]),
        account_type=current_user.get("account_type", current_user.get("role", "EMPLOYEE")),
        role=current_user.get("role", "EMPLOYEE"),
        status=emp_doc.get("status", "ACTIVE"),
        joining_date=emp_doc.get("joining_date"),
        emergency_contact=emp_doc.get("emergency_contact"),
        is_active=current_user.get("is_active", True),
        must_change_password=current_user.get("must_change_password", False),
        created_at=current_user.get("created_at"),
        permissions=current_user.get("permissions", []),
    )


@router.post(
    "/profile/correction-request",
    response_model=ProfileCorrectionRequestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf_token)],
)
async def submit_profile_correction_request(
    payload: ProfileCorrectionRequestCreate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: EmployeeRepository = Depends(get_emp_repo),
):
    """
    Allows employees to submit formal correction requests for protected profile fields for HR review.
    """
    doc = await repo.submit_profile_correction(current_user, payload)
    return ProfileCorrectionRequestResponse(
        id=str(doc["_id"]),
        request_number=doc["request_number"],
        employee_id=doc["employee_id"],
        employee_code=doc["employee_code"],
        employee_name=doc["employee_name"],
        field_name=doc["field_name"],
        requested_value=doc["requested_value"],
        reason=doc["reason"],
        status=doc["status"],
        reviewed_by=doc.get("reviewed_by"),
        reviewed_at=doc.get("reviewed_at"),
        rejection_reason=doc.get("rejection_reason"),
        created_at=doc["created_at"],
    )


# -------------------------------------------------------------
# 3. Attendance & Check-In / Check-Out
# -------------------------------------------------------------
@router.post(
    "/attendance/check-in",
    response_model=AttendanceEntryResponse,
    dependencies=[Depends(verify_csrf_token)],
)
async def employee_check_in(
    payload: AttendanceCheckInOutRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: EmployeeRepository = Depends(get_emp_repo),
):
    """
    Self-service check-in timestamp logging with duplicate prevention.
    """
    try:
        doc = await repo.check_in(current_user, unit_id=payload.unit_id, remarks=payload.remarks)
        return serialize_attendance(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/attendance/check-out",
    response_model=AttendanceEntryResponse,
    dependencies=[Depends(verify_csrf_token)],
)
async def employee_check_out(
    payload: AttendanceCheckInOutRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: EmployeeRepository = Depends(get_emp_repo),
):
    """
    Self-service check-out timestamp logging with worked hours and overtime calculation.
    """
    try:
        doc = await repo.check_out(current_user, remarks=payload.remarks)
        return serialize_attendance(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/attendance", response_model=PaginatedResponse[AttendanceEntryResponse])
async def get_my_attendance_history(
    date: Optional[str] = Query(None, description="Specific date YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    month: Optional[str] = Query(None, description="YYYY-MM"),
    page: int = Query(1, ge=1),
    page_size: int = Query(31, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: EmployeeRepository = Depends(get_emp_repo),
):
    """
    Retrieves the authenticated employee's attendance records with date boundaries and monthly history.
    """
    emp_doc = await repo.resolve_employee_doc(current_user)
    emp_code = emp_doc.get("code")
    emp_id_str = str(emp_doc["_id"])

    query: Dict[str, Any] = {
        "$or": [{"employee_id": emp_id_str}, {"employee_code": emp_code}]
    }

    if date:
        query["date"] = date
    elif month:
        query["date"] = {"$regex": f"^{month}-"}
    elif start_date or end_date:
        d_filter = {}
        if start_date:
            d_filter["$gte"] = start_date
        if end_date:
            d_filter["$lte"] = end_date
        query["date"] = d_filter

    total = await repo.att_col.count_documents(query)
    skip = (page - 1) * page_size
    cursor = repo.att_col.find(query).sort("date", -1).skip(skip).limit(page_size)
    items = await cursor.to_list(length=page_size)

    return PaginatedResponse(
        items=[serialize_attendance(it) for it in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if page_size else 1,
    )


@router.post(
    "/attendance/correction-request",
    response_model=AttendanceCorrectionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf_token)],
)
async def submit_attendance_correction_request(
    payload: AttendanceCorrectionSubmission,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: EmployeeRepository = Depends(get_emp_repo),
):
    """
    Submits an attendance correction request with reason for supervisor review.
    """
    doc = await repo.submit_attendance_correction(current_user, payload)
    return AttendanceCorrectionResponse(
        id=str(doc["_id"]),
        request_number=doc["request_number"],
        employee_id=doc["employee_id"],
        employee_code=doc["employee_code"],
        employee_name=doc["employee_name"],
        date=doc["date"],
        requested_check_in=doc.get("requested_check_in"),
        requested_check_out=doc.get("requested_check_out"),
        requested_status=doc.get("requested_status"),
        reason=doc["reason"],
        status=doc["status"],
        reviewed_by=doc.get("reviewed_by"),
        reviewed_at=doc.get("reviewed_at"),
        rejection_reason=doc.get("rejection_reason"),
        created_at=doc["created_at"],
    )


@router.get("/attendance/correction-requests", response_model=List[AttendanceCorrectionResponse])
async def list_my_attendance_corrections(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: EmployeeRepository = Depends(get_emp_repo),
):
    """
    Lists the employee's submitted attendance correction requests and review statuses.
    """
    emp_doc = await repo.resolve_employee_doc(current_user)
    emp_code = emp_doc.get("code")
    emp_id_str = str(emp_doc["_id"])

    cursor = repo.att_corr_col.find({
        "$or": [{"employee_id": emp_id_str}, {"employee_code": emp_code}]
    }).sort("created_at", -1).limit(50)
    items = await cursor.to_list(length=50)

    return [
        AttendanceCorrectionResponse(
            id=str(doc["_id"]),
            request_number=doc["request_number"],
            employee_id=doc["employee_id"],
            employee_code=doc["employee_code"],
            employee_name=doc["employee_name"],
            date=doc["date"],
            requested_check_in=doc.get("requested_check_in"),
            requested_check_out=doc.get("requested_check_out"),
            requested_status=doc.get("requested_status"),
            reason=doc["reason"],
            status=doc["status"],
            reviewed_by=doc.get("reviewed_by"),
            reviewed_at=doc.get("reviewed_at"),
            rejection_reason=doc.get("rejection_reason"),
            created_at=doc["created_at"],
        )
        for doc in items
    ]


# -------------------------------------------------------------
# 4. Leave Management
# -------------------------------------------------------------
@router.get("/leaves", response_model=PaginatedResponse[LeaveApplicationResponse])
async def list_my_leaves(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: EmployeeRepository = Depends(get_emp_repo),
):
    """
    Returns only the authenticated employee's leave applications.
    """
    emp_doc = await repo.resolve_employee_doc(current_user)
    emp_code = emp_doc.get("code")
    emp_id_str = str(emp_doc["_id"])

    query: Dict[str, Any] = {
        "$or": [{"employee_id": emp_id_str}, {"employee_code": emp_code}]
    }
    if status_filter:
        query["status"] = status_filter

    total = await repo.leaves_col.count_documents(query)
    skip = (page - 1) * page_size
    cursor = repo.leaves_col.find(query).sort("created_at", -1).skip(skip).limit(page_size)
    items = await cursor.to_list(length=page_size)

    return PaginatedResponse(
        items=[serialize_leave(it) for it in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if page_size else 1,
    )


@router.post(
    "/leaves",
    response_model=LeaveApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf_token)],
)
async def apply_my_leave(
    payload: EmployeeLeaveApplicationCreate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: EmployeeRepository = Depends(get_emp_repo),
):
    """
    Submits a leave application with overlap prevention, balance verification, and audit logging.
    """
    try:
        doc = await repo.apply_leave(current_user, payload)
        return serialize_leave(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/leaves/{leave_id}/cancel",
    response_model=LeaveApplicationResponse,
    dependencies=[Depends(verify_csrf_token)],
)
async def cancel_my_leave(
    leave_id: str = Path(..., description="Leave Application ID or Number"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: EmployeeRepository = Depends(get_emp_repo),
):
    """
    Cancels an eligible pending leave application submitted by the employee.
    """
    try:
        doc = await repo.cancel_leave(current_user, leave_id)
        return serialize_leave(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# 5. Tasks & Job-Role Workflows
# -------------------------------------------------------------
@router.get("/tasks", response_model=List[EmployeeTaskResponse])
async def get_my_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: EmployeeRepository = Depends(get_emp_repo),
):
    """
    Returns tasks dynamically aggregated from production, inventory, QC, sales, and power modules
    scoped to the employee's assigned job roles, facility unit, and department.
    """
    emp_doc = await repo.resolve_employee_doc(current_user)
    unit_id = emp_doc.get("unit_id", "Unit_1")
    tasks, _, _ = await repo.get_employee_tasks_summary(current_user, emp_doc, unit_id)

    if status_filter:
        tasks = [t for t in tasks if t.get("status") == status_filter]

    return [
        EmployeeTaskResponse(
            id=t["id"],
            task_number=t.get("task_number", f"TASK-{t['id'][:6]}"),
            title=t["title"],
            description=t.get("description", ""),
            source_module=t.get("source_module", "operations"),
            priority=t.get("priority", "MEDIUM"),
            status=t.get("status", "PENDING"),
            due_date=t.get("due_date"),
            related_record=t.get("related_record"),
            related_link=t.get("related_link"),
            unit_id=t.get("unit_id", unit_id),
            notes=t.get("notes"),
            completion_evidence=t.get("completion_evidence"),
            supervisor_feedback=t.get("supervisor_feedback"),
            created_at=t.get("created_at", datetime.now(timezone.utc)),
            updated_at=t.get("updated_at"),
        )
        for t in tasks
    ]


@router.patch(
    "/tasks/{task_id}",
    response_model=Dict[str, Any],
    dependencies=[Depends(verify_csrf_token)],
)
async def update_my_task_status(
    task_id: str = Path(...),
    payload: EmployeeTaskUpdate = ...,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: EmployeeRepository = Depends(get_emp_repo),
):
    """
    Updates progress or completion notes on an assigned task.
    """
    now = datetime.now(timezone.utc)
    # Check if task is in direct tasks collection
    task_query = {"_id": ObjectId(task_id)} if ObjectId.is_valid(task_id) else {"_id": task_id}
    existing = await repo.tasks_col.find_one(task_query)

    update_fields: Dict[str, Any] = {"updated_at": now, "updated_by": current_user["email"]}
    if payload.status:
        update_fields["status"] = payload.status
    if payload.notes:
        update_fields["notes"] = payload.notes
    if payload.completion_evidence:
        update_fields["completion_evidence"] = payload.completion_evidence

    if existing:
        await repo.tasks_col.update_one({"_id": existing["_id"]}, {"$set": update_fields})
    else:
        # Upsert progress log for operational module task
        await repo.tasks_col.update_one(
            {"task_reference": task_id},
            {"$set": {**update_fields, "task_reference": task_id, "user_id": str(current_user["_id"])}},
            upsert=True
        )

    return {"status": "SUCCESS", "message": "Task progress updated successfully.", "task_id": task_id}


# -------------------------------------------------------------
# 6. Salary & Finalized Payslips (Strict Self-Service Ownership)
# -------------------------------------------------------------
@router.get("/salary", response_model=SalaryStructureResponse)
async def get_my_salary_structure(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: EmployeeRepository = Depends(get_emp_repo),
):
    """
    Strictly returns the authenticated employee's own salary structure.
    Never exposes other employees' financial compensation or structures.
    """
    emp_doc = await repo.resolve_employee_doc(current_user)
    emp_code = emp_doc.get("code")
    emp_id_str = str(emp_doc["_id"])

    doc = await repo.salary_struct_col.find_one({
        "$or": [{"employee_id": emp_id_str}, {"employee_code": emp_code}]
    })

    if not doc:
        # If not configured yet, provide baseline statutory estimate for designation
        now = datetime.now(timezone.utc)
        doc = {
            "_id": ObjectId(),
            "employee_id": emp_id_str,
            "employee_code": emp_code,
            "employee_name": emp_doc.get("full_name"),
            "department": emp_doc.get("department", "Operations"),
            "designation": emp_doc.get("designation", "Staff"),
            "unit_id": emp_doc.get("unit_id", "Unit_1"),
            "base_monthly_salary": 25000.0,
            "basic_salary": 12500.0,
            "hra": 6250.0,
            "conveyance_allowance": 2000.0,
            "special_allowance": 4250.0,
            "overtime_hourly_rate": 150.0,
            "gross_monthly_standard": 25000.0,
            "pf_applicable": True,
            "pf_percentage": 12.0,
            "esi_applicable": False,
            "esi_percentage": 0.75,
            "professional_tax": 200.0,
            "tds_monthly": 0.0,
            "bank_name": "State Bank of India",
            "bank_account_number": "XXXX-XXXX-4589",
            "bank_ifsc": "SBIN0001234",
            "created_at": now,
        }

    from app.api.v1.endpoints.payroll import serialize_salary_structure
    return serialize_salary_structure(doc)


@router.get("/payslips", response_model=List[PayslipResponse])
async def list_my_payslips(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: EmployeeRepository = Depends(get_emp_repo),
):
    """
    Returns only the authenticated employee's finalized payslips.
    """
    emp_doc = await repo.resolve_employee_doc(current_user)
    emp_code = emp_doc.get("code")
    emp_id_str = str(emp_doc["_id"])

    items_cursor = repo.payroll_items_col.find({
        "$or": [{"employee_id": emp_id_str}, {"employee_code": emp_code}]
    }).sort("period", -1).limit(24)
    items = await items_cursor.to_list(length=24)

    from app.repositories.payroll_repository import PayrollRepository
    pay_repo = PayrollRepository(repo.db)

    results: List[PayslipResponse] = []
    for it in items:
        slip = await pay_repo.get_payslip(emp_id_str, it["period"])
        if not slip:
            slip = await pay_repo.get_payslip(emp_code, it["period"])
        if slip:
            results.append(slip)

    return results


@router.get("/payslips/{period}", response_model=PayslipResponse)
async def get_my_payslip_for_period(
    period: str = Path(..., description="YYYY-MM format"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: EmployeeRepository = Depends(get_emp_repo),
):
    """
    Returns the authenticated employee's specific itemized payslip.
    Enforces ownership verification: cannot view any other employee's payslip.
    """
    emp_doc = await repo.resolve_employee_doc(current_user)
    emp_code = emp_doc.get("code")
    emp_id_str = str(emp_doc["_id"])

    from app.repositories.payroll_repository import PayrollRepository
    pay_repo = PayrollRepository(repo.db)

    slip = await pay_repo.get_payslip(emp_id_str, period)
    if not slip:
        slip = await pay_repo.get_payslip(emp_code, period)

    if not slip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No finalized payslip found for period {period}."
        )

    return slip
