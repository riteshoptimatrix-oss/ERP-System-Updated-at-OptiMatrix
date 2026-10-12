from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from bson import ObjectId

class BaseRepository:
    """
    Abstract asynchronous MongoDB base repository.
    Provides standard CRUD abstraction, index management hooks, and transactional helpers.
    """
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str) -> None:
        self.db = db
        self.collection_name = collection_name
        self.collection: AsyncIOMotorCollection = db[collection_name]

    async def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Fetch document by ObjectID string."""
        if not ObjectId.is_valid(doc_id):
            return None
        return await self.collection.find_one({"_id": ObjectId(doc_id)})

    async def find_one(self, filter_query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find single document matching filter."""
        return await self.collection.find_one(filter_query)

    async def find_many(
        self, filter_query: Dict[str, Any], limit: int = 100, skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Find multiple documents with pagination."""
        cursor = self.collection.find(filter_query).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def insert_one(self, document: Dict[str, Any]) -> str:
        """Insert a single document and return its inserted ID."""
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def update_one(
        self, filter_query: Dict[str, Any], update_doc: Dict[str, Any]
    ) -> int:
        """Update single document matching query. Returns modified count."""
        result = await self.collection.update_one(filter_query, {"$set": update_doc})
        return result.modified_count

    async def delete_one(self, filter_query: Dict[str, Any]) -> int:
        """Delete single document matching query. Returns deleted count."""
        result = await self.collection.delete_one(filter_query)
        return result.deleted_count
