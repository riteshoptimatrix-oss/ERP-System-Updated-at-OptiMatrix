import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.models.user import RoleName, ManufacturingUnit
from app.core.security import hash_password
from datetime import datetime, timezone


@pytest.fixture
async def seed_bom_test_data(setup_test_db):
    """Seed test finished products, raw materials, and production manager."""
    db = setup_test_db

    # Seed Production Manager user
    await db["users"].insert_one({
        "email": "prod_mgr@testcorp.com",
        "full_name": "Production Manager",
        "hashed_password": hash_password("ValidPassword123!"),
        "role": RoleName.PRODUCTION_MANAGER.value,
        "allowed_units": [ManufacturingUnit.BOTH.value],
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    # Seed Finished Good
    fg_res = await db["finished_products"].insert_one({
        "code": "FG-BOM-MCH-01",
        "name": "Heavy Duty Milling Machine M1",
        "uom": "PCS",
        "standard_cost": 500000.0,
        "selling_price": 750000.0,
        "unit_id": "Unit_1",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    # Seed Raw Materials
    rm1_res = await db["raw_materials"].insert_one({
        "code": "RM-BOM-STEEL-PLATE",
        "name": "Structural Steel Plate 20mm",
        "uom": "KGS",
        "standard_cost": 100.0,
        "unit_id": "Unit_1",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    rm2_res = await db["raw_materials"].insert_one({
        "code": "RM-BOM-BALL-BEARING",
        "name": "Precision Ball Bearing 6205",
        "uom": "NOS",
        "standard_cost": 250.0,
        "unit_id": "Unit_1",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    return {
        "fg_id": str(fg_res.inserted_id),
        "rm1_id": str(rm1_res.inserted_id),
        "rm2_id": str(rm2_res.inserted_id),
    }


@pytest.mark.asyncio
async def test_bom_creation_scrap_and_cost_rollup(
    async_client: AsyncClient,
    setup_test_users,
    seed_bom_test_data,
):
    """
    Test BOM creation, gross quantity scrap calculation, and cost rollup policy.
    Formula: Gross = Net * (1 + Scrap% / 100)
    Cost = Gross * UnitCost
    """
    data = seed_bom_test_data

    # Login as Production Manager
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "prod_mgr@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.json()["csrf_token"]
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # Create Draft BOM with:
    # Component 1: 50 KGS with 10% scrap -> Gross 55 KGS @ 100 INR = 5500 INR
    # Component 2: 4 NOS with 0% scrap -> Gross 4 NOS @ 250 INR = 1000 INR
    # Expected Total Estimated Cost = 6500 INR
    create_payload = {
        "product_id": data["fg_id"],
        "unit_id": "Unit_1",
        "base_quantity": 1.0,
        "revision_no": "R1",
        "description": "Standard production recipe R1",
        "components": [
            {
                "material_id": data["rm1_id"],
                "net_quantity": 50.0,
                "uom": "KGS",
                "scrap_percentage": 10.0,
            },
            {
                "material_id": data["rm2_id"],
                "net_quantity": 4.0,
                "uom": "NOS",
                "scrap_percentage": 0.0,
            },
        ],
    }

    res = await async_client.post("/api/v1/bom", json=create_payload, headers=headers)
    assert res.status_code == 201, res.text
    bom = res.json()
    assert bom["status"] == "DRAFT"
    assert bom["revision_no"] == "R1"
    assert bom["total_estimated_cost"] == 6500.0

    c1 = next(c for c in bom["components"] if c["material_id"] == data["rm1_id"])
    assert c1["gross_quantity"] == 55.0
    assert c1["estimated_cost"] == 5500.0

    c2 = next(c for c in bom["components"] if c["material_id"] == data["rm2_id"])
    assert c2["gross_quantity"] == 4.0
    assert c2["estimated_cost"] == 1000.0


@pytest.mark.asyncio
async def test_circular_dependency_and_uom_validation(
    async_client: AsyncClient,
    setup_test_users,
    seed_bom_test_data,
):
    """
    Test guardrails:
    1. Circular dependency rejection (product cannot be component of itself).
    2. UoM mismatch rejection (master says KGS, component passes NOS).
    """
    data = seed_bom_test_data

    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "prod_mgr@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.json()["csrf_token"]
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 1. Circular dependency test
    circular_payload = {
        "product_id": data["fg_id"],
        "unit_id": "Unit_1",
        "base_quantity": 1.0,
        "revision_no": "R_CIRC",
        "components": [
            {
                "material_id": data["fg_id"],  # Self-reference!
                "net_quantity": 1.0,
                "uom": "PCS",
                "scrap_percentage": 0.0,
            }
        ],
    }
    res_circ = await async_client.post("/api/v1/bom", json=circular_payload, headers=headers)
    assert res_circ.status_code == 400
    err_circ = res_circ.json().get("error", {}).get("message", "") or res_circ.json().get("detail", "")
    assert "Circular dependency" in err_circ or "not exist in master data" in err_circ

    # 2. UoM mismatch test (RM1 master has UoM KGS, but we submit NOS)
    uom_mismatch_payload = {
        "product_id": data["fg_id"],
        "unit_id": "Unit_1",
        "base_quantity": 1.0,
        "revision_no": "R_UOM",
        "components": [
            {
                "material_id": data["rm1_id"],
                "net_quantity": 10.0,
                "uom": "NOS",  # Master is KGS
                "scrap_percentage": 0.0,
            }
        ],
    }
    res_uom = await async_client.post("/api/v1/bom", json=uom_mismatch_payload, headers=headers)
    assert res_uom.status_code == 400
    err_uom = res_uom.json().get("error", {}).get("message", "") or res_uom.json().get("detail", "")
    assert "Incompatible Unit of Measure" in err_uom


@pytest.mark.asyncio
async def test_bom_approval_lock_and_revision_creation(
    async_client: AsyncClient,
    setup_test_users,
    seed_bom_test_data,
):
    """
    Test approval lock (approved BOM becomes immutable) and new revision cloning.
    """
    data = seed_bom_test_data

    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "prod_mgr@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.json()["csrf_token"]
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 1. Create Draft BOM
    create_payload = {
        "product_id": data["fg_id"],
        "unit_id": "Unit_1",
        "base_quantity": 1.0,
        "revision_no": "R1",
        "components": [
            {
                "material_id": data["rm1_id"],
                "net_quantity": 20.0,
                "uom": "KGS",
                "scrap_percentage": 5.0,
            }
        ],
    }
    res_create = await async_client.post("/api/v1/bom", json=create_payload, headers=headers)
    assert res_create.status_code == 201
    bom_id = res_create.json()["id"]

    # 2. Submit for approval
    res_sub = await async_client.post(f"/api/v1/bom/{bom_id}/submit", headers=headers)
    assert res_sub.status_code == 200
    assert res_sub.json()["status"] == "PENDING_APPROVAL"

    # 3. Approve BOM (Login as Super Admin for approval permission)
    admin_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    admin_headers = {settings.CSRF_HEADER_NAME: admin_login.json()["csrf_token"]}

    res_app = await async_client.post(
        f"/api/v1/bom/{bom_id}/approve",
        json={"approved": True, "set_as_active": True, "remarks": "Approved by Chief Engineer"},
        headers=admin_headers,
    )
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "APPROVED"
    assert res_app.json()["is_active"] is True

    # 4. Attempt to modify approved BOM -> Must reject with 400
    res_edit = await async_client.put(
        f"/api/v1/bom/{bom_id}",
        json={"base_quantity": 2.0},
        headers=admin_headers,
    )
    assert res_edit.status_code == 400
    err_edit = res_edit.json().get("error", {}).get("message", "") or res_edit.json().get("detail", "")
    assert "Revision Lock" in err_edit

    # 5. Create new revision R2
    res_rev = await async_client.post(
        f"/api/v1/bom/{bom_id}/revisions",
        json={
            "new_revision_no": "R2",
            "description": "Upgraded alloy specification for 2026",
            "components": [
                {
                    "material_id": data["rm1_id"],
                    "net_quantity": 25.0,
                    "uom": "KGS",
                    "scrap_percentage": 2.0,
                }
            ],
        },
        headers=admin_headers,
    )
    assert res_rev.status_code == 201
    rev2 = res_rev.json()
    assert rev2["revision_no"] == "R2"
    assert rev2["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_material_requirements_calculation_with_inventory_shortage(
    async_client: AsyncClient,
    setup_test_users,
    seed_bom_test_data,
):
    """
    Test material requirements explosion against live inventory balances.
    Verifies shortage calculation without deducting stock balances.
    """
    data = seed_bom_test_data

    # Login as Super Admin
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    headers = {settings.CSRF_HEADER_NAME: login_res.json()["csrf_token"]}

    # Create and approve BOM
    create_payload = {
        "product_id": data["fg_id"],
        "unit_id": "Unit_1",
        "base_quantity": 1.0,
        "revision_no": "R1_EXPLODE",
        "components": [
            {
                "material_id": data["rm1_id"],
                "net_quantity": 10.0,
                "uom": "KGS",
                "scrap_percentage": 10.0,  # Gross = 11 KGS per unit
            }
        ],
    }
    bom_res = await async_client.post("/api/v1/bom", json=create_payload, headers=headers)
    bom_id = bom_res.json()["id"]

    await async_client.post(
        f"/api/v1/bom/{bom_id}/approve",
        json={"approved": True, "set_as_active": True},
        headers=headers,
    )

    # Inward only 50 KGS of RM1 into inventory
    # First seed warehouse if needed
    from app.database.mongodb import mongodb_manager
    test_db = mongodb_manager.get_database()
    wh_res = await test_db["warehouses"].insert_one({
        "code": "WH-BOM-STORE",
        "name": "BOM Test Store",
        "unit_id": "Unit_1",
        "is_active": True,
    })
    wh_id = str(wh_res.inserted_id)

    # Inward 50 KGS into inventory
    await async_client.post(
        "/api/v1/inventory/inward",
        json={
            "item_id": data["rm1_id"],
            "item_type": "RAW_MATERIAL",
            "warehouse_id": wh_id,
            "unit_id": "Unit_1",
            "quantity": 50.0,
            "unit_cost": 100.0,
        },
        headers=headers,
    )

    # Calculate requirements for 10 finished machines:
    # Required Gross = 10 * 11 KGS = 110 KGS
    # Available = 50 KGS -> Shortage = 60 KGS!
    calc_res = await async_client.post(
        f"/api/v1/bom/{bom_id}/calculate-requirements",
        json={"production_quantity": 10.0},
        headers=headers,
    )
    assert calc_res.status_code == 200, calc_res.text
    result = calc_res.json()
    assert result["production_quantity"] == 10.0
    assert result["has_sufficient_stock"] is False
    assert result["total_shortages_count"] == 1

    item_req = result["requirements"][0]
    assert item_req["gross_required_quantity"] == 110.0
    assert item_req["quantity_available"] == 50.0
    assert item_req["shortage_quantity"] == 60.0
    assert item_req["is_shortage"] is True

    # Verify inventory was NOT deducted (available must still be 50 KGS)
    bal_res = await async_client.get(f"/api/v1/inventory/balances?search=RM-BOM-STEEL-PLATE")
    assert bal_res.status_code == 200
    assert bal_res.json()["items"][0]["quantity_available"] == 50.0
