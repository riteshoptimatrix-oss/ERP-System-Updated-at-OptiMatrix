from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from app.models.user import ManufacturingUnit


class MeterType(str, Enum):
    GRID_EB = "GRID_EB"
    DIESEL_GENERATOR = "DIESEL_GENERATOR"
    SOLAR = "SOLAR"


class OutageType(str, Enum):
    GRID_FAILURE = "GRID_FAILURE"
    SCHEDULED_MAINTENANCE = "SCHEDULED_MAINTENANCE"
    EMERGENCY_SHUTDOWN = "EMERGENCY_SHUTDOWN"
    GENERATOR_FAILURE = "GENERATOR_FAILURE"
    LOCAL_TRIP = "LOCAL_TRIP"


class ReadingStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    AUDITED = "AUDITED"


# -------------------------------------------------------------
# Electricity Reading Models
# -------------------------------------------------------------
class ElectricityReadingCreate(BaseModel):
    reading_date: str = Field(..., description="ISO Date string (YYYY-MM-DD)")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    meter_id: str = Field(..., min_length=2, max_length=100, description="Meter identifier e.g. METER-MAIN-EF1")
    meter_type: MeterType = Field(default=MeterType.GRID_EB)
    opening_reading_kwh: float = Field(..., ge=0.0, description="Opening reading in kWh")
    closing_reading_kwh: float = Field(..., ge=0.0, description="Closing reading in kWh")
    power_factor: Optional[float] = Field(None, ge=0.0, le=1.0, description="Average power factor (e.g. 0.96)")
    shift: Optional[str] = Field(None, max_length=50, description="Shift 1, Shift 2, General")
    remarks: Optional[str] = Field(None, max_length=500)


class ElectricityReadingResponse(BaseModel):
    id: str
    reading_number: str
    reading_date: str
    unit_id: str
    meter_id: str
    meter_type: str
    opening_reading_kwh: float
    closing_reading_kwh: float
    units_consumed_kwh: float
    power_factor: Optional[float] = None
    shift: Optional[str] = None
    remarks: Optional[str] = None
    status: str
    created_at: datetime
    created_by: str


# -------------------------------------------------------------
# Power-Cut & Outage Models
# -------------------------------------------------------------
class PowerCutLogCreate(BaseModel):
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    start_time: datetime = Field(..., description="Start timestamp of the outage")
    end_time: datetime = Field(..., description="End timestamp of the outage")
    outage_type: OutageType = Field(default=OutageType.GRID_FAILURE)
    reason: str = Field(..., min_length=3, max_length=500, description="Reason for the power interruption")
    backup_generator_used: bool = Field(default=False, description="Whether diesel generator was started")
    fuel_consumed_liters: Optional[float] = Field(None, ge=0.0, description="Diesel liters consumed during DG run")
    affected_departments: List[str] = Field(default_factory=list, description="Affected departments/lines")
    production_order_ids: List[str] = Field(default_factory=list, description="Affected running production orders")
    remarks: Optional[str] = Field(None, max_length=500)


class PowerCutLogResponse(BaseModel):
    id: str
    incident_number: str
    unit_id: str
    start_time: datetime
    end_time: datetime
    duration_minutes: float
    outage_type: str
    reason: str
    backup_generator_used: bool
    fuel_consumed_liters: Optional[float] = None
    affected_departments: List[str]
    production_order_ids: List[str]
    remarks: Optional[str] = None
    created_at: datetime
    created_by: str


# -------------------------------------------------------------
# Power & Downtime Summary Models
# -------------------------------------------------------------
class PowerAnalyticsSummary(BaseModel):
    unit_id: Optional[str] = None
    total_outages_count: int
    total_downtime_minutes: float
    total_downtime_hours: float
    generator_run_count: int
    total_fuel_consumed_liters: float
    total_grid_consumption_kwh: float
    total_dg_consumption_kwh: float
    total_solar_consumption_kwh: float
