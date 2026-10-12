from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from app.database.mongodb import mongodb_manager
from app.api.deps import get_current_active_user, require_permission, verify_csrf_token
from app.repositories.production_repository import ProductionRepository
from app.schemas.production import (
    ProductionOrderCreate,
    MaterialIssueRequest,
    ProductionOutputInput,
    ProductionOrderResponse,
    ProductionVarianceReport,
    ProductionDashboardSummary,
)
from app.schemas.master import PaginatedResponse

router = APIRouter(prefix="/production", tags=["Production Planning & WIP"])


def get_production_repo() -> ProductionRepository:
    db = mongodb_manager.get_database()
    return ProductionRepository(db)


def serialize_production_order(doc: Dict[str, Any]) -> ProductionOrderResponse:
    """Formats MongoDB production order document to ProductionOrderResponse."""
    return ProductionOrderResponse(
        id=str(doc["_id"]),
        order_number=doc.get("order_number", ""),
        product_id=doc["product_id"],
        product_code=doc.get("product_code", ""),
        product_name=doc.get("product_name", ""),
        product_uom=doc.get("product_uom", "PCS"),
        bom_id=doc["bom_id"],
        bom_number=doc.get("bom_number", ""),
        bom_revision_no=doc.get("bom_revision_no", "R1"),
        unit_id=doc.get("unit_id", "Unit_1"),
        target_warehouse_id=doc["target_warehouse_id"],
        target_warehouse_code=doc.get("target_warehouse_code", ""),
        planned_quantity=doc.get("planned_quantity", 0.0),
        produced_quantity=doc.get("produced_quantity", 0.0),
        rejected_quantity=doc.get("rejected_quantity", 0.0),
        remaining_quantity=doc.get("remaining_quantity", 0.0),
        status=doc.get("status", "DRAFT"),
        completion_percentage=doc.get("completion_percentage", 0.0),
        materials=doc.get("materials", []),
        scheduled_start_date=doc.get("scheduled_start_date"),
        target_completion_date=doc.get("target_completion_date"),
        actual_start_date=doc.get("actual_start_date"),
        actual_completion_date=doc.get("actual_completion_date"),
        notes=doc.get("notes"),
        cancellation_reason=doc.get("cancellation_reason"),
        created_at=doc["created_at"],
        created_by=doc.get("created_by", "SYSTEM"),
        updated_at=doc.get("updated_at"),
        updated_by=doc.get("updated_by"),
    )


# -------------------------------------------------------------
# 1. Dashboard Metrics
# -------------------------------------------------------------
@router.get("/dashboard", response_model=ProductionDashboardSummary)
async def get_production_dashboard(
    unit_id: Optional[str] = Query(None, description="Filter summary by unit"),
    current_user: Dict[str, Any] = Depends(require_permission("production", "read")),
) -> ProductionDashboardSummary:
    """Retrieve shop floor operational KPIs: active orders, output, and yield percentage."""
    repo = get_production_repo()
    summary = await repo.get_dashboard_summary(unit_id)
    return ProductionDashboardSummary(**summary)


# -------------------------------------------------------------
# 2. List & Search Production Orders
# -------------------------------------------------------------
@router.get("/orders", response_model=PaginatedResponse[ProductionOrderResponse])
async def list_production_orders(
    product_id: Optional[str] = Query(None, description="Filter by Product ID"),
    unit_id: Optional[str] = Query(None, description="Filter by Facility Unit"),
    status: Optional[str] = Query(None, description="Filter by Order Status"),
    search: Optional[str] = Query(None, description="Search by Order #, product, or BOM"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(require_permission("production", "read")),
) -> PaginatedResponse[ProductionOrderResponse]:
    """Retrieve paginated list of production orders."""
    repo = get_production_repo()
    docs, total = await repo.list_orders(
        product_id=product_id,
        unit_id=unit_id,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=[serialize_production_order(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# -------------------------------------------------------------
# 3. Create Production Order
# -------------------------------------------------------------
@router.post("/orders", response_model=ProductionOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_production_order(
    order_data: ProductionOrderCreate,
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("production", "create")),
) -> ProductionOrderResponse:
    """Create a new production order snapshotting the active approved BOM recipe."""
    repo = get_production_repo()
    try:
        doc = await repo.create_order(
            order_data=order_data,
            created_by=current_user.get("email", "USER"),
        )
        return serialize_production_order(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# 4. Get Production Order Details
# -------------------------------------------------------------
@router.get("/orders/{order_id}", response_model=ProductionOrderResponse)
async def get_production_order(
    order_id: str = Path(..., description="Production Order ID or Order Number"),
    current_user: Dict[str, Any] = Depends(require_permission("production", "read")),
) -> ProductionOrderResponse:
    """Get full details of a production order including material consumption status."""
    repo = get_production_repo()
    doc = await repo.get_by_id(order_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production order not found.")
    return serialize_production_order(doc)


# -------------------------------------------------------------
# 5. Release Order & Reserve Materials
# -------------------------------------------------------------
@router.post("/orders/{order_id}/release", response_model=ProductionOrderResponse)
async def release_production_order(
    order_id: str = Path(...),
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("production", "update")),
) -> ProductionOrderResponse:
    """Release a draft production order to the shop floor and reserve raw materials in inventory."""
    repo = get_production_repo()
    try:
        doc = await repo.release_order(
            order_id=order_id,
            released_by=current_user.get("email", "USER"),
        )
        return serialize_production_order(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# 6. Issue Materials (Consumption)
# -------------------------------------------------------------
@router.post("/orders/{order_id}/issue-materials", response_model=ProductionOrderResponse)
async def issue_materials_to_order(
    order_id: str = Path(...),
    issue_request: MaterialIssueRequest = ...,
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("production", "post")),
) -> ProductionOrderResponse:
    """Issue raw materials from stock to production order with atomic inventory deduction."""
    repo = get_production_repo()
    try:
        doc = await repo.issue_materials(
            order_id=order_id,
            issue_request=issue_request,
            issued_by=current_user.get("email", "USER"),
        )
        return serialize_production_order(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# 7. Record Production Output (Good & Scrap)
# -------------------------------------------------------------
@router.post("/orders/{order_id}/record-output", response_model=ProductionOrderResponse)
async def record_production_output(
    order_id: str = Path(...),
    output_input: ProductionOutputInput = ...,
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("production", "post")),
) -> ProductionOrderResponse:
    """Record completed machine output, log scraps, and automatically receipt into finished goods inventory."""
    repo = get_production_repo()
    try:
        doc = await repo.record_output(
            order_id=order_id,
            output_input=output_input,
            recorded_by=current_user.get("email", "USER"),
        )
        return serialize_production_order(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# 8. Cancel Production Order
# -------------------------------------------------------------
@router.post("/orders/{order_id}/cancel", response_model=ProductionOrderResponse)
async def cancel_production_order(
    order_id: str = Path(...),
    reason: str = Query(..., min_length=3, description="Cancellation reason"),
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("production", "update")),
) -> ProductionOrderResponse:
    """Cancel a production order and unreserve any remaining allocated raw materials."""
    repo = get_production_repo()
    try:
        doc = await repo.cancel_order(
            order_id=order_id,
            reason=reason,
            cancelled_by=current_user.get("email", "USER"),
        )
        return serialize_production_order(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# 9. Material Variance Report
# -------------------------------------------------------------
@router.get("/orders/{order_id}/variance", response_model=ProductionVarianceReport)
async def get_order_variance_report(
    order_id: str = Path(...),
    current_user: Dict[str, Any] = Depends(require_permission("production", "read")),
) -> ProductionVarianceReport:
    """Retrieve standard vs actual material consumption variance and yield efficiency."""
    repo = get_production_repo()
    try:
        return await repo.get_variance_report(order_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
