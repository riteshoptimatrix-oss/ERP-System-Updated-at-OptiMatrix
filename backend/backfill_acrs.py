import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def backfill():
    client = AsyncIOMotorClient('mongodb://127.0.0.1:27017')
    db = client['rgtech_erp']
    docs = await db['attendance_correction_requests'].find().to_list(100)
    count = 0
    for i, d in enumerate(docs):
        if not d.get('request_number'):
            req_num = f'ACR-2026-{(i+1):04d}'
            await db['attendance_correction_requests'].update_one(
                {'_id': d['_id']},
                {'$set': {'request_number': req_num}}
            )
            count += 1
    print(f'Backfilled {count} documents with request_number.')

if __name__ == '__main__':
    asyncio.run(backfill())
