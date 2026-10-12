from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from app.database.mongodb import mongodb_manager
from app.api.deps import get_current_active_user, require_permission, verify_csrf_token
from app.models.user import ModuleName, ActionType
from app.repositories.wastage_repository import WastageRepository
from app.schemas.wastage import (
    ScrapEntryCreate,
    ScrapEntryUpdate,
    ScrapApprovalRequest,
    ScrapRejectionRequest,
    ScrapEntryResponse,
    PlannedVsActualWastageResponse,
    WastageDashboardSummary,
)
from app.schemas.master import PaginatedResponse

router = APIRouter(prefix="/wastage", tags=["Wastage & Scrap Tracking"])


def get_wastage_repo() -> WastageRepository:
    db = mongodb_manager.get_database()
    return WastageRepository(db)


def serialize_scrap_entry(doc: Dict[str, Any]) -> ScrapEntryResponse:
    return ScrapEntryResponse(
        id=str(doc["_id"]),
        entry_number=doc.get("entry_number", ""),
        entry_date=doc.get("entry_date", ""),
        unit_id=doc.get("unit_id", "Unit_1"),
        production_order_id=doc.get("production_order_id"),
        production_order_number=doc.get("production_order_number"),
        item_id=doc.get("item_id", ""),
        item_code=doc.get("item_code", ""),
        item_name=doc.get("item_name", ""),
        item_type=doc.get("item_type", "RAW_MATERIAL"),
        scrap_category=doc.get("scrap_category", "OTHER"),
        quantity=doc.get("quantity", 0.0),
        uom=doc.get("uom", "KG"),
        unit_cost=doc.get("unit_cost", 0.0),
        total_cost=doc.get("total_cost", 0.0),
        reason=doc.get("reason", ""),
        disposition=doc.get("disposition", "HOLD_REVIEW"),
        status=doc.get("status", "SUBMITTED"),
        operator_name=doc.get("operator_name"),
        machine_id=doc.get("machine_id"),
        notes=doc.get("notes"),
        created_at=doc["created_at"],
        created_by=doc.get("created_by", "SYSTEM"),
        approved_at=doc.get("approved_at"),
        approved_by=doc.get("approved_by"),
        rejection_reason=doc.get("rejection_reason"),
    )


# -------------------------------------------------------------
# 1. Wastage Summary & KPIs
# -------------------------------------------------------------
@router.get("/summary", response_model=WastageDashboardSummary)
async def get_wastage_summary(
    unit_id: Optional[str] = Query(None, description="Optional unit filter: Unit_1 | Unit_2"),
    current_user: Dict[str, Any] = Depends(require_permission(ModuleName.WASTAGE, ActionType.READ)),
    repo: WastageRepository = Depends(get_wastage_repo),
):
    """Retrieve high-level wastage dashboard metrics and category breakdown."""
    return await repo.get_wastage_summary(unit_id)


# -------------------------------------------------------------
# 2. Planned vs Actual Wastage Comparison
# -------------------------------------------------------------
@router.get("/comparison/{order_id}", response_model=PlannedVsActualWastageResponse)
async def get_planned_vs_actual_wastage(
    order_id: str = Path(..., description="Production Order ID or Order Number"),
    current_user: Dict[str, Any] = Depends(require_permission(ModuleName.WASTAGE, ActionType.READ)),
    repo: WastageRepository = Depends(get_wastage_repo),
):
    """
    Reconcile planned wastage (from production order's snapshot BOM) against
    actual approved shop-floor scrap records.
    """
    try:
        data = await repo.get_planned_vs_actual_wastage(order_id)
        return PlannedVsActualWastageResponse(**data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# -------------------------------------------------------------
# 3. Scrap Entries CRUD & Workflows
# -------------------------------------------------------------
@router.post("/entries", response_model=ScrapEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_scrap_entry(
    entry_data: ScrapEntryCreate,
    current_user: Dict[str, Any] = Depends(require_permission(ModuleName.WASTAGE, ActionType.CREATE)),
    csrf: None = Depends(verify_csrf_token),
    repo: WastageRepository = Depends(get_wastage_repo),
):
    """
    Create a new daily scrap/wastage record with production order link,
    standard costing, and duplicate prevention.
    """
    try:
        doc = await repo.create_scrap_entry(
            entry_data=entry_data,
            created_by=current_user.get("email", "USER"),
        )
        return serialize_scrap_entry(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/entries", response_model=PaginatedResponse[ScrapEntryResponse])
async def list_scrap_entries(
    unit_id: Optional[str] = Query(None),
    production_order_id: Optional[str] = Query(None),
    scrap_category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(require_permission(ModuleName.WASTAGE, ActionType.READ)),
    repo: WastageRepository = Depends(get_wastage_repo),
):
    """List scrap records with search, date range, category, and status filters."""
    items, total = await repo.list_scrap_entries(
        unit_id=unit_id,
        production_order_id=production_order_id,
        scrap_category=scrap_category,
        status=status_filter,
        start_date=start_date,
        end_date=end_date,
        search=search,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[serialize_scrap_entry(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if page_size > 0 else 0,
    )


@router.get("/entries/{id}", response_model=ScrapEntryResponse)
async def get_scrap_entry(
    id: str = Path(..., description="Scrap Entry ID or sequence number"),
    current_user: Dict[str, Any] = Depends(require_permission(ModuleName.WASTAGE, ActionType.READ)),
    repo: WastageRepository = Depends(get_wastage_repo),
):
    """Retrieve single scrap entry details."""
    doc = await repo.get_scrap_entry_by_id(id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scrap entry not found.")
    return serialize_scrap_entry(doc)


@router.put("/entries/{id}", response_model=ScrapEntryResponse)
async def update_scrap_entry(
    update_data: ScrapEntryUpdate,
    id: str = Path(..., description="Scrap Entry ID"),
    current_user: Dict[str, Any] = Depends(require_permission(ModuleName.WASTAGE, ActionType.UPDATE)),
    csrf: None = Depends(verify_csrf_token),
    repo: WastageRepository = Depends(get_wastage_repo),
):
    """Update or correct a scrap record (allowed while in DRAFT or SUBMITTED status)."""
    try:
        updated = await repo.update_scrap_entry(
            entry_id=id,
            update_data=update_data,
            updated_by=current_user.get("email", "USER"),
        )
        return serialize_scrap_entry(updated)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/entries/{id}/approve", response_model=ScrapEntryResponse)
async def approve_scrap_entry(
    approval_data: ScrapApprovalRequest,
    id: str = Path(..., description="Scrap Entry ID"),
    current_user: Dict[str, Any] = Depends(require_permission(ModuleName.WASTAGE, ActionType.APPROVE)),
    csrf: None = Depends(verify_csrf_token),
    repo: WastageRepository = Depends(get_wastage_repo),
):
    """Authorize scrap entry and approve disposition."""
    try:
        doc = await repo.approve_scrap_entry(
            entry_id=id,
            approval_data=approval_data,
            approved_by=current_user.get("email", "USER"),
        )
        return serialize_scrap_entry(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/entries/{id}/reject", response_model=ScrapEntryResponse)
async def reject_scrap_entry(
    rejection_data: ScrapRejectionRequest,
    id: str = Path(..., description="Scrap Entry ID"),
    current_user: Dict[str, Any] = Depends(require_permission(ModuleName.WASTAGE, ActionType.APPROVE)),
    csrf: None = Depends(verify_csrf_token),
    repo: WastageRepository = Depends(get_wastage_repo),
):
    """Reject scrap record with explicit reason."""
    try:
        doc = await repo.reject_scrap_entry(
            entry_id=id,
            rejection_data=rejection_data,
            rejected_by=current_user.get("email", "USER"),
        )
        return serialize_scrap_entry(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
