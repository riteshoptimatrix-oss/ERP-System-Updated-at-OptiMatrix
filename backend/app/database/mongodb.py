import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from app.core.config import settings

logger = logging.getLogger(__name__)


class MongoDBManager:
    """
    Manages asynchronous MongoDB connection lifecycle and client pooling.
    Provides safe connectivity checks and graceful shutdown.
    """
    def __init__(self) -> None:
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None

    async def connect(self) -> None:
        """
        Initialize the AsyncIOMotorClient pool and establish connection.
        """
        if self.client is not None:
            logger.warning("MongoDB client is already initialized.")
            return

        logger.info(
            "Connecting to MongoDB...",
            extra={"database": settings.MONGODB_DB_NAME}
        )

        try:
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
                maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                serverSelectionTimeoutMS=settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
                connectTimeoutMS=settings.MONGODB_CONNECT_TIMEOUT_MS,
            )
            self.database = self.client[settings.MONGODB_DB_NAME]
            # Verify connectivity immediately on startup
            await self.ping()
            logger.info("Successfully connected to MongoDB.")
        except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as exc:
            # We log error but do not crash the entire process on startup,
            # allowing readiness probes to signal dependency failure gracefully.
            logger.error(
                "Failed to connect to MongoDB on startup",
                exc_info=True,
                extra={"error_type": type(exc).__name__}
            )

    async def disconnect(self) -> None:
        """
        Close MongoDB connection pool cleanly.
        """
        if self.client is not None:
            logger.info("Closing MongoDB connection pool...")
            self.client.close()
            self.client = None
            self.database = None
            logger.info("MongoDB connection pool closed.")

    async def ping(self) -> bool:
        """
        Execute admin ping command to verify database connectivity.
        Returns True if database is alive and reachable, False otherwise.
        """
        if self.client is None:
            return False
        try:
            # Run admin command with strict timeout
            await self.client.admin.command("ping")
            return True
        except Exception as exc:
            logger.warning(
                "MongoDB ping check failed",
                extra={"error": str(exc), "error_type": type(exc).__name__}
            )
            return False

    def get_database(self) -> AsyncIOMotorDatabase:
        """
        Return the current database instance.
        Raises RuntimeError if not connected.
        """
        if self.database is None:
            raise RuntimeError("Database client is not initialized or disconnected.")
        return self.database


# Global singleton instance
mongodb_manager = MongoDBManager()
