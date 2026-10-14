import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def run():
    client = AsyncIOMotorClient('mongodb://127.0.0.1:27017')
    db = client['rgtech_erp']
    users = await db['users'].find().to_list(100)
    for u in sorted(users, key=lambda x: x.get('email', '')):
        email = u.get('email')
        role = u.get('role')
        dept = u.get('department')
        perms = [p for p in u.get('permissions', []) if 'production' in p]
        print(f"{email}: role={role}, dept={dept}, perms={perms}")

if __name__ == '__main__':
    asyncio.run(run())
