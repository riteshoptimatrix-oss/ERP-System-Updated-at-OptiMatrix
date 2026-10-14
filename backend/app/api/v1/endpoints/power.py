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
    DailyElectricityScrapTracker,
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
        restart_delay_minutes=doc.get("restart_delay_minutes"),
        downtime_duration_str=doc.get("downtime_duration_str"),
        power_cut_time=doc.get("power_cut_time"),
        power_restored_time=doc.get("power_restored_time"),
        incident_date=doc.get("incident_date"),
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


# -------------------------------------------------------------
# 4. Daily Electricity & Scrap Tracker
# -------------------------------------------------------------
@router.get("/scrap-tracker", response_model=PaginatedResponse[DailyElectricityScrapTracker])
async def list_electricity_scrap_tracker(
    unit_id: Optional[str] = Query(None),
    product_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(require_permission(ModuleName.POWER, ActionType.READ)),
    repo: PowerRepository = Depends(get_power_repo),
):
    """Retrieve all daily electricity and scrap tracker records."""
    items, total = await repo.list_electricity_scrap_tracker(
        unit_id=unit_id,
        product_type=product_type,
        search=search,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[
            DailyElectricityScrapTracker(
                id=str(d["_id"]),
                date=d.get("date", ""),
                total_production_kg=d.get("total_production_kg", 0.0),
                product_type=d.get("product_type", "Tubing"),
                startup_scrap_kg=d.get("startup_scrap_kg", 0.0),
                cutting_scrap_kg=d.get("cutting_scrap_kg", 0.0),
                total_scrap_kg=d.get("total_scrap_kg", 0.0),
                scrap_percent_str=d.get("scrap_percent_str", "0.00%"),
                electricity_off_count=d.get("electricity_off_count", 0),
                total_off_time_min=d.get("total_off_time_min", 0.0),
                machine_working_hours=str(d.get("machine_working_hours", "8.0")),
                shift_duration_hr=d.get("shift_duration_hr", 8.0),
                main_reason=d.get("main_reason"),
                remarks=d.get("remarks"),
                unit_id=d.get("unit_id", "Unit_1"),
                created_at=d.get("created_at"),
            )
            for d in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if page_size > 0 else 0,
    )


@router.post("/scrap-tracker", response_model=DailyElectricityScrapTracker, status_code=status.HTTP_201_CREATED)
async def create_electricity_scrap_entry(
    tracker_data: DailyElectricityScrapTracker,
    current_user: Dict[str, Any] = Depends(require_permission(ModuleName.POWER, ActionType.CREATE)),
    csrf: None = Depends(verify_csrf_token),
    repo: PowerRepository = Depends(get_power_repo),
):
    """Create a new daily electricity & scrap entry."""
    doc = await repo.create_electricity_scrap_tracker(tracker_data.dict())
    return DailyElectricityScrapTracker(
        id=str(doc["_id"]),
        date=doc.get("date", ""),
        total_production_kg=doc.get("total_production_kg", 0.0),
        product_type=doc.get("product_type", "Tubing"),
        startup_scrap_kg=doc.get("startup_scrap_kg", 0.0),
        cutting_scrap_kg=doc.get("cutting_scrap_kg", 0.0),
        total_scrap_kg=doc.get("total_scrap_kg", 0.0),
        scrap_percent_str=doc.get("scrap_percent_str", "0.00%"),
        electricity_off_count=doc.get("electricity_off_count", 0),
        total_off_time_min=doc.get("total_off_time_min", 0.0),
        machine_working_hours=str(doc.get("machine_working_hours", "8.0")),
        shift_duration_hr=doc.get("shift_duration_hr", 8.0),
        main_reason=doc.get("main_reason"),
        remarks=doc.get("remarks"),
        unit_id=doc.get("unit_id", "Unit_1"),
        created_at=doc.get("created_at"),
    )

