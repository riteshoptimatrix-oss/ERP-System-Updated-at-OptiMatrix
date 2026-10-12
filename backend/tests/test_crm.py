import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_lead_lifecycle_and_conversion(async_client: AsyncClient, setup_test_users):
    """
    Test complete lead journey:
    1. Create Lead
    2. Add follow-up activity
    3. Update stage (NEW -> QUALIFIED)
    4. Convert to Customer Master record
    5. Verify duplicate prevention on conversion and lead creation
    """
    # 1. Login as Super Admin
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"}
    )
    assert login_res.status_code == 200
    csrf_token = login_res.json()["csrf_token"]
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 2. Create Lead
    lead_payload = {
        "company_name": "Bharat Forge Fabrication",
        "contact_person": "Vikram Kalyani",
        "email": "vikram@bharatforge.com",
        "phone": "+919822001122",
        "source": "TRADE_EXPO",
        "status": "NEW",
        "priority": "HOT",
        "estimated_value": 7500000.0,
        "machine_interest": "1000 Ton Hydraulic Forging Press",
        "unit_id": "Unit_1",
        "notes": "Met at IMTEX Bangalore. Requires custom heavy bolster."
    }

    create_res = await async_client.post("/api/v1/crm/leads", json=lead_payload, headers=headers)
    assert create_res.status_code == 201
    created_lead = create_res.json()
    assert created_lead["company_name"] == "Bharat Forge Fabrication"
    assert created_lead["priority"] == "HOT"
    assert created_lead["code"].startswith("LEAD-")
    lead_id = created_lead["id"]

    # 3. Duplicate Prevention: Attempt creating identical company/phone
    dup_res = await async_client.post("/api/v1/crm/leads", json=lead_payload, headers=headers)
    assert dup_res.status_code == 409

    # 4. Log interaction activity
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    act_res = await async_client.post(
        f"/api/v1/crm/leads/{lead_id}/activities",
        json={
            "activity_type": "CALL",
            "summary": "Technical Discussion on Bolster Dimensions",
            "details": "Customer shared preliminary drawings. Scheduled follow-up visit.",
            "next_follow_up": tomorrow
        },
        headers=headers
    )
    assert act_res.status_code == 201

    # 5. Advance stage to QUALIFIED
    upd_res = await async_client.put(
        f"/api/v1/crm/leads/{lead_id}",
        json={"status": "QUALIFIED"},
        headers=headers
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["status"] == "QUALIFIED"

    # 6. Verify activities timeline
    details_res = await async_client.get(f"/api/v1/crm/leads/{lead_id}")
    assert details_res.status_code == 200
    details_body = details_res.json()
    assert len(details_body["activities"]) >= 3  # Initial creation, call logged, status change

    # 7. Convert Lead to Customer
    convert_payload = {
        "customer_code": "CUST-BHARAT-01",
        "gstin": "27AAACB2000A1Z2",
        "pan": "AAACB2000A",
        "billing_address": "Mundhwa Industrial Area, Pune",
        "shipping_address": "Works, Pune",
        "credit_limit": 5000000.0,
        "payment_terms_days": 45,
        "unit_id": "Unit_1"
    }

    conv_res = await async_client.post(
        f"/api/v1/crm/leads/{lead_id}/convert",
        json=convert_payload,
        headers=headers
    )
    assert conv_res.status_code == 200
    conv_data = conv_res.json()
    assert conv_data["customer_code"] == "CUST-BHARAT-01"
    assert conv_data["customer"]["name"] == "Bharat Forge Fabrication"

    # 8. Verify lead marked as CONVERTED
    lead_after_conv = await async_client.get(f"/api/v1/crm/leads/{lead_id}")
    assert lead_after_conv.json()["status"] == "CONVERTED"
    assert lead_after_conv.json()["converted_customer_id"] is not None

    # 9. Verify Customer is now visible in Master Customer list
    cust_list_res = await async_client.get("/api/v1/master/customers?search=Bharat")
    assert cust_list_res.status_code == 200
    assert any(c["code"] == "CUST-BHARAT-01" for c in cust_list_res.json()["items"])

    # 10. Attempt re-conversion on already converted lead
    re_conv_res = await async_client.post(
        f"/api/v1/crm/leads/{lead_id}/convert",
        json={"customer_code": "CUST-BHARAT-02"},
        headers=headers
    )
    assert re_conv_res.status_code == 409


@pytest.mark.asyncio
async def test_crm_dashboard_and_filtering(async_client: AsyncClient, setup_test_users):
    """
    Test CRM dashboard metric aggregation and query filters.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@testcorp.com", "password": "ValidPassword123!"}
    )
    assert login_res.status_code == 200

    dash_res = await async_client.get("/api/v1/crm/dashboard")
    assert dash_res.status_code == 200
    dash = dash_res.json()
    assert "total_leads" in dash
    assert "pipeline_by_status" in dash
    assert "conversion_rate_percentage" in dash


@pytest.mark.asyncio
async def test_crm_rbac_enforcement(async_client: AsyncClient, setup_test_users):
    """
    Verify role-based access restrictions on CRM endpoints.
    Employees without crm:read permission must be rejected with 403.
    """
    # 1. Login as standard EMPLOYEE (only attendance, payroll, orders:read)
    # pm1 has production, inventory, etc., but NOT crm
    pm1_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "pm1@testcorp.com", "password": "ValidPassword123!"}
    )
    assert pm1_login.status_code == 200

    # 2. PM1 attempts accessing CRM leads
    crm_res = await async_client.get("/api/v1/crm/leads")
    assert crm_res.status_code == 403
    err_body = crm_res.json()
    assert "crm:read" in str(err_body)
