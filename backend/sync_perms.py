import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.models.user import resolve_user_permissions

async def sync():
    client = AsyncIOMotorClient('mongodb://127.0.0.1:27017')
    db = client['rgtech_erp']
    users = await db['users'].find().to_list(100)
    for u in users:
        new_perms = resolve_user_permissions(u)
        await db['users'].update_one({'_id': u['_id']}, {'$set': {'permissions': new_perms}})
        if u.get('role') == 'INVENTORY_MANAGER' or u.get('job_role') == 'Inventory Manager':
            print(f"Updated {u.get('email')}: {new_perms}")

if __name__ == '__main__':
    asyncio.run(sync())
