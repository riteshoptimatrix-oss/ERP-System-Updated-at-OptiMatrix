import httpx
import asyncio

async def test_live_server():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=10.0) as client:
        # Login
        login_res = await client.post("/api/v1/auth/login", json={"email": "admin@rgtech.com", "password": "admin123"})
        print("Login status:", login_res.status_code)
        if login_res.status_code != 200:
            print("Login failed:", login_res.text)
            return

        csrf = client.cookies.get("RG_csrf")
        if not csrf and "Set-Cookie" in login_res.headers:
            for part in login_res.headers["Set-Cookie"].split(";"):
                if "RG_csrf=" in part:
                    csrf = part.split("=")[1].strip()
        print("CSRF:", csrf)
        client.headers.update({"X-CSRF-Token": csrf or ""})

        # Test orders
        print("\n--- 1. Testing GET /api/v1/orders ---")
        orders_res = await client.get("/api/v1/orders", params={"unit_id": "Unit_1", "page": 1, "page_size": 20})
        print("Orders HTTP:", orders_res.status_code)
        if orders_res.status_code == 200:
            data = orders_res.json()
            print("Orders count:", data.get("total"), "Items returned:", len(data.get("items", [])))
        else:
            print("Orders error:", orders_res.text)

        # Test power
        print("\n--- 2. Testing GET /api/v1/power/outages & summary ---")
        p_sum = await client.get("/api/v1/power/summary", params={"unit_id": "Unit_1"})
        print("Power summary HTTP:", p_sum.status_code, p_sum.text)
        p_out = await client.get("/api/v1/power/outages", params={"unit_id": "Unit_1", "page_size": 100})
        print("Power outages HTTP:", p_out.status_code)
        if p_out.status_code == 200:
            data = p_out.json()
            print("Outages count:", data.get("total"), "Items returned:", len(data.get("items", [])))
        else:
            print("Power outages error:", p_out.text)

        # Test tasks messages
        print("\n--- 3. Testing GET /api/v1/tasks/:id/messages ---")
        tasks_res = await client.get("/api/v1/tasks/my")
        print("Tasks my HTTP:", tasks_res.status_code)
        if tasks_res.status_code == 200:
            tasks_list = tasks_res.json()
            if isinstance(tasks_list, list) and len(tasks_list) > 0:
                first_task = tasks_list[0]
                task_id = first_task["id"]
                print(f"Testing messages for task {task_id} ({first_task.get('task_number')})...")
                msg_res = await client.get(f"/api/v1/tasks/{task_id}/messages")
                print("Messages HTTP:", msg_res.status_code)
                if msg_res.status_code == 200:
                    print("Messages count:", len(msg_res.json()))
                else:
                    print("Messages error:", msg_res.text)

if __name__ == "__main__":
    asyncio.run(test_live_server())
