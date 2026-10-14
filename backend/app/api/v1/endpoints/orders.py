from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from app.database.mongodb import mongodb_manager
from app.api.deps import get_current_active_user, require_permission, verify_csrf_token
from app.repositories.orders_repository import OrdersRepository
from app.services.inventory_contract import InventoryIntegrationContract
from app.schemas.orders import (
    SalesOrderCreate,
    SalesOrderUpdate,
    SalesOrderResponse,
    PackingSlipCreate,
    PackingSlipResponse,
    DispatchRecordCreate,
    DispatchRecordResponse,
    OrderDashboardSummary,
    OrderCancellationRequest,
    StockAvailabilityResult,
    OrderPlanningItem,
    OrderPlanningUpdate,
    OrderPlanningSummary,
)
from app.schemas.master import PaginatedResponse

router = APIRouter(prefix="/orders", tags=["Sales Orders & Dispatch"])


def get_orders_repo() -> OrdersRepository:
    db = mongodb_manager.get_database()
    return OrdersRepository(db)


def get_inventory_contract() -> InventoryIntegrationContract:
    db = mongodb_manager.get_database()
    return InventoryIntegrationContract(db)


# -------------------------------------------------------------
# 1. Dashboard KPI Metrics
# -------------------------------------------------------------
@router.get("/dashboard", response_model=OrderDashboardSummary)
async def get_orders_dashboard(
    unit_id: Optional[str] = Query(None, description="Filter KPI by manufacturing unit"),
    current_user: Dict[str, Any] = Depends(require_permission("orders", "read")),
) -> OrderDashboardSummary:
    """Retrieve high-level Sales Order, Dispatch, and pipeline financial metrics."""
    target_unit = unit_id
    if current_user.get("role") != "SUPER_ADMIN" and target_unit:
        allowed = current_user.get("allowed_units", ["BOTH"])
        if "BOTH" not in allowed and target_unit not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to facility metrics '{target_unit}' is unauthorized.",
            )

    repo = get_orders_repo()
    summary = await repo.get_dashboard_summary(target_unit)
    return OrderDashboardSummary(**summary)


# -------------------------------------------------------------
# Order Planning (By Variant and Length)
# Updated by Taha; one line per variant and length
# -------------------------------------------------------------
@router.get("/planning", response_model=List[OrderPlanningItem])
async def list_order_planning(
    unit_id: Optional[str] = Query(None, description="Filter planning lines by unit"),
    priority: Optional[str] = Query(None, description="Filter by priority: URGENT, HIGH, MEDIUM, LOW"),
    order_status: Optional[str] = Query(None, description="Filter by order status"),
    final_approval: Optional[str] = Query(None, description="Filter by approval: APPROVED, PENDING, ON_HOLD"),
    search: Optional[str] = Query(None, description="Search order#, customer, variant, length, brand"),
    current_user: Dict[str, Any] = Depends(require_permission("orders", "read")),
) -> List[OrderPlanningItem]:
    """
    Retrieve one line per variant and length for shop-floor production planning.
    Includes live calculated Balance Qty (Order - Produced) and Dispatch Balance (Order - Dispatched).
    """
    repo = get_orders_repo()
    docs = await repo.list_order_planning(
        unit_id=unit_id,
        priority=priority,
        order_status=order_status,
        final_approval=final_approval,
        search=search,
    )
    return [OrderPlanningItem(**d) for d in docs]


@router.get("/planning/summary", response_model=OrderPlanningSummary)
async def get_order_planning_summary(
    unit_id: Optional[str] = Query(None, description="Filter summary by unit"),
    current_user: Dict[str, Any] = Depends(require_permission("orders", "read")),
) -> OrderPlanningSummary:
    """
    Aggregated quantities and line statistics for the variant and length planning sheet.
    """
    repo = get_orders_repo()
    res = await repo.get_order_planning_summary(unit_id=unit_id)
    return OrderPlanningSummary(**res)


@router.put("/planning/{planning_id}", response_model=OrderPlanningItem)
async def update_order_planning(
    planning_id: str = Path(..., description="Order planning item ID"),
    payload: OrderPlanningUpdate = ...,
    current_user: Dict[str, Any] = Depends(require_permission("orders", "update")),
    _: None = Depends(verify_csrf_token),
) -> OrderPlanningItem:
    """
    Update planned quantity, produced quantity, approval status, or remarks on a planning line.
    """
    repo = get_orders_repo()
    user_name = current_user.get("full_name") or current_user.get("email") or "Taha"
    updated = await repo.update_order_planning_item(
        item_id=planning_id,
        update_data=payload.model_dump(exclude_unset=True),
        updated_by=user_name,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order planning record '{planning_id}' not found.",
        )
    return OrderPlanningItem(**updated)


@router.post("/planning/sync", response_model=Dict[str, Any])
async def sync_order_planning(
    current_user: Dict[str, Any] = Depends(require_permission("orders", "create")),
    _: None = Depends(verify_csrf_token),
) -> Dict[str, Any]:
    """
    Manually synchronize confirmed orders into the variant & length planning matrix.
    """
    repo = get_orders_repo()
    count = await repo.sync_order_planning_from_orders()
    return {"message": "Order planning synchronized successfully", "new_lines_created": count}


# -------------------------------------------------------------
# 2. List & Search Sales Orders
# -------------------------------------------------------------
@router.get("", response_model=PaginatedResponse[SalesOrderResponse])
async def list_orders(
    search: Optional[str] = Query(None, description="Search order number, customer name/code, or PO#"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by OrderStatus"),
    customer_id: Optional[str] = Query(None, description="Filter by customer"),
    unit_id: Optional[str] = Query(None, description="Filter by plant"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: Dict[str, Any] = Depends(require_permission("orders", "read")),
) -> PaginatedResponse[SalesOrderResponse]:
    """Retrieve paginated sales orders with unit scoping and filters."""
    target_unit = unit_id
    if current_user.get("role") != "SUPER_ADMIN":
        allowed = current_user.get("allowed_units", ["BOTH"])
        if "BOTH" not in allowed:
            if target_unit and target_unit not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access to unit '{target_unit}' is unauthorized.",
                )
            if not target_unit:
                target_unit = allowed[0]

    repo = get_orders_repo()
    order_dir = -1 if sort_order.lower() == "desc" else 1
    orders, total = await repo.list_orders(
        search=search,
        status=status_filter,
        customer_id=customer_id,
        unit_id=target_unit,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=order_dir,
    )

    items: List[SalesOrderResponse] = []
    for doc in orders:
        doc["id"] = str(doc["_id"])
        items.append(SalesOrderResponse(**doc))

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse[SalesOrderResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# -------------------------------------------------------------
# 3. Create Sales Order
# -------------------------------------------------------------
@router.post("", response_model=SalesOrderResponse, status_code=201)
async def create_sales_order(
    payload: SalesOrderCreate,
    current_user: Dict[str, Any] = Depends(require_permission("orders", "create")),
    _: None = Depends(verify_csrf_token),
) -> SalesOrderResponse:
    """Create a new Sales Order linked to customer and finished products."""
    if current_user.get("role") != "SUPER_ADMIN":
        allowed = current_user.get("allowed_units", ["BOTH"])
        if "BOTH" not in allowed and payload.unit_id.value not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot create orders for unit '{payload.unit_id.value}'.",
            )

    repo = get_orders_repo()
    try:
        created = await repo.create_sales_order(payload, created_by=current_user.get("email", "unknown"))
        created["id"] = str(created["_id"])
        return SalesOrderResponse(**created)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


# -------------------------------------------------------------
# 4. Get Sales Order Details & Audit Timeline
# -------------------------------------------------------------
@router.get("/{id}", response_model=SalesOrderResponse)
async def get_sales_order(
    id: str = Path(..., description="Sales Order ID or order number"),
    current_user: Dict[str, Any] = Depends(require_permission("orders", "read")),
) -> SalesOrderResponse:
    """Retrieve full details of a sales order along with line items and audit timeline."""
    repo = get_orders_repo()
    order = await repo.get_by_id(id)
    if not order:
        order = await repo.get_by_order_number(id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sales order '{id}' not found.")

    if current_user.get("role") != "SUPER_ADMIN":
        allowed = current_user.get("allowed_units", ["BOTH"])
        if "BOTH" not in allowed and order.get("unit_id") not in allowed and order.get("unit_id") != "BOTH":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to this sales order is unauthorized.")

    order["id"] = str(order["_id"])
    activities = await repo.get_order_activities(order["id"])
    for act in activities:
        act["id"] = str(act["_id"])
    order["activities"] = activities

    return SalesOrderResponse(**order)


# -------------------------------------------------------------
# 5. Update Sales Order
# -------------------------------------------------------------
@router.put("/{id}", response_model=SalesOrderResponse)
async def update_sales_order(
    payload: SalesOrderUpdate,
    id: str = Path(...),
    current_user: Dict[str, Any] = Depends(require_permission("orders", "update")),
    _: None = Depends(verify_csrf_token),
) -> SalesOrderResponse:
    """Update sales order details (permitted only in DRAFT or SUBMITTED status)."""
    repo = get_orders_repo()
    try:
        updated = await repo.update_sales_order(id, payload, updated_by=current_user.get("email", "unknown"))
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sales order '{id}' not found.")
        updated["id"] = str(updated["_id"])
        return SalesOrderResponse(**updated)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


# -------------------------------------------------------------
# 6. Workflow Transitions: Submit, Confirm, Cancel
# -------------------------------------------------------------
@router.post("/{id}/submit", response_model=SalesOrderResponse)
async def submit_order(
    id: str = Path(...),
    current_user: Dict[str, Any] = Depends(require_permission("orders", "update")),
    _: None = Depends(verify_csrf_token),
) -> SalesOrderResponse:
    """Submit DRAFT sales order for approval."""
    repo = get_orders_repo()
    try:
        order = await repo.submit_order(id, user_email=current_user.get("email", "unknown"))
        order["id"] = str(order["_id"])
        return SalesOrderResponse(**order)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


@router.post("/{id}/confirm", response_model=SalesOrderResponse)
async def confirm_order(
    id: str = Path(...),
    current_user: Dict[str, Any] = Depends(require_permission("orders", "update")),
    _: None = Depends(verify_csrf_token),
) -> SalesOrderResponse:
    """Confirm SUBMITTED sales order, making it ready for packing and dispatch."""
    repo = get_orders_repo()
    try:
        order = await repo.confirm_order(id, user_email=current_user.get("email", "unknown"))
        order["id"] = str(order["_id"])
        return SalesOrderResponse(**order)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


@router.post("/{id}/cancel", response_model=SalesOrderResponse)
async def cancel_order(
    payload: OrderCancellationRequest,
    id: str = Path(...),
    current_user: Dict[str, Any] = Depends(require_permission("orders", "update")),
    _: None = Depends(verify_csrf_token),
) -> SalesOrderResponse:
    """Cancel sales order with mandatory reason (not permitted once partially or fully dispatched)."""
    repo = get_orders_repo()
    try:
        order = await repo.cancel_order(id, reason=payload.reason, user_email=current_user.get("email", "unknown"))
        order["id"] = str(order["_id"])
        return SalesOrderResponse(**order)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


# -------------------------------------------------------------
# 7. Packing Slip Generation & Listing
# -------------------------------------------------------------
@router.post("/{id}/packing-slips", response_model=PackingSlipResponse, status_code=201)
async def generate_packing_slip(
    payload: PackingSlipCreate,
    id: str = Path(..., description="Sales Order ID"),
    current_user: Dict[str, Any] = Depends(require_permission("sales", "create")),
    _: None = Depends(verify_csrf_token),
) -> PackingSlipResponse:
    """Generate a packing slip referencing an active Sales Order."""
    repo = get_orders_repo()
    try:
        slip = await repo.create_packing_slip(id, payload, created_by=current_user.get("email", "unknown"))
        slip["id"] = str(slip["_id"])
        return PackingSlipResponse(**slip)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


@router.get("/{id}/packing-slips", response_model=List[PackingSlipResponse])
async def list_packing_slips(
    id: str = Path(..., description="Sales Order ID"),
    current_user: Dict[str, Any] = Depends(require_permission("sales", "read")),
) -> List[PackingSlipResponse]:
    """List all packing slips generated for this sales order."""
    repo = get_orders_repo()
    slips = await repo.list_packing_slips(id)
    items: List[PackingSlipResponse] = []
    for s in slips:
        s["id"] = str(s["_id"])
        items.append(PackingSlipResponse(**s))
    return items


# -------------------------------------------------------------
# 8. Dispatch Recording & Listing
# -------------------------------------------------------------
@router.post("/{id}/dispatch", response_model=DispatchRecordResponse, status_code=201)
async def post_dispatch(
    payload: DispatchRecordCreate,
    id: str = Path(..., description="Sales Order ID"),
    current_user: Dict[str, Any] = Depends(require_permission("sales", "post")),
    _: None = Depends(verify_csrf_token),
) -> DispatchRecordResponse:
    """
    Record full or partial dispatch for a sales order.
    Validates quantities, prevents over-dispatch, and updates cumulative order state.
    """
    repo = get_orders_repo()
    try:
        dsp = await repo.create_dispatch(id, payload, dispatched_by=current_user.get("email", "unknown"))
        dsp["id"] = str(dsp["_id"])
        return DispatchRecordResponse(**dsp)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


@router.get("/{id}/dispatches", response_model=List[DispatchRecordResponse])
async def list_dispatches(
    id: str = Path(..., description="Sales Order ID"),
    current_user: Dict[str, Any] = Depends(require_permission("sales", "read")),
) -> List[DispatchRecordResponse]:
    """List all dispatch records posted for a sales order."""
    repo = get_orders_repo()
    records = await repo.list_dispatches(id)
    items: List[DispatchRecordResponse] = []
    for r in records:
        r["id"] = str(r["_id"])
        items.append(DispatchRecordResponse(**r))
    return items


# -------------------------------------------------------------
# 9. Stock Availability Contract Check (Read-Only)
# -------------------------------------------------------------
@router.get("/check-stock/{product_id}", response_model=StockAvailabilityResult)
async def check_inventory_availability(
    product_id: str = Path(..., description="Product ID or code"),
    unit_id: str = Query("Unit_1", description="Manufacturing unit"),
    required_qty: float = Query(1.0, gt=0.0, description="Required quantity"),
    current_user: Dict[str, Any] = Depends(require_permission("orders", "read")),
) -> StockAvailabilityResult:
    """
    Read-only inventory availability check adhering strictly to the non-invented balance contract.
    """
    contract = get_inventory_contract()
    return await contract.check_availability(
        product_id=product_id,
        unit_id=unit_id,
        required_quantity=required_qty,
    )
