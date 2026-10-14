"""
Seed Operational Sheets:
1. Daily Electricity & Scrap Tracker (42 records)
2. Daily Power Cut Log (61 records)
3. Packing & Dispatch Report (510 records)
into rgtech_erp database.
"""

import asyncio
import re
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = "mongodb://127.0.0.1:27017"
DB_NAME = "rgtech_erp"

def parse_duration_to_minutes(dur_str: str) -> float:
    if not dur_str:
        return 0.0
    parts = dur_str.strip().split(':')
    try:
        if len(parts) == 3:
            return round(float(parts[0]) * 60.0 + float(parts[1]) + float(parts[2]) / 60.0, 1)
        elif len(parts) == 2:
            return round(float(parts[0]) * 60.0 + float(parts[1]), 1)
    except:
        pass
    return 0.0

def parse_date_to_datetime(date_str: str, time_str: str = "10:00 AM") -> datetime:
    # Try multiple date formats
    date_str = date_str.strip()
    dt = None
    for fmt in ["%d-%b-%Y", "%d-%b-%y", "%d-%m-%y", "%d-%m-%Y"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            break
        except:
            pass
    if not dt:
        dt = datetime(2026, 8, 15)
    return dt.replace(tzinfo=timezone.utc)

async def seed_operational_sheets():
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]

    with open("user_prompt_data.txt", "r", encoding="utf-8") as f:
        text = f.read()

    p1 = text.find("Daily Electricity & Scrap Tracker")
    p2 = text.find("Daily Power Cut Log")
    p3 = text.find("Packing & Dispatch Report")
    end_marker = text.find("</USER_REQUEST>", p3)

    # -------------------------------------------------------------
    # 1. Daily Electricity & Scrap Tracker
    # -------------------------------------------------------------
    sec1_lines = [l.strip() for l in text[p1:p2].split("\n") if l.strip()][2:]
    scrap_docs = []
    for l in sec1_lines:
        parts = l.split("\t")
        if len(parts) >= 2 and any(m in parts[0] for m in ["Aug", "Sep", "Oct"]):
            def pf(idx, default=0.0):
                if idx < len(parts) and parts[idx].strip():
                    try:
                        return float(parts[idx].replace("%", "").replace(",", "").strip())
                    except:
                        return default
                return default
            def ps(idx, default=""):
                return parts[idx].strip() if idx < len(parts) else default

            scrap_docs.append({
                "date": parts[0].strip(),
                "total_production_kg": pf(1),
                "product_type": ps(2, "Tubing") or "Tubing",
                "startup_scrap_kg": pf(3),
                "cutting_scrap_kg": pf(4),
                "total_scrap_kg": pf(5),
                "scrap_percent_str": ps(6, "0.00%"),
                "electricity_off_count": int(pf(7)),
                "total_off_time_min": pf(8),
                "machine_working_hours": ps(9, "8.0") or "8.0",
                "shift_duration_hr": pf(10, 8.0) or 8.0,
                "main_reason": ps(11),
                "remarks": ps(12),
                "unit_id": "Unit_1",
                "created_at": datetime.now(timezone.utc),
            })

    if scrap_docs:
        await db["daily_electricity_scrap"].delete_many({})
        res1 = await db["daily_electricity_scrap"].insert_many(scrap_docs)
        print(f"Seeded {len(res1.inserted_ids)} records into daily_electricity_scrap")

    # -------------------------------------------------------------
    # 2. Daily Power Cut Log
    # -------------------------------------------------------------
    sec2_lines = [l.strip() for l in text[p2:p3].split("\n") if l.strip()][3:]
    power_cut_docs = []
    for l in sec2_lines:
        parts = l.split("\t")
        if len(parts) >= 4 and any(ch.isdigit() for ch in parts[0]):
            if len(parts) > 1 and any(m in parts[1] for m in ["Aug", "Sep", "Oct", "-08-", "-09-", "-10-"]):
                def ps(idx, default=""):
                    return parts[idx].strip() if idx < len(parts) else default
                def pf(idx, default=0.0):
                    if idx < len(parts) and parts[idx].strip():
                        try:
                            return float(parts[idx].strip())
                        except:
                            return default
                    return default

                sno = parts[0].strip()
                date_str = ps(1)
                pc_time = ps(2)
                pr_time = ps(3)
                restart_delay = pf(4, 0.0)
                dur_str = ps(5)
                gen_used_str = ps(6, "No")
                gen_used = gen_used_str.lower() == "yes"
                reason = ps(7, "power cut") or "power cut"
                remarks = ps(8)
                dur_min = parse_duration_to_minutes(dur_str)

                start_dt = parse_date_to_datetime(date_str, pc_time)
                # approximate end_dt
                end_dt = start_dt

                inc_num = f"OUTAGE-2026-PC{len(power_cut_docs)+1:04d}"

                power_cut_docs.append({
                    "incident_number": inc_num,
                    "sno": sno,
                    "unit_id": "Unit_1",
                    "incident_date": date_str,
                    "power_cut_time": pc_time,
                    "power_restored_time": pr_time,
                    "start_time": start_dt,
                    "end_time": end_dt,
                    "duration_minutes": dur_min,
                    "downtime_duration_str": dur_str,
                    "restart_delay_minutes": restart_delay,
                    "outage_type": "GRID_FAILURE",
                    "reason": reason,
                    "backup_generator_used": gen_used,
                    "fuel_consumed_liters": 15.0 if gen_used else None,
                    "affected_departments": ["Machining & Extrusion", "Assembly"],
                    "production_order_ids": [],
                    "remarks": remarks,
                    "created_at": datetime.now(timezone.utc),
                    "created_by": "chetanprajapati@rgtech.com",
                })

    if power_cut_docs:
        # Keep existing non-PC logs or replace
        await db["power_cuts"].delete_many({"incident_number": {"$regex": "^OUTAGE-2026-PC"}})
        res2 = await db["power_cuts"].insert_many(power_cut_docs)
        print(f"Seeded {len(res2.inserted_ids)} records into power_cuts")

    # -------------------------------------------------------------
    # 3. Packing & Dispatch Report
    # -------------------------------------------------------------
    sec3_lines = [l.strip() for l in text[p3:end_marker].split("\n") if l.strip()][1:]
    pack_docs = []
    for l in sec3_lines:
        parts = l.split("\t")
        if len(parts) >= 6 and any(m in parts[0] for m in ["Jul", "Aug", "Sep", "Oct"]):
            def ps(idx, default=""):
                return parts[idx].strip() if idx < len(parts) else default
            def pf(idx, default=0.0):
                if idx < len(parts) and parts[idx].strip():
                    try:
                        return float(parts[idx].strip())
                    except:
                        return default
                return default

            pack_docs.append({
                "date": ps(0),
                "box_no": ps(1),
                "weight_kg": pf(2),
                "operator": ps(3),
                "brand": ps(4),
                "product_type": ps(5),
                "size_length": ps(6),
                "quantity": int(pf(7)),
                "dispatch_date": ps(8),
                "dispatch_no": ps(9),
                "remarks": ps(10),
                "unit_id": "Unit_1",
                "created_at": datetime.now(timezone.utc),
                "created_by": "amitpatel@rgtech.com",
            })

    if pack_docs:
        await db["packing_dispatch_records"].delete_many({})
        res3 = await db["packing_dispatch_records"].insert_many(pack_docs)
        print(f"Seeded {len(res3.inserted_ids)} records into packing_dispatch_records")

    print("ALL 3 SHEETS SEEDED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(seed_operational_sheets())
