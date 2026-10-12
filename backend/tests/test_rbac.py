import pytest
from httpx import AsyncClient
from datetime import datetime, timezone
from bson import ObjectId
from app.core.config import settings
from app.core.security import hash_password
from app.database.mongodb import mongodb_manager
from app.models.user import RoleName, ManufacturingUnit, AccountType, resolve_user_permissions


@pytest.mark.asyncio
async def test_rbac_permission_enforcement(async_client: AsyncClient, setup_test_users):
    """
    Test RBAC denies access to unauthorized modules (e.g., Production Manager accessing Users API).
    """
    # 1. Login as Production Manager (pm1)
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "pm1@testcorp.com", "password": "ValidPassword123!"}
    )
    assert login_res.status_code == 200
    pm_cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
    pm_csrf = login_res.json()["csrf_token"]

    pm_cookies = {
        settings.SESSION_COOKIE_NAME: pm_cookie,
        settings.CSRF_COOKIE_NAME: pm_csrf
    }

    # 2. PM tries to access /api/v1/users (requires users:read, which PM does not have)
    users_res = await async_client.get("/api/v1/users", cookies=pm_cookies)
    assert users_res.status_code == 403
    assert "Permission denied" in users_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_super_admin_has_read_only_monitoring_access(async_client: AsyncClient, setup_test_users):
    """
    Test Super Admin has read-only access to user directory and monitoring data.
    """
    # 1. Login as Super Admin (Owner - Ritesh Gajjar)
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@rgtech.com", "password": "admin123"}
    )
    assert login_res.status_code == 200
    admin_cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
    admin_csrf = login_res.json()["csrf_token"]

    admin_cookies = {
        settings.SESSION_COOKIE_NAME: admin_cookie,
        settings.CSRF_COOKIE_NAME: admin_csrf
    }

    # 2. Super Admin accesses /api/v1/users (read-only allowed)
    users_res = await async_client.get("/api/v1/users", cookies=admin_cookies)
    assert users_res.status_code == 200
    users_data = users_res.json()
    assert isinstance(users_data, list)
    assert len(users_data) >= 1


@pytest.mark.asyncio
async def test_owner_strict_read_only_blocks_business_mutations(async_client: AsyncClient, setup_test_users):
    """
    Test Super Admin (Owner) cannot mutate business records or provision users.
    Any write attempt returns HTTP 403 and records a security audit log.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@rgtech.com", "password": "admin123"}
    )
    admin_cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
    admin_csrf = login_res.json()["csrf_token"]

    admin_cookies = {
        settings.SESSION_COOKIE_NAME: admin_cookie,
        settings.CSRF_COOKIE_NAME: admin_csrf
    }

    # Attempt to create a user as Super Admin
    create_res = await async_client.post(
        "/api/v1/users",
        cookies=admin_cookies,
        headers={"X-CSRF-Token": admin_csrf},
        json={
            "email": "testownerwrite@rgtech.com",
            "full_name": "Test User",
            "password": "Password123!",
            "role": "EMPLOYEE",
            "allowed_units": ["BOTH"]
        }
    )
    assert create_res.status_code == 403
    assert "read-only monitoring" in create_res.json()["error"]["message"]

    # Verify audit log was recorded for security denial
    db = mongodb_manager.get_database()
    denial_log = await db["audit_logs"].find_one({"action": "SECURITY_OWNER_MUTATION_DENIED"})
    assert denial_log is not None
    assert denial_log["status"] == "DENIED"


@pytest.mark.asyncio
async def test_multi_job_role_permissions_union(async_client: AsyncClient, setup_test_db):
    """
    Test employee holding multiple job roles receives the deduplicated union of permissions
    across both roles.
    """
    db = setup_test_db
    # Create employee with two roles: Production Supervisor and QC Inspector
    emp_doc = {
        "email": "multi.role@rgtech.com",
        "full_name": "Multi Role Worker",
        "hashed_password": hash_password("ValidPassword123!"),
        "role": RoleName.EMPLOYEE.value,
        "account_type": AccountType.EMPLOYEE.value,
        "department": "Production Department",
        "job_roles": ["Production Supervisor", "QC Inspector"],
        "allowed_units": [ManufacturingUnit.BOTH.value],
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    await db["users"].insert_one(emp_doc)

    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "multi.role@rgtech.com", "password": "ValidPassword123!"}
    )
    assert login_res.status_code == 200
    user_data = login_res.json()["user"]
    perms = user_data["permissions"]

    # Must contain Production Supervisor perms
    assert "production:post" in perms
    assert "bom:read" in perms

    # Must contain QC Inspector perms
    assert "qc:approve" in perms
    assert "qc:update" in perms

    # Must have both job_roles returned
    assert "Production Supervisor" in user_data["job_roles"]
    assert "QC Inspector" in user_data["job_roles"]


@pytest.mark.asyncio
async def test_hr_privilege_escalation_prevention(async_client: AsyncClient, setup_test_db):
    """
    Test HR accounts cannot provision Administrator or Super Admin accounts,
    and cannot escalate existing users.
    """
    db = setup_test_db
    hr_doc = {
        "email": "hr_test@rgtech.com",
        "full_name": "HR Manager Test",
        "hashed_password": hash_password("ValidPassword123!"),
        "role": RoleName.HR.value,
        "account_type": AccountType.HR.value,
        "department": "HR & Administration",
        "job_roles": ["HR Manager"],
        "allowed_units": [ManufacturingUnit.BOTH.value],
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    await db["users"].insert_one(hr_doc)

    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "hr_test@rgtech.com", "password": "ValidPassword123!"}
    )
    assert login_res.status_code == 200
    hr_cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
    hr_csrf = login_res.json()["csrf_token"]

    hr_cookies = {
        settings.SESSION_COOKIE_NAME: hr_cookie,
        settings.CSRF_COOKIE_NAME: hr_csrf
    }
    hr_headers = {"X-CSRF-Token": hr_csrf}

    # 1. HR attempts to create an ADMIN account -> Rejected with 403 Forbidden
    create_admin_res = await async_client.post(
        "/api/v1/users",
        cookies=hr_cookies,
        headers=hr_headers,
        json={
            "email": "bad_admin@rgtech.com",
            "full_name": "Escalated Admin",
            "password": "Password123!",
            "role": "ADMIN",
            "allowed_units": ["BOTH"]
        }
    )
    assert create_admin_res.status_code == 403
    assert "HR accounts cannot provision Administrator" in create_admin_res.json()["error"]["message"]

    # 2. HR attempts to create an EMPLOYEE account -> Allowed with 201 Created
    create_emp_res = await async_client.post(
        "/api/v1/users",
        cookies=hr_cookies,
        headers=hr_headers,
        json={
            "email": "valid_emp@rgtech.com",
            "full_name": "Valid Worker",
            "password": "Password123!",
            "role": "EMPLOYEE",
            "department": "Quality Control",
            "job_roles": ["QC Inspector"],
            "allowed_units": ["Unit_2"]
        }
    )
    assert create_emp_res.status_code == 201
    created_id = create_emp_res.json()["id"]

    # 3. HR attempts to escalate the created employee to ADMIN -> Rejected with 403 Forbidden
    escalate_res = await async_client.patch(
        f"/api/v1/users/{created_id}",
        cookies=hr_cookies,
        headers=hr_headers,
        json={"role": "ADMIN"}
    )
    assert escalate_res.status_code == 403
    assert "HR accounts cannot escalate" in escalate_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_admin_cannot_escalate_to_super_admin(async_client: AsyncClient, setup_test_users, setup_test_db):
    """
    Test Admin cannot create or elevate anyone to Super Admin (Owner).
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"}
    )
    admin_cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
    admin_csrf = login_res.json()["csrf_token"]

    admin_cookies = {
        settings.SESSION_COOKIE_NAME: admin_cookie,
        settings.CSRF_COOKIE_NAME: admin_csrf
    }
    admin_headers = {"X-CSRF-Token": admin_csrf}

    # Admin tries to create Super Admin
    create_owner_res = await async_client.post(
        "/api/v1/users",
        cookies=admin_cookies,
        headers=admin_headers,
        json={
            "email": "fake_owner@rgtech.com",
            "full_name": "Fake Owner",
            "password": "Password123!",
            "role": "SUPER_ADMIN",
            "allowed_units": ["BOTH"]
        }
    )
    assert create_owner_res.status_code == 400
    assert "Super Admin" in create_owner_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_lockout_protection_for_last_active_owner(async_client: AsyncClient, setup_test_db):
    """
    Test that the last active Super Admin account cannot be deactivated or deleted.
    """
    db = setup_test_db
    # Seed 1 single Super Admin and 1 Admin
    owner_doc = {
        "email": "sole_owner@rgtech.com",
        "full_name": "Ritesh Gajjar",
        "hashed_password": hash_password("ValidPassword123!"),
        "role": RoleName.SUPER_ADMIN.value,
        "account_type": AccountType.SUPER_ADMIN.value,
        "allowed_units": [ManufacturingUnit.BOTH.value],
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    owner_res = await db["users"].insert_one(owner_doc)
    owner_id = str(owner_res.inserted_id)

    admin_doc = {
        "email": "sysadmin@rgtech.com",
        "full_name": "System Administrator",
        "hashed_password": hash_password("ValidPassword123!"),
        "role": RoleName.ADMIN.value,
        "allowed_units": [ManufacturingUnit.BOTH.value],
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    await db["users"].insert_one(admin_doc)

    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "sysadmin@rgtech.com", "password": "ValidPassword123!"}
    )
    admin_cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
    admin_csrf = login_res.json()["csrf_token"]

    admin_cookies = {
        settings.SESSION_COOKIE_NAME: admin_cookie,
        settings.CSRF_COOKIE_NAME: admin_csrf
    }
    admin_headers = {"X-CSRF-Token": admin_csrf}

    # Attempt to deactivate sole owner
    deact_res = await async_client.patch(
        f"/api/v1/users/{owner_id}",
        cookies=admin_cookies,
        headers=admin_headers,
        json={"is_active": False}
    )
    assert deact_res.status_code == 400
    assert "final active Super Admin" in deact_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_csrf_protection_rejects_missing_token(async_client: AsyncClient, setup_test_users):
    """
    Test state-changing operations require matching X-CSRF-Token.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"}
    )
    admin_cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
    admin_csrf = login_res.json()["csrf_token"]

    # Call POST without CSRF header
    create_res = await async_client.post(
        "/api/v1/users",
        cookies={
            settings.SESSION_COOKIE_NAME: admin_cookie,
            settings.CSRF_COOKIE_NAME: admin_csrf
        },
        json={
            "email": "newworker@testcorp.com",
            "full_name": "New Worker",
            "password": "Password123!",
            "role": "EMPLOYEE",
            "allowed_units": ["Unit_1"]
        }
    )
    assert create_res.status_code == 403
    assert "CSRF" in create_res.json()["error"]["message"]
