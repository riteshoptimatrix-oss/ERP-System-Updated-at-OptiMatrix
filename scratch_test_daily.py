import asyncio
import httpx

async def test_daily():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000/api/v1") as client:
        # RG Tech auth uses json payload {"email": ..., "password": ...}
        login_res = await client.post("/auth/login", json={"email": "admin@rgtech.com", "password": "AdminPassword123!"})
        if login_res.status_code != 200:
            print("Login failed:", login_res.status_code, login_res.text)
            return
        token = login_res.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # 1. List daily entries
        res = await client.get("/production/daily", headers=headers)
        print("GET /production/daily status:", res.status_code)
        data = res.json()
        print("Total items:", len(data))
        if data:
            print("First item sample:", data[0].get("order_no"), data[0].get("customer"), data[0].get("department"), "Earned:", data[0].get("daily_earned"))
        
        # 2. Get summary
        res_sum = await client.get("/production/daily/summary", headers=headers)
        print("GET /production/daily/summary status:", res_sum.status_code)
        sdata = res_sum.json()
        print("Summary stats:", {k: v for k, v in sdata.items() if k != "department_breakdown"})
        print("Department breakdowns count:", len(sdata.get("department_breakdown", [])))
        for dept in sdata.get("department_breakdown", []):
            print(f" - {dept.get('department')}: {dept.get('entry_count')} entries, Good: {dept.get('good_qty')}, Earned: ₹{dept.get('daily_earned')}")

asyncio.run(test_daily())
