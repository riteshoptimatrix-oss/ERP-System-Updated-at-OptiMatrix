from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from app.models.user import ManufacturingUnit


class ItemType(str, Enum):
    RAW_MATERIAL = "RAW_MATERIAL"
    FINISHED_GOOD = "FINISHED_GOOD"


class MovementType(str, Enum):
    OPENING_STOCK = "OPENING_STOCK"
    MATERIAL_INWARD = "MATERIAL_INWARD"
    MATERIAL_OUTWARD = "MATERIAL_OUTWARD"
    TRANSFER_OUT = "TRANSFER_OUT"
    TRANSFER_IN = "TRANSFER_IN"
    ADJUSTMENT_IN = "ADJUSTMENT_IN"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"
    SALES_DISPATCH = "SALES_DISPATCH"
    PRODUCTION_CONSUMPTION = "PRODUCTION_CONSUMPTION"
    PRODUCTION_RECEIPT = "PRODUCTION_RECEIPT"


class AdjustmentReason(str, Enum):
    PHYSICAL_COUNT_DISCREPANCY = "PHYSICAL_COUNT_DISCREPANCY"
    DAMAGED_GOODS = "DAMAGED_GOODS"
    OBSOLETE_SCRAP = "OBSOLETE_SCRAP"
    QUALITY_REJECT = "QUALITY_REJECT"
    SAMPLE_TESTING = "SAMPLE_TESTING"
    CORRECTION = "CORRECTION"


# -------------------------------------------------------------
# Stock Balance Models
# -------------------------------------------------------------
class StockBalanceResponse(BaseModel):
    id: str
    item_id: str
    item_code: str
    item_name: str
    item_type: ItemType
    warehouse_id: str
    warehouse_code: str
    warehouse_name: str
    unit_id: ManufacturingUnit
    batch_no: str
    quantity_on_hand: float
    quantity_reserved: float
    quantity_available: float
    uom: str
    valuation_rate: float
    total_valuation: float
    reorder_level: float
    safety_stock: float
    is_below_reorder: bool
    updated_at: datetime


# -------------------------------------------------------------
# Material Inward & Outward
# -------------------------------------------------------------
class MaterialInwardCreate(BaseModel):
    item_id: str = Field(..., description="Raw Material or Finished Product ID or Code")
    item_type: ItemType
    warehouse_id: str = Field(..., description="Destination Warehouse ID or Code")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    quantity: float = Field(..., gt=0.0, description="Inward quantity")
    unit_cost: float = Field(default=0.0, ge=0.0, description="Purchase or production unit cost")
    batch_no: Optional[str] = Field("DEFAULT", max_length=100)
    supplier_id: Optional[str] = Field(None, description="Vendor / Supplier code or ID")
    invoice_no: Optional[str] = Field(None, max_length=100)
    po_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)


class MaterialOutwardCreate(BaseModel):
    item_id: str = Field(..., description="Item ID or Code")
    warehouse_id: str = Field(..., description="Source Warehouse ID or Code")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    quantity: float = Field(..., gt=0.0, description="Outward quantity")
    destination: Optional[str] = Field(None, max_length=150, description="Machine Line, Sub-contractor, or Department")
    department: Optional[str] = Field(None, max_length=100)
    batch_no: Optional[str] = Field("DEFAULT", max_length=100)
    notes: Optional[str] = Field(None, max_length=500)


# -------------------------------------------------------------
# Warehouse Transfers
# -------------------------------------------------------------
class StockTransferCreate(BaseModel):
    source_warehouse_id: str = Field(..., description="Origin Warehouse ID or Code")
    target_warehouse_id: str = Field(..., description="Destination Warehouse ID or Code")
    item_id: str = Field(..., description="Item ID or Code")
    quantity: float = Field(..., gt=0.0, description="Quantity to transfer")
    batch_no: Optional[str] = Field("DEFAULT", max_length=100)
    transfer_reason: Optional[str] = Field("INTER_FACILITY_TRANSFER", max_length=200)
    vehicle_number: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=500)


# -------------------------------------------------------------
# Stock Adjustment
# -------------------------------------------------------------
class StockAdjustmentCreate(BaseModel):
    item_id: str = Field(..., description="Item ID or Code")
    warehouse_id: str = Field(..., description="Warehouse ID or Code")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    quantity_delta: float = Field(..., description="Quantity delta: positive for surplus (IN), negative for deficit (OUT)")
    reason: AdjustmentReason
    batch_no: Optional[str] = Field("DEFAULT", max_length=100)
    notes: str = Field(..., min_length=3, max_length=500, description="Mandatory audit justification for adjustment")


# -------------------------------------------------------------
# Opening Stock Bulk Import
# -------------------------------------------------------------
class OpeningStockImportItem(BaseModel):
    item_code: str = Field(..., description="Raw Material or Finished Product code")
    item_type: ItemType
    warehouse_code: str = Field(..., description="Target warehouse code e.g. WH-E1-RM01")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    quantity: float = Field(..., gt=0.0)
    unit_cost: float = Field(default=0.0, ge=0.0)
    batch_no: Optional[str] = Field("DEFAULT", max_length=100)


class OpeningStockImportRequest(BaseModel):
    items: List[OpeningStockImportItem] = Field(..., min_length=1)
    notes: Optional[str] = Field("Initial Opening Stock Migration", max_length=500)


# -------------------------------------------------------------
# Movement Ledger Responses
# -------------------------------------------------------------
class StockMovementLedgerResponse(BaseModel):
    id: str
    transaction_number: str
    movement_type: MovementType
    item_id: str
    item_code: str
    item_name: str
    item_type: ItemType
    warehouse_id: str
    warehouse_code: str
    warehouse_name: str
    unit_id: ManufacturingUnit
    batch_no: str
    quantity_change: float
    balance_after: float
    uom: str
    reference_id: Optional[str] = None
    reference_type: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    created_by: str


# -------------------------------------------------------------
# Low Stock Alert & Summary KPIs
# -------------------------------------------------------------
class LowStockAlertResponse(BaseModel):
    item_id: str
    item_code: str
    item_name: str
    item_type: ItemType
    unit_id: ManufacturingUnit
    total_on_hand: float
    total_reserved: float
    total_available: float
    uom: str
    reorder_level: float
    safety_stock: float
    shortage_quantity: float


class InventoryDashboardSummary(BaseModel):
    total_items_tracked: int
    raw_material_items: int
    finished_goods_items: int
    total_valuation_inr: float
    low_stock_alerts_count: int
    warehouses_count: int
    movements_today_count: int
