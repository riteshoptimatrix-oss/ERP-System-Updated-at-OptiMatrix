from typing import Optional, List, Dict, Any, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, model_validator
from app.models.user import ManufacturingUnit

# Generic type for paginated responses
T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

# Common base audit fields
class AuditBase(BaseModel):
    created_at: datetime
    created_by: str
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


# ==========================================================
# 1. Customer Master
# ==========================================================
class CustomerCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Unique customer code e.g. CUST-001")
    name: str = Field(..., min_length=2, max_length=150)
    gstin: Optional[str] = Field(None, max_length=15, description="GSTIN e.g. 24AAAAA0000A1Z5")
    pan: Optional[str] = Field(None, max_length=10)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    billing_address: Optional[str] = Field(None, max_length=500)
    shipping_address: Optional[str] = Field(None, max_length=500)
    credit_limit: float = Field(default=0.0, ge=0.0)
    payment_terms_days: int = Field(default=30, ge=0)
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.BOTH)
    is_active: bool = True

    @model_validator(mode="before")
    @classmethod
    def sanitize_empty_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            for field in ["gstin", "pan", "contact_person", "phone", "email", "billing_address", "shipping_address"]:
                if values.get(field) == "":
                    values[field] = None
        return values

class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    gstin: Optional[str] = Field(None, max_length=15)
    pan: Optional[str] = Field(None, max_length=10)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    billing_address: Optional[str] = Field(None, max_length=500)
    shipping_address: Optional[str] = Field(None, max_length=500)
    credit_limit: Optional[float] = Field(None, ge=0.0)
    payment_terms_days: Optional[int] = Field(None, ge=0)
    unit_id: Optional[ManufacturingUnit] = None
    is_active: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def sanitize_empty_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            for field in ["gstin", "pan", "contact_person", "phone", "email", "billing_address", "shipping_address"]:
                if values.get(field) == "":
                    values[field] = None
        return values

class CustomerResponse(CustomerCreate, AuditBase):
    id: str


# ==========================================================
# 2. Supplier & Vendor Master
# ==========================================================
class VendorCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Unique vendor code e.g. VEND-001")
    name: str = Field(..., min_length=2, max_length=150)
    gstin: Optional[str] = Field(None, max_length=15)
    pan: Optional[str] = Field(None, max_length=10)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, max_length=500)
    payment_terms_days: int = Field(default=30, ge=0)
    category: Optional[str] = Field(None, max_length=50, description="Raw Material, Consumable, Services")
    rating: Optional[float] = Field(default=5.0, ge=1.0, le=5.0)
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.BOTH)
    is_active: bool = True

class VendorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    gstin: Optional[str] = Field(None, max_length=15)
    pan: Optional[str] = Field(None, max_length=10)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, max_length=500)
    payment_terms_days: Optional[int] = Field(None, ge=0)
    category: Optional[str] = Field(None, max_length=50)
    rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    unit_id: Optional[ManufacturingUnit] = None
    is_active: Optional[bool] = None

class VendorResponse(VendorCreate, AuditBase):
    id: str


# ==========================================================
# 3. Employee Master
# ==========================================================
class EmployeeCreate(BaseModel):
    code: Optional[str] = Field(default=None, max_length=50, description="Unique employee badge code e.g. EMP-001 (auto-generated if omitted)")
    full_name: str = Field(..., min_length=2, max_length=150)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    department: str = Field(..., min_length=2, max_length=100, description="Manufacturing department")
    designation: str = Field(..., min_length=2, max_length=100, description="Designation / Employee Job Role")
    account_type: Optional[str] = Field(default="EMPLOYEE", description="Account type category: EMPLOYEE, HR, ADMIN")
    job_role: Optional[str] = Field(default=None, description="Specific employee job role")
    joining_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    reporting_officer_id: Optional[str] = Field(None, description="Assigned reporting officer user or employee ID")
    reporting_officer_name: Optional[str] = Field(None, description="Reporting officer name")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    status: str = Field(default="ACTIVE", description="ACTIVE, DEACTIVATED, ON_LEAVE, RESIGNED, TERMINATED")
    emergency_contact: Optional[str] = Field(None, max_length=100)
    create_user_account: Optional[bool] = Field(default=True, description="Optionally provision ERP user login account")
    user_password: Optional[str] = Field(default="admin123", min_length=6, description="Initial password if provisioning ERP account (default admin123)")
    confirm_user_password: Optional[str] = Field(default="admin123", min_length=6, description="Confirm initial password")
    must_change_password: Optional[bool] = Field(default=True, description="Require password change on first login")
    is_active: bool = True

    @model_validator(mode="before")
    @classmethod
    def sanitize_empty_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            for field in ["email", "phone", "emergency_contact", "joining_date", "code", "reporting_officer_id", "reporting_officer_name"]:
                if values.get(field) == "":
                    values[field] = None
            if values.get("email"):
                if values.get("create_user_account") is None:
                    values["create_user_account"] = True
                if not values.get("user_password"):
                    values["user_password"] = "admin123"
                if not values.get("confirm_user_password"):
                    values["confirm_user_password"] = values["user_password"]
            else:
                values["user_password"] = None
                values["confirm_user_password"] = None
        return values

    @model_validator(mode="after")
    def validate_user_account_passwords(self):
        if self.create_user_account and self.user_password:
            # Enforce 12-character minimum password policy when setting a custom password
            if self.user_password not in ["admin123", "admin@123"] and len(self.user_password) < 12:
                raise ValueError("Initial password must be at least 12 characters long.")
            if self.confirm_user_password and self.confirm_user_password != self.user_password:
                raise ValueError("Initial password and confirmation do not match.")
        return self

class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, min_length=2, max_length=100)
    designation: Optional[str] = Field(None, min_length=2, max_length=100)
    account_type: Optional[str] = None
    job_role: Optional[str] = None
    joining_date: Optional[str] = None
    reporting_officer_id: Optional[str] = None
    reporting_officer_name: Optional[str] = None
    unit_id: Optional[ManufacturingUnit] = None
    status: Optional[str] = None
    emergency_contact: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def sanitize_empty_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            for field in ["email", "phone", "emergency_contact", "joining_date", "reporting_officer_id", "reporting_officer_name"]:
                if values.get(field) == "":
                    values[field] = None
        return values

class EmployeeResponse(AuditBase):
    id: str
    code: str
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    department: str
    designation: str
    account_type: Optional[str] = "EMPLOYEE"
    job_role: Optional[str] = None
    joining_date: Optional[str] = None
    reporting_officer_id: Optional[str] = None
    reporting_officer_name: Optional[str] = None
    unit_id: ManufacturingUnit = ManufacturingUnit.Unit_1
    status: str = "ACTIVE"
    emergency_contact: Optional[str] = None
    is_active: bool = True
    user_id: Optional[str] = None


# ==========================================================
# 4. Finished-Product Master
# ==========================================================
class FinishedProductCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Product / Model code e.g. FP-ENV-100")
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    category_id: Optional[str] = Field(None, description="Category code or ID")
    uom: str = Field(default="PCS", min_length=1, max_length=20, description="Base UoM e.g. PCS, SET, NOS")
    drawing_no: Optional[str] = Field(None, max_length=100, description="Engineering blueprint drawing number")
    revision_no: Optional[str] = Field(default="R0", max_length=20)
    standard_cost: float = Field(default=0.0, ge=0.0)
    selling_price: float = Field(default=0.0, ge=0.0)
    min_stock_level: float = Field(default=0.0, ge=0.0)
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.BOTH)
    is_active: bool = True

class FinishedProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    category_id: Optional[str] = None
    uom: Optional[str] = Field(None, min_length=1, max_length=20)
    drawing_no: Optional[str] = Field(None, max_length=100)
    revision_no: Optional[str] = Field(None, max_length=20)
    standard_cost: Optional[float] = Field(None, ge=0.0)
    selling_price: Optional[float] = Field(None, ge=0.0)
    min_stock_level: Optional[float] = Field(None, ge=0.0)
    unit_id: Optional[ManufacturingUnit] = None
    is_active: Optional[bool] = None

class FinishedProductResponse(FinishedProductCreate, AuditBase):
    id: str


# ==========================================================
# 5. Raw-Material Master
# ==========================================================
class RawMaterialCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Raw material code e.g. RM-MS-PLATE-10MM")
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    category_id: Optional[str] = Field(None, description="Material category code or ID")
    uom: str = Field(default="KG", min_length=1, max_length=20, description="UoM e.g. KG, MTR, PCS, LTR")
    hsn_code: Optional[str] = Field(None, max_length=20)
    reorder_level: float = Field(default=0.0, ge=0.0)
    safety_stock: float = Field(default=0.0, ge=0.0)
    default_vendor_code: Optional[str] = Field(None, max_length=50)
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.BOTH)
    is_active: bool = True

class RawMaterialUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    category_id: Optional[str] = None
    uom: Optional[str] = Field(None, min_length=1, max_length=20)
    hsn_code: Optional[str] = Field(None, max_length=20)
    reorder_level: Optional[float] = Field(None, ge=0.0)
    safety_stock: Optional[float] = Field(None, ge=0.0)
    default_vendor_code: Optional[str] = Field(None, max_length=50)
    unit_id: Optional[ManufacturingUnit] = None
    is_active: Optional[bool] = None

class RawMaterialResponse(RawMaterialCreate, AuditBase):
    id: str


# ==========================================================
# 6. Unit of Measure (UoM) Master
# ==========================================================
class UoMCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=20, description="Unique UoM code e.g. KG, MTR, PCS")
    name: str = Field(..., min_length=1, max_length=100)
    symbol: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = Field(None, max_length=200)
    is_active: bool = True

class UoMUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    symbol: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None

class UoMResponse(UoMCreate, AuditBase):
    id: str


# ==========================================================
# 7. Warehouse & Storage Location Master
# ==========================================================
class WarehouseCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Unique warehouse/location code e.g. WH-E1-RM01")
    name: str = Field(..., min_length=2, max_length=150)
    unit_id: ManufacturingUnit = Field(..., description="Facility Unit_1 or Unit_2")
    location_type: str = Field(default="RAW_MATERIAL", description="RAW_MATERIAL, WIP, FINISHED_GOODS, SCRAP, TOOL_ROOM")
    bay_rack: Optional[str] = Field(None, max_length=100, description="Bay / Rack / Shelf locator")
    capacity_description: Optional[str] = Field(None, max_length=200)
    is_active: bool = True

class WarehouseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    unit_id: Optional[ManufacturingUnit] = None
    location_type: Optional[str] = None
    bay_rack: Optional[str] = Field(None, max_length=100)
    capacity_description: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None

class WarehouseResponse(WarehouseCreate, AuditBase):
    id: str


# ==========================================================
# 8. Product & Material Categories Master
# ==========================================================
class CategoryCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Unique category code e.g. CAT-RAW-STEEL")
    name: str = Field(..., min_length=2, max_length=150)
    category_type: str = Field(default="RAW_MATERIAL", description="RAW_MATERIAL, FINISHED_PRODUCT, CONSUMABLE, SPARES")
    description: Optional[str] = Field(None, max_length=300)
    is_active: bool = True

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    category_type: Optional[str] = None
    description: Optional[str] = Field(None, max_length=300)
    is_active: Optional[bool] = None

class CategoryResponse(CategoryCreate, AuditBase):
    id: str
