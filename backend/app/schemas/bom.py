from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from app.models.user import ManufacturingUnit


class BOMStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    OBSOLETE = "OBSOLETE"


# -------------------------------------------------------------
# Component Line Item Models
# -------------------------------------------------------------
class BOMComponentInput(BaseModel):
    material_id: str = Field(..., description="Raw Material ID or Code")
    net_quantity: float = Field(..., gt=0.0, description="Theoretical engineering quantity per base batch")
    uom: str = Field(..., min_length=1, max_length=20, description="Unit of measure matching raw material master")
    scrap_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Approved scrap / wastage allowance percentage")
    notes: Optional[str] = Field(None, max_length=300)


class BOMComponentResponse(BaseModel):
    material_id: str
    material_code: str
    material_name: str
    uom: str
    net_quantity: float
    scrap_percentage: float
    gross_quantity: float
    unit_cost: float
    estimated_cost: float
    notes: Optional[str] = None


# -------------------------------------------------------------
# BOM CRUD Models
# -------------------------------------------------------------
class BOMCreate(BaseModel):
    product_id: str = Field(..., description="Finished Product ID or Code")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    base_quantity: float = Field(default=1.0, gt=0.0, description="Base finished product yield for this BOM")
    revision_no: str = Field(default="R1", max_length=20, description="Revision identifier e.g. R1, R2")
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    description: Optional[str] = Field(None, max_length=500)
    components: List[BOMComponentInput] = Field(..., min_length=1, description="List of raw material components")


class BOMUpdate(BaseModel):
    base_quantity: Optional[float] = Field(None, gt=0.0)
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    description: Optional[str] = Field(None, max_length=500)
    components: Optional[List[BOMComponentInput]] = Field(None, min_length=1)


class BOMRevisionCreate(BaseModel):
    new_revision_no: str = Field(..., max_length=20, description="New revision identifier (e.g. R2)")
    description: Optional[str] = Field(None, max_length=500, description="Engineering change reason")
    components: Optional[List[BOMComponentInput]] = None


class BOMApprovalAction(BaseModel):
    approved: bool = Field(..., description="True to approve, False to reject")
    remarks: Optional[str] = Field(None, max_length=500)
    set_as_active: bool = Field(default=True, description="Whether to make this the active BOM for the product/unit")


class BOMResponse(BaseModel):
    id: str
    bom_number: str
    product_id: str
    product_code: str
    product_name: str
    product_uom: str
    unit_id: ManufacturingUnit
    base_quantity: float
    revision_no: str
    status: BOMStatus
    is_active: bool
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    description: Optional[str] = None
    total_estimated_cost: float
    components: List[BOMComponentResponse]
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    created_by: str
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


# -------------------------------------------------------------
# Material Requirements Calculation Models
# -------------------------------------------------------------
class MaterialRequirementCalculationRequest(BaseModel):
    production_quantity: float = Field(..., gt=0.0, description="Target production batch quantity")
    warehouse_id: Optional[str] = Field(None, description="Optional warehouse to check inventory against")


class MaterialRequirementItem(BaseModel):
    material_id: str
    material_code: str
    material_name: str
    uom: str
    net_required_quantity: float
    scrap_percentage: float
    gross_required_quantity: float
    unit_cost: float
    total_estimated_cost: float
    quantity_on_hand: float
    quantity_reserved: float
    quantity_available: float
    shortage_quantity: float
    is_shortage: bool


class MaterialRequirementCalculationResponse(BaseModel):
    bom_id: str
    bom_number: str
    product_code: str
    product_name: str
    revision_no: str
    unit_id: ManufacturingUnit
    production_quantity: float
    total_estimated_material_cost: float
    total_shortages_count: int
    has_sufficient_stock: bool
    requirements: List[MaterialRequirementItem]


# -------------------------------------------------------------
# Dashboard Summary & Import Models
# -------------------------------------------------------------
class BOMDashboardSummary(BaseModel):
    total_boms: int
    approved_boms: int
    pending_approval_boms: int
    draft_boms: int
    active_boms: int
    products_with_bom_count: int


class BOMImportItem(BaseModel):
    product_code: str
    revision_no: str = "R1"
    unit_id: ManufacturingUnit = ManufacturingUnit.Unit_1
    base_quantity: float = 1.0
    material_code: str
    net_quantity: float
    uom: str
    scrap_percentage: float = 0.0
    description: Optional[str] = None


class BOMImportRequest(BaseModel):
    items: List[BOMImportItem] = Field(..., min_length=1)
    auto_approve: bool = False
