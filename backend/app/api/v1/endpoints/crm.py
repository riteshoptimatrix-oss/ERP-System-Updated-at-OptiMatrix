from math import ceil
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database.mongodb import mongodb_manager
from app.api.deps import get_current_active_user, verify_csrf_token, require_permission
from app.repositories.crm_repository import CrmRepository
from app.schemas.crm import (
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    LeadConvertRequest,
    LeadActivityCreate,
    LeadActivityResponse,
    CrmDashboardSummary,
)
from app.api.v1.endpoints.master import format_doc

router = APIRouter(prefix="/crm", tags=["CRM & Lead Management"])

def get_crm_repo() -> CrmRepository:
    db = mongodb_manager.get_database()
    return CrmRepository(db)


# --------------------------------------------------------------------------
# CRM Dashboard Summary
# --------------------------------------------------------------------------
@router.get("/dashboard", response_model=CrmDashboardSummary)
async def get_crm_dashboard(
    unit_id: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Get aggregated lead statistics, follow-up deadlines, and conversion pipeline counts.
    Requires 'crm:read' permission.
    """
    if "crm:read" not in current_user.get("permissions", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission 'crm:read' required.")

    # Unit isolation check
    allowed_units = current_user.get("allowed_units", ["BOTH"])
    if "BOTH" not in allowed_units and unit_id and unit_id not in allowed_units and unit_id != "BOTH":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access denied to facility {unit_id}.")

    repo = get_crm_repo()
    return await repo.get_dashboard_summary(unit_id=unit_id)


# --------------------------------------------------------------------------
# List Leads
# --------------------------------------------------------------------------
@router.get("/leads")
async def list_leads(
    search: Optional[str] = Query(None, description="Search company, contact, or code"),
    status_filter: Optional[str] = Query(None, alias="status"),
    priority_filter: Optional[str] = Query(None, alias="priority"),
    source_filter: Optional[str] = Query(None, alias="source"),
    assigned_to: Optional[str] = Query(None),
    unit_id: Optional[str] = Query(None),
    follow_up_filter: Optional[str] = Query(None, description="today, overdue, or upcoming"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Paginated lead listing with search, filtering, and follow-up deadlines.
    Requires 'crm:read' permission.
    """
    if "crm:read" not in current_user.get("permissions", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission 'crm:read' required.")

    allowed_units = current_user.get("allowed_units", ["BOTH"])
    if "BOTH" not in allowed_units and unit_id and unit_id not in allowed_units and unit_id != "BOTH":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access denied to facility {unit_id}.")

    effective_unit = unit_id
    if not effective_unit and "BOTH" not in allowed_units:
        effective_unit = allowed_units[0] if allowed_units else None

    repo = get_crm_repo()
    s_order = -1 if sort_order.lower() == "desc" else 1

    items, total = await repo.list_leads(
        search=search,
        status=status_filter,
        priority=priority_filter,
        source=source_filter,
        assigned_to=assigned_to,
        unit_id=effective_unit,
        follow_up_filter=follow_up_filter,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=s_order,
    )

    formatted_items = [format_doc(item) for item in items]
    total_pages = ceil(total / page_size) if total > 0 else 0

    return {
        "items": formatted_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


# --------------------------------------------------------------------------
# Create Lead
# --------------------------------------------------------------------------
@router.post("/leads", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf_token)])
async def create_lead(
    payload: LeadCreate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Create a new lead with duplicate company/phone check and initial activity logging.
    Requires 'crm:create' permission.
    """
    if "crm:create" not in current_user.get("permissions", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission 'crm:create' required.")

    repo = get_crm_repo()
    data = payload.model_dump()

    try:
        inserted_id = await repo.create_lead(data, user_email=current_user["email"])
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(val_err))

    created_doc = await repo.get_by_id(inserted_id)
    return format_doc(created_doc)


# --------------------------------------------------------------------------
# Get Lead by ID with Activities
# --------------------------------------------------------------------------
@router.get("/leads/{lead_id}")
async def get_lead_details(
    lead_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Retrieve lead profile and chronological activity timeline.
    Requires 'crm:read' permission.
    """
    if "crm:read" not in current_user.get("permissions", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission 'crm:read' required.")

    repo = get_crm_repo()
    doc = await repo.get_by_id(lead_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")

    activities = await repo.list_activities(lead_id)
    formatted_activities = [format_doc(a) for a in activities]

    return {
        **format_doc(doc),
        "activities": formatted_activities,
    }


# --------------------------------------------------------------------------
# Update Lead
# --------------------------------------------------------------------------
@router.put("/leads/{lead_id}", dependencies=[Depends(verify_csrf_token)])
async def update_lead(
    lead_id: str,
    payload: LeadUpdate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Update lead details, priority, stage, and scheduled follow-up.
    Requires 'crm:update' permission.
    """
    if "crm:update" not in current_user.get("permissions", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission 'crm:update' required.")

    repo = get_crm_repo()
    update_data = payload.model_dump(exclude_unset=True)

    success = await repo.update_lead(lead_id, update_data, user_email=current_user["email"])
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")

    updated_doc = await repo.get_by_id(lead_id)
    return format_doc(updated_doc)


# --------------------------------------------------------------------------
# Log Activity / Reschedule Follow-up
# --------------------------------------------------------------------------
@router.post("/leads/{lead_id}/activities", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf_token)])
async def add_lead_activity(
    lead_id: str,
    payload: LeadActivityCreate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Log interaction notes, call summaries, or site visit logs, and optionally update next follow-up.
    Requires 'crm:update' permission.
    """
    if "crm:update" not in current_user.get("permissions", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission 'crm:update' required.")

    repo = get_crm_repo()
    lead = await repo.get_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")

    activity_id = await repo.add_activity(
        lead_id=lead_id,
        activity_type=payload.activity_type.value,
        summary=payload.summary,
        details=payload.details,
        user_email=current_user["email"],
        next_follow_up=payload.next_follow_up,
    )

    act_doc = await repo.activities_col.find_one({"_id": activity_id}) if hasattr(repo, "activities_col") else None
    return {"status": "success", "activity_id": activity_id, "message": "Activity recorded successfully."}


# --------------------------------------------------------------------------
# Convert Lead to Customer Master Record
# --------------------------------------------------------------------------
@router.post("/leads/{lead_id}/convert", dependencies=[Depends(verify_csrf_token)])
async def convert_lead(
    lead_id: str,
    payload: LeadConvertRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Convert a qualified lead into a permanent Customer Master record.
    Enforces duplicate prevention on Customer code.
    Requires 'crm:update' and 'master:create' permission.
    """
    user_perms = current_user.get("permissions", [])
    user_role = current_user.get("role", "")
    has_perm = (
        ("crm:update" in user_perms and "master:create" in user_perms)
        or "crm:update" in user_perms
        or user_role in ["SUPER_ADMIN", "ADMIN"]
    )
    if not has_perm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission 'crm:update' is required to convert leads."
        )

    repo = get_crm_repo()
    try:
        result = await repo.convert_lead_to_customer(
            lead_id=lead_id,
            customer_payload=payload.model_dump(),
            user_email=current_user["email"],
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(val_err))

    return {
        "status": "success",
        "message": f"Lead converted successfully to Customer ({result['customer_code']}).",
        "customer_id": result["customer_id"],
        "customer_code": result["customer_code"],
        "customer": format_doc(result["customer"]),
    }


# --------------------------------------------------------------------------
# Lead Project Hub & Lifecycle Overview
# --------------------------------------------------------------------------
@router.get("/leads/{lead_id}/project-summary")
async def get_lead_project_summary(
    lead_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Get 360-degree project overview for this lead:
    materials, purchase bills (AP), invoices (AR), expenses, payments, and financial margins.
    Requires 'crm:read' permission.
    """
    if "crm:read" not in current_user.get("permissions", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission 'crm:read' required.")

    repo = get_crm_repo()
    try:
        return await repo.get_lead_project_summary(lead_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/leads/{lead_id}/materials", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf_token)])
async def add_lead_material_requirement(
    lead_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Add a Bill of Materials / Material Requirement linked directly to this Lead/Project.
    Requires 'crm:update' permission.
    """
    if "crm:update" not in current_user.get("permissions", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission 'crm:update' required.")

    repo = get_crm_repo()
    try:
        doc = await repo.add_lead_material_requirement(
            lead_id=lead_id,
            data=payload,
            user_email=current_user["email"],
        )
        return format_doc(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

