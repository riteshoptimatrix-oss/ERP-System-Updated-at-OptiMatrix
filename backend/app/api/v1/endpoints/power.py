from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from app.database.mongodb import mongodb_manager
from app.api.deps import get_current_active_user, require_permission, verify_csrf_token
from app.models.user import ModuleName, ActionType
from app.repositories.power_repository import PowerRepository
from app.schemas.power import (
    ElectricityReadingCreate,
    ElectricityReadingResponse,
    PowerCutLogCreate,
    PowerCutLogResponse,
    PowerAnalyticsSummary,
)
from app.schemas.master import PaginatedResponse

router = APIRouter(prefix="/power", tags=["Electricity & Power-Cut Tracking"])


def get_power_repo() -> PowerRepository:
    db = mongodb_manager.get_database()
    return PowerRepository(db)


def serialize_reading(doc: Dict[str, Any]) -> ElectricityReadingResponse:
    return ElectricityReadingResponse(
        id=str(doc["_id"]),
        reading_number=doc.get("reading_number", ""),
        reading_date=doc.get("reading_date", ""),
        unit_id=doc.get("unit_id", "Unit_1"),
        meter_id=doc.get("meter_id", ""),
        meter_type=doc.get("meter_type", "GRID_EB"),
        opening_reading_kwh=doc.get("opening_reading_kwh", 0.0),
        closing_reading_kwh=doc.get("closing_reading_kwh", 0.0),
        units_consumed_kwh=doc.get("units_consumed_kwh", 0.0),
        power_factor=doc.get("power_factor"),
        shift=doc.get("shift"),
        remarks=doc.get("remarks"),
        status=doc.get("status", "CONFIRMED"),
        created_at=doc["created_at"],
        created_by=doc.get("created_by", "SYSTEM"),
    )


def serialize_outage(doc: Dict[str, Any]) -> PowerCutLogResponse:
    return PowerCutLogResponse(
        id=str(doc["_id"]),
        incident_number=doc.get("incident_number", ""),
        unit_id=doc.get("unit_id", "Unit_1"),
        start_time=doc["start_time"],
        end_time=doc["end_time"],
        duration_minutes=doc.get("duration_minutes", 0.0),
        outage_type=doc.get("outage_type", "GRID_FAILURE"),
        reason=doc.get("reason", ""),
        backup_generator_used=doc.get("backup_generator_used", False),
        fuel_consumed_liters=doc.get("fuel_consumed_liters"),
        affected_departments=doc.get("affected_departments", []),
        production_order_ids=doc.get("production_order_ids", []),
        remarks=doc.get("remarks"),
        created_at=doc["created_at"],
        created_by=doc.get("created_by", "SYSTEM"),
    )


# -------------------------------------------------------------
# 1. Summary & Analytics
# -------------------------------------------------------------
@router.get("/summary", response_model=PowerAnalyticsSummary)
async def get_power_summary(
    unit_id: Optional[str] = Query(None, description="Optional unit filter: Unit_1 | Unit_2"),
    current_user: Dict[str, Any] = Depends(require_permission(ModuleName.POWER, ActionType.READ)),
    repo: PowerRepository = Depends(get_power_repo),
):
    """Retrieve high-level power downtime metrics and electricity consumption totals."""
    return await repo.get_power_summary(unit_id)


# -------------------------------------------------------------
# 2. Electricity Readings
# -------------------------------------------------------------
@router.post("/readings", response_model=ElectricityReadingResponse, status_code=status.HTTP_201_CREATED)
async def record_electricity_reading(
    reading_data: ElectricityReadingCreate,
    current_user: Dict[str, Any] = Depends(require_permission(ModuleName.POWER, ActionType.CREATE)),
    csrf: None = Depends(verify_csrf_token),
    repo: PowerRepository = Depends(get_power_repo),
):
    """Record daily electricity meter reading with arithmetic validation and duplicate prevention."""
    try:
        doc = await repo.record_electricity_reading(
            reading_data=reading_data,
            recorded_by=current_user.get("email", "USER"),
        )
        return serialize_reading(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/readings", response_model=PaginatedResponse[ElectricityReadingResponse])
async def list_electricity_readings(
    unit_id: Optional[str] = Query(None),
    meter_id: Optional[str] = Query(None),
    meter_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(require_permission(ModuleName.POWER, ActionType.READ)),
    repo: PowerRepository = Depends(get_power_repo),
):
    """List electricity meter readings with filtering and pagination."""
    items, total = await repo.list_electricity_readings(
        unit_id=unit_id,
        meter_id=meter_id,
        meter_type=meter_type,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[serialize_reading(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if page_size > 0 else 0,
    )


# -------------------------------------------------------------
# 3. Power-Cuts & Downtime Incidents
# -------------------------------------------------------------
@router.post("/outages", response_model=PowerCutLogResponse, status_code=status.HTTP_201_CREATED)
async def record_power_cut(
    outage_data: PowerCutLogCreate,
    current_user: Dict[str, Any] = Depends(require_permission(ModuleName.POWER, ActionType.CREATE)),
    csrf: None = Depends(verify_csrf_token),
    repo: PowerRepository = Depends(get_power_repo),
):
    """Log power outage incident with duration auto-calculation and overlap prevention."""
    try:
        doc = await repo.record_power_cut(
            outage_data=outage_data,
            logged_by=current_user.get("email", "USER"),
        )
        return serialize_outage(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/outages", response_model=PaginatedResponse[PowerCutLogResponse])
async def list_power_cuts(
    unit_id: Optional[str] = Query(None),
    outage_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(require_permission(ModuleName.POWER, ActionType.READ)),
    repo: PowerRepository = Depends(get_power_repo),
):
    """List power outages and downtime incidents."""
    items, total = await repo.list_power_cuts(
        unit_id=unit_id,
        outage_type=outage_type,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[serialize_outage(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if page_size > 0 else 0,
    )
