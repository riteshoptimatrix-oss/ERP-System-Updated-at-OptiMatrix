"""
Database Restore Script
Restores all JSON backup collections from database_backup into local MongoDB (rgtech_erp).
"""
import os
import glob
from bson import json_util
import pymongo

BACKUP_DIR = os.path.join(os.path.dirname(__file__), "database_backup", "backup_rgtech_erp_20261014_140431")
MONGODB_URI = "mongodb://127.0.0.1:27017"
DB_NAME = "rgtech_erp"

def restore_database():
    print(f"Connecting to MongoDB at {MONGODB_URI}...")
    client = pymongo.MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    
    # Verify connection
    client.server_info()
    print(f"Connected to local MongoDB successfully. Target Database: '{DB_NAME}'")
    
    json_files = glob.glob(os.path.join(BACKUP_DIR, "*.json"))
    json_files = [f for f in json_files if not os.path.basename(f).startswith("_")]
    json_files.sort()
    
    total_files = len(json_files)
    total_inserted = 0
    
    print(f"Found {total_files} collection backup files in:\n  {BACKUP_DIR}\n")
    
    for idx, file_path in enumerate(json_files, 1):
        col_name = os.path.splitext(os.path.basename(file_path))[0]
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json_util.loads(f.read())
            
        col = db[col_name]
        col.drop() # Clean restore for this collection
        
        if data:
            result = col.insert_many(data)
            count = len(result.inserted_ids)
        else:
            count = 0
            
        total_inserted += count
        print(f"[{idx:02d}/{total_files}] Restored '{col_name}': {count} documents")
        
    print(f"\n[SUCCESS] All collections restored successfully into '{DB_NAME}'!")
    print(f"Total Collections: {total_files}")
    print(f"Total Documents Inserted: {total_inserted}")

if __name__ == "__main__":
    restore_database()
