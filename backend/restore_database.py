"""
Database Restore Utility (Read-only / Safe recovery tool)
Restores collections from an existing backup snapshot directory.
"""
import asyncio
import os
import sys
from bson import json_util
from app.database.mongodb import mongodb_manager
from app.core.config import settings

async def restore_database(backup_dir_name: str):
    base_backup_dir = os.path.join(os.path.dirname(__file__), "database_backup", backup_dir_name)
    if not os.path.exists(base_backup_dir):
        print(f"[!] Error: Backup folder not found: {base_backup_dir}")
        return

    print(f"Connecting to MongoDB: {settings.MONGODB_URI}")
    await mongodb_manager.connect()
    db = mongodb_manager.get_database()
    print(f"[*] Starting restore to '{settings.MONGODB_DB_NAME}' from:\n    {base_backup_dir}\n")

    files = [f for f in os.listdir(base_backup_dir) if f.endswith(".json") and not f.startswith("_")]
    files.sort()

    for file_name in files:
        col_name = file_name[:-5]
        file_path = os.path.join(base_backup_dir, file_name)

        with open(file_path, "r", encoding="utf-8") as f:
            docs = json_util.loads(f.read())

        if docs:
            await db[col_name].delete_many({})
            await db[col_name].insert_many(docs)
            print(f"  [+] Restored '{col_name}': {len(docs)} documents")
        else:
            print(f"  [-] Skipped '{col_name}': 0 documents")

    print("\n[SUCCESS] Database restore completed successfully!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python restore_database.py <backup_folder_name>")
    else:
        asyncio.run(restore_database(sys.argv[1]))
