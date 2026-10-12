import pytest
from typing import AsyncGenerator
from httpx import ASGITransport, AsyncClient
from app.main import create_application
from app.database.mongodb import mongodb_manager

from mongomock_motor import AsyncMongoMockClient
from app.core.config import settings

@pytest.fixture(autouse=True)
async def setup_test_db():
    """
    Automatically initializes an isolated in-memory MongoDB client for testing
    and seeds default system roles.
    """
    settings.ENVIRONMENT = "test"
    mock_client = AsyncMongoMockClient()
    mock_db = mock_client["RG_erp_test"]
    mongodb_manager.client = mock_client
    mongodb_manager.database = mock_db

    # Seed roles
    from app.models.user import DEFAULT_ROLE_PERMISSIONS
    roles_col = mock_db["roles"]
    for role_name, perms in DEFAULT_ROLE_PERMISSIONS.items():
        await roles_col.insert_one({
            "name": role_name.value,
            "permissions": perms
        })

    yield mock_db

    mock_client.close()
    mongodb_manager.client = None
    mongodb_manager.database = None

from datetime import datetime, timezone
from app.core.security import hash_password
from app.models.user import RoleName, ManufacturingUnit

@pytest.fixture
async def setup_test_users(setup_test_db):
    """
    Seed test database with test users for authentication and RBAC tests.
    """
    db = setup_test_db

    admin_id = await db["users"].insert_one({
        "email": "superadmin@testcorp.com",
        "full_name": "Super Admin Test",
        "hashed_password": hash_password("ValidPassword123!"),
        "role": RoleName.SUPER_ADMIN.value,
        "allowed_units": [ManufacturingUnit.BOTH.value],
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    # Super Admin (Owner) credentials: admin / admin123
    owner_admin_id = await db["users"].insert_one({
        "email": "admin@rgtech.com",
        "username": "admin",
        "full_name": "Ritesh Gajjar",
        "hashed_password": hash_password("admin123"),
        "role": RoleName.SUPER_ADMIN.value,
        "allowed_units": [ManufacturingUnit.BOTH.value],
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    pm1_id = await db["users"].insert_one({
        "email": "pm1@testcorp.com",
        "full_name": "Production Mgr Unit 1",
        "hashed_password": hash_password("ValidPassword123!"),
        "role": RoleName.PRODUCTION_MANAGER.value,
        "allowed_units": [ManufacturingUnit.Unit_1.value],
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    admin_ops_id = await db["users"].insert_one({
        "email": "admin_ops@testcorp.com",
        "full_name": "Operations Admin",
        "hashed_password": hash_password("ValidPassword123!"),
        "role": RoleName.ADMIN.value,
        "allowed_units": [ManufacturingUnit.BOTH.value],
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    deact_id = await db["users"].insert_one({
        "email": "deactivated@testcorp.com",
        "full_name": "Deactivated Worker",
        "hashed_password": hash_password("ValidPassword123!"),
        "role": RoleName.EMPLOYEE.value,
        "allowed_units": [ManufacturingUnit.Unit_1.value],
        "is_active": False,
        "created_at": datetime.now(timezone.utc),
    })

    return {
        "admin_id": str(admin_id.inserted_id),
        "admin_ops_id": str(admin_ops_id.inserted_id),
        "pm1_id": str(pm1_id.inserted_id),
        "deact_id": str(deact_id.inserted_id)
    }

@pytest.fixture
async def test_app():
    """
    Creates an isolated instance of the FastAPI application for testing.
    """
    app = create_application()
    return app

@pytest.fixture
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """
    Provides an async HTTP test client using httpx.
    """
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
