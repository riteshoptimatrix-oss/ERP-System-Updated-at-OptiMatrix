from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, Field
from app.models.user import ManufacturingUnit


class ReportType(str, Enum):
    SALES = "sales"
    ORDERS = "orders"
    DISPATCH = "dispatch"
    INVENTORY = "inventory"
    BOM = "bom"
    PRODUCTION = "production"
    WIP = "wip"
    QC = "qc"
    WASTAGE = "wastage"
    DOWNTIME = "downtime"
    ATTENDANCE = "attendance"
    PAYROLL = "payroll"
    FINANCE = "finance"


class ExportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    XLSX = "xlsx"


class ImportEntityType(str, Enum):
    CUSTOMERS = "customers"
    VENDORS = "vendors"
    RAW_MATERIALS = "raw_materials"
    FINISHED_PRODUCTS = "finished_products"
    EMPLOYEES = "employees"
    WAREHOUSES = "warehouses"
    CATEGORIES = "categories"
    UOMS = "uoms"
    OPENING_STOCK = "opening_stock"


class ImportBatchStatus(str, Enum):
    DRY_RUN_PASSED = "DRY_RUN_PASSED"
    DRY_RUN_FAILED = "DRY_RUN_FAILED"
    COMMITTED = "COMMITTED"
    REJECTED = "REJECTED"


class RowErrorDetail(BaseModel):
    row_number: int
    column: Optional[str] = None
    value: Optional[Any] = None
    error_message: str
    is_duplicate: bool = False


# -----------------------------------------------------------------------------
# Report Schemas
# -----------------------------------------------------------------------------

class ReportSummaryKpi(BaseModel):
    metric_name: str
    metric_value: Union[float, int, str]
    formatted_value: str
    description: Optional[str] = None


class GenericReportResponse(BaseModel):
    report_type: ReportType
    unit_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    kpis: List[ReportSummaryKpi] = []
    columns: List[Dict[str, str]]
    items: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int
    generated_at: datetime


# -----------------------------------------------------------------------------
# Import & Migration Schemas
# -----------------------------------------------------------------------------

class ImportDryRunResponse(BaseModel):
    batch_token: str
    entity_type: ImportEntityType
    filename: str
    total_rows: int
    valid_rows_count: int
    error_rows_count: int
    duplicate_rows_count: int
    can_commit: bool
    errors: List[RowErrorDetail]
    preview_rows: List[Dict[str, Any]]
    validation_summary: str


class ImportCommitRequest(BaseModel):
    batch_token: str
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    notes: Optional[str] = Field(None, max_length=500)


class ImportCommitResponse(BaseModel):
    batch_id: str
    entity_type: str
    status: str
    inserted_count: int
    skipped_count: int
    committed_by: str
    committed_at: datetime
    message: str


class ImportBatchSummary(BaseModel):
    id: str
    batch_id: str
    batch_token: str
    entity_type: str
    filename: str
    unit_id: str
    total_rows: int
    valid_rows_count: int
    error_rows_count: int
    status: str
    committed_by: Optional[str] = None
    committed_at: Optional[datetime] = None
    created_at: datetime
    created_by: str
    errors_sample: List[RowErrorDetail] = []
