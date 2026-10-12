from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from bson import ObjectId
import logging
from app.schemas.power import (
    ElectricityReadingCreate,
    PowerCutLogCreate,
    ReadingStatus,
    MeterType,
    OutageType,
)
from app.models.user import ManufacturingUnit

logger = logging.getLogger(__name__)


class PowerRepository:
    def __init__(self, db: Any):
        self.db = db
        self.readings_col = db["electricity_readings"]
        self.outages_col = db["power_cuts"]

    async def generate_reading_number(self) -> str:
        """Generate sequence-safe unique identifier e.g. ELEC-202610-0001."""
        now = datetime.now(timezone.utc)
        ym_prefix = now.strftime("%Y%m")
        count = await self.readings_col.count_documents({
            "reading_number": {"$regex": f"^ELEC-{ym_prefix}-"}
        })
        return f"ELEC-{ym_prefix}-{(count + 1):04d}"

    async def generate_incident_number(self) -> str:
        """Generate sequence-safe unique identifier e.g. OUTAGE-202610-0001."""
        now = datetime.now(timezone.utc)
        ym_prefix = now.strftime("%Y%m")
        count = await self.outages_col.count_documents({
            "incident_number": {"$regex": f"^OUTAGE-{ym_prefix}-"}
        })
        return f"OUTAGE-{ym_prefix}-{(count + 1):04d}"

    # -------------------------------------------------------------
    # 1. Electricity Readings
    # -------------------------------------------------------------
    async def record_electricity_reading(
        self,
        reading_data: ElectricityReadingCreate,
        recorded_by: str,
    ) -> Dict[str, Any]:
        """
        Record daily or per-shift electricity meter readings.
        Enforces opening/closing arithmetic validation and duplicate prevention.
        """
        if reading_data.closing_reading_kwh < reading_data.opening_reading_kwh:
            raise ValueError(
                f"Invalid meter readings: Closing reading ({reading_data.closing_reading_kwh}) "
                f"cannot be less than opening reading ({reading_data.opening_reading_kwh})."
            )

        units_consumed = round(reading_data.closing_reading_kwh - reading_data.opening_reading_kwh, 2)

        # Duplicate check: same unit, meter, date, and shift
        dup_query = {
            "unit_id": reading_data.unit_id.value,
            "meter_id": reading_data.meter_id,
            "reading_date": reading_data.reading_date,
        }
        if reading_data.shift:
            dup_query["shift"] = reading_data.shift

        existing = await self.readings_col.find_one(dup_query)
        if existing:
            raise ValueError(
                f"Duplicate electricity reading prevented: A reading for meter '{reading_data.meter_id}' "
                f"at {reading_data.unit_id.value} already exists for {reading_data.reading_date} "
                f"(Reading: {existing.get('reading_number')})."
            )

        now = datetime.now(timezone.utc)
        reading_num = await self.generate_reading_number()

        doc = {
            "reading_number": reading_num,
            "reading_date": reading_data.reading_date,
            "unit_id": reading_data.unit_id.value,
            "meter_id": reading_data.meter_id,
            "meter_type": reading_data.meter_type.value,
            "opening_reading_kwh": float(reading_data.opening_reading_kwh),
            "closing_reading_kwh": float(reading_data.closing_reading_kwh),
            "units_consumed_kwh": units_consumed,
            "power_factor": reading_data.power_factor,
            "shift": reading_data.shift,
            "remarks": reading_data.remarks,
            "status": ReadingStatus.CONFIRMED.value,
            "created_at": now,
            "created_by": recorded_by,
        }

        res = await self.readings_col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def list_electricity_readings(
        self,
        unit_id: Optional[str] = None,
        meter_id: Optional[str] = None,
        meter_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Paginated list of electricity readings."""
        query: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id
        if meter_id:
            query["meter_id"] = meter_id
        if meter_type:
            query["meter_type"] = meter_type
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            query["reading_date"] = date_filter

        total = await self.readings_col.count_documents(query)
        skip = (page - 1) * page_size
        cursor = self.readings_col.find(query).sort("reading_date", -1).skip(skip).limit(page_size)
        items = await cursor.to_list(length=page_size)
        return items, total

    # -------------------------------------------------------------
    # 2. Power-Cuts & Downtime Logs
    # -------------------------------------------------------------
    async def record_power_cut(
        self,
        outage_data: PowerCutLogCreate,
        logged_by: str,
    ) -> Dict[str, Any]:
        """
        Record power outage incident with start/end duration calculation,
        preventing overlapping outages for the same manufacturing facility.
        """
        start = outage_data.start_time
        end = outage_data.end_time

        if end <= start:
            raise ValueError(
                f"Invalid outage times: End time ({end.isoformat()}) must be after start time ({start.isoformat()})."
            )

        duration_minutes = round((end - start).total_seconds() / 60.0, 1)

        # Overlap check for the same unit
        overlap_query = {
            "unit_id": outage_data.unit_id.value,
            "start_time": {"$lt": end},
            "end_time": {"$gt": start},
        }
        overlapping_doc = await self.outages_col.find_one(overlap_query)
        if overlapping_doc:
            raise ValueError(
                f"Overlapping power-cut record prevented: Incident {overlapping_doc.get('incident_number')} "
                f"is already recorded from {overlapping_doc.get('start_time')} to {overlapping_doc.get('end_time')} "
                f"at {outage_data.unit_id.value}."
            )

        incident_number = await self.generate_incident_number()
        now = datetime.now(timezone.utc)

        doc = {
            "incident_number": incident_number,
            "unit_id": outage_data.unit_id.value,
            "start_time": start,
            "end_time": end,
            "duration_minutes": duration_minutes,
            "outage_type": outage_data.outage_type.value,
            "reason": outage_data.reason,
            "backup_generator_used": outage_data.backup_generator_used,
            "fuel_consumed_liters": outage_data.fuel_consumed_liters,
            "affected_departments": outage_data.affected_departments,
            "production_order_ids": outage_data.production_order_ids,
            "remarks": outage_data.remarks,
            "created_at": now,
            "created_by": logged_by,
        }

        res = await self.outages_col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def list_power_cuts(
        self,
        unit_id: Optional[str] = None,
        outage_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Paginated search for power-cuts and downtime incidents."""
        query: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id
        if outage_type:
            query["outage_type"] = outage_type
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = datetime.fromisoformat(start_date)
            if end_date:
                date_filter["$lte"] = datetime.fromisoformat(end_date)
            query["start_time"] = date_filter

        total = await self.outages_col.count_documents(query)
        skip = (page - 1) * page_size
        cursor = self.outages_col.find(query).sort("start_time", -1).skip(skip).limit(page_size)
        items = await cursor.to_list(length=page_size)
        return items, total

    # -------------------------------------------------------------
    # 3. Analytics & Summary Aggregations
    # -------------------------------------------------------------
    async def get_power_summary(self, unit_id: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate downtime metrics and electricity consumption totals."""
        unit_filter: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            unit_filter["unit_id"] = unit_id

        # Outages aggregation
        outage_pipeline = [
            {"$match": unit_filter},
            {
                "$group": {
                    "_id": None,
                    "total_count": {"$sum": 1},
                    "total_minutes": {"$sum": "$duration_minutes"},
                    "dg_count": {
                        "$sum": {"$cond": [{"$eq": ["$backup_generator_used", True]}, 1, 0]}
                    },
                    "total_fuel": {"$sum": "$fuel_consumed_liters"},
                }
            }
        ]
        outage_res = await self.outages_col.aggregate(outage_pipeline).to_list(length=1)
        if outage_res:
            row = outage_res[0]
            total_count = int(row.get("total_count", 0))
            total_minutes = round(float(row.get("total_minutes", 0.0)), 1)
            total_hours = round(total_minutes / 60.0, 2)
            dg_count = int(row.get("dg_count", 0))
            total_fuel = round(float(row.get("total_fuel", 0.0)), 2)
        else:
            total_count = 0
            total_minutes = 0.0
            total_hours = 0.0
            dg_count = 0
            total_fuel = 0.0

        # Readings aggregation by meter type
        readings_pipeline = [
            {"$match": unit_filter},
            {
                "$group": {
                    "_id": "$meter_type",
                    "total_kwh": {"$sum": "$units_consumed_kwh"},
                }
            }
        ]
        readings_res = await self.readings_col.aggregate(readings_pipeline).to_list(length=10)
        consumption_by_type = {r["_id"]: float(r["total_kwh"]) for r in readings_res}

        return {
            "unit_id": unit_id,
            "total_outages_count": total_count,
            "total_downtime_minutes": total_minutes,
            "total_downtime_hours": total_hours,
            "generator_run_count": dg_count,
            "total_fuel_consumed_liters": total_fuel,
            "total_grid_consumption_kwh": round(consumption_by_type.get(MeterType.GRID_EB.value, 0.0), 2),
            "total_dg_consumption_kwh": round(consumption_by_type.get(MeterType.DIESEL_GENERATOR.value, 0.0), 2),
            "total_solar_consumption_kwh": round(consumption_by_type.get(MeterType.SOLAR.value, 0.0), 2),
        }
