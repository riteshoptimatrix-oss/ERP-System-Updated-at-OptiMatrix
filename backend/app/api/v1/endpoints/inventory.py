from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.database.mongodb import mongodb_manager
from app.api.deps import get_current_active_user, require_permission, verify_csrf_token
from app.repositories.inventory_repository import InventoryRepository
from app.schemas.inventory import (
    StockBalanceResponse,
    MaterialInwardCreate,
    MaterialOutwardCreate,
    StockTransferCreate,
    StockAdjustmentCreate,
    OpeningStockImportRequest,
    StockMovementLedgerResponse,
    LowStockAlertResponse,
    InventoryDashboardSummary,
)
from app.schemas.master import PaginatedResponse

router = APIRouter(prefix="/inventory", tags=["Inventory & Warehouse Management"])


def get_inventory_repo() -> InventoryRepository:
    db = mongodb_manager.get_database()
    return InventoryRepository(db)


# -------------------------------------------------------------
# 1. Inventory Dashboard Summary KPIs
# -------------------------------------------------------------
@router.get("/dashboard", response_model=InventoryDashboardSummary)
async def get_inventory_dashboard_summary(
    unit_id: Optional[str] = Query(None, description="Filter KPI metrics by manufacturing unit"),
    current_user: Dict[str, Any] = Depends(require_permission("inventory", "read")),
) -> InventoryDashboardSummary:
    """Retrieve high-level inventory valuation, alerts count, and stock movement KPIs."""
    target_unit = unit_id
    if current_user.get("role") != "SUPER_ADMIN" and target_unit:
        allowed = current_user.get("allowed_units", ["BOTH"])
        if "BOTH" not in allowed and target_unit not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to facility inventory metrics '{target_unit}' is unauthorized.",
            )

    repo = get_inventory_repo()
    summary = await repo.get_dashboard_summary(target_unit)
    return InventoryDashboardSummary(**summary)


# -------------------------------------------------------------
# 2. Stock Balances Across Warehouses
# -------------------------------------------------------------
@router.get("/balances", response_model=PaginatedResponse[StockBalanceResponse])
async def list_stock_balances(
    item_type: Optional[str] = Query(None, description="Filter by RAW_MATERIAL or FINISHED_GOOD"),
    warehouse_id: Optional[str] = Query(None, description="Filter by warehouse ID"),
    unit_id: Optional[str] = Query(None, description="Filter by unit ID"),
    search: Optional[str] = Query(None, description="Search by item code, item name, or batch"),
    below_reorder_only: bool = Query(False, description="Filter items at or below reorder level"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(require_permission("inventory", "read")),
) -> PaginatedResponse[StockBalanceResponse]:
    """List real-time stock balances across warehouses with live valuation and reservation status."""
    target_unit = unit_id
    if current_user.get("role") != "SUPER_ADMIN" and target_unit:
        allowed = current_user.get("allowed_units", ["BOTH"])
        if "BOTH" not in allowed and target_unit not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to facility stock balances '{target_unit}' is unauthorized.",
            )

    repo = get_inventory_repo()
    items, total = await repo.list_stock_balances(
        item_type=item_type,
        warehouse_id=warehouse_id,
        unit_id=target_unit,
        search=search,
        below_reorder_only=below_reorder_only,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=[StockBalanceResponse(**b) for b in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# -------------------------------------------------------------
# 3. Stock Movement Ledger
# -------------------------------------------------------------
@router.get("/ledger", response_model=PaginatedResponse[StockMovementLedgerResponse])
async def list_movement_ledger(
    item_id: Optional[str] = Query(None, description="Filter by Item ID"),
    warehouse_id: Optional[str] = Query(None, description="Filter by Warehouse ID"),
    unit_id: Optional[str] = Query(None, description="Filter by Unit ID"),
    movement_type: Optional[str] = Query(None, description="Filter by Movement Type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(require_permission("inventory", "read")),
) -> PaginatedResponse[StockMovementLedgerResponse]:
    """Audit log of all immutable stock movements with running balances and references."""
    target_unit = unit_id
    if current_user.get("role") != "SUPER_ADMIN" and target_unit:
        allowed = current_user.get("allowed_units", ["BOTH"])
        if "BOTH" not in allowed and target_unit not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to facility ledger '{target_unit}' is unauthorized.",
            )

    repo = get_inventory_repo()
    entries, total = await repo.list_ledger_entries(
        item_id=item_id,
        warehouse_id=warehouse_id,
        unit_id=target_unit,
        movement_type=movement_type,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=[StockMovementLedgerResponse(**e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# -------------------------------------------------------------
# 4. Low Stock Alerts
# -------------------------------------------------------------
@router.get("/low-stock-alerts", response_model=List[LowStockAlertResponse])
async def get_low_stock_alerts(
    unit_id: Optional[str] = Query(None, description="Filter alerts by unit"),
    current_user: Dict[str, Any] = Depends(require_permission("inventory", "read")),
) -> List[LowStockAlertResponse]:
    """Retrieve items needing replenishment (available quantity <= reorder level)."""
    target_unit = unit_id
    if current_user.get("role") != "SUPER_ADMIN" and target_unit:
        allowed = current_user.get("allowed_units", ["BOTH"])
        if "BOTH" not in allowed and target_unit not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to facility alerts '{target_unit}' is unauthorized.",
            )

    repo = get_inventory_repo()
    alerts = await repo.get_low_stock_alerts(target_unit)
    return [LowStockAlertResponse(**a) for a in alerts]


# -------------------------------------------------------------
# 5. Material Inward (Receipt / GRN)
# -------------------------------------------------------------
@router.post("/inward", response_model=StockMovementLedgerResponse, status_code=status.HTTP_201_CREATED)
async def create_material_inward(
    inward_data: MaterialInwardCreate,
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("inventory", "create")),
) -> StockMovementLedgerResponse:
    """Record receipt of raw materials or finished products into a designated warehouse."""
    if current_user.get("role") != "SUPER_ADMIN":
        allowed = current_user.get("allowed_units", ["BOTH"])
        if "BOTH" not in allowed and inward_data.unit_id.value not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unauthorized to inward materials into facility '{inward_data.unit_id.value}'.",
            )

    repo = get_inventory_repo()
    try:
        ledger_entry = await repo.process_material_inward(
            inward_data=inward_data,
            created_by=current_user.get("email", "USER"),
        )
        return StockMovementLedgerResponse(
            id=str(ledger_entry["_id"]),
            transaction_number=ledger_entry["transaction_number"],
            movement_type=ledger_entry["movement_type"],
            item_id=ledger_entry["item_id"],
            item_code=ledger_entry["item_code"],
            item_name=ledger_entry["item_name"],
            item_type=ledger_entry["item_type"],
            warehouse_id=ledger_entry["warehouse_id"],
            warehouse_code=ledger_entry["warehouse_code"],
            warehouse_name=ledger_entry["warehouse_name"],
            unit_id=ledger_entry["unit_id"],
            batch_no=ledger_entry["batch_no"],
            quantity_change=ledger_entry["quantity_change"],
            balance_after=ledger_entry["balance_after"],
            uom=ledger_entry["uom"],
            reference_id=ledger_entry.get("reference_id"),
            reference_type=ledger_entry.get("reference_type"),
            reason=ledger_entry.get("reason"),
            notes=ledger_entry.get("notes"),
            created_at=ledger_entry["created_at"],
            created_by=ledger_entry["created_by"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# 6. Material Outward (Issue to Floor)
# -------------------------------------------------------------
@router.post("/outward", response_model=StockMovementLedgerResponse, status_code=status.HTTP_201_CREATED)
async def create_material_outward(
    outward_data: MaterialOutwardCreate,
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("inventory", "update")),
) -> StockMovementLedgerResponse:
    """Issue raw materials to production floor or machine lines with atomic negative stock prevention."""
    if current_user.get("role") != "SUPER_ADMIN":
        allowed = current_user.get("allowed_units", ["BOTH"])
        if "BOTH" not in allowed and outward_data.unit_id.value not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unauthorized to issue materials from facility '{outward_data.unit_id.value}'.",
            )

    repo = get_inventory_repo()
    try:
        ledger_entry = await repo.process_material_outward(
            outward_data=outward_data,
            created_by=current_user.get("email", "USER"),
        )
        return StockMovementLedgerResponse(
            id=str(ledger_entry["_id"]),
            transaction_number=ledger_entry["transaction_number"],
            movement_type=ledger_entry["movement_type"],
            item_id=ledger_entry["item_id"],
            item_code=ledger_entry["item_code"],
            item_name=ledger_entry["item_name"],
            item_type=ledger_entry["item_type"],
            warehouse_id=ledger_entry["warehouse_id"],
            warehouse_code=ledger_entry["warehouse_code"],
            warehouse_name=ledger_entry["warehouse_name"],
            unit_id=ledger_entry["unit_id"],
            batch_no=ledger_entry["batch_no"],
            quantity_change=ledger_entry["quantity_change"],
            balance_after=ledger_entry["balance_after"],
            uom=ledger_entry["uom"],
            reference_id=ledger_entry.get("reference_id"),
            reference_type=ledger_entry.get("reference_type"),
            reason=ledger_entry.get("reason"),
            notes=ledger_entry.get("notes"),
            created_at=ledger_entry["created_at"],
            created_by=ledger_entry["created_by"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# 7. Stock Transfer (Inter-Warehouse / Inter-Unit)
# -------------------------------------------------------------
@router.post("/transfer", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_stock_transfer(
    transfer_data: StockTransferCreate,
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("inventory", "update")),
) -> Dict[str, Any]:
    """Transfer materials between warehouses or facilities with paired ledger audit entries."""
    repo = get_inventory_repo()
    try:
        result = await repo.process_stock_transfer(
            transfer_data=transfer_data,
            created_by=current_user.get("email", "USER"),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# 8. Stock Adjustment (Audit Justification Required)
# -------------------------------------------------------------
@router.post("/adjust", response_model=StockMovementLedgerResponse, status_code=status.HTTP_201_CREATED)
async def create_stock_adjustment(
    adjustment_data: StockAdjustmentCreate,
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("inventory", "post")),
) -> StockMovementLedgerResponse:
    """Record authorized stock adjustments for physical discrepancy, scrap, or damage."""
    repo = get_inventory_repo()
    try:
        ledger_entry = await repo.process_stock_adjustment(
            adjustment_data=adjustment_data,
            created_by=current_user.get("email", "USER"),
        )
        return StockMovementLedgerResponse(
            id=str(ledger_entry["_id"]),
            transaction_number=ledger_entry["transaction_number"],
            movement_type=ledger_entry["movement_type"],
            item_id=ledger_entry["item_id"],
            item_code=ledger_entry["item_code"],
            item_name=ledger_entry["item_name"],
            item_type=ledger_entry["item_type"],
            warehouse_id=ledger_entry["warehouse_id"],
            warehouse_code=ledger_entry["warehouse_code"],
            warehouse_name=ledger_entry["warehouse_name"],
            unit_id=ledger_entry["unit_id"],
            batch_no=ledger_entry["batch_no"],
            quantity_change=ledger_entry["quantity_change"],
            balance_after=ledger_entry["balance_after"],
            uom=ledger_entry["uom"],
            reference_id=ledger_entry.get("reference_id"),
            reference_type=ledger_entry.get("reference_type"),
            reason=ledger_entry.get("reason"),
            notes=ledger_entry.get("notes"),
            created_at=ledger_entry["created_at"],
            created_by=ledger_entry["created_by"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# 9. Opening Stock Bulk Import
# -------------------------------------------------------------
@router.post("/opening-stock", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def import_opening_stock(
    import_request: OpeningStockImportRequest,
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("inventory", "create")),
) -> Dict[str, Any]:
    """Bulk import opening stock with duplicate prevention and validation."""
    repo = get_inventory_repo()
    result = await repo.import_opening_stock(
        import_request=import_request,
        created_by=current_user.get("email", "USER"),
    )
    return result
