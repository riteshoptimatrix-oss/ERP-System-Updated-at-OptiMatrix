import pytest
from datetime import datetime, timezone
from httpx import ASGITransport, AsyncClient
from app.main import create_application
from app.core.security import hash_password, verify_password
from app.models.user import RoleName, ManufacturingUnit, DEPARTMENT_JOB_ROLES, JOB_ROLE_DEFAULT_PERMISSIONS

app = create_application()


@pytest.mark.asyncio
async def test_department_catalog_and_seed_manifest(setup_test_db):
    """
    Verifies that all 8 manufacturing departments and authorized job roles
    are registered and properly mapped in the system catalog.
    """
    expected_departments = [
        "Production Department",
        "Quality Control",
        "Inventory & Purchase",
        "Sales & CRM",
        "Dispatch & Logistics",
        "Billing & Finance",
        "HR & Administration",
        "Maintenance & Technical",
    ]
    for dept in expected_departments:
        assert dept in DEPARTMENT_JOB_ROLES, f"Department '{dept}' missing from DEPARTMENT_JOB_ROLES catalog"
        roles = DEPARTMENT_JOB_ROLES[dept]
        assert len(roles) >= 2, f"Department '{dept}' has fewer than 2 authorized job roles: {roles}"

        # Verify each role has default permissions mapped
        for r in roles:
            assert r in JOB_ROLE_DEFAULT_PERMISSIONS, f"Job role '{r}' missing in JOB_ROLE_DEFAULT_PERMISSIONS"


@pytest.mark.asyncio
async def test_first_login_mandatory_password_change_enforcement(setup_test_db):
    """
    Verifies the end-to-end authentication lifecycle:
    1. First login succeeds with initial dev password 'admin@123'
    2. Response strictly indicates must_change_password=True
    3. Direct API requests to protected endpoints are blocked with 403 Forbidden
    4. Password change enforces policy (min 12 chars, confirmation match, different from old)
    5. After successful password change, must_change_password=False and protected endpoints accessible
    6. Old password is invalidated on subsequent logins
    """
    db = setup_test_db
    test_email = "tester@rgtech.com"
    initial_pass = "admin@123"
    initial_hash = hash_password(initial_pass)

    # Provision user with must_change_password=True
    user_res = await db["users"].insert_one({
        "email": test_email,
        "username": "tester",
        "full_name": "Test QA Employee",
        "hashed_password": initial_hash,
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "department": "Production Department",
        "job_role": "Production Manager",
        "job_roles": ["Production Manager"],
        "employee_code": "EMP-999",
        "allowed_units": [ManufacturingUnit.Unit_1.value],
        "is_active": True,
        "must_change_password": True,
        "is_test_seed": True,
        "created_at": datetime.now(timezone.utc),
    })

    await db["employees"].insert_one({
        "code": "EMP-999",
        "full_name": "Test QA Employee",
        "email": test_email,
        "department": "Production Department",
        "designation": "Production Manager",
        "account_type": "EMPLOYEE",
        "job_role": "Production Manager",
        "unit_id": "Unit_1",
        "status": "ACTIVE",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Login with initial temporary password
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": initial_pass
        })
        assert login_resp.status_code == 200
        login_data = login_resp.json()
        assert login_data["user"]["must_change_password"] is True

        csrf_token = login_resp.cookies.get("RG_csrf") or login_data.get("csrf_token")
        headers = {"X-CSRF-Token": csrf_token}

        # 2. Verify direct access to protected endpoint is BLOCKED (403)
        prot_resp = await client.get("/api/v1/employee/dashboard")
        assert prot_resp.status_code == 403
        err_msg = prot_resp.json().get("error", {}).get("message", "") or prot_resp.json().get("detail", "")
        assert "Password change required" in err_msg

        # 3. Password change: Reject short password (< 12 chars via schema validation)
        short_resp = await client.post("/api/v1/auth/change-password", json={
            "current_password": initial_pass,
            "new_password": "short",
            "confirm_password": "short"
        }, headers=headers)
        assert short_resp.status_code in [400, 422]

        # 4. Password change: Reject same password when >= 12 chars
        same_pass_12 = "InitialPass#123"
        same_resp = await client.post("/api/v1/auth/change-password", json={
            "current_password": same_pass_12,
            "new_password": same_pass_12,
            "confirm_password": same_pass_12
        }, headers=headers)
        assert same_resp.status_code == 400

        # 5. Password change: Reject mismatched confirm password
        mismatch_resp = await client.post("/api/v1/auth/change-password", json={
            "current_password": initial_pass,
            "new_password": "ValidNewPassword#2026",
            "confirm_password": "DifferentPassword#2026"
        }, headers=headers)
        assert mismatch_resp.status_code == 400

        # 6. Password change: Valid new password
        new_valid_pass = "ValidNewPassword#2026"
        chg_resp = await client.post("/api/v1/auth/change-password", json={
            "current_password": initial_pass,
            "new_password": new_valid_pass,
            "confirm_password": new_valid_pass
        }, headers=headers)
        assert chg_resp.status_code == 200
        assert chg_resp.json()["must_change_password"] is False

        # 7. Protected endpoint now ACCESSIBLE (200)
        prot_ok = await client.get("/api/v1/employee/dashboard")
        assert prot_ok.status_code == 200
        assert prot_ok.json()["employee_code"] == "EMP-999"

        # 8. Logout
        new_csrf = chg_resp.cookies.get("RG_csrf") or client.cookies.get("RG_csrf")
        logout_resp = await client.post("/api/v1/auth/logout", json={}, headers={"X-CSRF-Token": new_csrf})
        assert logout_resp.status_code == 200

        # 9. Verify old password no longer works
        old_login = await client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": initial_pass
        })
        assert old_login.status_code == 401

        # 10. Verify new password works
        new_login = await client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": new_valid_pass
        })
        assert new_login.status_code == 200
        assert new_login.json()["user"]["must_change_password"] is False


@pytest.mark.asyncio
async def test_super_admin_full_access_policy(setup_test_db):
    """
    Verifies that Super Admin has full unrestricted access across the system.
    Super Admin can read records, login, and perform creations/mutations.
    """
    db = setup_test_db
    owner_pass = "ValidOwnerPass123!"
    await db["users"].insert_one({
        "email": "owner@rgtech.com",
        "username": "owner",
        "full_name": "Executive Owner",
        "hashed_password": hash_password(owner_pass),
        "role": RoleName.SUPER_ADMIN.value,
        "allowed_units": [ManufacturingUnit.BOTH.value],
        "is_active": True,
        "must_change_password": False,
        "created_at": datetime.now(timezone.utc),
    })

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_res = await client.post("/api/v1/auth/login", json={
            "email": "owner@rgtech.com",
            "password": owner_pass
        })
        assert login_res.status_code == 200
        csrf = login_res.cookies.get("RG_csrf")

        # Owner CAN read dashboard
        me_res = await client.get("/api/v1/auth/me")
        assert me_res.status_code == 200

        # Owner CAN create users
        mutate_res = await client.post("/api/v1/users", json={
            "email": "createdbyowner@rgtech.com",
            "full_name": "Created By Owner",
            "password": "Password123!456",
            "role": "EMPLOYEE"
        }, headers={"X-CSRF-Token": csrf})
        assert mutate_res.status_code == 201
