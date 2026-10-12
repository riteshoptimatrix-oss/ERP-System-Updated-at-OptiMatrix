import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.models.user import RoleName, ManufacturingUnit
from app.core.security import hash_password
from datetime import datetime, timezone


@pytest.fixture
async def seed_production_test_data(setup_test_db):
    """Seed finished product, raw material, warehouse, approved BOM, and stock."""
    db = setup_test_db

    # 1. Finished Product
    fg_res = await db["finished_products"].insert_one({
        "code": "FG-PRD-CNC-100",
        "name": "Precision CNC Lathe Machine",
        "uom": "PCS",
        "standard_cost": 300000.0,
        "selling_price": 450000.0,
        "unit_id": "Unit_1",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })
    fg_id = str(fg_res.inserted_id)

    # 2. Raw Material
    rm_res = await db["raw_materials"].insert_one({
        "code": "RM-PRD-CASTING-BODY",
        "name": "Heavy Cast Iron Bed",
        "uom": "NOS",
        "standard_cost": 40000.0,
        "unit_id": "Unit_1",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })
    rm_id = str(rm_res.inserted_id)

    # 3. Warehouses
    wh_rm_res = await db["warehouses"].insert_one({
        "code": "WH-PRD-RM-STORE",
        "name": "Production RM Store",
        "unit_id": "Unit_1",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })
    wh_rm_id = str(wh_rm_res.inserted_id)

    wh_fg_res = await db["warehouses"].insert_one({
        "code": "WH-PRD-FG-STORE",
        "name": "Finished Goods Central Yard",
        "unit_id": "Unit_1",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })
    wh_fg_id = str(wh_fg_res.inserted_id)

    # 4. Approved BOM (1 Finished Machine requires 2 Cast Iron Beds with 0% scrap)
    bom_res = await db["boms"].insert_one({
        "bom_number": "BOM-2026-TEST-01",
        "product_id": fg_id,
        "product_code": "FG-PRD-CNC-100",
        "product_name": "Precision CNC Lathe Machine",
        "product_uom": "PCS",
        "unit_id": "Unit_1",
        "base_quantity": 1.0,
        "revision_no": "R1",
        "status": "APPROVED",
        "is_active": True,
        "total_estimated_cost": 80000.0,
        "components": [
            {
                "material_id": rm_id,
                "material_code": "RM-PRD-CASTING-BODY",
                "material_name": "Heavy Cast Iron Bed",
                "uom": "NOS",
                "net_quantity": 2.0,
                "scrap_percentage": 0.0,
                "gross_quantity": 2.0,
                "unit_cost": 40000.0,
                "estimated_cost": 80000.0,
            }
        ],
        "created_at": datetime.now(timezone.utc),
        "created_by": "system",
    })
    bom_id = str(bom_res.inserted_id)

    return {
        "fg_id": fg_id,
        "rm_id": rm_id,
        "wh_rm_id": wh_rm_id,
        "wh_fg_id": wh_fg_id,
        "bom_id": bom_id,
    }


@pytest.mark.asyncio
async def test_production_order_full_lifecycle_and_inventory_reconciliation(
    async_client: AsyncClient,
    setup_test_users,
    seed_production_test_data,
):
    """
    Test complete manufacturing lifecycle:
    1. Inward Raw Materials into stock.
    2. Create Production Order (DRAFT) for 5 CNC Lathes.
    3. Release Order (RELEASED) -> reserves 10 Cast Iron Beds in inventory.
    4. Issue Materials -> issues 10 Cast Iron Beds via PRODUCTION_CONSUMPTION.
    5. Record Output -> 5 good units produced -> receipt into Finished Goods inventory (PRODUCTION_RECEIPT).
    6. Verify order status transitions to COMPLETED and remaining quantity is 0.
    """
    data = seed_production_test_data

    # Login as Super Admin
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.json()["csrf_token"]
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 1. Inward 20 units of Cast Iron Bed into RM warehouse
    await async_client.post(
        "/api/v1/inventory/inward",
        json={
            "item_id": data["rm_id"],
            "item_type": "RAW_MATERIAL",
            "warehouse_id": data["wh_rm_id"],
            "unit_id": "Unit_1",
            "quantity": 20.0,
            "unit_cost": 40000.0,
        },
        headers=headers,
    )

    # 2. Create Production Order for 5 CNC Lathes (requires 10 beds)
    create_payload = {
        "product_id": data["fg_id"],
        "bom_id": data["bom_id"],
        "unit_id": "Unit_1",
        "target_warehouse_id": data["wh_fg_id"],
        "planned_quantity": 5.0,
        "notes": "Batch CNC production for Maharashtra client",
    }
    res_create = await async_client.post(
        "/api/v1/production/orders",
        json=create_payload,
        headers=headers,
    )
    assert res_create.status_code == 201, res_create.text
    order = res_create.json()
    order_id = order["id"]
    assert order["status"] == "DRAFT"
    assert order["planned_quantity"] == 5.0
    assert order["materials"][0]["total_standard_required"] == 10.0

    # 3. Release Order
    res_rel = await async_client.post(
        f"/api/v1/production/orders/{order_id}/release",
        headers=headers,
    )
    assert res_rel.status_code == 200, res_rel.text
    assert res_rel.json()["status"] == "RELEASED"

    # Check that 10 units were reserved in inventory
    bal_res = await async_client.get("/api/v1/inventory/balances?search=RM-PRD-CASTING-BODY")
    assert bal_res.status_code == 200
    rm_bal = bal_res.json()["items"][0]
    assert rm_bal["quantity_on_hand"] == 20.0
    assert rm_bal["quantity_reserved"] == 10.0
    assert rm_bal["quantity_available"] == 10.0

    # 4. Issue Materials (10 units to production line)
    issue_payload = {
        "items": [
            {
                "material_id": data["rm_id"],
                "warehouse_id": data["wh_rm_id"],
                "quantity": 10.0,
            }
        ]
    }
    res_iss = await async_client.post(
        f"/api/v1/production/orders/{order_id}/issue-materials",
        json=issue_payload,
        headers=headers,
    )
    assert res_iss.status_code == 200, res_iss.text
    order_in_prog = res_iss.json()
    assert order_in_prog["status"] == "IN_PROGRESS"
    assert order_in_prog["materials"][0]["total_issued"] == 10.0

    # Verify inventory was consumed and reservation cleared
    bal_after_iss = await async_client.get("/api/v1/inventory/balances?search=RM-PRD-CASTING-BODY")
    rm_bal_2 = bal_after_iss.json()["items"][0]
    assert rm_bal_2["quantity_on_hand"] == 10.0
    assert rm_bal_2["quantity_reserved"] == 0.0
    assert rm_bal_2["quantity_available"] == 10.0

    # 5. Record Output (5 good machines produced)
    output_payload = {
        "produced_quantity": 5.0,
        "rejected_quantity": 0.0,
        "warehouse_id": data["wh_fg_id"],
        "batch_no": "LOT-CNC-2026-001",
        "operator_name": "Ramesh Kumar",
        "notes": "All 5 machines cleared QA calibration",
    }
    res_out = await async_client.post(
        f"/api/v1/production/orders/{order_id}/record-output",
        json=output_payload,
        headers=headers,
    )
    assert res_out.status_code == 200, res_out.text
    order_done = res_out.json()
    assert order_done["status"] == "COMPLETED"
    assert order_done["produced_quantity"] == 5.0
    assert order_done["remaining_quantity"] == 0.0
    assert order_done["completion_percentage"] == 100.0

    # Verify Finished Good inventory has 5 machines
    fg_bal_res = await async_client.get("/api/v1/inventory/balances?search=FG-PRD-CNC-100")
    assert fg_bal_res.status_code == 200
    fg_bal = fg_bal_res.json()["items"][0]
    assert fg_bal["quantity_on_hand"] == 5.0
    assert fg_bal["quantity_available"] == 5.0


@pytest.mark.asyncio
async def test_production_variance_report(
    async_client: AsyncClient,
    setup_test_users,
    seed_production_test_data,
):
    """
    Test material consumption variance:
    When standard requires 10 units but shop-floor consumes 12 units (2 extra due to re-work),
    the variance report accurately reflects 2 units excess and cost variance.
    """
    data = seed_production_test_data

    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    headers = {settings.CSRF_HEADER_NAME: login_res.json()["csrf_token"]}

    # Inward 30 units of Cast Iron Bed
    await async_client.post(
        "/api/v1/inventory/inward",
        json={
            "item_id": data["rm_id"],
            "item_type": "RAW_MATERIAL",
            "warehouse_id": data["wh_rm_id"],
            "unit_id": "Unit_1",
            "quantity": 30.0,
            "unit_cost": 40000.0,
        },
        headers=headers,
    )

    # Create & release order for 5 machines (standard = 10 units)
    res_create = await async_client.post(
        "/api/v1/production/orders",
        json={
            "product_id": data["fg_id"],
            "bom_id": data["bom_id"],
            "unit_id": "Unit_1",
            "target_warehouse_id": data["wh_fg_id"],
            "planned_quantity": 5.0,
        },
        headers=headers,
    )
    order_id = res_create.json()["id"]

    await async_client.post(f"/api/v1/production/orders/{order_id}/release", headers=headers)

    # Issue 12 units (2 excess units)
    await async_client.post(
        f"/api/v1/production/orders/{order_id}/issue-materials",
        json={
            "items": [
                {
                    "material_id": data["rm_id"],
                    "warehouse_id": data["wh_rm_id"],
                    "quantity": 12.0,
                }
            ]
        },
        headers=headers,
    )

    # Query Variance Report
    var_res = await async_client.get(
        f"/api/v1/production/orders/{order_id}/variance",
        headers=headers,
    )
    assert var_res.status_code == 200, var_res.text
    var_data = var_res.json()
    assert var_data["planned_quantity"] == 5.0

    mat_var = var_data["material_variances"][0]
    assert mat_var["standard_required"] == 10.0
    assert mat_var["actual_issued"] == 12.0
    assert mat_var["variance_quantity"] == 2.0
    assert mat_var["is_favorable"] is False
    assert mat_var["cost_variance"] == 80000.0  # 2 * 40,000 INR
