import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.models.user import RoleName, ManufacturingUnit
from app.core.security import hash_password
from datetime import datetime, timezone, timedelta


@pytest.fixture
async def seed_wastage_test_data(setup_test_db):
    """Seed raw material, finished product, and a production order with BOM scrap."""
    db = setup_test_db

    # 1. Raw material with standard cost
    rm_res = await db["raw_materials"].insert_one({
        "code": "RM-STEEL-PLATE-500",
        "name": "Heavy Steel Structural Plate",
        "uom": "KG",
        "standard_cost": 85.0,
        "unit_id": "Unit_1",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })
    rm_id = str(rm_res.inserted_id)

    # 2. Finished Product
    fg_res = await db["finished_products"].insert_one({
        "code": "FG-HYD-PRESS-20",
        "name": "20T Hydraulic Press",
        "uom": "PCS",
        "standard_cost": 150000.0,
        "selling_price": 220000.0,
        "unit_id": "Unit_1",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })
    fg_id = str(fg_res.inserted_id)

    # 3. BOM with 5% scrap allowance
    bom_res = await db["boms"].insert_one({
        "bom_number": "BOM-HYD-PRESS-01",
        "product_id": fg_id,
        "product_code": "FG-HYD-PRESS-20",
        "product_name": "20T Hydraulic Press",
        "unit_id": "Unit_1",
        "base_quantity": 1.0,
        "revision_no": "R1",
        "status": "APPROVED",
        "is_active": True,
        "components": [
            {
                "material_id": rm_id,
                "material_code": "RM-STEEL-PLATE-500",
                "material_name": "Heavy Steel Structural Plate",
                "uom": "KG",
                "net_quantity": 100.0,
                "scrap_percentage": 5.0,
                "gross_quantity": 105.0,
                "unit_cost": 85.0,
                "estimated_cost": 8925.0,
            }
        ],
        "total_estimated_cost": 8925.0,
        "created_at": datetime.now(timezone.utc),
    })
    bom_id = str(bom_res.inserted_id)

    # 4. Production order for 10 machines
    po_res = await db["production_orders"].insert_one({
        "order_number": "PRD-202610-TEST-01",
        "product_id": fg_id,
        "product_code": "FG-HYD-PRESS-20",
        "product_name": "20T Hydraulic Press",
        "product_uom": "PCS",
        "bom_id": bom_id,
        "bom_number": "BOM-HYD-PRESS-01",
        "bom_revision_no": "R1",
        "unit_id": "Unit_1",
        "target_warehouse_id": "WH-FG-MAIN",
        "target_warehouse_code": "WH-FG-MAIN",
        "planned_quantity": 10.0,
        "produced_quantity": 8.0,
        "rejected_quantity": 0.0,
        "remaining_quantity": 2.0,
        "status": "IN_PROGRESS",
        "completion_percentage": 80.0,
        "materials": [
            {
                "material_id": rm_id,
                "material_code": "RM-STEEL-PLATE-500",
                "material_name": "Heavy Steel Structural Plate",
                "uom": "KG",
                "standard_quantity_per_unit": 100.0,
                "total_standard_required": 1000.0,
                "total_issued": 1050.0,
                "unit_cost": 85.0,
                "standard_total_cost": 85000.0,
                "actual_total_cost": 89250.0,
            }
        ],
        "created_at": datetime.now(timezone.utc),
    })
    po_id = str(po_res.inserted_id)

    return {
        "rm_id": rm_id,
        "fg_id": fg_id,
        "bom_id": bom_id,
        "po_id": po_id,
    }


@pytest.mark.asyncio
async def test_scrap_entry_lifecycle_and_costing(async_client: AsyncClient, setup_test_users, seed_wastage_test_data):
    """Test creating, calculating cost, updating, and approving a scrap entry."""
    data = seed_wastage_test_data
    po_id = data["po_id"]
    rm_id = data["rm_id"]

    # 1. Login as super admin
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 2. Record daily scrap entry (25 KG of steel offcuts)
    scrap_payload = {
        "entry_date": "2026-10-10",
        "unit_id": "Unit_1",
        "production_order_id": po_id,
        "item_id": rm_id,
        "item_code": "RM-STEEL-PLATE-500",
        "item_name": "Heavy Steel Structural Plate",
        "item_type": "RAW_MATERIAL",
        "scrap_category": "CUTTING_OFFCUT",
        "quantity": 25.0,
        "uom": "KG",
        "reason": "Edge trimming offcuts from laser cutting bed",
        "disposition": "SCRAP_YARD_SALE",
        "operator_name": "Ramesh Kumar",
        "machine_id": "LASER-CUTTER-01",
    }
    create_res = await async_client.post(
        "/api/v1/wastage/entries",
        json=scrap_payload,
        headers=headers,
    )
    assert create_res.status_code == 201
    entry = create_res.json()
    assert entry["entry_number"].startswith("SCRAP-")
    assert entry["quantity"] == 25.0
    assert entry["unit_cost"] == 85.0
    assert entry["total_cost"] == 2125.0  # 25 * 85.0
    assert entry["status"] == "SUBMITTED"
    entry_id = entry["id"]

    # 3. Duplicate prevention: Attempt to submit identical scrap entry for same order, item, category, and date
    dup_res = await async_client.post(
        "/api/v1/wastage/entries",
        json=scrap_payload,
        headers=headers,
    )
    assert dup_res.status_code == 400
    err_msg = dup_res.json().get("error", {}).get("message") or dup_res.json().get("detail", "")
    assert "Duplicate scrap entry prevented" in err_msg

    # 4. Update/correct scrap quantity (e.g. weighed 30 KG instead of 25 KG)
    update_res = await async_client.put(
        f"/api/v1/wastage/entries/{entry_id}",
        json={"quantity": 30.0, "reason": "Corrected calibrated scale reading"},
        headers=headers,
    )
    assert update_res.status_code == 200
    updated_entry = update_res.json()
    assert updated_entry["quantity"] == 30.0
    assert updated_entry["total_cost"] == 2550.0  # 30 * 85.0

    # 5. Approve scrap entry
    approve_res = await async_client.post(
        f"/api/v1/wastage/entries/{entry_id}/approve",
        json={"notes": "Verified by shop-floor supervisor"},
        headers=headers,
    )
    assert approve_res.status_code == 200
    approved_entry = approve_res.json()
    assert approved_entry["status"] == "APPROVED"
    assert approved_entry["approved_by"] == "admin_ops@testcorp.com"


@pytest.mark.asyncio
async def test_planned_vs_actual_wastage_comparison(async_client: AsyncClient, setup_test_users, seed_wastage_test_data):
    """Test planned vs actual scrap reconciliation for a production order."""
    data = seed_wastage_test_data
    po_id = data["po_id"]
    rm_id = data["rm_id"]

    # 1. Login
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    csrf_token = login_res.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 2. Record and approve scrap of 45 KG (BOM planned scrap is 5% of 1000 = 50 KG)
    scrap_payload = {
        "entry_date": "2026-10-10",
        "unit_id": "Unit_1",
        "production_order_id": po_id,
        "item_id": rm_id,
        "item_code": "RM-STEEL-PLATE-500",
        "item_name": "Heavy Steel Structural Plate",
        "item_type": "RAW_MATERIAL",
        "scrap_category": "MACHINING_SWARF",
        "quantity": 45.0,
        "uom": "KG",
        "reason": "Milling swarf chips collected from shop floor",
    }
    create_res = await async_client.post("/api/v1/wastage/entries", json=scrap_payload, headers=headers)
    assert create_res.status_code == 201
    entry_id = create_res.json()["id"]

    await async_client.post(f"/api/v1/wastage/entries/{entry_id}/approve", json={}, headers=headers)

    # 3. Retrieve Planned vs Actual Comparison report
    comp_res = await async_client.get(f"/api/v1/wastage/comparison/{po_id}")
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["order_number"] == "PRD-202610-TEST-01"
    assert len(comp_data["components"]) == 1

    comp_item = comp_data["components"][0]
    assert comp_item["material_code"] == "RM-STEEL-PLATE-500"
    assert comp_item["planned_scrap_percentage"] == 5.0
    assert comp_item["planned_scrap_quantity"] == 50.0  # 1000 * 5%
    assert comp_item["actual_scrap_quantity"] == 45.0
    assert comp_item["scrap_variance"] == -5.0  # 5 KG less scrap than planned allowance!


@pytest.mark.asyncio
async def test_electricity_readings_validation_and_duplicate_prevention(async_client: AsyncClient, setup_test_users):
    """Test electricity meter reading validation, consumption math, and duplicate prevention."""
    # 1. Login
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    csrf_token = login_res.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 2. Record valid electricity reading
    reading_payload = {
        "reading_date": "2026-10-10",
        "unit_id": "Unit_1",
        "meter_id": "METER-MAIN-EB-01",
        "meter_type": "GRID_EB",
        "opening_reading_kwh": 125000.0,
        "closing_reading_kwh": 126450.0,
        "power_factor": 0.98,
        "shift": "Shift 1",
        "remarks": "Normal operation",
    }
    create_res = await async_client.post("/api/v1/power/readings", json=reading_payload, headers=headers)
    assert create_res.status_code == 201
    reading = create_res.json()
    assert reading["reading_number"].startswith("ELEC-")
    assert reading["units_consumed_kwh"] == 1450.0  # 126450.0 - 125000.0

    # 3. Prevent duplicate reading for same meter, unit, date, and shift
    dup_res = await async_client.post("/api/v1/power/readings", json=reading_payload, headers=headers)
    assert dup_res.status_code == 400
    err_msg = dup_res.json().get("error", {}).get("message") or dup_res.json().get("detail", "")
    assert "Duplicate electricity reading prevented" in err_msg

    # 4. Reject invalid reading where closing < opening
    invalid_payload = {
        "reading_date": "2026-10-10",
        "unit_id": "Unit_1",
        "meter_id": "METER-DG-01",
        "meter_type": "DIESEL_GENERATOR",
        "opening_reading_kwh": 5000.0,
        "closing_reading_kwh": 4800.0,  # Negative consumption!
    }
    invalid_res = await async_client.post("/api/v1/power/readings", json=invalid_payload, headers=headers)
    assert invalid_res.status_code == 400
    inv_msg = invalid_res.json().get("error", {}).get("message") or invalid_res.json().get("detail", "")
    assert "cannot be less than opening reading" in inv_msg


@pytest.mark.asyncio
async def test_power_cut_logging_and_overlap_prevention(async_client: AsyncClient, setup_test_users):
    """Test power outage recording, duration calculation, and overlap prevention."""
    # 1. Login
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    csrf_token = login_res.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    start_t = datetime(2026, 10, 10, 14, 0, 0, tzinfo=timezone.utc)
    end_t = datetime(2026, 10, 10, 15, 30, 0, tzinfo=timezone.utc)

    # 2. Record power outage of 90 minutes
    outage_payload = {
        "unit_id": "Unit_1",
        "start_time": start_t.isoformat(),
        "end_time": end_t.isoformat(),
        "outage_type": "GRID_FAILURE",
        "reason": "Substation transformer feeder trip due to storm",
        "backup_generator_used": True,
        "fuel_consumed_liters": 45.0,
        "affected_departments": ["Machine Shop", "Assembly Line 1"],
    }
    create_res = await async_client.post("/api/v1/power/outages", json=outage_payload, headers=headers)
    assert create_res.status_code == 201
    outage = create_res.json()
    assert outage["incident_number"].startswith("OUTAGE-")
    assert outage["duration_minutes"] == 90.0
    assert outage["backup_generator_used"] is True
    assert outage["fuel_consumed_liters"] == 45.0

    # 3. Reject invalid outage where end_time <= start_time
    invalid_payload = {
        "unit_id": "Unit_1",
        "start_time": end_t.isoformat(),
        "end_time": start_t.isoformat(),
        "reason": "Invalid timestamps",
    }
    invalid_res = await async_client.post("/api/v1/power/outages", json=invalid_payload, headers=headers)
    assert invalid_res.status_code == 400
    inv_t_msg = invalid_res.json().get("error", {}).get("message") or invalid_res.json().get("detail", "")
    assert "must be after start time" in inv_t_msg

    # 4. Prevent overlapping outage for the same facility
    overlapping_payload = {
        "unit_id": "Unit_1",
        "start_time": (start_t + timedelta(minutes=30)).isoformat(),  # 14:30
        "end_time": (end_t + timedelta(minutes=30)).isoformat(),      # 16:00
        "reason": "Overlapping outage attempt",
    }
    dup_res = await async_client.post("/api/v1/power/outages", json=overlapping_payload, headers=headers)
    assert dup_res.status_code == 400
    dup_t_msg = dup_res.json().get("error", {}).get("message") or dup_res.json().get("detail", "")
    assert "Overlapping power-cut record prevented" in dup_t_msg

    # 5. Summary KPI check
    summary_res = await async_client.get("/api/v1/power/summary?unit_id=Unit_1")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_outages_count"] >= 1
    assert summary["total_downtime_minutes"] >= 90.0
    assert summary["generator_run_count"] >= 1
