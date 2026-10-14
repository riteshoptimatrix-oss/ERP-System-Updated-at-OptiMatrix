from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from app.models.user import ManufacturingUnit
from app.schemas.master import AuditBase


class OrderStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    PARTIALLY_DISPATCHED = "PARTIALLY_DISPATCHED"
    DISPATCHED = "DISPATCHED"
    CANCELLED = "CANCELLED"


class DispatchStatus(str, Enum):
    PREPARED = "PREPARED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


# -------------------------------------------------------------
# Line Items
# -------------------------------------------------------------
class OrderLineItem(BaseModel):
    product_id: str = Field(..., description="Finished product Master ID")
    product_code: str = Field(..., description="Product SKU / Model Code")
    product_name: str = Field(..., description="Product name / Description")
    uom: str = Field(default="PCS", description="Unit of measure")
    quantity: float = Field(..., gt=0.0, description="Ordered quantity")
    unit_price: float = Field(..., ge=0.0, description="Unit sales price in INR")
    discount_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    tax_percent: float = Field(default=18.0, ge=0.0, le=40.0, description="GST / IGST percent")
    dispatched_quantity: float = Field(default=0.0, ge=0.0, description="Cumulative dispatched quantity")
    notes: Optional[str] = Field(None, max_length=200)

    @property
    def remaining_quantity(self) -> float:
        return max(0.0, self.quantity - self.dispatched_quantity)

    @property
    def subtotal(self) -> float:
        discounted = self.unit_price * (1.0 - (self.discount_percent / 100.0))
        return round(self.quantity * discounted, 2)

    @property
    def tax_amount(self) -> float:
        return round(self.subtotal * (self.tax_percent / 100.0), 2)

    @property
    def total_amount(self) -> float:
        return round(self.subtotal + self.tax_amount, 2)


# -------------------------------------------------------------
# Sales Order Payloads & Responses
# -------------------------------------------------------------
class SalesOrderCreate(BaseModel):
    customer_id: str = Field(..., description="Customer Master record ID")
    customer_po_number: Optional[str] = Field(None, max_length=100, description="Client Purchase Order #")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1, description="Originating manufacturing unit")
    order_date: Optional[str] = Field(None, description="Order placement date ISO string")
    delivery_due_date: Optional[str] = Field(None, description="Committed delivery date")
    billing_address: Optional[str] = Field(None, max_length=500)
    shipping_address: Optional[str] = Field(None, max_length=500)
    items: List[OrderLineItem] = Field(..., min_length=1, description="Ordered items list")
    notes: Optional[str] = Field(None, max_length=1000)


class SalesOrderUpdate(BaseModel):
    customer_po_number: Optional[str] = Field(None, max_length=100)
    delivery_due_date: Optional[str] = None
    billing_address: Optional[str] = Field(None, max_length=500)
    shipping_address: Optional[str] = Field(None, max_length=500)
    items: Optional[List[OrderLineItem]] = None
    notes: Optional[str] = Field(None, max_length=1000)


class OrderCancellationRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500, description="Mandatory reason for cancelling sales order")


class OrderActivity(BaseModel):
    id: str
    order_id: str
    action: str
    description: str
    performed_by: str
    timestamp: datetime


class SalesOrderResponse(BaseModel):
    id: str
    order_number: str
    customer_id: str
    customer_code: str
    customer_name: str
    customer_po_number: Optional[str] = None
    unit_id: ManufacturingUnit
    status: OrderStatus
    order_date: datetime
    delivery_due_date: Optional[str] = None
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None
    items: List[Dict[str, Any]]
    subtotal: float
    tax_total: float
    grand_total: float
    total_ordered_qty: float
    total_dispatched_qty: float
    dispatch_percent: float
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    created_by: str
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    activities: Optional[List[OrderActivity]] = None


# -------------------------------------------------------------
# Packing Slip Payloads & Responses
# -------------------------------------------------------------
class PackingSlipItem(BaseModel):
    product_id: str
    product_code: str
    product_name: str
    ordered_quantity: float
    pack_quantity: float = Field(..., gt=0.0, description="Quantity packed in this container/slip")
    package_type: str = Field(default="WOODEN_CRATE", description="Packaging type: WOODEN_CRATE, CARTON, PALLET, BUNDLE")
    notes: Optional[str] = None


class PackingSlipCreate(BaseModel):
    items: List[PackingSlipItem] = Field(..., min_length=1)
    packages_count: int = Field(default=1, ge=1)
    gross_weight_kg: Optional[float] = Field(None, ge=0.0)
    net_weight_kg: Optional[float] = Field(None, ge=0.0)
    special_handling_notes: Optional[str] = Field(None, max_length=500)


class PackingSlipResponse(BaseModel):
    id: str
    slip_number: str
    order_id: str
    order_number: str
    customer_id: str
    customer_name: str
    unit_id: ManufacturingUnit
    packages_count: int
    gross_weight_kg: Optional[float] = None
    net_weight_kg: Optional[float] = None
    special_handling_notes: Optional[str] = None
    items: List[Dict[str, Any]]
    created_at: datetime
    created_by: str


# -------------------------------------------------------------
# Dispatch Records Payloads & Responses
# -------------------------------------------------------------
class DispatchItem(BaseModel):
    product_id: str
    product_code: str
    product_name: str
    quantity: float = Field(..., gt=0.0, description="Dispatched quantity")


class DispatchRecordCreate(BaseModel):
    packing_slip_id: Optional[str] = Field(None, description="Optional packing slip reference")
    carrier_name: str = Field(..., min_length=2, max_length=150, description="Logistics / Transporter partner")
    vehicle_number: str = Field(..., min_length=2, max_length=50, description="Truck / Vehicle registration number")
    lr_number: Optional[str] = Field(None, max_length=100, description="Lorry Receipt / Consignment Note #")
    driver_name: Optional[str] = Field(None, max_length=100)
    driver_phone: Optional[str] = Field(None, max_length=20)
    dispatched_date: Optional[str] = Field(None, description="Date of dispatch")
    items: List[DispatchItem] = Field(..., min_length=1, description="Products and quantities dispatched")
    remarks: Optional[str] = Field(None, max_length=500)


class DispatchRecordResponse(BaseModel):
    id: str
    dispatch_number: str
    order_id: str
    order_number: str
    customer_id: str
    customer_name: str
    packing_slip_id: Optional[str] = None
    packing_slip_number: Optional[str] = None
    unit_id: ManufacturingUnit
    carrier_name: str
    vehicle_number: str
    lr_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    dispatched_date: datetime
    status: DispatchStatus
    items: List[Dict[str, Any]]
    total_quantity: float
    remarks: Optional[str] = None
    created_at: datetime
    created_by: str


# -------------------------------------------------------------
# Stock Availability Contract Result
# -------------------------------------------------------------
class StockAvailabilityResult(BaseModel):
    product_id: str
    product_code: str
    unit_id: str
    required_quantity: float
    available_quantity: Optional[float] = None
    is_sufficient: bool
    status: str = Field(description="VERIFIED, UNTRACKED, or INSUFFICIENT")
    message: str


# -------------------------------------------------------------
# KPI Summary
# -------------------------------------------------------------
class OrderDashboardSummary(BaseModel):
    total_orders: int
    draft_orders: int
    confirmed_orders: int
    partially_dispatched_orders: int
    fully_dispatched_orders: int
    cancelled_orders: int
    total_pipeline_value: float
    total_dispatched_value: float
    total_pending_dispatches: int


# -------------------------------------------------------------
# Order Planning (By Variant and Length)
# Updated by Taha; one line per variant and length
# -------------------------------------------------------------
class OrderPlanningItem(BaseModel):
    id: Optional[str] = None
    order_id: Optional[str] = None
    order_number: str = Field(..., description="Order No. e.g. SO-2026-0001")
    order_date: str = Field(..., description="Order Date (YYYY-MM-DD)")
    customer: str = Field(..., description="Customer Name")
    customer_code: Optional[str] = None
    brand: str = Field(default="OptiMatrix", description="Brand")
    variant: str = Field(..., description="Variant / Machine Model")
    length: str = Field(default="Standard", description="Cut length or dimensional spec")
    order_qty: float = Field(..., ge=0.0, description="Order Qty")
    required_dispatch_date: Optional[str] = Field(None, description="Required Dispatch Date")
    priority: str = Field(default="MEDIUM", description="Priority (URGENT, HIGH, MEDIUM, LOW)")
    order_status: str = Field(default="CONFIRMED", description="Order Status")
    planned_qty: float = Field(default=0.0, ge=0.0, description="Planned Qty")
    produced_qty: float = Field(default=0.0, ge=0.0, description="Produced Qty")
    balance_qty: float = Field(default=0.0, description="Balance Qty (Order Qty - Produced Qty)")
    dispatch_qty: float = Field(default=0.0, ge=0.0, description="Dispatch Qty")
    dispatch_balance: float = Field(default=0.0, description="Dispatch Balance (Order Qty - Dispatch Qty)")
    final_approval: str = Field(default="APPROVED", description="Final Approval (APPROVED, PENDING, ON_HOLD)")
    remarks: Optional[str] = Field(None, description="Remarks")
    unit_id: Optional[str] = "Unit_1"
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = "Taha"


class OrderPlanningUpdate(BaseModel):
    planned_qty: Optional[float] = None
    produced_qty: Optional[float] = None
    dispatch_qty: Optional[float] = None
    required_dispatch_date: Optional[str] = None
    priority: Optional[str] = None
    order_status: Optional[str] = None
    final_approval: Optional[str] = None
    remarks: Optional[str] = None
    brand: Optional[str] = None
    variant: Optional[str] = None
    length: Optional[str] = None


class OrderPlanningSummary(BaseModel):
    total_planning_lines: int
    total_order_qty: float
    total_planned_qty: float
    total_produced_qty: float
    total_balance_qty: float
    total_dispatch_qty: float
    total_dispatch_balance: float
    approved_lines: int
    pending_lines: int
