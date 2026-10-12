import io
import csv
from typing import Any, Dict, List, Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse

from app.database.mongodb import mongodb_manager
from app.api.deps import require_permission, get_current_active_user, verify_csrf_token
from app.models.user import RoleName
from app.repositories.master_repository import MasterRepository
from app.schemas.master import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    VendorCreate, VendorUpdate, VendorResponse,
    EmployeeCreate, EmployeeUpdate, EmployeeResponse,
    FinishedProductCreate, FinishedProductUpdate, FinishedProductResponse,
    RawMaterialCreate, RawMaterialUpdate, RawMaterialResponse,
    UoMCreate, UoMUpdate, UoMResponse,
    WarehouseCreate, WarehouseUpdate, WarehouseResponse,
    CategoryCreate, CategoryUpdate, CategoryResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/master", tags=["Master Data Management"])

# Configuration map for collections and schemas
ENTITY_CONFIG = {
    "customers": {
        "collection": "customers",
        "create_schema": CustomerCreate,
        "update_schema": CustomerUpdate,
        "response_schema": CustomerResponse,
        "permission_read": ("master", "read"),
        "permission_write": ("master", "create"),
        "csv_headers": ["code", "name", "gstin", "pan", "contact_person", "phone", "email", "billing_address", "shipping_address", "credit_limit", "payment_terms_days", "unit_id"],
        "sample_row": ["CUST-001", "Acme Hydraulics Ltd", "24AAAAA0000A1Z5", "AAAAA0000A", "Rajesh Sharma", "+919876543210", "rajesh@acme.com", "Plot 12, GIDC, Vadodara", "Plot 12, GIDC, Vadodara", "500000", "45", "BOTH"]
    },
    "vendors": {
        "collection": "vendors",
        "create_schema": VendorCreate,
        "update_schema": VendorUpdate,
        "response_schema": VendorResponse,
        "permission_read": ("master", "read"),
        "permission_write": ("master", "create"),
        "csv_headers": ["code", "name", "gstin", "pan", "contact_person", "phone", "email", "address", "payment_terms_days", "category", "rating", "unit_id"],
        "sample_row": ["VEND-001", "Gujarat Steel Tube Mills", "24BBBBB0000B1Z5", "BBBBB0000B", "Suresh Patel", "+919812345678", "sales@gjsteel.com", "Survey 45, Ankleshwar", "30", "Raw Material", "4.8", "BOTH"]
    },
    "employees": {
        "collection": "employees",
        "create_schema": EmployeeCreate,
        "update_schema": EmployeeUpdate,
        "response_schema": EmployeeResponse,
        "permission_read": ("master", "read"),
        "permission_write": ("master", "create"),
        "csv_headers": ["code", "full_name", "email", "phone", "department", "designation", "joining_date", "unit_id", "status", "emergency_contact"],
        "sample_row": ["EMP-001", "Amit Kumar Verma", "amit.verma@RGmachines.com", "+919712345670", "Machining", "Senior CNC Operator", "2024-01-15", "Unit_1", "ACTIVE", "+919712345671"]
    },
    "products": {
        "collection": "finished_products",
        "create_schema": FinishedProductCreate,
        "update_schema": FinishedProductUpdate,
        "response_schema": FinishedProductResponse,
        "permission_read": ("master", "read"),
        "permission_write": ("master", "create"),
        "csv_headers": ["code", "name", "description", "category_id", "uom", "drawing_no", "revision_no", "standard_cost", "selling_price", "min_stock_level", "unit_id"],
        "sample_row": ["FP-ENV-500", "500 Ton High Precision Hydraulic Press", "Custom heavy duty 4-pillar hydraulic press", "CAT-PRESS", "SET", "DWG-ENV-500-01", "R1", "450000", "650000", "1", "BOTH"]
    },
    "materials": {
        "collection": "raw_materials",
        "create_schema": RawMaterialCreate,
        "update_schema": RawMaterialUpdate,
        "response_schema": RawMaterialResponse,
        "permission_read": ("master", "read"),
        "permission_write": ("master", "create"),
        "csv_headers": ["code", "name", "description", "category_id", "uom", "hsn_code", "reorder_level", "safety_stock", "default_vendor_code", "unit_id"],
        "sample_row": ["RM-MS-PL-25", "Mild Steel Plate 25mm IS 2062", "High tensile steel plate for machine base", "CAT-STEEL", "KG", "7208", "500", "200", "VEND-001", "Unit_1"]
    },
    "uom": {
        "collection": "uom",
        "create_schema": UoMCreate,
        "update_schema": UoMUpdate,
        "response_schema": UoMResponse,
        "permission_read": ("master", "read"),
        "permission_write": ("master", "create"),
        "csv_headers": ["code", "name", "symbol", "description"],
        "sample_row": ["KG", "Kilogram", "kg", "Standard metric mass unit"]
    },
    "warehouses": {
        "collection": "warehouses",
        "create_schema": WarehouseCreate,
        "update_schema": WarehouseUpdate,
        "response_schema": WarehouseResponse,
        "permission_read": ("master", "read"),
        "permission_write": ("master", "create"),
        "csv_headers": ["code", "name", "unit_id", "location_type", "bay_rack", "capacity_description"],
        "sample_row": ["WH-E1-RM01", "Unit 1 Primary Raw Material Yard", "Unit_1", "RAW_MATERIAL", "Bay 1 - Heavy Plates", "Max 100 Tons"]
    },
    "categories": {
        "collection": "categories",
        "create_schema": CategoryCreate,
        "update_schema": CategoryUpdate,
        "response_schema": CategoryResponse,
        "permission_read": ("master", "read"),
        "permission_write": ("master", "create"),
        "csv_headers": ["code", "name", "category_type", "description"],
        "sample_row": ["CAT-STEEL", "Structural Steel & Plates", "RAW_MATERIAL", "Plates, pipes, beams and raw billets"]
    },
}

# Alias mappings for compatibility
ENTITY_CONFIG["finished_products"] = ENTITY_CONFIG["products"]
ENTITY_CONFIG["raw_materials"] = ENTITY_CONFIG["materials"]

def get_repo(entity: str) -> MasterRepository:
    if entity not in ENTITY_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master entity '{entity}' not found. Supported: {list(ENTITY_CONFIG.keys())}"
        )
    db = mongodb_manager.get_database()
    return MasterRepository(db, ENTITY_CONFIG[entity]["collection"])


# --------------------------------------------------------------------------
# Generic List Endpoint
# --------------------------------------------------------------------------
@router.get("/{entity}")
async def list_master_records(
    entity: str,
    search: Optional[str] = Query(None, description="Search term for code/name"),
    unit_id: Optional[str] = Query(None, description="Scope by facility (Unit_1, Unit_2, BOTH)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    department: Optional[str] = Query(None, description="Filter by department"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    List master data records with search, filtering, pagination, and sorting.
    Enforces 'master:read' permission and unit isolation.
    """
    if "master:read" not in current_user.get("permissions", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission 'master:read' required.")

    # Unit isolation check: If user is bound to Unit_1 and requests Unit_2, deny
    allowed_units = current_user.get("allowed_units", ["BOTH"])
    if "BOTH" not in allowed_units and unit_id and unit_id not in allowed_units and unit_id != "BOTH":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access denied to facility {unit_id}.")

    # Fallback to user's assigned unit if not explicitly passed
    effective_unit = unit_id
    if not effective_unit and "BOTH" not in allowed_units:
        effective_unit = allowed_units[0] if allowed_units else None

    repo = get_repo(entity)
    s_order = -1 if sort_order.lower() == "desc" else 1

    items, total = await repo.list_paginated(
        search=search,
        unit_id=effective_unit,
        is_active=is_active,
        category=category,
        department=department,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=s_order,
    )

    formatted_items = [
        format_doc(item) for item in items
    ]

    total_pages = ceil(total / page_size) if total > 0 else 0

    return {
        "items": formatted_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


# --------------------------------------------------------------------------
# Template Download Endpoint
# --------------------------------------------------------------------------
@router.get("/{entity}/template")
async def download_master_template(
    entity: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Generate downloadable CSV template for Excel data preparation.
    Includes headers and standard example row.
    """
    if "master:read" not in current_user.get("permissions", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission 'master:read' required.")

    if entity not in ENTITY_CONFIG:
        raise HTTPException(status_code=404, detail="Unknown entity")

    cfg = ENTITY_CONFIG[entity]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(cfg["csv_headers"])
    writer.writerow(cfg["sample_row"])

    output.seek(0)
    filename = f"RG_template_{entity}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def format_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d


# --------------------------------------------------------------------------
# Get Next Auto-Generated Code for Employees
# --------------------------------------------------------------------------
@router.get("/employees/next-code")
async def get_next_employee_code(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Returns the next sequential auto-generated employee badge code e.g. EMP-001.
    """
    if "master:read" not in current_user.get("permissions", []) and "hr:read" not in current_user.get("permissions", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission required.")

    repo = get_repo("employees")
    next_code = await repo.generate_next_employee_code()
    return {"next_code": next_code}


# --------------------------------------------------------------------------
# Get Record by ID
# --------------------------------------------------------------------------
@router.get("/{entity}/{record_id}")
async def get_master_record(
    entity: str,
    record_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Retrieve single master record by MongoDB ID.
    """
    if "master:read" not in current_user.get("permissions", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission 'master:read' required.")

    repo = get_repo(entity)
    doc = await repo.get_by_id(record_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity.capitalize()} record not found.")

    return format_doc(doc)


# --------------------------------------------------------------------------
# Create Record Endpoint
# --------------------------------------------------------------------------
@router.post("/{entity}", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf_token)])
async def create_master_record(
    entity: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Create a new master record with validation, duplicate code prevention, and audit stamp.
    Requires 'master:create' permission.
    """
    if current_user.get("role") == RoleName.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin (Owner) has strict read-only monitoring access. Master record creation is prohibited."
        )
    if "master:create" not in current_user.get("permissions", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission 'master:create' required.")

    cfg = ENTITY_CONFIG.get(entity)
    if not cfg:
        raise HTTPException(status_code=404, detail="Unknown master entity")

    # Validate against entity Pydantic schema
    try:
        validated_model = cfg["create_schema"](**payload)
        data = validated_model.model_dump()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    repo = get_repo(entity)
    try:
        inserted_id = await repo.create_record(data, user_email=current_user["email"])
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(val_err))

    created_doc = await repo.get_by_id(inserted_id)
    return format_doc(created_doc)


# --------------------------------------------------------------------------
# Update Record Endpoint
# --------------------------------------------------------------------------
@router.put("/{entity}/{record_id}", dependencies=[Depends(verify_csrf_token)])
async def update_master_record(
    entity: str,
    record_id: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Update an existing master record with duplicate code prevention and audit trail.
    Requires 'master:update' permission.
    """
    if current_user.get("role") == RoleName.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin (Owner) has strict read-only monitoring access. Master record updates are prohibited."
        )
    if "master:update" not in current_user.get("permissions", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission 'master:update' required.")

    cfg = ENTITY_CONFIG.get(entity)
    if not cfg:
        raise HTTPException(status_code=404, detail="Unknown master entity")

    try:
        validated_model = cfg["update_schema"](**payload)
        update_data = validated_model.model_dump(exclude_unset=True)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    repo = get_repo(entity)
    try:
        success = await repo.update_record(record_id, update_data, user_email=current_user["email"])
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(val_err))

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity.capitalize()} record not found.")

    updated_doc = await repo.get_by_id(record_id)
    return format_doc(updated_doc)


# --------------------------------------------------------------------------
# Delete / Deactivate Endpoint
# --------------------------------------------------------------------------
@router.delete("/{entity}/{record_id}", dependencies=[Depends(verify_csrf_token)])
async def delete_master_record(
    entity: str,
    record_id: str,
    permanent: bool = Query(False, description="If true, permanently deletes record; otherwise deactivates"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Deactivate or permanently remove a master record.
    Requires 'master:update' (or 'master:delete' / 'master:administer') permission.
    """
    if current_user.get("role") == RoleName.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin (Owner) has strict read-only monitoring access. Master record deletion is prohibited."
        )
    if "master:update" not in current_user.get("permissions", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission 'master:update' required.")

    repo = get_repo(entity)
    success = await repo.delete_record(
        record_id,
        soft_delete=not permanent,
        user_email=current_user["email"]
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity.capitalize()} record not found.")

    return {"status": "success", "message": f"{entity.capitalize()} record successfully {'deleted' if permanent else 'deactivated'}."}
