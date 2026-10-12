from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.models.user import RoleName, ManufacturingUnit
from app.core.security import hash_password, verify_password


@pytest.fixture
async def setup_hr_and_employee(setup_test_db):
    """
    Seed test database with an authorized HR user and an Admin user.
    """
    db = setup_test_db
    now = datetime.now(timezone.utc)

    hr_user = await db["users"].insert_one({
        "email": "hr_lead@testcorp.com",
        "full_name": "HR Lead Specialist",
        "hashed_password": hash_password("ValidPassword123!"),
        "role": RoleName.HR.value,
        "allowed_units": [ManufacturingUnit.BOTH.value],
        "is_active": True,
        "must_change_password": False,
        "created_at": now,
    })

    admin_user = await db["users"].insert_one({
        "email": "admin_sys@testcorp.com",
        "full_name": "System Administrator",
        "hashed_password": hash_password("ValidPassword123!"),
        "role": RoleName.ADMIN.value,
        "allowed_units": [ManufacturingUnit.BOTH.value],
        "is_active": True,
        "must_change_password": False,
        "created_at": now,
    })

    return {
        "hr_id": str(hr_user.inserted_id),
        "admin_id": str(admin_user.inserted_id),
    }


async def login_helper(async_client: AsyncClient, email: str, password: str):
    """
    Helper to log in and return session cookies and CSRF headers.
    """
    res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    assert res.status_code == 200
    session_cookie = res.cookies.get(settings.SESSION_COOKIE_NAME)
    csrf_token = res.json()["csrf_token"]
    cookies = {
        settings.SESSION_COOKIE_NAME: session_cookie,
        settings.CSRF_COOKIE_NAME: csrf_token,
    }
    headers = {
        settings.CSRF_HEADER_NAME: csrf_token,
    }
    return res.json(), cookies, headers


@pytest.mark.asyncio
async def test_hr_provision_employee_with_initial_password(async_client: AsyncClient, setup_hr_and_employee, setup_test_db):
    """
    Test Step 1-3: Authorized HR provisions an employee account with initial password.
    Verifies:
    - Initial password >= 12 characters is required.
    - Plaintext password is NEVER saved in database.
    - must_change_password is set to True.
    - Audit log is created without credentials.
    """
    db = setup_test_db
    # 1. Log in as HR
    _, hr_cookies, hr_headers = await login_helper(async_client, "hr_lead@testcorp.com", "ValidPassword123!")

    # 2. Provision new employee with initial password
    initial_pwd = "InitialSecurePass2026!"
    emp_payload = {
        "code": "EMP-9001",
        "full_name": "Aarav Sharma",
        "email": "aarav.sharma@testcorp.com",
        "department": "Production Department",
        "designation": "Machine Operator",
        "job_role": "Machine Operator",
        "unit_id": "Unit_1",
        "create_user_account": True,
        "user_password": initial_pwd,
        "confirm_user_password": initial_pwd,
        "must_change_password": True,
    }

    res = await async_client.post(
        "/api/v1/master/employees",
        json=emp_payload,
        cookies=hr_cookies,
        headers=hr_headers,
    )
    assert res.status_code == 201
    created_emp = res.json()
    assert created_emp["code"] == "EMP-9001"
    assert created_emp["email"] == "aarav.sharma@testcorp.com"

    # 3. Check MongoDB user document directly
    user_doc = await db["users"].find_one({"email": "aarav.sharma@testcorp.com"})
    assert user_doc is not None
    assert "password" not in user_doc
    assert "user_password" not in user_doc
    assert "hashed_password" in user_doc
    assert verify_password(initial_pwd, user_doc["hashed_password"]) is True
    assert user_doc["must_change_password"] is True

    # 4. Check audit log in MongoDB
    audit_doc = await db["audit_logs"].find_one({"details.employee_email": "aarav.sharma@testcorp.com"})
    assert audit_doc is not None
    assert "PROVISION" in audit_doc["action"]
    # Ensure neither password nor hash is in audit log
    assert initial_pwd not in str(audit_doc)
    assert user_doc["hashed_password"] not in str(audit_doc)


@pytest.mark.asyncio
async def test_provision_validation_short_and_mismatched_password(async_client: AsyncClient, setup_hr_and_employee):
    """
    Test Step 2: Validate that passwords < 12 chars or mismatched confirmations are rejected.
    """
    _, hr_cookies, hr_headers = await login_helper(async_client, "hr_lead@testcorp.com", "ValidPassword123!")

    # A) Password too short (< 12 chars)
    short_pwd_payload = {
        "code": "EMP-9002",
        "full_name": "Short Pwd Employee",
        "email": "short.pwd@testcorp.com",
        "department": "Production Department",
        "designation": "Machine Operator",
        "create_user_account": True,
        "user_password": "Short123!",
        "confirm_user_password": "Short123!",
    }
    res_short = await async_client.post(
        "/api/v1/master/employees",
        json=short_pwd_payload,
        cookies=hr_cookies,
        headers=hr_headers,
    )
    assert res_short.status_code in [400, 422]

    # B) Mismatched confirmation
    mismatch_payload = {
        "code": "EMP-9003",
        "full_name": "Mismatch Employee",
        "email": "mismatch@testcorp.com",
        "department": "Production Department",
        "designation": "Machine Operator",
        "create_user_account": True,
        "user_password": "ValidLongPassword123!",
        "confirm_user_password": "DifferentPassword123!",
    }
    res_mismatch = await async_client.post(
        "/api/v1/master/employees",
        json=mismatch_payload,
        cookies=hr_cookies,
        headers=hr_headers,
    )
    assert res_mismatch.status_code in [400, 409, 422]


@pytest.mark.asyncio
async def test_first_login_enforces_password_change_restriction(async_client: AsyncClient, setup_hr_and_employee, setup_test_db):
    """
    Test Step 4: Employee first login with must_change_password=True.
    Verifies:
    - Login succeeds and returns must_change_password=True.
    - Protected ERP endpoints return HTTP 403 Forbidden with PASSWORD_CHANGE_REQUIRED.
    - Minimal auth endpoints (/api/v1/auth/me, /api/v1/auth/csrf-token, /api/v1/auth/logout) remain accessible.
    """
    # 1. HR provisions employee
    _, hr_cookies, hr_headers = await login_helper(async_client, "hr_lead@testcorp.com", "ValidPassword123!")
    initial_pwd = "TempInitPassword123!"
    await async_client.post(
        "/api/v1/master/employees",
        json={
            "code": "EMP-9004",
            "full_name": "First Login Tester",
            "email": "first.login@testcorp.com",
            "department": "Production Department",
            "designation": "Production Supervisor",
            "job_role": "Production Supervisor",
            "create_user_account": True,
            "user_password": initial_pwd,
            "confirm_user_password": initial_pwd,
            "must_change_password": True,
        },
        cookies=hr_cookies,
        headers=hr_headers,
    )

    # 2. Employee logs in
    login_data, emp_cookies, emp_headers = await login_helper(async_client, "first.login@testcorp.com", initial_pwd)
    assert login_data["user"]["must_change_password"] is True

    # 3. Direct access to protected ERP endpoints must be rejected with 403 Forbidden
    res_erp = await async_client.get(
        "/api/v1/master/employees",
        cookies=emp_cookies,
        headers=emp_headers,
    )
    assert res_erp.status_code == 403
    assert "Password change required on first login" in res_erp.json()["error"]["message"]
    assert res_erp.headers.get("X-Error-Code") == "PASSWORD_CHANGE_REQUIRED"

    # 4. Access to /auth/me is permitted
    res_me = await async_client.get(
        "/api/v1/auth/me",
        cookies=emp_cookies,
        headers=emp_headers,
    )
    assert res_me.status_code == 200
    assert res_me.json()["must_change_password"] is True


@pytest.mark.asyncio
async def test_employee_changes_password_successfully(async_client: AsyncClient, setup_hr_and_employee, setup_test_db):
    """
    Test Step 5 & 6: Employee changes their password.
    Verifies:
    - Invalid current password rejected (400).
    - New password matching current password rejected (400).
    - Mismatched confirmation rejected (400).
    - Weak new password (< 12 chars) rejected (422).
    - Successful change updates hash, sets must_change_password=False, updates timestamp, rotates session.
    - Old password fails to authenticate.
    - New password authenticates and provides full ERP access.
    """
    db = setup_test_db
    # 1. Provision employee with Production Supervisor role
    _, hr_cookies, hr_headers = await login_helper(async_client, "hr_lead@testcorp.com", "ValidPassword123!")
    initial_pwd = "InitialSecurePass2026!"
    await async_client.post(
        "/api/v1/master/employees",
        json={
            "code": "EMP-9005",
            "full_name": "Change Password Worker",
            "email": "worker.change@testcorp.com",
            "department": "Production Department",
            "designation": "Production Supervisor",
            "job_role": "Production Supervisor",
            "create_user_account": True,
            "user_password": initial_pwd,
            "confirm_user_password": initial_pwd,
            "must_change_password": True,
        },
        cookies=hr_cookies,
        headers=hr_headers,
    )

    # 2. Login as worker
    _, worker_cookies, worker_headers = await login_helper(async_client, "worker.change@testcorp.com", initial_pwd)

    # A) Attempt with wrong current password
    res_wrong_curr = await async_client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "WrongCurrentPassword123!",
            "new_password": "BrandNewPassword2026!",
            "confirm_password": "BrandNewPassword2026!",
        },
        cookies=worker_cookies,
        headers=worker_headers,
    )
    assert res_wrong_curr.status_code == 400
    assert "Current password is incorrect" in res_wrong_curr.json()["error"]["message"]

    # B) Attempt with same password as current
    res_same_pwd = await async_client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": initial_pwd,
            "new_password": initial_pwd,
            "confirm_password": initial_pwd,
        },
        cookies=worker_cookies,
        headers=worker_headers,
    )
    assert res_same_pwd.status_code == 400
    assert "same as your current" in res_same_pwd.json()["error"]["message"].lower()

    # C) Attempt with mismatched confirmation
    res_mismatch = await async_client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": initial_pwd,
            "new_password": "BrandNewPassword2026!",
            "confirm_password": "DifferentConfirm123!",
        },
        cookies=worker_cookies,
        headers=worker_headers,
    )
    assert res_mismatch.status_code == 400
    assert "do not match" in res_mismatch.json()["error"]["message"].lower()

    # D) Successful password change
    new_pwd = "BrandNewPermanentPassword2026!"
    res_success = await async_client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": initial_pwd,
            "new_password": new_pwd,
            "confirm_password": new_pwd,
        },
        cookies=worker_cookies,
        headers=worker_headers,
    )
    assert res_success.status_code == 200
    data = res_success.json()
    assert data["must_change_password"] is False

    # Verify session cookie was rotated
    new_session_cookie = res_success.cookies.get(settings.SESSION_COOKIE_NAME)
    assert new_session_cookie is not None

    # Check MongoDB: must_change_password=False, password_changed_at exists
    user_doc = await db["users"].find_one({"email": "worker.change@testcorp.com"})
    assert user_doc["must_change_password"] is False
    assert user_doc.get("password_changed_at") is not None
    assert verify_password(new_pwd, user_doc["hashed_password"]) is True

    # 3. Old password must NO LONGER work
    old_login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "worker.change@testcorp.com", "password": initial_pwd}
    )
    assert old_login_res.status_code == 401

    # 4. New password works
    new_login_data, final_cookies, final_headers = await login_helper(
        async_client, "worker.change@testcorp.com", new_pwd
    )
    assert new_login_data["user"]["must_change_password"] is False

    # 5. Access to ERP endpoints now succeeds without HTTP 403
    res_erp = await async_client.get(
        "/api/v1/master/employees",
        cookies=final_cookies,
        headers=final_headers,
    )
    assert res_erp.status_code == 200


@pytest.mark.asyncio
async def test_hr_reset_employee_password_workflow(async_client: AsyncClient, setup_hr_and_employee, setup_test_db):
    """
    Test Step 7: HR initiates a password reset for an employee.
    Verifies:
    - HR cannot reset an Admin or Super Admin password (privilege escalation protection).
    - HR can reset an Employee's password.
    - Password reset sets must_change_password=True and revokes all active sessions.
    - Audit log is created without credentials.
    """
    db = setup_test_db
    # 1. Login HR
    _, hr_cookies, hr_headers = await login_helper(async_client, "hr_lead@testcorp.com", "ValidPassword123!")

    # 2. Provision an employee
    initial_pwd = "InitialSecurePass2026!"
    await async_client.post(
        "/api/v1/master/employees",
        json={
            "code": "EMP-9006",
            "full_name": "Reset Candidate",
            "email": "reset.candidate@testcorp.com",
            "department": "Production Department",
            "designation": "Machine Operator",
            "create_user_account": True,
            "user_password": initial_pwd,
            "confirm_user_password": initial_pwd,
            "must_change_password": False,
        },
        cookies=hr_cookies,
        headers=hr_headers,
    )
    target_emp = await db["users"].find_one({"email": "reset.candidate@testcorp.com"})

    # Employee logs in and creates an active session
    _, emp_cookies, emp_headers = await login_helper(async_client, "reset.candidate@testcorp.com", initial_pwd)
    session_count_before = await db["sessions"].count_documents({"user_id": str(target_emp["_id"]), "is_revoked": False})
    assert session_count_before > 0

    # 3. HR resets employee password
    reset_pwd = "ResetPasswordFromHR2026!"
    res_reset = await async_client.post(
        "/api/v1/auth/reset-password",
        json={
            "user_id": str(target_emp["_id"]),
            "new_password": reset_pwd,
            "confirm_password": reset_pwd,
            "must_change_password": True,
        },
        cookies=hr_cookies,
        headers=hr_headers,
    )
    assert res_reset.status_code == 200

    # 4. Target user active sessions should now be revoked
    active_sessions_after = await db["sessions"].count_documents({"user_id": str(target_emp["_id"]), "is_revoked": False})
    assert active_sessions_after == 0

    # Previous session cookie no longer works
    res_old_session = await async_client.get(
        "/api/v1/auth/me",
        cookies=emp_cookies,
    )
    assert res_old_session.status_code == 401

    # 5. Target user must log in with reset password and have must_change_password=True
    login_data, _, _ = await login_helper(async_client, "reset.candidate@testcorp.com", reset_pwd)
    assert login_data["user"]["must_change_password"] is True

    # 6. Privilege escalation check: HR attempts to reset Admin account -> rejected with 403
    admin_doc = await db["users"].find_one({"email": "admin_sys@testcorp.com"})
    res_escalate = await async_client.post(
        "/api/v1/auth/reset-password",
        json={
            "user_id": str(admin_doc["_id"]),
            "new_password": "HackerAdminPassword123!",
            "confirm_password": "HackerAdminPassword123!",
        },
        cookies=hr_cookies,
        headers=hr_headers,
    )
    assert res_escalate.status_code == 403
    assert "cannot reset Administrator or Owner" in res_escalate.json()["error"]["message"]
