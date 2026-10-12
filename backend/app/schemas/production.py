from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from app.models.user import ManufacturingUnit


class ProductionOrderStatus(str, Enum):
    DRAFT = "DRAFT"
    RELEASED = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# -------------------------------------------------------------
# Component Requirement & Consumption Models
# -------------------------------------------------------------
class ProductionMaterialRequirement(BaseModel):
    material_id: str
    material_code: str
    material_name: str
    uom: str
    standard_quantity_per_unit: float
    total_standard_required: float
    total_issued: float = 0.0
    unit_cost: float = 0.0
    standard_total_cost: float = 0.0
    actual_total_cost: float = 0.0


class MaterialIssueItemInput(BaseModel):
    material_id: str = Field(..., description="Raw Material ID or Code")
    warehouse_id: str = Field(..., description="Source warehouse where stock is drawn from")
    quantity: float = Field(..., gt=0.0, description="Quantity issued to production line")
    batch_no: Optional[str] = Field("DEFAULT", max_length=100)
    notes: Optional[str] = Field(None, max_length=300)


class MaterialIssueRequest(BaseModel):
    items: List[MaterialIssueItemInput] = Field(..., min_length=1)
    notes: Optional[str] = Field(None, max_length=500)


# -------------------------------------------------------------
# Production Output & Finished Goods Receipt Models
# -------------------------------------------------------------
class ProductionOutputInput(BaseModel):
    produced_quantity: float = Field(..., ge=0.0, description="Good finished machines produced")
    rejected_quantity: float = Field(default=0.0, ge=0.0, description="Rejections / scraps produced")
    warehouse_id: str = Field(..., description="Target finished goods warehouse to receipt into")
    batch_no: Optional[str] = Field(None, max_length=100, description="Finished product batch/serial number")
    operator_name: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)


class ProductionOutputRecord(BaseModel):
    id: str
    order_id: str
    produced_quantity: float
    rejected_quantity: float
    warehouse_id: str
    warehouse_code: str
    batch_no: str
    operator_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    created_by: str


# -------------------------------------------------------------
# Production Order CRUD Models
# -------------------------------------------------------------
class ProductionOrderCreate(BaseModel):
    product_id: str = Field(..., description="Finished Product ID or Code")
    bom_id: Optional[str] = Field(None, description="Optional BOM ID (uses active approved BOM if omitted)")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    target_warehouse_id: str = Field(..., description="Default finished goods warehouse for receipts")
    planned_quantity: float = Field(..., gt=0.0, description="Number of finished units to manufacture")
    scheduled_start_date: Optional[datetime] = None
    target_completion_date: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=500)


class ProductionOrderResponse(BaseModel):
    id: str
    order_number: str
    product_id: str
    product_code: str
    product_name: str
    product_uom: str
    bom_id: str
    bom_number: str
    bom_revision_no: str
    unit_id: ManufacturingUnit
    target_warehouse_id: str
    target_warehouse_code: str
    planned_quantity: float
    produced_quantity: float
    rejected_quantity: float
    remaining_quantity: float
    status: ProductionOrderStatus
    completion_percentage: float
    materials: List[ProductionMaterialRequirement]
    scheduled_start_date: Optional[datetime] = None
    target_completion_date: Optional[datetime] = None
    actual_start_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    created_by: str
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


# -------------------------------------------------------------
# Variance Report & Dashboard Models
# -------------------------------------------------------------
class MaterialVarianceItem(BaseModel):
    material_id: str
    material_code: str
    material_name: str
    uom: str
    standard_required: float
    actual_issued: float
    variance_quantity: float
    is_favorable: bool
    standard_cost: float
    actual_cost: float
    cost_variance: float


class ProductionVarianceReport(BaseModel):
    order_id: str
    order_number: str
    product_code: str
    product_name: str
    planned_quantity: float
    produced_quantity: float
    rejected_quantity: float
    yield_efficiency_percentage: float
    total_standard_cost: float
    total_actual_cost: float
    net_cost_variance: float
    material_variances: List[MaterialVarianceItem]


class ProductionDashboardSummary(BaseModel):
    total_orders: int
    draft_orders: int
    released_orders: int
    in_progress_orders: int
    completed_orders: int
    total_planned_units: float
    total_produced_units: float
    total_rejected_units: float
    overall_yield_percentage: float
