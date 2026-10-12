import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.database.mongodb import mongodb_manager


@pytest.mark.asyncio
async def test_owner_single_login_and_read_dashboard(async_client: AsyncClient, setup_test_users):
    """
    Test that Owner (Ritesh Gajjar, admin / admin123) can sign in through single login
    and read executive dashboards across both manufacturing units.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin", "password": "admin123"}
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["authenticated"] is True
    assert login_data["user"]["role"] == "SUPER_ADMIN"
    assert login_data["user"]["full_name"] == "Ritesh Gajjar"
    assert "BOTH" in login_data["user"]["allowed_units"]

    owner_cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
    owner_csrf = login_data["csrf_token"]
    cookies = {
        settings.SESSION_COOKIE_NAME: owner_cookie,
        settings.CSRF_COOKIE_NAME: owner_csrf,
    }

    # 1. Dashboard summary read
    dash_res = await async_client.get("/api/v1/dashboard/summary", cookies=cookies)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "kpis" in dash_data
    assert "total_permitted_kpis" in dash_data
    assert dash_data["total_permitted_kpis"] > 0
    assert "orders" in dash_data["kpis"]
    assert "production" in dash_data["kpis"]

    # 2. Cross-facility inspection: read Unit 1 & Unit 2 orders
    orders_enflow1 = await async_client.get("/api/v1/orders?unit_id=Unit_1", cookies=cookies)
    assert orders_enflow1.status_code == 200

    orders_enflow2 = await async_client.get("/api/v1/orders?unit_id=Unit_2", cookies=cookies)
    assert orders_enflow2.status_code == 200

    # 3. Read Inventory, BOM, Production, Wastage, Reports, Users, Roles
    inv_res = await async_client.get("/api/v1/inventory/balances", cookies=cookies)
    assert inv_res.status_code == 200

    bom_res = await async_client.get("/api/v1/bom", cookies=cookies)
    assert bom_res.status_code == 200

    prod_res = await async_client.get("/api/v1/production/orders", cookies=cookies)
    assert prod_res.status_code == 200

    roles_res = await async_client.get("/api/v1/roles", cookies=cookies)
    assert roles_res.status_code == 200

    users_res = await async_client.get("/api/v1/users", cookies=cookies)
    assert users_res.status_code == 200


@pytest.mark.asyncio
async def test_owner_search_filter_paginate_allowed(async_client: AsyncClient, setup_test_users):
    """
    Test that Owner can search, filter, sort, and paginate authorized data.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin", "password": "admin123"}
    )
    cookies = {
        settings.SESSION_COOKIE_NAME: login_res.cookies.get(settings.SESSION_COOKIE_NAME),
        settings.CSRF_COOKIE_NAME: login_res.json()["csrf_token"],
    }

    # Paginated master data read
    res = await async_client.get(
        "/api/v1/master/customers?page=1&page_size=10&sort_by=name&sort_order=asc",
        cookies=cookies
    )
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_owner_prohibited_from_creating_or_updating_business_records(async_client: AsyncClient, setup_test_users):
    """
    Test that Owner CANNOT create or update business records:
    POST /orders, POST /inventory/adjust, POST /bom, POST /production/orders, etc.
    All must return HTTP 403 Forbidden with zero database mutation and security audit log entry.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin", "password": "admin123"}
    )
    owner_cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
    owner_csrf = login_res.json()["csrf_token"]
    cookies = {
        settings.SESSION_COOKIE_NAME: owner_cookie,
        settings.CSRF_COOKIE_NAME: owner_csrf,
    }
    headers = {
        settings.CSRF_HEADER_NAME: owner_csrf
    }

    db = mongodb_manager.get_database()
    initial_orders_count = await db["sales_orders"].count_documents({})
    initial_users_count = await db["users"].count_documents({})

    # 1. Prohibited: Create Sales Order
    order_payload = {
        "customer_id": "cust123",
        "order_date": "2026-10-12",
        "delivery_due_date": "2026-10-25",
        "unit_id": "Unit_1",
        "items": [
            {
                "product_id": "prod1",
                "product_code": "PROD-1",
                "product_name": "Hydraulic Pump",
                "quantity": 5,
                "unit_price": 1000.0
            }
        ]
    }
    order_res = await async_client.post("/api/v1/orders", json=order_payload, cookies=cookies, headers=headers)
    assert order_res.status_code == 403
    assert "read-only monitoring access" in order_res.json()["error"]["message"]

    # Verify database was NOT touched
    current_orders_count = await db["sales_orders"].count_documents({})
    assert current_orders_count == initial_orders_count

    # 2. Prohibited: Create User
    user_payload = {
        "email": "hackeduser@rgtech.com",
        "full_name": "Intruder User",
        "password": "Password123!",
        "role": "EMPLOYEE",
        "allowed_units": ["Unit_1"]
    }
    user_res = await async_client.post("/api/v1/users", json=user_payload, cookies=cookies, headers=headers)
    assert user_res.status_code == 403

    current_users_count = await db["users"].count_documents({})
    assert current_users_count == initial_users_count

    # 3. Prohibited: Create Master Customer
    cust_payload = {
        "code": "CUST-OWNER-TEST",
        "name": "Owner Prohibited Customer",
        "gstin": "24ABCDE1234F1Z5",
        "pan": "ABCDE1234F",
        "billing_address": "Test Street",
        "shipping_address": "Test Street",
        "credit_limit": 100000.0,
        "payment_terms_days": 30,
        "unit_id": "Unit_1"
    }
    cust_res = await async_client.post("/api/v1/master/customers", json=cust_payload, cookies=cookies, headers=headers)
    assert cust_res.status_code == 403

    # 4. Prohibited: Inventory Adjustment
    adjust_payload = {
        "item_id": "item123",
        "warehouse_id": "wh123",
        "batch_no": "BATCH-1",
        "physical_count": 10.0,
        "reason_code": "PHYSICAL_COUNT_AUDIT",
        "notes": "Unauthorized Owner count"
    }
    adj_res = await async_client.post("/api/v1/inventory/adjust", json=adjust_payload, cookies=cookies, headers=headers)
    assert adj_res.status_code == 403

    # 5. Prohibited: Create Production Order
    prod_payload = {
        "product_id": "prod123",
        "bom_id": "bom123",
        "planned_quantity": 50.0,
        "unit_id": "Unit_1",
        "target_start_date": "2026-10-12",
        "target_completion_date": "2026-10-20"
    }
    prod_res = await async_client.post("/api/v1/production/orders", json=prod_payload, cookies=cookies, headers=headers)
    assert prod_res.status_code == 403

    # Verify audit log recorded security denials
    denials = await db["audit_logs"].find({"action": "SECURITY_OWNER_MUTATION_DENIED"}).to_list(10)
    assert len(denials) >= 3


@pytest.mark.asyncio
async def test_owner_cannot_execute_workflows_or_change_roles(async_client: AsyncClient, setup_test_users):
    """
    Test that Owner cannot approve, reject, submit, confirm, or cancel workflows,
    nor update roles or permissions.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin", "password": "admin123"}
    )
    owner_cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
    owner_csrf = login_res.json()["csrf_token"]
    cookies = {
        settings.SESSION_COOKIE_NAME: owner_cookie,
        settings.CSRF_COOKIE_NAME: owner_csrf,
    }
    headers = {
        settings.CSRF_HEADER_NAME: owner_csrf
    }

    # Workflow transition: Submit order
    submit_res = await async_client.post("/api/v1/orders/fakeid123/submit", cookies=cookies, headers=headers)
    assert submit_res.status_code == 403

    # Workflow transition: Confirm order
    confirm_res = await async_client.post("/api/v1/orders/fakeid123/confirm", cookies=cookies, headers=headers)
    assert confirm_res.status_code == 403

    # Workflow transition: Cancel order
    cancel_res = await async_client.post(
        "/api/v1/orders/fakeid123/cancel",
        json={"reason": "Owner test cancel"},
        cookies=cookies,
        headers=headers
    )
    assert cancel_res.status_code == 403

    # Attempt to change another user's role via PATCH /api/v1/users/{id}
    target_user_id = setup_test_users["pm1_id"]
    patch_res = await async_client.patch(
        f"/api/v1/users/{target_user_id}",
        json={"role": "ADMIN"},
        cookies=cookies,
        headers=headers
    )
    assert patch_res.status_code == 403

    # Verify the target user was NOT modified
    db = mongodb_manager.get_database()
    from bson import ObjectId
    user_doc = await db["users"].find_one({"_id": ObjectId(target_user_id)})
    assert user_doc["role"] == "PRODUCTION_MANAGER"


@pytest.mark.asyncio
async def test_admin_operational_actions_remain_functional(async_client: AsyncClient, setup_test_users):
    """
    Test separation of duties: operational Admin (admin_ops) CAN perform administrative operations,
    while Owner cannot.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"}
    )
    assert login_res.status_code == 200
    admin_cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
    admin_csrf = login_res.json()["csrf_token"]
    cookies = {
        settings.SESSION_COOKIE_NAME: admin_cookie,
        settings.CSRF_COOKIE_NAME: admin_csrf,
    }
    headers = {
        settings.CSRF_HEADER_NAME: admin_csrf
    }

    # Admin CAN create a customer
    cust_payload = {
        "code": "CUST-ADMIN-OK",
        "name": "Admin Authorized Customer",
        "gstin": "24ABCDE1234F1Z5",
        "pan": "ABCDE1234F",
        "billing_address": "Admin Street",
        "shipping_address": "Admin Street",
        "credit_limit": 500000.0,
        "payment_terms_days": 30,
        "unit_id": "Unit_1"
    }
    cust_res = await async_client.post("/api/v1/master/customers", json=cust_payload, cookies=cookies, headers=headers)
    assert cust_res.status_code == 201
    assert cust_res.json()["code"] == "CUST-ADMIN-OK"
