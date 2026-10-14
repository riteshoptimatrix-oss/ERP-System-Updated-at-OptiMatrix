import asyncio
import httpx

creds_to_test = [
    ("amitpatel@rgtech.com", "Amit@rgtech.com"),
    ("ananyaiyer@rgtech.com", "Ananya123@rgtech.com"),
    ("chetanprajapati@rgtech.com", "Chetan@rgtech.com"),
    ("deepakjoshi@rgtech.com", "Deepak@rgtech.com"),
    ("hr@rgtech.com", "admin123"),
    ("manishtiwari@rgtech.com", "Manish@rgtech.com"),
    ("mayan@rgtech.com", "admin123"),
    ("nehamodi@rgtech.com", "Neha@rgtech.com"),
    ("priyashah@rgtech.com", "Priya@rgtech.com"),
    ("rahulsharma@rgtech.com", "Rahul@rgtech.com"),
    ("rajeshkhatri@rgtech.com", "Rajesh123@rgtech.com"),
    ("rameshsolanki@rgtech.com", "Ramesh@rgtech.com"),
    ("rohangupta@rgtech.com", "Rohan@rgtech.com"),
    ("sanjayrawat@rgtech.com", "Sanjay123@rgtech.com"),
    ("sureshraina@rgtech.com", "Suresh@rgtech.com"),
    ("admin@rgtech.com", "AdminPassword123!"),  # Old preserved
]

async def test_logins():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000/api/v1") as client:
        success = 0
        for email, pwd in creds_to_test:
            res = await client.post("/auth/login", json={"email": email, "password": pwd})
            if res.status_code == 200:
                print(f"SUCCESS: {email} -> Logged in successfully!")
                success += 1
            else:
                print(f"FAILED: {email} -> {res.status_code} {res.text}")
        print(f"\nResult: {success}/{len(creds_to_test)} accounts logged in successfully!")

asyncio.run(test_logins())
