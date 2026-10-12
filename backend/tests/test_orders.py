import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from app.core.config import settings
from app.models.user import RoleName, ManufacturingUnit
from app.core.security import hash_password


@pytest.fixture
async def seed_orders_master_data(setup_test_db):
    """Seed test customer and finished products for orders testing."""
    db = setup_test_db

    # Additional Sales Dispatch user
    await db["users"].insert_one({
        "email": "dispatch_user@testcorp.com",
        "full_name": "Dispatch Specialist",
        "hashed_password": hash_password("ValidPassword123!"),
        "role": RoleName.SALES_DISPATCH.value,
        "allowed_units": [ManufacturingUnit.Unit_1.value],
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    # Customer
    cust_res = await db["customers"].insert_one({
        "code": "CUST-TEST-001",
        "name": "Precision Heavy Industries Ltd",
        "gstin": "27ABCDE1234F1Z5",
        "pan": "ABCDE1234F",
        "contact_person": "Vikram Malhotra",
        "phone": "+919876543210",
        "email": "vikram@precision.com",
        "billing_address": "Plot 10, MIDC Bhosari, Pune",
        "shipping_address": "Plant 2, MIDC Chakan, Pune",
        "credit_limit": 5000000.0,
        "payment_terms_days": 30,
        "unit_id": "BOTH",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "created_by": "system",
    })

    # Finished Products
    p1_res = await db["finished_products"].insert_one({
        "code": "FP-ENV-500",
        "name": "Heavy Duty CNC Milling 5-Axis",
        "description": "5-Axis High Precision Machine",
        "category_id": "MACHINES",
        "uom": "SET",
        "drawing_no": "DWG-500-R2",
        "revision_no": "R2",
        "standard_cost": 2500000.0,
        "selling_price": 3500000.0,
        "min_stock_level": 2.0,
        "unit_id": "Unit_1",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "created_by": "system",
    })

    p2_res = await db["finished_products"].insert_one({
        "code": "FP-ENV-200",
        "name": "Rotary Chuck Assembly",
        "description": "Hydraulic clamping rotary chuck",
        "category_id": "SUB_ASSEMBLY",
        "uom": "NOS",
        "drawing_no": "DWG-200-R1",
        "revision_no": "R1",
        "standard_cost": 150000.0,
        "selling_price": 220000.0,
        "min_stock_level": 5.0,
        "unit_id": "Unit_1",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "created_by": "system",
    })

    return {
        "customer_id": str(cust_res.inserted_id),
        "p1_id": str(p1_res.inserted_id),
        "p2_id": str(p2_res.inserted_id),
    }


@pytest.mark.asyncio
async def test_sales_order_full_lifecycle(
    async_client: AsyncClient,
    setup_test_users,
    seed_orders_master_data,
):
    """
    Test complete sales order journey:
    1. Check inventory availability via explicit contract (read-only, non-invented).
    2. Create Sales Order in DRAFT state.
    3. Submit and confirm order.
    4. Generate Packing Slip.
    5. Partial dispatch record 1 -> status transitions to PARTIALLY_DISPATCHED.
    6. Partial dispatch record 2 -> status transitions to DISPATCHED.
    7. Verify order activity history and reconciliation.
    """
    # 1. Login as Super Admin
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.json()["csrf_token"]
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    data = seed_orders_master_data
    c_id = data["customer_id"]
    p1_id = data["p1_id"]
    p2_id = data["p2_id"]

    # 2. Check stock availability (Contract check)
    stock_res = await async_client.get(
        f"/api/v1/orders/check-stock/{p1_id}?unit_id=Unit_1&required_qty=2.0",
        headers=headers,
    )
    assert stock_res.status_code == 200
    stock_body = stock_res.json()
    assert stock_body["product_code"] == "FP-ENV-500"
    assert stock_body["status"] == "UNTRACKED"
    assert stock_body["is_sufficient"] is True

    # 3. Create Sales Order
    order_payload = {
        "customer_id": c_id,
        "customer_po_number": "PO-PRECISION-9874",
        "unit_id": "Unit_1",
        "order_date": "2026-10-10T00:00:00Z",
        "delivery_due_date": "2026-11-15",
        "items": [
            {
                "product_id": p1_id,
                "product_code": "FP-ENV-500",
                "product_name": "Heavy Duty CNC Milling 5-Axis",
                "uom": "SET",
                "quantity": 2.0,
                "unit_price": 3500000.0,
                "discount_percent": 5.0,
                "tax_percent": 18.0,
            },
            {
                "product_id": p2_id,
                "product_code": "FP-ENV-200",
                "product_name": "Rotary Chuck Assembly",
                "uom": "NOS",
                "quantity": 4.0,
                "unit_price": 220000.0,
                "discount_percent": 0.0,
                "tax_percent": 18.0,
            },
        ],
        "notes": "Urgent dispatch required for Plant 2.",
    }

    create_res = await async_client.post("/api/v1/orders", json=order_payload, headers=headers)
    assert create_res.status_code == 201
    order = create_res.json()
    order_id = order["id"]
    assert order["status"] == "DRAFT"
    assert order["order_number"].startswith("SO-")
    assert order["total_ordered_qty"] == 6.0
    assert order["total_dispatched_qty"] == 0.0

    # 4. Submit Order
    sub_res = await async_client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] == "SUBMITTED"

    # 5. Confirm Order
    conf_res = await async_client.post(f"/api/v1/orders/{order_id}/confirm", headers=headers)
    assert conf_res.status_code == 200
    assert conf_res.json()["status"] == "CONFIRMED"

    # 6. Generate Packing Slip
    slip_payload = {
        "items": [
            {
                "product_id": p1_id,
                "product_code": "FP-ENV-500",
                "product_name": "Heavy Duty CNC Milling 5-Axis",
                "ordered_quantity": 2.0,
                "pack_quantity": 1.0,
                "package_type": "WOODEN_CRATE",
            },
            {
                "product_id": p2_id,
                "product_code": "FP-ENV-200",
                "product_name": "Rotary Chuck Assembly",
                "ordered_quantity": 4.0,
                "pack_quantity": 2.0,
                "package_type": "CARTON",
            },
        ],
        "packages_count": 2,
        "gross_weight_kg": 3500.0,
        "net_weight_kg": 3200.0,
        "special_handling_notes": "Handle with crane.",
    }
    ps_res = await async_client.post(f"/api/v1/orders/{order_id}/packing-slips", json=slip_payload, headers=headers)
    assert ps_res.status_code == 201
    ps = ps_res.json()
    assert ps["slip_number"].startswith("PS-")
    assert ps["packages_count"] == 2
    ps_id = ps["id"]

    # 7. Post Partial Dispatch 1 (1 of P1, 2 of P2)
    dsp1_payload = {
        "packing_slip_id": ps_id,
        "carrier_name": "VRL Logistics Heavy Haul",
        "vehicle_number": "MH-12-QW-4589",
        "lr_number": "LR-VRL-897451",
        "driver_name": "Suresh Yadav",
        "driver_phone": "+919822001122",
        "items": [
            {
                "product_id": p1_id,
                "product_code": "FP-ENV-500",
                "product_name": "Heavy Duty CNC Milling 5-Axis",
                "quantity": 1.0,
            },
            {
                "product_id": p2_id,
                "product_code": "FP-ENV-200",
                "product_name": "Rotary Chuck Assembly",
                "quantity": 2.0,
            },
        ],
        "remarks": "Part 1 dispatched as requested.",
    }
    dsp1_res = await async_client.post(f"/api/v1/orders/{order_id}/dispatch", json=dsp1_payload, headers=headers)
    assert dsp1_res.status_code == 201
    dsp1 = dsp1_res.json()
    assert dsp1["dispatch_number"].startswith("DSP-")
    assert dsp1["total_quantity"] == 3.0

    # Verify Order is PARTIALLY_DISPATCHED
    chk1 = await async_client.get(f"/api/v1/orders/{order_id}", headers=headers)
    assert chk1.status_code == 200
    chk1_body = chk1.json()
    assert chk1_body["status"] == "PARTIALLY_DISPATCHED"
    assert chk1_body["total_dispatched_qty"] == 3.0
    assert chk1_body["dispatch_percent"] == 50.0

    # 8. Post Final Dispatch (Remaining 1 of P1, 2 of P2)
    dsp2_payload = {
        "carrier_name": "GATI KWE Cargo",
        "vehicle_number": "MH-14-GH-1234",
        "lr_number": "LR-GATI-456789",
        "items": [
            {
                "product_id": p1_id,
                "product_code": "FP-ENV-500",
                "product_name": "Heavy Duty CNC Milling 5-Axis",
                "quantity": 1.0,
            },
            {
                "product_id": p2_id,
                "product_code": "FP-ENV-200",
                "product_name": "Rotary Chuck Assembly",
                "quantity": 2.0,
            },
        ],
        "remarks": "Final balance batch dispatched.",
    }
    dsp2_res = await async_client.post(f"/api/v1/orders/{order_id}/dispatch", json=dsp2_payload, headers=headers)
    assert dsp2_res.status_code == 201

    # Verify Order is fully DISPATCHED
    chk2 = await async_client.get(f"/api/v1/orders/{order_id}", headers=headers)
    assert chk2.status_code == 200
    chk2_body = chk2.json()
    assert chk2_body["status"] == "DISPATCHED"
    assert chk2_body["total_dispatched_qty"] == 6.0
    assert chk2_body["dispatch_percent"] == 100.0
    assert len(chk2_body["activities"]) >= 4


@pytest.mark.asyncio
async def test_over_dispatch_and_cancellation_guards(
    async_client: AsyncClient,
    setup_test_users,
    seed_orders_master_data,
):
    """
    Test validation guards:
    1. Over-dispatch rejection.
    2. Cancellation prevention on partially dispatched orders.
    3. Packing slip rejected on DRAFT orders.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.json()["csrf_token"]
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    data = seed_orders_master_data
    c_id = data["customer_id"]
    p1_id = data["p1_id"]

    # Create Order with 1 unit
    create_res = await async_client.post(
        "/api/v1/orders",
        json={
            "customer_id": c_id,
            "unit_id": "Unit_1",
            "items": [
                {
                    "product_id": p1_id,
                    "product_code": "FP-ENV-500",
                    "product_name": "Heavy Duty CNC Milling 5-Axis",
                    "quantity": 1.0,
                    "unit_price": 100000.0,
                }
            ],
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    order_id = create_res.json()["id"]

    # 1. Attempt packing slip in DRAFT state -> Expect 400
    inv_ps = await async_client.post(
        f"/api/v1/orders/{order_id}/packing-slips",
        json={
            "items": [
                {
                    "product_id": p1_id,
                    "product_code": "FP-ENV-500",
                    "product_name": "Heavy Duty CNC Milling 5-Axis",
                    "ordered_quantity": 1.0,
                    "pack_quantity": 1.0,
                }
            ]
        },
        headers=headers,
    )
    assert inv_ps.status_code == 400

    # Advance to CONFIRMED
    await async_client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)
    await async_client.post(f"/api/v1/orders/{order_id}/confirm", headers=headers)

    # 2. Attempt Over-Dispatch (dispatching 5 units when 1 is ordered) -> Expect 400
    over_res = await async_client.post(
        f"/api/v1/orders/{order_id}/dispatch",
        json={
            "carrier_name": "Express Logistics",
            "vehicle_number": "MH-12-AB-9999",
            "items": [
                {
                    "product_id": p1_id,
                    "product_code": "FP-ENV-500",
                    "product_name": "Heavy Duty CNC Milling 5-Axis",
                    "quantity": 5.0,
                }
            ],
        },
        headers=headers,
    )
    assert over_res.status_code == 400
    over_err = over_res.json().get("error", {}).get("message") or over_res.json().get("detail", "")
    assert "Over-dispatch prevented" in over_err

    # 3. Successful partial dispatch of 0.5 units
    part_res = await async_client.post(
        f"/api/v1/orders/{order_id}/dispatch",
        json={
            "carrier_name": "Express Logistics",
            "vehicle_number": "MH-12-AB-9999",
            "items": [
                {
                    "product_id": p1_id,
                    "product_code": "FP-ENV-500",
                    "product_name": "Heavy Duty CNC Milling 5-Axis",
                    "quantity": 0.5,
                }
            ],
        },
        headers=headers,
    )
    assert part_res.status_code == 201

    # 4. Attempt Cancellation while PARTIALLY_DISPATCHED -> Expect 400
    cancel_res = await async_client.post(
        f"/api/v1/orders/{order_id}/cancel",
        json={"reason": "Customer cancelled order"},
        headers=headers,
    )
    assert cancel_res.status_code == 400
    cancel_err = cancel_res.json().get("error", {}).get("message") or cancel_res.json().get("detail", "")
    assert "Cannot cancel an order that has already been partially dispatched" in cancel_err
