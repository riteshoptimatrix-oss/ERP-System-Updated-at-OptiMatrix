"""
Database Backup Utility (Read-only exporter)
Exports all collections from rgtech_erp database to BSON/JSON backups without modifying any database content.
"""
import asyncio
import os
import json
from datetime import datetime
from bson import json_util
from app.database.mongodb import mongodb_manager
from app.core.config import settings

async def backup_database():
    print(f"Connecting to MongoDB: {settings.MONGODB_URI}")
    await mongodb_manager.connect()
    db = mongodb_manager.get_database()
    db_name = settings.MONGODB_DB_NAME
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder = os.path.join(os.path.dirname(__file__), "database_backup", f"backup_{db_name}_{timestamp}")
    os.makedirs(backup_folder, exist_ok=True)
    
    print(f"[*] Starting full backup of database '{db_name}' to:\n    {backup_folder}\n")
    
    collections = await db.list_collection_names()
    collections.sort()
    
    summary = {}
    total_docs = 0
    
    for col_name in collections:
        col = db[col_name]
        count = await col.count_documents({})
        file_path = os.path.join(backup_folder, f"{col_name}.json")
        
        cursor = col.find({})
        docs = await cursor.to_list(length=None)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json_util.dumps(docs, indent=2))
            
        summary[col_name] = count
        total_docs += count
        print(f"  [+] Exported '{col_name}': {count} documents -> {col_name}.json")
        
    meta = {
        "database": db_name,
        "backup_timestamp": timestamp,
        "total_collections": len(collections),
        "total_documents": total_docs,
        "collections": summary,
    }
    
    meta_path = os.path.join(backup_folder, "_backup_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        
    print(f"\n[SUCCESS] Backup completed successfully!")
    print(f"  Total Collections: {len(collections)}")
    print(f"  Total Documents:   {total_docs}")
    print(f"  Location:          {backup_folder}")

if __name__ == "__main__":
    asyncio.run(backup_database())
