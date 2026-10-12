from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, Field
from app.models.user import ManufacturingUnit


class ScrapCategory(str, Enum):
    CUTTING_OFFCUT = "CUTTING_OFFCUT"
    MACHINING_SWARF = "MACHINING_SWARF"
    REJECTED_DEFECTIVE = "REJECTED_DEFECTIVE"
    TOOLING_SETUP = "TOOLING_SETUP"
    DAMAGE_IN_HANDLING = "DAMAGE_IN_HANDLING"
    CONTAMINATION = "CONTAMINATION"
    OBSOLETE_MATERIAL = "OBSOLETE_MATERIAL"
    OTHER = "OTHER"


class ScrapDisposition(str, Enum):
    DISPOSAL = "DISPOSAL"
    RECYCLE_INTERNAL = "RECYCLE_INTERNAL"
    SCRAP_YARD_SALE = "SCRAP_YARD_SALE"
    HOLD_REVIEW = "HOLD_REVIEW"


class ScrapEntryStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# -------------------------------------------------------------
# Scrap Entry Input Models
# -------------------------------------------------------------
class ScrapEntryCreate(BaseModel):
    entry_date: Optional[str] = Field(None, description="ISO Date string (YYYY-MM-DD)")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    production_order_id: Optional[str] = Field(None, description="Optional associated Production Order ID")
    production_order_number: Optional[str] = Field(None, description="Optional associated Production Order Number")
    item_id: str = Field(..., description="Raw material or Finished Good ID")
    item_code: str = Field(..., description="Item Code")
    item_name: str = Field(..., description="Item Name")
    item_type: str = Field(default="RAW_MATERIAL", description="RAW_MATERIAL | FINISHED_GOOD | WIP")
    scrap_category: ScrapCategory = Field(default=ScrapCategory.MACHINING_SWARF)
    quantity: float = Field(..., gt=0.0, description="Scrap quantity in base UoM")
    uom: str = Field(..., min_length=1, max_length=20, description="Unit of measurement e.g. KG, PCS")
    reason: str = Field(..., min_length=2, max_length=500, description="Specific reason or shop-floor observation")
    disposition: ScrapDisposition = Field(default=ScrapDisposition.HOLD_REVIEW)
    operator_name: Optional[str] = Field(None, max_length=100)
    machine_id: Optional[str] = Field(None, max_length=100, description="Machine/workstation identifier")
    notes: Optional[str] = Field(None, max_length=500)


class ScrapEntryUpdate(BaseModel):
    scrap_category: Optional[ScrapCategory] = None
    quantity: Optional[float] = Field(None, gt=0.0)
    reason: Optional[str] = Field(None, min_length=2, max_length=500)
    disposition: Optional[ScrapDisposition] = None
    operator_name: Optional[str] = None
    machine_id: Optional[str] = None
    notes: Optional[str] = None


class ScrapApprovalRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=500)
    disposition: Optional[ScrapDisposition] = None


class ScrapRejectionRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=3, max_length=500)


# -------------------------------------------------------------
# Scrap Entry Response Models
# -------------------------------------------------------------
class ScrapEntryResponse(BaseModel):
    id: str
    entry_number: str
    entry_date: str
    unit_id: str
    production_order_id: Optional[str] = None
    production_order_number: Optional[str] = None
    item_id: str
    item_code: str
    item_name: str
    item_type: str
    scrap_category: str
    quantity: float
    uom: str
    unit_cost: float
    total_cost: float
    reason: str
    disposition: str
    status: str
    operator_name: Optional[str] = None
    machine_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    created_by: str
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None


# -------------------------------------------------------------
# Planned vs Actual Wastage Comparison
# -------------------------------------------------------------
class ComponentWastageComparison(BaseModel):
    material_id: str
    material_code: str
    material_name: str
    uom: str
    planned_quantity: float
    planned_scrap_percentage: float
    planned_scrap_quantity: float
    actual_scrap_quantity: float
    scrap_variance: float
    unit_cost: float
    planned_scrap_cost: float
    actual_scrap_cost: float
    cost_variance: float


class PlannedVsActualWastageResponse(BaseModel):
    production_order_id: str
    order_number: str
    product_code: str
    product_name: str
    unit_id: str
    planned_production_qty: float
    actual_produced_qty: float
    components: List[ComponentWastageComparison]
    total_planned_scrap_cost: float
    total_actual_scrap_cost: float
    total_cost_variance: float


# -------------------------------------------------------------
# Wastage Summary / Dashboard Models
# -------------------------------------------------------------
class CategoryScrapMetric(BaseModel):
    category: str
    total_quantity: float
    total_cost: float
    entry_count: int


class WastageDashboardSummary(BaseModel):
    total_scrap_entries: int
    pending_approvals: int
    approved_entries: int
    total_scrap_cost: float
    category_breakdown: List[CategoryScrapMetric]
    unit_id: Optional[str] = None
