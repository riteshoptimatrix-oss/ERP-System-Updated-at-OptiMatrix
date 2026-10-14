import asyncio
from app.database.mongodb import mongodb_manager

async def main():
    await mongodb_manager.connect()
    db = mongodb_manager.get_database()
    res = await db["announcements"].update_many(
        {},
        {"$set": {"is_deleted": False, "audience_type": "all", "recipients": []}}
    )
    print(f"Updated: {res.modified_count}")
    cnt = await db["announcements"].count_documents({"is_deleted": False})
    print(f"Non-deleted announcements count: {cnt}")

if __name__ == "__main__":
    asyncio.run(main())
