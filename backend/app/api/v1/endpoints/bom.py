from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from app.database.mongodb import mongodb_manager
from app.api.deps import get_current_active_user, require_permission, verify_csrf_token
from app.repositories.bom_repository import BOMRepository
from app.schemas.bom import (
    BOMCreate,
    BOMUpdate,
    BOMRevisionCreate,
    BOMApprovalAction,
    BOMResponse,
    BOMDashboardSummary,
    MaterialRequirementCalculationRequest,
    MaterialRequirementCalculationResponse,
    BOMImportRequest,
)
from app.schemas.master import PaginatedResponse

router = APIRouter(prefix="/bom", tags=["Bill of Materials (BOM)"])


def get_bom_repo() -> BOMRepository:
    db = mongodb_manager.get_database()
    return BOMRepository(db)


def serialize_bom(doc: Dict[str, Any]) -> BOMResponse:
    """Formats MongoDB BOM document to BOMResponse."""
    return BOMResponse(
        id=str(doc["_id"]),
        bom_number=doc.get("bom_number", ""),
        product_id=doc["product_id"],
        product_code=doc.get("product_code", ""),
        product_name=doc.get("product_name", ""),
        product_uom=doc.get("product_uom", "PCS"),
        unit_id=doc.get("unit_id", "Unit_1"),
        base_quantity=doc.get("base_quantity", 1.0),
        revision_no=doc.get("revision_no", "R1"),
        status=doc.get("status", "DRAFT"),
        is_active=doc.get("is_active", False),
        effective_from=doc.get("effective_from"),
        effective_to=doc.get("effective_to"),
        description=doc.get("description"),
        total_estimated_cost=doc.get("total_estimated_cost", 0.0),
        components=doc.get("components", []),
        approved_by=doc.get("approved_by"),
        approved_at=doc.get("approved_at"),
        created_at=doc["created_at"],
        created_by=doc.get("created_by", "SYSTEM"),
        updated_at=doc.get("updated_at"),
        updated_by=doc.get("updated_by"),
    )


# -------------------------------------------------------------
# 1. Dashboard Metrics
# -------------------------------------------------------------
@router.get("/dashboard", response_model=BOMDashboardSummary)
async def get_bom_dashboard_summary(
    unit_id: Optional[str] = Query(None, description="Filter summary by unit"),
    current_user: Dict[str, Any] = Depends(require_permission("bom", "read")),
) -> BOMDashboardSummary:
    """Retrieve high-level statistics on BOMs, approvals, and coverage."""
    repo = get_bom_repo()
    summary = await repo.get_dashboard_summary(unit_id)
    return BOMDashboardSummary(**summary)


# -------------------------------------------------------------
# 2. List & Search BOMs
# -------------------------------------------------------------
@router.get("", response_model=PaginatedResponse[BOMResponse])
async def list_boms(
    product_id: Optional[str] = Query(None, description="Filter by Product ID"),
    unit_id: Optional[str] = Query(None, description="Filter by Manufacturing Unit"),
    status: Optional[str] = Query(None, description="Filter by BOM Status"),
    is_active: Optional[bool] = Query(None, description="Filter active versions only"),
    search: Optional[str] = Query(None, description="Search by BOM number, product, or description"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(require_permission("bom", "read")),
) -> PaginatedResponse[BOMResponse]:
    """Retrieve paginated Bill of Materials."""
    repo = get_bom_repo()
    docs, total = await repo.list_boms(
        product_id=product_id,
        unit_id=unit_id,
        status=status,
        is_active=is_active,
        search=search,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=[serialize_bom(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# -------------------------------------------------------------
# 3. Create Draft BOM
# -------------------------------------------------------------
@router.post("", response_model=BOMResponse, status_code=status.HTTP_201_CREATED)
async def create_bom(
    bom_data: BOMCreate,
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("bom", "create")),
) -> BOMResponse:
    """Create a new Bill of Materials in DRAFT status with non-circularity and UoM checks."""
    repo = get_bom_repo()
    try:
        doc = await repo.create_bom(
            bom_data=bom_data,
            created_by=current_user.get("email", "USER"),
        )
        return serialize_bom(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# 4. Get BOM Details
# -------------------------------------------------------------
@router.get("/{bom_id}", response_model=BOMResponse)
async def get_bom(
    bom_id: str = Path(..., description="BOM ID or BOM Number"),
    current_user: Dict[str, Any] = Depends(require_permission("bom", "read")),
) -> BOMResponse:
    """Get full details of a specific Bill of Materials and its component breakdown."""
    repo = get_bom_repo()
    doc = await repo.get_by_id(bom_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BOM not found.")
    return serialize_bom(doc)


# -------------------------------------------------------------
# 5. Update Draft BOM
# -------------------------------------------------------------
@router.put("/{bom_id}", response_model=BOMResponse)
async def update_bom(
    bom_id: str = Path(..., description="BOM ID or BOM Number"),
    update_data: BOMUpdate = ...,
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("bom", "update")),
) -> BOMResponse:
    """Update a draft BOM. Blocked if the BOM is already APPROVED."""
    repo = get_bom_repo()
    try:
        doc = await repo.update_bom(
            bom_id=bom_id,
            update_data=update_data,
            updated_by=current_user.get("email", "USER"),
        )
        return serialize_bom(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# 6. Clone New Revision
# -------------------------------------------------------------
@router.post("/{bom_id}/revisions", response_model=BOMResponse, status_code=status.HTTP_201_CREATED)
async def create_new_revision(
    bom_id: str = Path(..., description="Base BOM ID"),
    rev_data: BOMRevisionCreate = ...,
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("bom", "create")),
) -> BOMResponse:
    """Create a new engineering revision cloned from an existing BOM."""
    repo = get_bom_repo()
    try:
        doc = await repo.create_revision(
            base_bom_id=bom_id,
            rev_data=rev_data,
            created_by=current_user.get("email", "USER"),
        )
        return serialize_bom(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# 7. Workflow: Submit & Approve
# -------------------------------------------------------------
@router.post("/{bom_id}/submit", response_model=BOMResponse)
async def submit_bom_for_approval(
    bom_id: str = Path(...),
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("bom", "update")),
) -> BOMResponse:
    """Submit a draft BOM for management approval."""
    repo = get_bom_repo()
    try:
        doc = await repo.submit_for_approval(
            bom_id=bom_id,
            submitted_by=current_user.get("email", "USER"),
        )
        return serialize_bom(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{bom_id}/approve", response_model=BOMResponse)
async def approve_bom_revision(
    bom_id: str = Path(...),
    action: BOMApprovalAction = ...,
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("bom", "approve")),
) -> BOMResponse:
    """Approve or reject a BOM revision. Approving locks the version and sets active state."""
    repo = get_bom_repo()
    try:
        doc = await repo.approve_bom(
            bom_id=bom_id,
            action=action,
            reviewed_by=current_user.get("email", "USER"),
        )
        return serialize_bom(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# 8. Material Requirements Explosion & Stock Shortage Check
# -------------------------------------------------------------
@router.post("/{bom_id}/calculate-requirements", response_model=MaterialRequirementCalculationResponse)
async def calculate_material_requirements(
    bom_id: str = Path(...),
    calc_request: MaterialRequirementCalculationRequest = ...,
    current_user: Dict[str, Any] = Depends(require_permission("bom", "read")),
) -> MaterialRequirementCalculationResponse:
    """
    Explodes the BOM for target batch production quantity.
    Checks live inventory without mutating stock balances.
    """
    repo = get_bom_repo()
    try:
        result = await repo.calculate_material_requirements(
            bom_id=bom_id,
            calc_request=calc_request,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# 9. Bulk Import
# -------------------------------------------------------------
@router.post("/import", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def import_boms(
    import_request: BOMImportRequest,
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("bom", "create")),
) -> Dict[str, Any]:
    """Bulk import multi-level BOMs from templates."""
    repo = get_bom_repo()
    res = await repo.import_boms(
        import_request=import_request,
        created_by=current_user.get("email", "USER"),
    )
    return res
