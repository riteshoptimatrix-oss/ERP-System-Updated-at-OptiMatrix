import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.models.user import RoleName, ManufacturingUnit
from app.core.security import hash_password
from datetime import datetime, timezone


@pytest.fixture
async def seed_inventory_test_data(setup_test_db):
    """Seed test raw materials, finished products, and warehouses."""
    db = setup_test_db

    # Seed Inventory Manager user
    await db["users"].insert_one({
        "email": "inv_manager@testcorp.com",
        "full_name": "Inventory Manager",
        "hashed_password": hash_password("ValidPassword123!"),
        "role": RoleName.INVENTORY_MANAGER.value,
        "allowed_units": [ManufacturingUnit.BOTH.value],
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    # Seed Raw Material
    rm_res = await db["raw_materials"].insert_one({
        "code": "RM-INV-001",
        "name": "Hardened Alloy Plate 50mm",
        "uom": "KGS",
        "standard_cost": 150.0,
        "reorder_level": 40.0,
        "safety_stock": 20.0,
        "unit_id": "Unit_1",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    # Seed Finished Good
    fg_res = await db["finished_products"].insert_one({
        "code": "FG-INV-001",
        "name": "Industrial Rotary Pump V2",
        "uom": "NOS",
        "standard_cost": 25000.0,
        "reorder_level": 5.0,
        "safety_stock": 2.0,
        "unit_id": "Unit_1",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    # Seed Warehouse 1 (Unit 1)
    wh1_res = await db["warehouses"].insert_one({
        "code": "WH-E1-MAIN",
        "name": "Unit 1 Central Store",
        "unit_id": "Unit_1",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    # Seed Warehouse 2 (Unit 2)
    wh2_res = await db["warehouses"].insert_one({
        "code": "WH-E2-AUX",
        "name": "Unit 2 Auxiliary Store",
        "unit_id": "Unit_2",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    return {
        "rm_id": str(rm_res.inserted_id),
        "fg_id": str(fg_res.inserted_id),
        "wh1_id": str(wh1_res.inserted_id),
        "wh2_id": str(wh2_res.inserted_id),
    }


@pytest.mark.asyncio
async def test_material_inward_outward_and_negative_stock_rejection(
    async_client: AsyncClient,
    setup_test_users,
    seed_inventory_test_data,
):
    """
    Test material inward increases stock, outward decreases stock,
    and atomic negative stock rejection.
    """
    data = seed_inventory_test_data

    # Login as Inventory Manager
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "inv_manager@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.json()["csrf_token"]
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 1. Inward 100 KGS
    inward_payload = {
        "item_id": data["rm_id"],
        "item_type": "RAW_MATERIAL",
        "warehouse_id": data["wh1_id"],
        "unit_id": "Unit_1",
        "quantity": 100.0,
        "unit_cost": 150.0,
        "batch_no": "LOT-2026-A",
        "supplier_id": "VEND-001",
        "invoice_no": "INV-5501",
    }
    res_in = await async_client.post(
        "/api/v1/inventory/inward",
        json=inward_payload,
        headers=headers,
    )
    assert res_in.status_code == 201, res_in.text
    in_doc = res_in.json()
    assert in_doc["quantity_change"] == 100.0
    assert in_doc["balance_after"] == 100.0
    assert in_doc["movement_type"] == "MATERIAL_INWARD"

    # Check stock balances
    res_bal = await async_client.get(
        "/api/v1/inventory/balances?search=RM-INV-001",
    )
    assert res_bal.status_code == 200
    bal_data = res_bal.json()
    assert bal_data["total"] >= 1
    item_bal = next(b for b in bal_data["items"] if b["item_code"] == "RM-INV-001")
    assert item_bal["quantity_on_hand"] == 100.0
    assert item_bal["quantity_available"] == 100.0

    # 2. Outward 40 KGS
    outward_payload = {
        "item_id": data["rm_id"],
        "warehouse_id": data["wh1_id"],
        "unit_id": "Unit_1",
        "quantity": 40.0,
        "destination": "Assembly Line 1",
        "batch_no": "LOT-2026-A",
    }
    res_out = await async_client.post(
        "/api/v1/inventory/outward",
        json=outward_payload,
        headers=headers,
    )
    assert res_out.status_code == 201, res_out.text
    assert res_out.json()["balance_after"] == 60.0

    # 3. Attempt over-outward 80 KGS (Only 60 available) -> Must reject with 400
    excess_outward = {
        "item_id": data["rm_id"],
        "warehouse_id": data["wh1_id"],
        "unit_id": "Unit_1",
        "quantity": 80.0,
        "destination": "Assembly Line 1",
        "batch_no": "LOT-2026-A",
    }
    res_excess = await async_client.post(
        "/api/v1/inventory/outward",
        json=excess_outward,
        headers=headers,
    )
    assert res_excess.status_code == 400
    err_msg = res_excess.json().get("error", {}).get("message", "") or res_excess.json().get("detail", "")
    assert "Negative stock prohibited" in err_msg


@pytest.mark.asyncio
async def test_inter_warehouse_transfer_and_ledger_audit(
    async_client: AsyncClient,
    setup_test_users,
    seed_inventory_test_data,
):
    """
    Test transferring stock between warehouses generates paired TRANSFER_OUT and TRANSFER_IN ledger records.
    """
    data = seed_inventory_test_data

    # Login as Inventory Manager
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "inv_manager@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.json()["csrf_token"]
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # Initial inward 50 units of Finished Good into WH1
    await async_client.post(
        "/api/v1/inventory/inward",
        json={
            "item_id": data["fg_id"],
            "item_type": "FINISHED_GOOD",
            "warehouse_id": data["wh1_id"],
            "unit_id": "Unit_1",
            "quantity": 50.0,
            "unit_cost": 25000.0,
        },
        headers=headers,
    )

    # Transfer 20 units from WH1 (Unit 1) to WH2 (Unit 2)
    transfer_payload = {
        "source_warehouse_id": data["wh1_id"],
        "target_warehouse_id": data["wh2_id"],
        "item_id": data["fg_id"],
        "quantity": 20.0,
        "vehicle_number": "MH-12-PQ-8888",
        "transfer_reason": "Unit 2 demand replenishment",
    }
    res_trf = await async_client.post(
        "/api/v1/inventory/transfer",
        json=transfer_payload,
        headers=headers,
    )
    assert res_trf.status_code == 201, res_trf.text
    trf_res = res_trf.json()
    assert trf_res["status"] == "COMPLETED"
    assert trf_res["quantity"] == 20.0

    # Query ledger for FG-INV-001
    res_ledger = await async_client.get(
        f"/api/v1/inventory/ledger?item_id={data['fg_id']}",
    )
    assert res_ledger.status_code == 200
    entries = res_ledger.json()["items"]
    movement_types = [e["movement_type"] for e in entries]
    assert "TRANSFER_OUT" in movement_types
    assert "TRANSFER_IN" in movement_types


@pytest.mark.asyncio
async def test_stock_adjustment_and_low_stock_alerts(
    async_client: AsyncClient,
    setup_test_users,
    seed_inventory_test_data,
):
    """
    Test stock adjustments with mandatory reason and low stock alert generation.
    """
    data = seed_inventory_test_data

    # Login as Inventory Manager
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "inv_manager@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.json()["csrf_token"]
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # Inward 50 KGS of raw material (reorder level is 40 KGS)
    await async_client.post(
        "/api/v1/inventory/inward",
        json={
            "item_id": data["rm_id"],
            "item_type": "RAW_MATERIAL",
            "warehouse_id": data["wh1_id"],
            "unit_id": "Unit_1",
            "quantity": 50.0,
            "unit_cost": 150.0,
        },
        headers=headers,
    )

    # Initial check: stock is 50, reorder is 40 -> Should not be in alerts
    res_alerts_1 = await async_client.get("/api/v1/inventory/low-stock-alerts")
    assert res_alerts_1.status_code == 200
    alerts_1 = [a for a in res_alerts_1.json() if a["item_code"] == "RM-INV-001"]
    assert len(alerts_1) == 0

    # Adjust stock downward by -15 KGS (damaged goods) -> brings balance to 35 KGS (< 40)
    adj_payload = {
        "item_id": data["rm_id"],
        "warehouse_id": data["wh1_id"],
        "unit_id": "Unit_1",
        "quantity_delta": -15.0,
        "reason": "DAMAGED_GOODS",
        "notes": "Corroded during monsoon storage",
    }
    res_adj = await async_client.post(
        "/api/v1/inventory/adjust",
        json=adj_payload,
        headers=headers,
    )
    assert res_adj.status_code == 201, res_adj.text
    assert res_adj.json()["balance_after"] == 35.0

    # Check alerts: now stock is 35 KGS, below reorder level (40 KGS) -> Must trigger alert!
    res_alerts_2 = await async_client.get("/api/v1/inventory/low-stock-alerts")
    assert res_alerts_2.status_code == 200
    alerts_2 = [a for a in res_alerts_2.json() if a["item_code"] == "RM-INV-001"]
    assert len(alerts_2) == 1
    assert alerts_2[0]["shortage_quantity"] == 5.0  # 40 - 35
