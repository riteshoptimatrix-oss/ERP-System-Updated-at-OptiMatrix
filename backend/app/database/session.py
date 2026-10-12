from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database.mongodb import mongodb_manager

async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """
    FastAPI dependency that yields the current AsyncIOMotorDatabase instance.
    Keeps database access decoupled from route controllers and business logic.
    """
    db = mongodb_manager.get_database()
    try:
        yield db
    finally:
        pass
