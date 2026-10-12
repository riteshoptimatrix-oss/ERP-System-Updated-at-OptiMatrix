import pytest
from httpx import AsyncClient
from app.core.config import settings


@pytest.mark.asyncio
async def test_successful_login_and_cookies(async_client: AsyncClient, setup_test_users):
    """
    Test single unified login sets HttpOnly session cookie and CSRF cookie on success.
    """
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@testcorp.com", "password": "ValidPassword123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["user"]["email"] == "superadmin@testcorp.com"
    assert data["user"]["role"] == "SUPER_ADMIN"
    assert "csrf_token" in data

    # Check cookies
    cookies = response.cookies
    assert settings.SESSION_COOKIE_NAME in cookies
    assert settings.CSRF_COOKIE_NAME in cookies


@pytest.mark.asyncio
async def test_login_invalid_password_returns_generic_error(async_client: AsyncClient, setup_test_users):
    """
    Test invalid password returns 401 without revealing password-specific details.
    """
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@testcorp.com", "password": "WrongPassword999!"}
    )
    assert response.status_code == 401
    data = response.json()
    assert "Invalid corporate email or password" in data["error"]["message"]


@pytest.mark.asyncio
async def test_login_nonexistent_email_returns_identical_generic_error(async_client: AsyncClient, setup_test_users):
    """
    Test non-existent user returns exact same 401 message (anti-enumeration).
    """
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@testcorp.com", "password": "SomePassword123!"}
    )
    assert response.status_code == 401
    data = response.json()
    assert "Invalid corporate email or password" in data["error"]["message"]


@pytest.mark.asyncio
async def test_deactivated_user_cannot_login(async_client: AsyncClient, setup_test_users):
    """
    Test deactivated user cannot log in and gets 403 Forbidden.
    """
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "deactivated@testcorp.com", "password": "ValidPassword123!"}
    )
    assert response.status_code == 403
    data = response.json()
    assert "deactivated" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_session_logout_revocation(async_client: AsyncClient, setup_test_users):
    """
    Test logging out revokes the session in MongoDB and rejects subsequent calls.
    """
    # 1. Login
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@testcorp.com", "password": "ValidPassword123!"}
    )
    session_cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
    csrf_token = login_res.json()["csrf_token"]

    client_cookies = {
        settings.SESSION_COOKIE_NAME: session_cookie,
        settings.CSRF_COOKIE_NAME: csrf_token
    }
    client_headers = {
        settings.CSRF_HEADER_NAME: csrf_token
    }

    # 2. Access /me succeeds
    me_res = await async_client.get("/api/v1/auth/me", cookies=client_cookies)
    assert me_res.status_code == 200

    # 3. Logout
    logout_res = await async_client.post(
        "/api/v1/auth/logout",
        cookies=client_cookies,
        headers=client_headers
    )
    assert logout_res.status_code == 200

    # 4. Accessing /me after logout fails with 401
    post_logout_me = await async_client.get("/api/v1/auth/me", cookies=client_cookies)
    assert post_logout_me.status_code == 401


@pytest.mark.asyncio
async def test_super_admin_owner_login_with_username_and_email(async_client: AsyncClient, setup_test_users):
    """
    Test logging in with Super Admin (Owner) credentials:
    1. Username 'admin' and password 'admin123'
    2. Email 'admin@rgtech.com' and password 'admin123'
    """
    # 1. Login with username 'admin'
    res_username = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin", "password": "admin123"}
    )
    assert res_username.status_code == 200
    data_username = res_username.json()
    assert data_username["authenticated"] is True
    assert data_username["user"]["role"] == "SUPER_ADMIN"
    assert data_username["user"]["full_name"] == "Ritesh Gajjar"

    # 2. Login with email 'admin@rgtech.com'
    res_email = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@rgtech.com", "password": "admin123"}
    )
    assert res_email.status_code == 200
    data_email = res_email.json()
    assert data_email["authenticated"] is True
    assert data_email["user"]["role"] == "SUPER_ADMIN"
