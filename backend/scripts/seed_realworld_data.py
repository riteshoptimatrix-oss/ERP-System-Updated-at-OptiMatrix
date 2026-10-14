"""
Opti Matrix ERP — Real-World Data Seeding Script
File: backend/scripts/seed_realworld_data.py

Seeds realistic manufacturing ERP data across all departments:
  - Master Data: Customers, Vendors, Finished Products, Raw Materials,
                 UoMs, Warehouses, Categories
  - BOM (Bill of Materials) with components
  - HR: Shift configs, Attendance records, Leave applications
  - Payroll: Salary structures, Payroll runs
  - Inventory: Opening stock balances
  - Production: Production orders
  - Sales: Sales orders
  - Finance: Chart of Accounts, Invoices, Supplier Bills, Expenses

Usage:
    python scripts/seed_realworld_data.py            # Seed all data
    python scripts/seed_realworld_data.py --cleanup  # Remove seeded data only
"""

import sys
import os
import argparse
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
import motor.motor_asyncio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
NOW = datetime.now(timezone.utc)
ADMIN = "admin@rgtech.com"
SEED_TAG = "realworld_seed_v1"


def ts(days_offset: int = 0) -> datetime:
    return NOW - timedelta(days=days_offset)


def date_str(days_offset: int = 0) -> str:
    return (NOW - timedelta(days=days_offset)).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# 1. CATEGORIES
# ---------------------------------------------------------------------------
CATEGORIES: List[Dict[str, Any]] = [
    {"code": "CAT-RAW-STEEL",   "name": "Steel & Metal",               "category_type": "RAW_MATERIAL",     "description": "MS plates, SS rods, CI castings"},
    {"code": "CAT-RAW-POLYMER", "name": "Polymers & Rubber",           "category_type": "RAW_MATERIAL",     "description": "Engineering plastics and rubber gaskets"},
    {"code": "CAT-RAW-ELEC",    "name": "Electrical Components",       "category_type": "RAW_MATERIAL",     "description": "Motors, capacitors, wiring harnesses"},
    {"code": "CAT-RAW-CONS",    "name": "Consumables & Chemicals",     "category_type": "CONSUMABLE",       "description": "Cutting oils, welding rods, abrasives"},
    {"code": "CAT-FP-ENV",      "name": "Industrial Envelope Machines","category_type": "FINISHED_PRODUCT", "description": "Paper envelope manufacturing machines"},
    {"code": "CAT-FP-PKG",      "name": "Packaging Machines",          "category_type": "FINISHED_PRODUCT", "description": "Automated carton & blister pack machines"},
    {"code": "CAT-SPARE",       "name": "Spare Parts",                 "category_type": "SPARES",           "description": "Maintenance spare parts inventory"},
]

# ---------------------------------------------------------------------------
# 2. UoM MASTER
# ---------------------------------------------------------------------------
UOMS: List[Dict[str, Any]] = [
    {"code": "KG",  "name": "Kilogram", "symbol": "kg",  "description": "Weight – kilograms"},
    {"code": "MTR", "name": "Metre",    "symbol": "m",   "description": "Length – metres"},
    {"code": "PCS", "name": "Pieces",   "symbol": "pcs", "description": "Countable units"},
    {"code": "LTR", "name": "Litre",    "symbol": "L",   "description": "Volume – litres"},
    {"code": "NOS", "name": "Numbers",  "symbol": "nos", "description": "Numbers / count"},
    {"code": "SET", "name": "Set",      "symbol": "set", "description": "Bundled set"},
    {"code": "ROL", "name": "Roll",     "symbol": "rol", "description": "Roll of material"},
    {"code": "BOX", "name": "Box",      "symbol": "box", "description": "Packaged box"},
]

# ---------------------------------------------------------------------------
# 3. WAREHOUSES
# ---------------------------------------------------------------------------
WAREHOUSES: List[Dict[str, Any]] = [
    {"code": "WH-U1-RM01", "name": "Unit-1 Raw Material Store A", "unit_id": "Unit_1", "location_type": "RAW_MATERIAL",   "bay_rack": "Bay-A, Racks 1-10", "capacity_description": "Heavy raw materials, steel & plates"},
    {"code": "WH-U1-RM02", "name": "Unit-1 Raw Material Store B", "unit_id": "Unit_1", "location_type": "RAW_MATERIAL",   "bay_rack": "Bay-B, Racks 1-8",  "capacity_description": "Electrical components & polymers"},
    {"code": "WH-U1-WIP",  "name": "Unit-1 WIP Staging Area",     "unit_id": "Unit_1", "location_type": "WIP",            "bay_rack": "Bay-C",             "capacity_description": "Sub-assemblies & WIP"},
    {"code": "WH-U1-FG01", "name": "Unit-1 Finished Goods Store", "unit_id": "Unit_1", "location_type": "FINISHED_GOODS", "bay_rack": "Bay-D, Racks 1-12", "capacity_description": "Envelope machines, tested & packed"},
    {"code": "WH-U1-SCRAP","name": "Unit-1 Scrap & Reject Yard",  "unit_id": "Unit_1", "location_type": "SCRAP",          "bay_rack": "Yard-E",            "capacity_description": "Rejection & scrap material"},
    {"code": "WH-U2-RM01", "name": "Unit-2 Raw Material Store A", "unit_id": "Unit_2", "location_type": "RAW_MATERIAL",   "bay_rack": "Bay-A, Racks 1-10", "capacity_description": "Steel, CI castings"},
    {"code": "WH-U2-RM02", "name": "Unit-2 Raw Material Store B", "unit_id": "Unit_2", "location_type": "RAW_MATERIAL",   "bay_rack": "Bay-B, Racks 1-6",  "capacity_description": "Rubber, plastics, consumables"},
    {"code": "WH-U2-FG01", "name": "Unit-2 Finished Goods Store", "unit_id": "Unit_2", "location_type": "FINISHED_GOODS", "bay_rack": "Bay-C, Racks 1-10", "capacity_description": "Packaging machines, ready for dispatch"},
    {"code": "WH-U2-SCRAP","name": "Unit-2 Scrap Yard",           "unit_id": "Unit_2", "location_type": "SCRAP",          "bay_rack": "Yard-D",            "capacity_description": "Scrap & waste"},
]

# ---------------------------------------------------------------------------
# 4. RAW MATERIALS
# ---------------------------------------------------------------------------
RAW_MATERIALS: List[Dict[str, Any]] = [
    {"code": "RM-MS-PLATE-6MM",  "name": "MS Plate 6mm",              "category_id": "CAT-RAW-STEEL",   "uom": "KG",  "hsn_code": "72085100", "reorder_level": 1000.0, "safety_stock": 500.0, "description": "Mild Steel Plate 6mm thickness IS:2062"},
    {"code": "RM-MS-PLATE-10MM", "name": "MS Plate 10mm",             "category_id": "CAT-RAW-STEEL",   "uom": "KG",  "hsn_code": "72085100", "reorder_level": 800.0,  "safety_stock": 400.0, "description": "Mild Steel Plate 10mm thickness IS:2062"},
    {"code": "RM-SS-ROD-20MM",   "name": "SS Round Bar 20mm",         "category_id": "CAT-RAW-STEEL",   "uom": "KG",  "hsn_code": "72221900", "reorder_level": 300.0,  "safety_stock": 150.0, "description": "Stainless Steel 304 Round Bar 20mm"},
    {"code": "RM-CI-CAST-001",   "name": "CI Body Casting",           "category_id": "CAT-RAW-STEEL",   "uom": "NOS", "hsn_code": "73259100", "reorder_level": 50.0,   "safety_stock": 25.0,  "description": "Cast Iron Machine Body Casting Rough"},
    {"code": "RM-MS-CHANNEL",    "name": "MS Channel 100x50",         "category_id": "CAT-RAW-STEEL",   "uom": "MTR", "hsn_code": "72162100", "reorder_level": 200.0,  "safety_stock": 100.0, "description": "MS Structural Channel 100x50mm IS:808"},
    {"code": "RM-MOTOR-0.5HP",   "name": "AC Induction Motor 0.5 HP","category_id": "CAT-RAW-ELEC",    "uom": "NOS", "hsn_code": "85011000", "reorder_level": 20.0,   "safety_stock": 10.0,  "description": "Single Phase AC Motor 0.5 HP 1440 RPM"},
    {"code": "RM-MOTOR-1HP",     "name": "AC Induction Motor 1 HP",  "category_id": "CAT-RAW-ELEC",    "uom": "NOS", "hsn_code": "85011000", "reorder_level": 15.0,   "safety_stock": 8.0,   "description": "Single Phase AC Motor 1 HP 1440 RPM"},
    {"code": "RM-BEARING-6205",  "name": "Ball Bearing 6205 ZZ",     "category_id": "CAT-RAW-ELEC",    "uom": "NOS", "hsn_code": "84821000", "reorder_level": 100.0,  "safety_stock": 50.0,  "description": "Deep groove ball bearing 6205 ZZ"},
    {"code": "RM-CAPACITOR-25",  "name": "Run Capacitor 25uF",       "category_id": "CAT-RAW-ELEC",    "uom": "NOS", "hsn_code": "85322990", "reorder_level": 50.0,   "safety_stock": 25.0,  "description": "Motor run capacitor 25uF 440V"},
    {"code": "RM-RUBBER-GSKT",   "name": "Rubber Gasket Strip 3mm",  "category_id": "CAT-RAW-POLYMER", "uom": "MTR", "hsn_code": "40081100", "reorder_level": 500.0,  "safety_stock": 200.0, "description": "Natural Rubber Gasket Strip 3mm thick"},
    {"code": "RM-NYLON-BUSH",    "name": "Nylon Bush 20mm ID",        "category_id": "CAT-RAW-POLYMER", "uom": "NOS", "hsn_code": "39262090", "reorder_level": 200.0,  "safety_stock": 100.0, "description": "Engineering Nylon PA6 Bush 20mm ID x 30mm OD"},
    {"code": "RM-WELD-ROD-E6013","name": "Welding Rod E6013 3.15mm", "category_id": "CAT-RAW-CONS",    "uom": "KG",  "hsn_code": "83111000", "reorder_level": 50.0,   "safety_stock": 20.0,  "description": "AWS E6013 General purpose welding electrodes"},
    {"code": "RM-CUTTING-OIL",   "name": "Cutting & Coolant Oil",    "category_id": "CAT-RAW-CONS",    "uom": "LTR", "hsn_code": "27101940", "reorder_level": 200.0,  "safety_stock": 100.0, "description": "Servo-cut S cutting oil for machining"},
    {"code": "RM-PAINT-GREY",    "name": "Industrial Grey Paint",    "category_id": "CAT-RAW-CONS",    "uom": "LTR", "hsn_code": "32089090", "reorder_level": 50.0,   "safety_stock": 20.0,  "description": "Synthetic enamel machine grey paint"},
]

# ---------------------------------------------------------------------------
# 5. FINISHED PRODUCTS
# ---------------------------------------------------------------------------
FINISHED_PRODUCTS: List[Dict[str, Any]] = [
    {"code": "FP-ENV-100",  "name": "Envelope Making Machine ENV-100",  "category_id": "CAT-FP-ENV", "uom": "PCS", "drawing_no": "DWG-ENV-100-R3",  "revision_no": "R3", "standard_cost": 185000.0, "selling_price": 245000.0, "min_stock_level": 2.0, "description": "Semi-automatic envelope machine 100 env/min"},
    {"code": "FP-ENV-200",  "name": "Envelope Making Machine ENV-200",  "category_id": "CAT-FP-ENV", "uom": "PCS", "drawing_no": "DWG-ENV-200-R2",  "revision_no": "R2", "standard_cost": 310000.0, "selling_price": 415000.0, "min_stock_level": 1.0, "description": "Fully automatic envelope machine 200 env/min"},
    {"code": "FP-PKG-300",  "name": "Carton Packing Machine PKG-300",   "category_id": "CAT-FP-PKG", "uom": "PCS", "drawing_no": "DWG-PKG-300-R1",  "revision_no": "R1", "standard_cost": 420000.0, "selling_price": 565000.0, "min_stock_level": 1.0, "description": "Automated carton packing machine 30 cartons/min"},
    {"code": "FP-ENV-MINI", "name": "Mini Envelope Machine ENV-MINI",   "category_id": "CAT-FP-ENV", "uom": "PCS", "drawing_no": "DWG-ENV-MINI-R1", "revision_no": "R1", "standard_cost": 95000.0,  "selling_price": 128000.0, "min_stock_level": 3.0, "description": "Desktop mini envelope machine 50 env/min"},
]

# ---------------------------------------------------------------------------
# 6. CUSTOMERS
# ---------------------------------------------------------------------------
CUSTOMERS: List[Dict[str, Any]] = [
    {"code": "CUST-001", "name": "Ravi Stationery Pvt Ltd",        "gstin": "24AAACR1234C1Z5", "pan": "AAACR1234C", "contact_person": "Ravi Mehta",     "phone": "+91 79 2234 5678", "email": "purchase@ravistat.com",    "billing_address": "12 Navrangpura, Ahmedabad - 380009, Gujarat",        "shipping_address": "12 Navrangpura, Ahmedabad - 380009, Gujarat",        "credit_limit": 1500000.0, "payment_terms_days": 45, "unit_id": "Unit_1"},
    {"code": "CUST-002", "name": "National Paper Industries",       "gstin": "27AAACN5678D1Z3", "pan": "AAACN5678D", "contact_person": "Deepa Shetty",    "phone": "+91 22 6654 3210", "email": "orders@npi.in",             "billing_address": "Saki Vihar Road, Andheri East, Mumbai - 400072, MH", "shipping_address": "Saki Vihar Road, Andheri East, Mumbai - 400072, MH", "credit_limit": 2500000.0, "payment_terms_days": 30, "unit_id": "BOTH"},
    {"code": "CUST-003", "name": "Bengaluru Office Supplies Ltd",   "gstin": "29AAACB2345E1Z7", "pan": "AAACB2345E", "contact_person": "Sunil Kumar",     "phone": "+91 80 4155 6789", "email": "procurement@bosltd.in",    "billing_address": "Koramangala 5th Block, Bengaluru - 560034, KA",      "shipping_address": "Peenya Industrial Area, Bengaluru - 560058, KA",    "credit_limit": 1000000.0, "payment_terms_days": 30, "unit_id": "Unit_2"},
    {"code": "CUST-004", "name": "Delhi Packaging Solutions",       "gstin": "07AAACD3456F1Z1", "pan": "AAACD3456F", "contact_person": "Anil Sharma",     "phone": "+91 11 4567 8901", "email": "anil@dps-delhi.com",        "billing_address": "Okhla Industrial Phase II, New Delhi - 110020",       "shipping_address": "Okhla Industrial Phase II, New Delhi - 110020",       "credit_limit": 800000.0,  "payment_terms_days": 45, "unit_id": "Unit_1"},
    {"code": "CUST-005", "name": "Hyderabad Print & Pack Co.",      "gstin": "36AAACH4567G1Z9", "pan": "AAACH4567G", "contact_person": "Padma Reddy",     "phone": "+91 40 6678 9012", "email": "padma@hppc.in",             "billing_address": "IDA Jeedimetla, Hyderabad - 500055, TS",              "shipping_address": "IDA Jeedimetla, Hyderabad - 500055, TS",              "credit_limit": 750000.0,  "payment_terms_days": 60, "unit_id": "BOTH"},
    {"code": "CUST-006", "name": "Pune Industrial Traders",         "gstin": "27AAACP5678H1Z5", "pan": "AAACP5678H", "contact_person": "Ashish Joshi",    "phone": "+91 20 2567 3456", "email": "ashish@puneindustrial.com", "billing_address": "Bhosari MIDC, Pune - 411026, MH",                    "shipping_address": "Bhosari MIDC, Pune - 411026, MH",                    "credit_limit": 600000.0,  "payment_terms_days": 30, "unit_id": "Unit_1"},
    {"code": "CUST-007", "name": "Chennai Office Machines Pvt Ltd", "gstin": "33AAACM6789I1Z3", "pan": "AAACM6789I", "contact_person": "Karthik Raja",    "phone": "+91 44 2823 5678", "email": "karthik@comachines.in",     "billing_address": "Ambattur Industrial Estate, Chennai - 600058, TN",   "shipping_address": "Ambattur Industrial Estate, Chennai - 600058, TN",   "credit_limit": 900000.0,  "payment_terms_days": 45, "unit_id": "Unit_2"},
]

# ---------------------------------------------------------------------------
# 7. VENDORS / SUPPLIERS
# ---------------------------------------------------------------------------
VENDORS: List[Dict[str, Any]] = [
    {"code": "VEND-001", "name": "Jindal Steel & Power Ltd",     "gstin": "09AAACJ1234A1Z5", "pan": "AAACJ1234A", "contact_person": "Ramesh Gupta",   "phone": "+91 11 4105 6000", "email": "sales@jindal.com",       "address": "Plot 12, Sector 25, Noida - 201301, UP",          "payment_terms_days": 30, "category": "Raw Material", "rating": 4.8},
    {"code": "VEND-002", "name": "Bharat Electrical Motors",     "gstin": "27AAACB2345B1Z3", "pan": "AAACB2345B", "contact_person": "Pradeep Vora",   "phone": "+91 22 2579 3456", "email": "orders@bharatemotors.com","address": "LBS Road, Kurla West, Mumbai - 400070, MH",       "payment_terms_days": 45, "category": "Raw Material", "rating": 4.5},
    {"code": "VEND-003", "name": "Ahmedabad Rubber Products",    "gstin": "24AAACA3456C1Z7", "pan": "AAACA3456C", "contact_person": "Bhavesh Patel",  "phone": "+91 79 2240 5678", "email": "bhavesh@arpindia.com",   "address": "Naroda GIDC, Ahmedabad - 382330, Gujarat",        "payment_terms_days": 30, "category": "Raw Material", "rating": 4.2},
    {"code": "VEND-004", "name": "Indian Welding & Consumables", "gstin": "24AAACI4567D1Z1", "pan": "AAACI4567D", "contact_person": "Mahesh Shah",    "phone": "+91 79 2250 1234", "email": "mahesh@iwelding.in",     "address": "Vatva GIDC Phase-2, Ahmedabad - 382445, Gujarat", "payment_terms_days": 30, "category": "Consumable",   "rating": 4.0},
    {"code": "VEND-005", "name": "SKF India Ltd",                "gstin": "24AAACS5678E1Z9", "pan": "AAACS5678E", "contact_person": "Neerav Jain",    "phone": "+91 79 2657 3000", "email": "neerav@skfindia.com",    "address": "Khatodara, Surat - 395003, Gujarat",              "payment_terms_days": 60, "category": "Raw Material", "rating": 4.9},
    {"code": "VEND-006", "name": "Reliance Petro Lubricants",    "gstin": "27AAACRP678F1Z5", "pan": "AAACRP678F", "contact_person": "Sangeeta Nair",  "phone": "+91 22 4477 0000", "email": "lubricants@ril.com",     "address": "Ghansoli, Navi Mumbai - 400701, MH",              "payment_terms_days": 30, "category": "Consumable",   "rating": 4.3},
    {"code": "VEND-007", "name": "Gujarat Castings Pvt Ltd",     "gstin": "24AAACG7890G1Z1", "pan": "AAACG7890G", "contact_person": "Yogesh Trivedi", "phone": "+91 265 2341567",  "email": "yogesh@gujcastings.com", "address": "Makarpura GIDC, Vadodara - 390010, Gujarat",      "payment_terms_days": 45, "category": "Raw Material", "rating": 4.4},
]

# ---------------------------------------------------------------------------
# 8. CHART OF ACCOUNTS
# ---------------------------------------------------------------------------
ACCOUNTS: List[Dict[str, Any]] = [
    {"account_code": "1010-BANK-HDFC",             "name": "HDFC Bank - Current Account",    "account_type": "ASSET",     "description": "Primary operating bank account HDFC"},
    {"account_code": "1011-BANK-SBI",              "name": "SBI Bank - Current Account",     "account_type": "ASSET",     "description": "Secondary bank account SBI"},
    {"account_code": "1020-PETTY-CASH",            "name": "Petty Cash",                     "account_type": "ASSET",     "description": "On-hand petty cash"},
    {"account_code": "1100-AR",                    "name": "Accounts Receivable",            "account_type": "ASSET",     "description": "Customer outstanding receivables"},
    {"account_code": "1200-RAW-MATERIAL-INVENTORY","name": "Raw Material Inventory",         "account_type": "ASSET",     "description": "Value of raw material stock"},
    {"account_code": "1210-FINISHED-GOODS-INVENTORY","name": "Finished Goods Inventory",    "account_type": "ASSET",     "description": "Value of finished goods stock"},
    {"account_code": "1300-ADVANCE-TO-VENDORS",    "name": "Advances to Vendors",            "account_type": "ASSET",     "description": "Advance payments made to suppliers"},
    {"account_code": "1500-PLANT-MACHINERY",       "name": "Plant & Machinery (Gross)",      "account_type": "ASSET",     "description": "Fixed asset - manufacturing plant & machinery"},
    {"account_code": "1510-ACCUM-DEPRECIATION",    "name": "Accumulated Depreciation",       "account_type": "ASSET",     "description": "Accumulated depreciation on fixed assets"},
    {"account_code": "2100-AP",                    "name": "Accounts Payable",               "account_type": "LIABILITY", "description": "Vendor / supplier outstanding payables"},
    {"account_code": "2200-GST-OUTPUT",            "name": "GST Output Tax Payable",         "account_type": "LIABILITY", "description": "GST collected on sales"},
    {"account_code": "2210-GST-INPUT",             "name": "GST Input Tax Credit",           "account_type": "LIABILITY", "description": "GST paid on purchases (ITC)"},
    {"account_code": "2300-PF-PAYABLE",            "name": "Provident Fund Payable",         "account_type": "LIABILITY", "description": "Employee & employer PF contribution payable"},
    {"account_code": "2310-ESI-PAYABLE",           "name": "ESI Payable",                    "account_type": "LIABILITY", "description": "ESI contribution payable"},
    {"account_code": "2320-TDS-PAYABLE",           "name": "TDS Payable",                    "account_type": "LIABILITY", "description": "Tax deducted at source payable"},
    {"account_code": "2400-SALARY-PAYABLE",        "name": "Salaries & Wages Payable",       "account_type": "LIABILITY", "description": "Net salaries payable to employees"},
    {"account_code": "3000-SHARE-CAPITAL",         "name": "Share Capital",                  "account_type": "EQUITY",    "description": "Paid-up equity share capital"},
    {"account_code": "3100-RETAINED-EARNINGS",     "name": "Retained Earnings",              "account_type": "EQUITY",    "description": "Accumulated profits retained"},
    {"account_code": "4000-SALES-REVENUE",         "name": "Sales Revenue - Machines",       "account_type": "REVENUE",   "description": "Revenue from machine sales"},
    {"account_code": "4010-SERVICE-REVENUE",       "name": "Service & AMC Revenue",           "account_type": "REVENUE",   "description": "Revenue from after-sales service & AMC"},
    {"account_code": "5000-COGS",                  "name": "Cost of Goods Sold",             "account_type": "EXPENSE",   "description": "Direct manufacturing cost"},
    {"account_code": "5100-SALARY-EXPENSE",        "name": "Salaries & Wages",               "account_type": "EXPENSE",   "description": "Employee salary cost"},
    {"account_code": "5200-MATERIAL-EXPENSE",      "name": "Raw Material Consumed",          "account_type": "EXPENSE",   "description": "RM consumed in production"},
    {"account_code": "5300-OPERATING-EXPENSES",    "name": "Operating Expenses",             "account_type": "EXPENSE",   "description": "General overhead & operating expenses"},
    {"account_code": "5310-ELECTRICITY",           "name": "Electricity & Utilities",        "account_type": "EXPENSE",   "description": "Power & utility charges"},
    {"account_code": "5320-FREIGHT-EXPENSE",       "name": "Freight & Logistics",            "account_type": "EXPENSE",   "description": "Outward & inward freight charges"},
    {"account_code": "5330-REPAIRS-MAINT",         "name": "Repairs & Maintenance",          "account_type": "EXPENSE",   "description": "Plant & machinery repair charges"},
    {"account_code": "5400-DEPRECIATION-EXP",      "name": "Depreciation Expense",           "account_type": "EXPENSE",   "description": "Annual depreciation on fixed assets"},
]

# ---------------------------------------------------------------------------
# 9. SHIFT CONFIGURATIONS
# ---------------------------------------------------------------------------
SHIFT_CONFIGS: List[Dict[str, Any]] = [
    {"shift_code": "SHIFT-GEN",   "name": "General Shift",  "shift_type": "GENERAL", "start_time": "09:00", "end_time": "18:00", "break_duration_minutes": 60, "grace_period_minutes": 15, "standard_work_hours": 8.0, "unit_id": "BOTH"},
    {"shift_code": "SHIFT-MORN",  "name": "Morning Shift",  "shift_type": "SHIFT_1", "start_time": "06:00", "end_time": "14:00", "break_duration_minutes": 30, "grace_period_minutes": 10, "standard_work_hours": 8.0, "unit_id": "BOTH"},
    {"shift_code": "SHIFT-EVE",   "name": "Evening Shift",  "shift_type": "SHIFT_2", "start_time": "14:00", "end_time": "22:00", "break_duration_minutes": 30, "grace_period_minutes": 10, "standard_work_hours": 8.0, "unit_id": "BOTH"},
    {"shift_code": "SHIFT-NIGHT", "name": "Night Shift",    "shift_type": "NIGHT",   "start_time": "22:00", "end_time": "06:00", "break_duration_minutes": 30, "grace_period_minutes": 10, "standard_work_hours": 8.0, "unit_id": "BOTH"},
]


# ---------------------------------------------------------------------------
# Verify environment safety
# ---------------------------------------------------------------------------
def verify_environment_safety():
    env = os.getenv("ENVIRONMENT", settings.ENVIRONMENT).lower()
    if env in ["prod", "production"] or settings.is_production:
        print("[ERROR] Cannot run real-world seeding in production!")
        sys.exit(1)


# ---------------------------------------------------------------------------
# SEED FUNCTIONS
# ---------------------------------------------------------------------------

async def seed_categories(db) -> Dict[str, str]:
    col = db["master_categories"]
    col_std = db["categories"]
    id_map: Dict[str, str] = {}
    for cat in CATEGORIES:
        existing = await col.find_one({"code": cat["code"]})
        if existing:
            id_map[cat["code"]] = str(existing["_id"])
            await col_std.replace_one({"code": cat["code"]}, existing, upsert=True)
            continue
        doc = {**cat, "_seed": SEED_TAG, "is_active": True, "created_at": NOW, "created_by": ADMIN, "updated_at": NOW, "updated_by": ADMIN}
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id
        await col_std.replace_one({"code": cat["code"]}, doc, upsert=True)
        id_map[cat["code"]] = str(res.inserted_id)
        print(f"  [CAT] {cat['code']} - {cat['name']}")
    return id_map


async def seed_uoms(db) -> Dict[str, str]:
    col = db["master_uoms"]
    col_std = db["uom"]
    id_map: Dict[str, str] = {}
    for uom in UOMS:
        existing = await col.find_one({"code": uom["code"]})
        if existing:
            id_map[uom["code"]] = str(existing["_id"])
            await col_std.replace_one({"code": uom["code"]}, existing, upsert=True)
            continue
        doc = {**uom, "_seed": SEED_TAG, "is_active": True, "created_at": NOW, "created_by": ADMIN, "updated_at": NOW, "updated_by": ADMIN}
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id
        await col_std.replace_one({"code": uom["code"]}, doc, upsert=True)
        id_map[uom["code"]] = str(res.inserted_id)
        print(f"  [UOM] {uom['code']} - {uom['name']}")
    return id_map


async def seed_warehouses(db) -> Dict[str, str]:
    col = db["master_warehouses"]
    col_std = db["warehouses"]
    id_map: Dict[str, str] = {}
    for wh in WAREHOUSES:
        existing = await col.find_one({"code": wh["code"]})
        if existing:
            id_map[wh["code"]] = str(existing["_id"])
            await col_std.replace_one({"code": wh["code"]}, existing, upsert=True)
            continue
        doc = {**wh, "_seed": SEED_TAG, "is_active": True, "created_at": NOW, "created_by": ADMIN, "updated_at": NOW, "updated_by": ADMIN}
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id
        await col_std.replace_one({"code": wh["code"]}, doc, upsert=True)
        id_map[wh["code"]] = str(res.inserted_id)
        print(f"  [WH] {wh['code']} - {wh['name']}")
    return id_map


async def seed_raw_materials(db) -> Dict[str, str]:
    col = db["master_raw_materials"]
    col_std = db["raw_materials"]
    id_map: Dict[str, str] = {}
    for rm in RAW_MATERIALS:
        existing = await col.find_one({"code": rm["code"]})
        if existing:
            id_map[rm["code"]] = str(existing["_id"])
            await col_std.replace_one({"code": rm["code"]}, existing, upsert=True)
            continue
        doc = {**rm, "_seed": SEED_TAG, "unit_id": "BOTH", "is_active": True,
               "created_at": NOW, "created_by": ADMIN, "updated_at": NOW, "updated_by": ADMIN}
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id
        await col_std.replace_one({"code": rm["code"]}, doc, upsert=True)
        id_map[rm["code"]] = str(res.inserted_id)
        print(f"  [RM] {rm['code']} - {rm['name']}")
    return id_map


async def seed_finished_products(db) -> Dict[str, str]:
    col = db["master_finished_products"]
    col_std = db["finished_products"]
    id_map: Dict[str, str] = {}
    for fp in FINISHED_PRODUCTS:
        existing = await col.find_one({"code": fp["code"]})
        if existing:
            id_map[fp["code"]] = str(existing["_id"])
            await col_std.replace_one({"code": fp["code"]}, existing, upsert=True)
            continue
        doc = {**fp, "_seed": SEED_TAG, "unit_id": "BOTH", "is_active": True,
               "created_at": NOW, "created_by": ADMIN, "updated_at": NOW, "updated_by": ADMIN}
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id
        await col_std.replace_one({"code": fp["code"]}, doc, upsert=True)
        id_map[fp["code"]] = str(res.inserted_id)
        print(f"  [FP] {fp['code']} - {fp['name']}")
    return id_map


async def seed_customers(db) -> Dict[str, str]:
    col = db["master_customers"]
    col_std = db["customers"]
    id_map: Dict[str, str] = {}
    for c in CUSTOMERS:
        existing = await col.find_one({"code": c["code"]})
        if existing:
            id_map[c["code"]] = str(existing["_id"])
            await col_std.replace_one({"code": c["code"]}, existing, upsert=True)
            continue
        doc = {**c, "_seed": SEED_TAG, "is_active": True,
               "created_at": NOW, "created_by": ADMIN, "updated_at": NOW, "updated_by": ADMIN}
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id
        await col_std.replace_one({"code": c["code"]}, doc, upsert=True)
        id_map[c["code"]] = str(res.inserted_id)
        print(f"  [CUST] {c['code']} - {c['name']}")
    return id_map


async def seed_vendors(db) -> Dict[str, str]:
    col = db["master_vendors"]
    col_std = db["vendors"]
    id_map: Dict[str, str] = {}
    for v in VENDORS:
        existing = await col.find_one({"code": v["code"]})
        if existing:
            id_map[v["code"]] = str(existing["_id"])
            await col_std.replace_one({"code": v["code"]}, existing, upsert=True)
            continue
        doc = {**v, "_seed": SEED_TAG, "unit_id": "BOTH", "is_active": True,
               "created_at": NOW, "created_by": ADMIN, "updated_at": NOW, "updated_by": ADMIN}
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id
        await col_std.replace_one({"code": v["code"]}, doc, upsert=True)
        id_map[v["code"]] = str(res.inserted_id)
        print(f"  [VEND] {v['code']} - {v['name']}")
    return id_map


async def seed_accounts(db):
    col = db["finance_accounts"]
    for acc in ACCOUNTS:
        existing = await col.find_one({"account_code": acc["account_code"]})
        if existing:
            continue
        doc = {**acc, "_seed": SEED_TAG, "unit_id": "BOTH", "current_balance": 0.0,
               "is_active": True, "created_at": NOW, "created_by": ADMIN}
        await col.insert_one(doc)
        print(f"  [COA] {acc['account_code']} - {acc['name']}")


async def seed_shift_configs(db):
    col = db["hr_shift_configs"]
    for sc in SHIFT_CONFIGS:
        existing = await col.find_one({"shift_code": sc["shift_code"]})
        if existing:
            continue
        doc = {**sc, "_seed": SEED_TAG, "is_active": True, "created_at": NOW, "created_by": ADMIN}
        await col.insert_one(doc)
        print(f"  [SHIFT] {sc['shift_code']} - {sc['name']}")


async def seed_boms(db, rm_id_map: Dict[str, str], fp_id_map: Dict[str, str]) -> Dict[str, str]:
    col = db["boms"]
    id_map: Dict[str, str] = {}

    bom_data = [
        {
            "product_code": "FP-ENV-100",
            "bom_number": "BOM-ENV100-R3",
            "revision_no": "R3",
            "unit_id": "Unit_1",
            "description": "BOM for Envelope Machine ENV-100 Rev 3",
            "components": [
                ("RM-MS-PLATE-6MM",  180.0, "KG",  5.0),
                ("RM-MS-PLATE-10MM", 80.0,  "KG",  4.0),
                ("RM-MS-CHANNEL",    8.0,   "MTR", 3.0),
                ("RM-MOTOR-0.5HP",   2.0,   "NOS", 0.0),
                ("RM-BEARING-6205",  6.0,   "NOS", 0.0),
                ("RM-CAPACITOR-25",  2.0,   "NOS", 0.0),
                ("RM-RUBBER-GSKT",   4.0,   "MTR", 8.0),
                ("RM-NYLON-BUSH",    8.0,   "NOS", 0.0),
                ("RM-WELD-ROD-E6013",2.0,   "KG",  10.0),
                ("RM-CUTTING-OIL",   2.0,   "LTR", 0.0),
                ("RM-PAINT-GREY",    1.5,   "LTR", 5.0),
            ],
        },
        {
            "product_code": "FP-ENV-200",
            "bom_number": "BOM-ENV200-R2",
            "revision_no": "R2",
            "unit_id": "Unit_1",
            "description": "BOM for Envelope Machine ENV-200 Rev 2",
            "components": [
                ("RM-MS-PLATE-6MM",  250.0, "KG",  5.0),
                ("RM-MS-PLATE-10MM", 120.0, "KG",  4.0),
                ("RM-SS-ROD-20MM",   25.0,  "KG",  3.0),
                ("RM-CI-CAST-001",   2.0,   "NOS", 0.0),
                ("RM-MS-CHANNEL",    12.0,  "MTR", 3.0),
                ("RM-MOTOR-1HP",     3.0,   "NOS", 0.0),
                ("RM-BEARING-6205",  10.0,  "NOS", 0.0),
                ("RM-CAPACITOR-25",  3.0,   "NOS", 0.0),
                ("RM-RUBBER-GSKT",   6.0,   "MTR", 8.0),
                ("RM-NYLON-BUSH",    12.0,  "NOS", 0.0),
                ("RM-WELD-ROD-E6013",3.5,   "KG",  10.0),
                ("RM-CUTTING-OIL",   3.0,   "LTR", 0.0),
                ("RM-PAINT-GREY",    2.0,   "LTR", 5.0),
            ],
        },
        {
            "product_code": "FP-PKG-300",
            "bom_number": "BOM-PKG300-R1",
            "revision_no": "R1",
            "unit_id": "Unit_2",
            "description": "BOM for Carton Packing Machine PKG-300",
            "components": [
                ("RM-MS-PLATE-6MM",  320.0, "KG",  5.0),
                ("RM-MS-PLATE-10MM", 150.0, "KG",  4.0),
                ("RM-CI-CAST-001",   4.0,   "NOS", 0.0),
                ("RM-MOTOR-1HP",     4.0,   "NOS", 0.0),
                ("RM-BEARING-6205",  16.0,  "NOS", 0.0),
                ("RM-RUBBER-GSKT",   8.0,   "MTR", 8.0),
                ("RM-WELD-ROD-E6013",5.0,   "KG",  10.0),
                ("RM-CUTTING-OIL",   5.0,   "LTR", 0.0),
                ("RM-PAINT-GREY",    3.0,   "LTR", 5.0),
            ],
        },
        {
            "product_code": "FP-ENV-MINI",
            "bom_number": "BOM-ENVMINI-R1",
            "revision_no": "R1",
            "unit_id": "Unit_1",
            "description": "BOM for Mini Envelope Machine ENV-MINI",
            "components": [
                ("RM-MS-PLATE-6MM",  60.0,  "KG",  5.0),
                ("RM-MS-CHANNEL",    3.0,   "MTR", 3.0),
                ("RM-MOTOR-0.5HP",   1.0,   "NOS", 0.0),
                ("RM-BEARING-6205",  4.0,   "NOS", 0.0),
                ("RM-CAPACITOR-25",  1.0,   "NOS", 0.0),
                ("RM-RUBBER-GSKT",   2.0,   "MTR", 8.0),
                ("RM-WELD-ROD-E6013",0.8,   "KG",  10.0),
                ("RM-PAINT-GREY",    0.8,   "LTR", 5.0),
            ],
        },
    ]

    for bom in bom_data:
        existing = await col.find_one({"bom_number": bom["bom_number"]})
        if existing:
            id_map[bom["bom_number"]] = str(existing["_id"])
            continue

        product_code = bom["product_code"]
        product_id = fp_id_map.get(product_code, product_code)
        product_name = next((fp["name"] for fp in FINISHED_PRODUCTS if fp["code"] == product_code), product_code)

        components_resolved = []
        for (mat_code, net_qty, uom, scrap_pct) in bom["components"]:
            mat_id = rm_id_map.get(mat_code, mat_code)
            mat_name = next((rm["name"] for rm in RAW_MATERIALS if rm["code"] == mat_code), mat_code)
            gross_qty = round(net_qty * (1 + scrap_pct / 100.0), 4)
            components_resolved.append({
                "material_id": mat_id,
                "material_code": mat_code,
                "material_name": mat_name,
                "uom": uom,
                "net_quantity": net_qty,
                "gross_quantity": gross_qty,
                "scrap_percentage": scrap_pct,
                "unit_cost": 0.0,
                "estimated_cost": 0.0,
                "notes": None,
            })

        doc = {
            "_seed": SEED_TAG,
            "bom_number": bom["bom_number"],
            "product_id": product_id,
            "product_code": product_code,
            "product_name": product_name,
            "product_uom": "PCS",
            "unit_id": bom["unit_id"],
            "base_quantity": 1.0,
            "revision_no": bom["revision_no"],
            "status": "APPROVED",
            "is_active": True,
            "description": bom["description"],
            "total_estimated_cost": 0.0,
            "components": components_resolved,
            "approved_by": ADMIN,
            "approved_at": ts(60),
            "created_at": ts(90),
            "created_by": ADMIN,
            "updated_at": ts(60),
            "updated_by": ADMIN,
        }
        res = await col.insert_one(doc)
        id_map[bom["bom_number"]] = str(res.inserted_id)
        print(f"  [BOM] {bom['bom_number']} - {product_code}")

    return id_map


async def seed_inventory(db, rm_id_map: Dict[str, str], fp_id_map: Dict[str, str], wh_id_map: Dict[str, str]):
    col = db["inventory_stock"]

    stock_entries = [
        # Unit 1 Raw Materials
        ("RM-MS-PLATE-6MM",  "RAW_MATERIAL", "WH-U1-RM01", "Unit_1", 2500.0, 58.0),
        ("RM-MS-PLATE-10MM", "RAW_MATERIAL", "WH-U1-RM01", "Unit_1", 1800.0, 62.0),
        ("RM-SS-ROD-20MM",   "RAW_MATERIAL", "WH-U1-RM01", "Unit_1", 450.0,  195.0),
        ("RM-CI-CAST-001",   "RAW_MATERIAL", "WH-U1-RM01", "Unit_1", 80.0,   3500.0),
        ("RM-MS-CHANNEL",    "RAW_MATERIAL", "WH-U1-RM01", "Unit_1", 320.0,  145.0),
        ("RM-MOTOR-0.5HP",   "RAW_MATERIAL", "WH-U1-RM02", "Unit_1", 35.0,   2800.0),
        ("RM-MOTOR-1HP",     "RAW_MATERIAL", "WH-U1-RM02", "Unit_1", 28.0,   4200.0),
        ("RM-BEARING-6205",  "RAW_MATERIAL", "WH-U1-RM02", "Unit_1", 180.0,  185.0),
        ("RM-CAPACITOR-25",  "RAW_MATERIAL", "WH-U1-RM02", "Unit_1", 95.0,   120.0),
        ("RM-RUBBER-GSKT",   "RAW_MATERIAL", "WH-U1-RM02", "Unit_1", 650.0,  38.0),
        ("RM-NYLON-BUSH",    "RAW_MATERIAL", "WH-U1-RM02", "Unit_1", 280.0,  45.0),
        ("RM-WELD-ROD-E6013","RAW_MATERIAL", "WH-U1-RM02", "Unit_1", 85.0,   110.0),
        ("RM-CUTTING-OIL",   "RAW_MATERIAL", "WH-U1-RM02", "Unit_1", 320.0,  95.0),
        ("RM-PAINT-GREY",    "RAW_MATERIAL", "WH-U1-RM02", "Unit_1", 75.0,   210.0),
        # Unit 2 Raw Materials
        ("RM-MS-PLATE-6MM",  "RAW_MATERIAL", "WH-U2-RM01", "Unit_2", 1800.0, 58.0),
        ("RM-MS-PLATE-10MM", "RAW_MATERIAL", "WH-U2-RM01", "Unit_2", 1200.0, 62.0),
        ("RM-CI-CAST-001",   "RAW_MATERIAL", "WH-U2-RM01", "Unit_2", 60.0,   3500.0),
        ("RM-MOTOR-1HP",     "RAW_MATERIAL", "WH-U2-RM02", "Unit_2", 22.0,   4200.0),
        ("RM-BEARING-6205",  "RAW_MATERIAL", "WH-U2-RM02", "Unit_2", 150.0,  185.0),
        ("RM-RUBBER-GSKT",   "RAW_MATERIAL", "WH-U2-RM02", "Unit_2", 420.0,  38.0),
        ("RM-WELD-ROD-E6013","RAW_MATERIAL", "WH-U2-RM02", "Unit_2", 60.0,   110.0),
        # Finished Goods
        ("FP-ENV-100",       "FINISHED_GOOD","WH-U1-FG01", "Unit_1", 5.0,    185000.0),
        ("FP-ENV-200",       "FINISHED_GOOD","WH-U1-FG01", "Unit_1", 3.0,    310000.0),
        ("FP-ENV-MINI",      "FINISHED_GOOD","WH-U1-FG01", "Unit_1", 8.0,    95000.0),
        ("FP-PKG-300",       "FINISHED_GOOD","WH-U2-FG01", "Unit_2", 2.0,    420000.0),
    ]

    for (item_code, item_type, wh_code, unit_id, qty, unit_cost) in stock_entries:
        existing = await col.find_one({"item_code": item_code, "warehouse_code": wh_code, "unit_id": unit_id})
        if existing:
            continue

        item_id = rm_id_map.get(item_code) or fp_id_map.get(item_code, item_code)
        wh_id = wh_id_map.get(wh_code, wh_code)
        item_name = (
            next((r["name"] for r in RAW_MATERIALS if r["code"] == item_code), None)
            or next((f["name"] for f in FINISHED_PRODUCTS if f["code"] == item_code), item_code)
        )
        uom = (
            next((r["uom"] for r in RAW_MATERIALS if r["code"] == item_code), None)
            or next((f["uom"] for f in FINISHED_PRODUCTS if f["code"] == item_code), "PCS")
        )
        reorder = next((r.get("reorder_level", 0) for r in RAW_MATERIALS if r["code"] == item_code), 0.0)
        safety = next((r.get("safety_stock", 0) for r in RAW_MATERIALS if r["code"] == item_code), 0.0)
        wh_name = next((w["name"] for w in WAREHOUSES if w["code"] == wh_code), wh_code)

        doc = {
            "_seed": SEED_TAG,
            "item_id": item_id,
            "item_code": item_code,
            "item_name": item_name,
            "item_type": item_type,
            "warehouse_id": wh_id,
            "warehouse_code": wh_code,
            "warehouse_name": wh_name,
            "unit_id": unit_id,
            "batch_no": "OPENING",
            "quantity_on_hand": qty,
            "quantity_reserved": 0.0,
            "quantity_available": qty,
            "uom": uom,
            "valuation_rate": unit_cost,
            "total_valuation": round(qty * unit_cost, 2),
            "reorder_level": reorder,
            "safety_stock": safety,
            "is_below_reorder": qty < reorder,
            "updated_at": NOW,
            "created_at": ts(120),
            "created_by": ADMIN,
        }
        await col.insert_one(doc)
        print(f"  [STOCK] {item_code} @ {wh_code} - qty: {qty}")


async def seed_salary_structures(db, emp_col) -> None:
    col = db["payroll_salary_structures"]

    salary_map = {
        "Production Manager":     {"base": 65000, "basic": 38000, "hra": 12000, "conv": 3000, "special": 12000, "pf": True,  "esi": False},
        "Production Supervisor":  {"base": 42000, "basic": 24000, "hra": 8000,  "conv": 2500, "special": 7500,  "pf": True,  "esi": True},
        "QC Manager":             {"base": 60000, "basic": 35000, "hra": 11000, "conv": 3000, "special": 11000, "pf": True,  "esi": False},
        "QC Inspector":           {"base": 38000, "basic": 22000, "hra": 7000,  "conv": 2500, "special": 6500,  "pf": True,  "esi": True},
        "Inventory Manager":      {"base": 55000, "basic": 32000, "hra": 10000, "conv": 3000, "special": 10000, "pf": True,  "esi": False},
        "Storekeeper":            {"base": 32000, "basic": 18000, "hra": 6000,  "conv": 2000, "special": 6000,  "pf": True,  "esi": True},
        "Sales Manager":          {"base": 70000, "basic": 40000, "hra": 14000, "conv": 4000, "special": 12000, "pf": True,  "esi": False},
        "Sales Executive":        {"base": 40000, "basic": 23000, "hra": 8000,  "conv": 3000, "special": 6000,  "pf": True,  "esi": True},
        "Dispatch Manager":       {"base": 52000, "basic": 30000, "hra": 10000, "conv": 3000, "special": 9000,  "pf": True,  "esi": False},
        "Dispatch Executive":     {"base": 34000, "basic": 19000, "hra": 7000,  "conv": 2500, "special": 5500,  "pf": True,  "esi": True},
        "Billing Manager":        {"base": 62000, "basic": 36000, "hra": 12000, "conv": 3000, "special": 11000, "pf": True,  "esi": False},
        "Accountant":             {"base": 45000, "basic": 26000, "hra": 9000,  "conv": 3000, "special": 7000,  "pf": True,  "esi": False},
        "HR Manager":             {"base": 68000, "basic": 39000, "hra": 13000, "conv": 3500, "special": 12500, "pf": True,  "esi": False},
        "HR Executive":           {"base": 38000, "basic": 22000, "hra": 7500,  "conv": 2500, "special": 6000,  "pf": True,  "esi": True},
        "Maintenance Manager":    {"base": 58000, "basic": 34000, "hra": 11000, "conv": 3000, "special": 10000, "pf": True,  "esi": False},
        "Maintenance Technician": {"base": 36000, "basic": 21000, "hra": 7000,  "conv": 2500, "special": 5500,  "pf": True,  "esi": True},
    }

    banks = [
        ("HDFC Bank",  "50100123456789",  "HDFC0001234"),
        ("SBI",        "12345678901234",  "SBIN0001234"),
        ("ICICI Bank", "123456789012",    "ICIC0001234"),
        ("Axis Bank",  "915010023456789", "UTIB0001234"),
        ("Kotak Bank", "4012345678",      "KKBK0001234"),
    ]

    employees = await emp_col.find({"is_active": True}).to_list(length=100)
    for i, emp in enumerate(employees):
        existing = await col.find_one({"employee_id": str(emp["_id"])})
        if existing:
            continue

        job_role = emp.get("job_role") or emp.get("designation", "")
        sal = salary_map.get(job_role, {"base": 35000, "basic": 20000, "hra": 7000, "conv": 2500, "special": 5500, "pf": True, "esi": True})
        bk = banks[i % len(banks)]
        unit_id = emp.get("unit_id", "Unit_1")
        if unit_id not in ["Unit_1", "Unit_2"]:
            unit_id = "Unit_1"

        doc = {
            "_seed": SEED_TAG,
            "employee_id": str(emp["_id"]),
            "employee_code": emp.get("code", f"EMP-{i+100}"),
            "employee_name": emp.get("full_name", ""),
            "department": emp.get("department", ""),
            "designation": emp.get("designation", ""),
            "unit_id": unit_id,
            "base_monthly_salary": sal["base"],
            "basic_salary": sal["basic"],
            "hra": sal["hra"],
            "conveyance_allowance": sal["conv"],
            "special_allowance": sal["special"],
            "overtime_hourly_rate": round(sal["basic"] / (26 * 8), 2),
            "pf_applicable": sal["pf"],
            "pf_percentage": 12.0,
            "esi_applicable": sal["esi"],
            "esi_percentage": 0.75,
            "professional_tax": 200.0,
            "tds_monthly": 0.0,
            "gross_monthly_standard": sal["basic"] + sal["hra"] + sal["conv"] + sal["special"],
            "bank_name": bk[0],
            "bank_account_number": bk[1],
            "bank_ifsc": bk[2],
            "created_at": ts(120),
            "updated_at": ts(30),
        }
        await col.insert_one(doc)
        print(f"  [SALARY] {emp.get('full_name', '')} - Rs.{sal['base']:,}/mo")


async def seed_attendance(db, emp_col):
    col = db["hr_attendance"]
    employees = await emp_col.find({"is_active": True}).to_list(length=100)
    total_inserted = 0

    for emp in employees:
        emp_id = str(emp["_id"])
        emp_code = emp.get("code", "EMP-000")
        emp_name = emp.get("full_name", "")
        dept = emp.get("department", "")
        desig = emp.get("designation", "")
        unit_id = emp.get("unit_id", "Unit_1")
        if unit_id not in ["Unit_1", "Unit_2"]:
            unit_id = "Unit_1"

        for day_offset in range(1, 31):
            dt = NOW - timedelta(days=day_offset)
            if dt.weekday() == 6:  # Skip Sundays
                continue
            date_s = dt.strftime("%Y-%m-%d")

            existing = await col.find_one({"employee_id": emp_id, "date": date_s})
            if existing:
                continue

            rand_val = (hash(emp_id + date_s) % 100)
            if rand_val < 85:
                status, hrs, ot = "PRESENT", 8.0, (1.5 if rand_val < 20 else 0.0)
                check_in = "09:05"
                check_out = "18:30" if ot > 0 else "18:05"
            elif rand_val < 90:
                status, hrs, ot = "HALF_DAY", 4.0, 0.0
                check_in, check_out = "09:00", "13:00"
            elif rand_val < 95:
                status, hrs, ot = "ON_LEAVE", 0.0, 0.0
                check_in = check_out = None
            else:
                status, hrs, ot = "ABSENT", 0.0, 0.0
                check_in = check_out = None

            doc = {
                "_seed": SEED_TAG,
                "employee_id": emp_id,
                "employee_code": emp_code,
                "employee_name": emp_name,
                "department": dept,
                "designation": desig,
                "date": date_s,
                "unit_id": unit_id,
                "shift_code": "SHIFT-GEN",
                "check_in": check_in,
                "check_out": check_out,
                "status": status,
                "hours_worked": hrs,
                "overtime_hours": ot,
                "is_corrected": False,
                "correction_reason": None,
                "corrected_by": None,
                "created_at": dt.replace(tzinfo=timezone.utc),
                "created_by": ADMIN,
            }
            await col.insert_one(doc)
            total_inserted += 1

    print(f"  [ATTENDANCE] Inserted {total_inserted} records for {len(employees)} employees over 30 days")


async def seed_leave_applications(db, emp_col):
    col = db["hr_leaves"]
    employees = await emp_col.find({"is_active": True}).to_list(length=100)

    scenarios = [
        ("CASUAL_LEAVE",  2, "Personal work and family commitments",    "APPROVED", 18),
        ("SICK_LEAVE",    1, "Fever and medical consultation",           "APPROVED", 12),
        ("EARNED_LEAVE",  3, "Planned vacation - family trip",           "APPROVED",  8),
        ("CASUAL_LEAVE",  1, "Urgent personal work",                     "PENDING",   3),
        ("SICK_LEAVE",    2, "Stomach ailment - doctor advised rest",    "APPROVED", 25),
    ]

    for i, emp in enumerate(employees):
        emp_id = str(emp["_id"])
        emp_code = emp.get("code", "EMP-000")
        emp_name = emp.get("full_name", "")
        dept = emp.get("department", "")
        unit_id = emp.get("unit_id", "Unit_1")
        if unit_id not in ["Unit_1", "Unit_2"]:
            unit_id = "Unit_1"

        for j in range(2):
            sc = scenarios[(i + j) % len(scenarios)]
            leave_type, days, reason, status, offset = sc
            app_num = f"LEAVE-{(i * 10 + j + 1):04d}"

            existing = await col.find_one({"application_number": app_num})
            if existing:
                continue

            start = (NOW - timedelta(days=offset)).strftime("%Y-%m-%d")
            end = (NOW - timedelta(days=offset - days + 1)).strftime("%Y-%m-%d")

            doc = {
                "_seed": SEED_TAG,
                "application_number": app_num,
                "employee_id": emp_id,
                "employee_code": emp_code,
                "employee_name": emp_name,
                "department": dept,
                "unit_id": unit_id,
                "leave_type": leave_type,
                "start_date": start,
                "end_date": end,
                "days_count": float(days),
                "reason": reason,
                "status": status,
                "approved_by": ADMIN if status == "APPROVED" else None,
                "approved_at": ts(offset - 1) if status == "APPROVED" else None,
                "rejection_reason": None,
                "created_at": ts(offset + 2),
                "created_by": emp_id,
            }
            await col.insert_one(doc)

    print(f"  [LEAVES] Seeded leave applications for {len(employees)} employees")


async def seed_payroll_run(db, emp_col):
    runs_col = db["payroll_runs"]
    items_col = db["payroll_items"]
    sal_col = db["payroll_salary_structures"]

    period = (NOW - timedelta(days=30)).strftime("%Y-%m")
    run_num = f"PAY-{period}"

    existing = await runs_col.find_one({"run_number": run_num})
    if existing:
        print(f"  [PAYROLL] Run {run_num} already exists, skipping")
        return

    employees = await emp_col.find({"is_active": True}).to_list(length=100)
    working_days = 26
    total_gross = total_deductions = total_net = 0.0
    items = []

    for emp in employees:
        emp_id = str(emp["_id"])
        sal = await sal_col.find_one({"employee_id": emp_id})
        if not sal:
            continue

        unit_id = emp.get("unit_id", "Unit_1")
        if unit_id not in ["Unit_1", "Unit_2"]:
            unit_id = "Unit_1"

        present_days = round(working_days * 0.9 + (hash(emp_id) % 3), 1)
        paid_leave = 1.5
        unpaid_leave = max(0.0, working_days - present_days - paid_leave)
        ot_hours = round((abs(hash(emp_id[:4])) % 10) * 0.5, 1)

        daily_basic = sal["basic_salary"] / working_days
        lop_ded = round(daily_basic * unpaid_leave, 2)
        pf_ded = round(sal["basic_salary"] * sal["pf_percentage"] / 100, 2) if sal["pf_applicable"] else 0.0
        esi_ded = round(sal["base_monthly_salary"] * sal["esi_percentage"] / 100, 2) if sal["esi_applicable"] else 0.0
        ot_pay = round(ot_hours * sal["overtime_hourly_rate"], 2)
        gross = sal["basic_salary"] + sal["hra"] + sal["conveyance_allowance"] + sal["special_allowance"] + ot_pay
        total_ded = lop_ded + pf_ded + esi_ded + sal["professional_tax"]
        net = round(gross - total_ded, 2)

        total_gross += gross
        total_deductions += total_ded
        total_net += net

        items.append({
            "_seed": SEED_TAG,
            "payroll_run_id": "__placeholder__",
            "employee_id": emp_id,
            "employee_code": emp.get("code", ""),
            "employee_name": emp.get("full_name", ""),
            "department": emp.get("department", ""),
            "designation": emp.get("designation", ""),
            "period": period,
            "unit_id": unit_id,
            "standard_working_days": working_days,
            "present_days": present_days,
            "paid_leave_days": paid_leave,
            "unpaid_leave_days": unpaid_leave,
            "overtime_hours": ot_hours,
            "basic": sal["basic_salary"],
            "hra": sal["hra"],
            "conveyance": sal["conveyance_allowance"],
            "special_allowance": sal["special_allowance"],
            "overtime_pay": ot_pay,
            "gross_earnings": gross,
            "lop_deduction": lop_ded,
            "pf_deduction": pf_ded,
            "esi_deduction": esi_ded,
            "professional_tax": sal["professional_tax"],
            "tds_deduction": 0.0,
            "total_deductions": total_ded,
            "net_pay": net,
            "bank_account_number": sal.get("bank_account_number"),
            "bank_ifsc": sal.get("bank_ifsc"),
        })

    run_doc = {
        "_seed": SEED_TAG,
        "run_number": run_num,
        "period": period,
        "unit_id": "BOTH",
        "working_days_in_month": working_days,
        "total_employees": len(items),
        "total_gross_payout": round(total_gross, 2),
        "total_deductions": round(total_deductions, 2),
        "total_net_payout": round(total_net, 2),
        "status": "APPROVED",
        "notes": f"Regular payroll run for {period}",
        "created_at": ts(10),
        "created_by": ADMIN,
        "reviewed_at": ts(8), "reviewed_by": ADMIN,
        "approved_at": ts(7), "approved_by": ADMIN,
        "posted_at": ts(5),   "posted_by": ADMIN,
    }
    run_res = await runs_col.insert_one(run_doc)
    run_id = str(run_res.inserted_id)

    for item in items:
        item["payroll_run_id"] = run_id
        await items_col.insert_one(item)

    print(f"  [PAYROLL] Run {run_num} - {len(items)} employees - Net: Rs.{round(total_net):,}")


async def seed_sales_orders(db, cust_id_map: Dict[str, str], fp_id_map: Dict[str, str]):
    col = db["sales_orders"]

    orders_data = [
        {"order_number": "SO-202609-001", "customer_code": "CUST-001", "customer_po_number": "PO/RAVI/2026/145", "unit_id": "Unit_1", "status": "DISPATCHED",           "order_date_offset": 45, "delivery_offset": 15,
         "items": [("FP-ENV-100", 3.0, 245000.0, 3.0), ("FP-ENV-MINI", 5.0, 128000.0, 2.0)],
         "notes": "Priority order – deliver before festival season. 3% bulk discount agreed."},
        {"order_number": "SO-202609-002", "customer_code": "CUST-002", "customer_po_number": "NPI/PURCHASE/2026/082", "unit_id": "BOTH", "status": "CONFIRMED",          "order_date_offset": 30, "delivery_offset": 10,
         "items": [("FP-ENV-200", 2.0, 415000.0, 2.0)],
         "notes": "Customer requires installation and commissioning support."},
        {"order_number": "SO-202610-001", "customer_code": "CUST-003", "customer_po_number": "BOS/2026/056",        "unit_id": "Unit_2","status": "PARTIALLY_DISPATCHED","order_date_offset": 20, "delivery_offset":  5,
         "items": [("FP-PKG-300", 1.0, 565000.0, 0.0), ("FP-ENV-MINI", 3.0, 128000.0, 0.0)],
         "notes": "PKG-300 to be dispatched first. ENV-MINI in second lot."},
        {"order_number": "SO-202610-002", "customer_code": "CUST-004", "customer_po_number": "DPS/PO/2026/031",    "unit_id": "Unit_1","status": "SUBMITTED",           "order_date_offset": 10, "delivery_offset": -20,
         "items": [("FP-ENV-100", 2.0, 245000.0, 0.0)],
         "notes": "Standard order. Payment terms Net-45."},
        {"order_number": "SO-202610-003", "customer_code": "CUST-005", "customer_po_number": "HPPC/2026/018",       "unit_id": "BOTH", "status": "CONFIRMED",          "order_date_offset":  8, "delivery_offset": -15,
         "items": [("FP-ENV-200", 1.0, 415000.0, 5.0), ("FP-ENV-100", 2.0, 245000.0, 3.0)],
         "notes": "5% special discount on ENV-200 for repeat customer. AMC contract included."},
        {"order_number": "SO-202610-004", "customer_code": "CUST-006", "customer_po_number": "PIT/ORDER/2026/012",  "unit_id": "Unit_1","status": "DRAFT",              "order_date_offset":  3, "delivery_offset": -30,
         "items": [("FP-ENV-MINI", 6.0, 128000.0, 4.0)],
         "notes": "Bulk mini machine order. Awaiting management approval."},
        {"order_number": "SO-202610-005", "customer_code": "CUST-007", "customer_po_number": "COM/PO/2026/009",     "unit_id": "Unit_2","status": "DISPATCHED",         "order_date_offset": 60, "delivery_offset": 20,
         "items": [("FP-PKG-300", 2.0, 565000.0, 2.0)],
         "notes": "Annual procurement order. Both machines shipped together."},
    ]

    for order in orders_data:
        existing = await col.find_one({"order_number": order["order_number"]})
        if existing:
            continue

        cust_code = order["customer_code"]
        cust_id = cust_id_map.get(cust_code, cust_code)
        cust_name = next((c["name"] for c in CUSTOMERS if c["code"] == cust_code), cust_code)
        cust_data = next((c for c in CUSTOMERS if c["code"] == cust_code), {})
        order_date = ts(order["order_date_offset"])
        delivery_date = (NOW - timedelta(days=order["delivery_offset"])).strftime("%Y-%m-%d") if order["delivery_offset"] != 0 else None

        items_resolved = []
        subtotal = tax_total = 0.0
        for (fp_code, qty, price, disc) in order["items"]:
            fp_id = fp_id_map.get(fp_code, fp_code)
            fp_name = next((f["name"] for f in FINISHED_PRODUCTS if f["code"] == fp_code), fp_code)
            discounted = price * (1 - disc / 100.0)
            st = round(qty * discounted, 2)
            tax = round(st * 0.18, 2)
            disp_qty = qty if order["status"] == "DISPATCHED" else (qty / 2.0 if order["status"] == "PARTIALLY_DISPATCHED" else 0.0)
            items_resolved.append({
                "product_id": fp_id, "product_code": fp_code, "product_name": fp_name,
                "uom": "PCS", "quantity": qty, "unit_price": price,
                "discount_percent": disc, "tax_percent": 18.0, "dispatched_quantity": disp_qty, "notes": None,
            })
            subtotal += st
            tax_total += tax

        grand_total = round(subtotal + tax_total, 2)
        total_ordered = sum(it["quantity"] for it in items_resolved)
        total_dispatched = sum(it["dispatched_quantity"] for it in items_resolved)

        doc = {
            "_seed": SEED_TAG,
            "order_number": order["order_number"],
            "customer_id": cust_id, "customer_code": cust_code, "customer_name": cust_name,
            "customer_po_number": order.get("customer_po_number"),
            "unit_id": order["unit_id"], "status": order["status"],
            "order_date": order_date, "delivery_due_date": delivery_date,
            "billing_address": cust_data.get("billing_address"),
            "shipping_address": cust_data.get("shipping_address"),
            "items": items_resolved,
            "subtotal": subtotal, "tax_total": tax_total, "grand_total": grand_total,
            "total_ordered_qty": total_ordered, "total_dispatched_qty": total_dispatched,
            "dispatch_percent": round((total_dispatched / total_ordered * 100) if total_ordered > 0 else 0, 2),
            "notes": order.get("notes"), "cancellation_reason": None,
            "created_at": order_date, "created_by": ADMIN,
            "updated_at": ts(1), "updated_by": ADMIN,
        }
        await col.insert_one(doc)
        print(f"  [ORDER] {order['order_number']} - {cust_code} - Rs.{grand_total:,.0f} - {order['status']}")


async def seed_invoices(db, cust_id_map: Dict[str, str]):
    col = db["finance_invoices"]

    invoices = [
        {"invoice_number": "INV-202609-001", "customer_code": "CUST-001", "invoice_date": date_str(40), "due_date": date_str(0), "status": "PAID",
         "lines": [("FP-ENV-100", "Envelope Machine ENV-100 x3", 3, 245000.0, 3.0, 18.0), ("FP-ENV-MINI", "Mini Envelope Machine x5", 5, 128000.0, 2.0, 18.0)]},
        {"invoice_number": "INV-202609-002", "customer_code": "CUST-007", "invoice_date": date_str(55), "due_date": date_str(10), "status": "PAID",
         "lines": [("FP-PKG-300", "Carton Packing Machine PKG-300 x2", 2, 565000.0, 2.0, 18.0)]},
        {"invoice_number": "INV-202610-001", "customer_code": "CUST-003", "invoice_date": date_str(18), "due_date": date_str(-12), "status": "PARTIALLY_PAID",
         "lines": [("FP-PKG-300", "Carton Packing Machine PKG-300", 1, 565000.0, 0.0, 18.0)]},
        {"invoice_number": "INV-202610-002", "customer_code": "CUST-005", "invoice_date": date_str(6), "due_date": date_str(-39), "status": "POSTED",
         "lines": [("FP-ENV-200", "Envelope Machine ENV-200", 1, 415000.0, 5.0, 18.0), ("FP-ENV-100", "Envelope Machine ENV-100 x2", 2, 245000.0, 3.0, 18.0)]},
    ]

    for inv in invoices:
        existing = await col.find_one({"invoice_number": inv["invoice_number"]})
        if existing:
            continue

        cust_code = inv["customer_code"]
        cust_id = cust_id_map.get(cust_code, cust_code)
        cust_name = next((c["name"] for c in CUSTOMERS if c["code"] == cust_code), cust_code)

        subtotal = tax_total = 0.0
        lines_resolved = []
        for (item_code, desc, qty, price, disc, tax_pct) in inv["lines"]:
            discounted = price * (1 - disc / 100.0)
            st = round(qty * discounted, 2)
            tax = round(st * tax_pct / 100.0, 2)
            subtotal += st
            tax_total += tax
            lines_resolved.append({"item_code": item_code, "description": desc, "quantity": qty, "unit_price": price,
                                    "discount_percent": disc, "tax_percent": tax_pct, "subtotal": st, "tax_amount": tax, "total": st + tax})

        total = round(subtotal + tax_total, 2)
        amount_paid = total if inv["status"] == "PAID" else (round(total * 0.5, 2) if inv["status"] == "PARTIALLY_PAID" else 0.0)

        doc = {
            "_seed": SEED_TAG,
            "invoice_number": inv["invoice_number"],
            "customer_id": cust_id, "customer_code": cust_code, "customer_name": cust_name,
            "unit_id": "Unit_1",
            "invoice_date": inv["invoice_date"], "due_date": inv["due_date"],
            "lines": lines_resolved,
            "subtotal_amount": subtotal, "tax_amount": tax_total, "total_amount": total,
            "amount_paid": amount_paid, "balance_due": round(total - amount_paid, 2),
            "status": inv["status"], "notes": None,
            "created_at": ts(40), "created_by": ADMIN,
        }
        await col.insert_one(doc)
        print(f"  [INVOICE] {inv['invoice_number']} - Rs.{total:,.0f} - {inv['status']}")


async def seed_supplier_bills(db, vendor_id_map: Dict[str, str]):
    col = db["finance_bills"]

    bills = [
        {"bill_number": "BILL-202609-001", "vendor_code": "VEND-001", "bill_number_vendor": "JSP/INV/2026/4521",  "po_ref": "PO-RM-2026-045", "date": date_str(35), "due": date_str(5),   "status": "PAID",     "qc_hold": False, "qc_reason": None,
         "lines": [("RM-MS-PLATE-6MM",  "MS Plate 6mm - 2000 KG",  2000, 58.0,   18.0), ("RM-MS-PLATE-10MM","MS Plate 10mm - 1200 KG", 1200, 62.0, 18.0)]},
        {"bill_number": "BILL-202609-002", "vendor_code": "VEND-002", "bill_number_vendor": "BEM/PI/2026/789",     "po_ref": "PO-RM-2026-047", "date": date_str(28), "due": date_str(-17), "status": "APPROVED", "qc_hold": False, "qc_reason": None,
         "lines": [("RM-MOTOR-0.5HP",  "AC Motor 0.5HP - 30 Nos",  30,   2800.0, 18.0), ("RM-MOTOR-1HP",    "AC Motor 1HP - 25 Nos",    25, 4200.0, 18.0), ("RM-BEARING-6205","Bearing 6205 ZZ - 200 Nos",200, 185.0, 18.0)]},
        {"bill_number": "BILL-202610-001", "vendor_code": "VEND-005", "bill_number_vendor": "SKF/INV/2026/1122",   "po_ref": "PO-RM-2026-052", "date": date_str(15), "due": date_str(-45), "status": "POSTED",   "qc_hold": False, "qc_reason": None,
         "lines": [("RM-BEARING-6205",  "Bearing 6205 ZZ - 150 Nos",150,  185.0,  18.0)]},
        {"bill_number": "BILL-202610-002", "vendor_code": "VEND-004", "bill_number_vendor": "IWC/BILL/2026/345",   "po_ref": "PO-CONS-2026-011","date": date_str(10),"due": date_str(-20), "status": "ON_HOLD",  "qc_hold": True,  "qc_reason": "E6013 electrode quality test pending - hardness below spec. Batch awaiting QC clearance.",
         "lines": [("RM-WELD-ROD-E6013","Welding Rod E6013 - 80 KG", 80,   110.0,  18.0)]},
        {"bill_number": "BILL-202610-003", "vendor_code": "VEND-007", "bill_number_vendor": "GCP/INV/2026/456",    "po_ref": "PO-RM-2026-058", "date": date_str(5),  "due": date_str(-40), "status": "DRAFT",    "qc_hold": False, "qc_reason": None,
         "lines": [("RM-CI-CAST-001",   "CI Body Casting - 50 Nos",  50,   3500.0, 18.0)]},
    ]

    for bill in bills:
        existing = await col.find_one({"bill_number": bill["bill_number"]})
        if existing:
            continue

        vend_code = bill["vendor_code"]
        vend_id = vendor_id_map.get(vend_code, vend_code)
        vend_name = next((v["name"] for v in VENDORS if v["code"] == vend_code), vend_code)

        subtotal = tax_total = 0.0
        lines_resolved = []
        for (item_code, desc, qty, price, tax_pct) in bill["lines"]:
            st = round(qty * price, 2)
            tax = round(st * tax_pct / 100.0, 2)
            subtotal += st
            tax_total += tax
            lines_resolved.append({"item_code": item_code, "description": desc, "quantity": qty, "unit_price": price,
                                    "tax_percent": tax_pct, "subtotal": st, "tax_amount": tax, "total": st + tax})

        total = round(subtotal + tax_total, 2)
        amount_paid = total if bill["status"] == "PAID" else 0.0

        doc = {
            "_seed": SEED_TAG,
            "bill_number": bill["bill_number"],
            "vendor_id": vend_id, "vendor_code": vend_code, "vendor_name": vend_name,
            "bill_number_vendor": bill["bill_number_vendor"],
            "po_reference": bill.get("po_ref"),
            "unit_id": "Unit_1",
            "bill_date": bill["date"], "due_date": bill["due"],
            "lines": lines_resolved,
            "subtotal_amount": subtotal, "tax_amount": tax_total, "total_amount": total,
            "amount_paid": amount_paid, "balance_due": round(total - amount_paid, 2),
            "status": bill["status"],
            "has_qc_hold": bill["qc_hold"], "qc_hold_reason": bill["qc_reason"],
            "notes": None,
            "created_at": ts(35), "created_by": ADMIN,
        }
        await col.insert_one(doc)
        print(f"  [BILL] {bill['bill_number']} - Rs.{total:,.0f} - {bill['status']}")


async def seed_expenses(db):
    col = db["finance_expenses"]

    expenses = [
        ("EXP-202609-001", "ELECTRICITY", "5310-ELECTRICITY",     date_str(32), 85000.0,  0.0,    "BANK_TRANSFER","1010-BANK-HDFC","Madhya Gujarat Vij Company Ltd (MGVCL)",  "MGVCL/2026/10/001","Monthly power bill Unit-1 - Oct 2026"),
        ("EXP-202609-002", "ELECTRICITY", "5310-ELECTRICITY",     date_str(32), 52000.0,  0.0,    "BANK_TRANSFER","1010-BANK-HDFC","Madhya Gujarat Vij Company Ltd (MGVCL)",  "MGVCL/2026/10/002","Monthly power bill Unit-2 - Oct 2026"),
        ("EXP-202609-003", "REPAIRS",     "5330-REPAIRS-MAINT",   date_str(20), 24500.0,  4410.0, "BANK_TRANSFER","1010-BANK-HDFC","Mehta Hydraulics & Pneumatics",            "MHP/INV/2026/221","CNC lathe hydraulic pump repair & seals"),
        ("EXP-202609-004", "FREIGHT",     "5320-FREIGHT-EXPENSE", date_str(18), 18000.0,  3240.0, "BANK_TRANSFER","1010-BANK-HDFC","Shree Mahavir Logistics",                  "SML/LR/2026/5467","Outward freight for SO-202609-001 dispatch"),
        ("EXP-202609-005", "TRAVEL",      "5300-OPERATING-EXPENSES",date_str(15),12500.0, 0.0,    "CASH",         "1020-PETTY-CASH","Sales Travel Reimbursements",             "HR/TRAVEL/OCT/01","Sales team travel to Mumbai & Hyderabad"),
        ("EXP-202610-001", "ELECTRICITY", "5310-ELECTRICITY",     date_str(2),  88500.0,  0.0,    "BANK_TRANSFER","1010-BANK-HDFC","Madhya Gujarat Vij Company Ltd (MGVCL)",  "MGVCL/2026/11/001","Nov 2026 power bill Unit-1"),
        ("EXP-202610-002", "FREIGHT",     "5320-FREIGHT-EXPENSE", date_str(14), 22000.0,  3960.0, "NEFT_RTGS",    "1010-BANK-HDFC","Blue Dart Express Ltd",                   "BD/SHIPMENT/88901","Expedited air freight - PKG-300 dispatch Bengaluru"),
        ("EXP-202610-003", "REPAIRS",     "5330-REPAIRS-MAINT",   date_str(8),  8500.0,   1530.0, "CHEQUE",       "1011-BANK-SBI", "Kumar Electrical Services",               "KES/INV/156",      "Electrical panel wiring repair - Unit-2"),
        ("EXP-202610-004", "INSURANCE",   "5300-OPERATING-EXPENSES",date_str(5), 45000.0, 0.0,    "BANK_TRANSFER","1010-BANK-HDFC","New India Assurance Co Ltd",              "NIA/POLICY/2026/01","Annual factory & machinery insurance premium"),
        ("EXP-202610-005", "HOUSEKEEPING","5300-OPERATING-EXPENSES",date_str(1), 18000.0, 0.0,    "BANK_TRANSFER","1010-BANK-HDFC","Safalya Facilities Management",            "SFM/OCT26/INV",   "Monthly housekeeping & security contract"),
    ]

    for (exp_num, category, acc_code, exp_date, amount, tax, method, paid_from, payee, ref, notes) in expenses:
        existing = await col.find_one({"expense_number": exp_num})
        if existing:
            continue

        doc = {
            "_seed": SEED_TAG,
            "expense_number": exp_num,
            "expense_category": category,
            "expense_account_code": acc_code,
            "unit_id": "Unit_1",
            "expense_date": exp_date,
            "amount": amount, "tax_amount": tax, "total_amount": amount + tax,
            "payment_method": method,
            "paid_from_account_code": paid_from,
            "vendor_or_payee": payee,
            "reference_number": ref,
            "notes": notes,
            "created_at": ts(30), "created_by": ADMIN,
        }
        await col.insert_one(doc)
        print(f"  [EXPENSE] {exp_num} - Rs.{amount:,.0f} - {category}")


async def seed_production_orders(db, fp_id_map: Dict[str, str], bom_id_map: Dict[str, str], wh_id_map: Dict[str, str]):
    col = db["production_orders"]

    prod_orders = [
        ("PRD-202609-001", "FP-ENV-100",  "BOM-ENV100-R3",  "Unit_1","WH-U1-FG01", 5.0, 5.0, 0.0, "COMPLETED",  45, 15),
        ("PRD-202609-002", "FP-ENV-MINI", "BOM-ENVMINI-R1", "Unit_1","WH-U1-FG01",10.0, 8.0, 1.0, "COMPLETED",  50, 20),
        ("PRD-202610-001", "FP-ENV-200",  "BOM-ENV200-R2",  "Unit_1","WH-U1-FG01", 3.0, 1.0, 0.0, "IN_PROGRESS",10,-20),
        ("PRD-202610-002", "FP-PKG-300",  "BOM-PKG300-R1",  "Unit_2","WH-U2-FG01", 3.0, 2.0, 0.0, "COMPLETED",  35, 5),
        ("PRD-202610-003", "FP-ENV-100",  "BOM-ENV100-R3",  "Unit_1","WH-U1-FG01", 4.0, 0.0, 0.0, "RELEASED",   -5,-35),
        ("PRD-202610-004", "FP-ENV-MINI", "BOM-ENVMINI-R1", "Unit_1","WH-U1-FG01", 8.0, 0.0, 0.0, "DRAFT",     -10,-45),
    ]

    for (order_num, fp_code, bom_num, unit_id, wh_code, planned, produced, rejected, status, start_off, complete_off) in prod_orders:
        existing = await col.find_one({"order_number": order_num})
        if existing:
            continue

        fp_id = fp_id_map.get(fp_code, fp_code)
        fp_name = next((f["name"] for f in FINISHED_PRODUCTS if f["code"] == fp_code), fp_code)
        bom_id = bom_id_map.get(bom_num, bom_num)
        wh_id = wh_id_map.get(wh_code, wh_code)
        remaining = max(0.0, planned - produced)
        completion_pct = round((produced / planned * 100) if planned > 0 else 0, 2)

        doc = {
            "_seed": SEED_TAG,
            "order_number": order_num,
            "product_id": fp_id, "product_code": fp_code, "product_name": fp_name, "product_uom": "PCS",
            "bom_id": bom_id, "bom_number": bom_num, "bom_revision_no": bom_num.split("-")[-1],
            "unit_id": unit_id,
            "target_warehouse_id": wh_id, "target_warehouse_code": wh_code,
            "planned_quantity": planned, "produced_quantity": produced,
            "rejected_quantity": rejected, "remaining_quantity": remaining,
            "status": status, "completion_percentage": completion_pct,
            "materials": [],
            "scheduled_start_date": ts(start_off),
            "target_completion_date": NOW - timedelta(days=complete_off),
            "actual_start_date": ts(start_off) if status not in ["DRAFT", "RELEASED"] else None,
            "actual_completion_date": ts(complete_off) if status == "COMPLETED" else None,
            "notes": f"Production order for {fp_name}",
            "cancellation_reason": None,
            "created_at": ts(start_off + 5), "created_by": ADMIN,
            "updated_at": ts(1), "updated_by": ADMIN,
        }
        await col.insert_one(doc)
        print(f"  [PROD] {order_num} - {fp_code} x{planned} - {status}")


# ---------------------------------------------------------------------------
# CLEANUP
# ---------------------------------------------------------------------------
async def run_cleanup(db):
    collections = [
        "master_categories", "master_uoms", "master_warehouses",
        "master_raw_materials", "master_finished_products",
        "master_customers", "master_vendors",
        "finance_accounts", "finance_invoices", "finance_bills", "finance_expenses",
        "hr_shift_configs", "hr_attendance", "hr_leaves",
        "payroll_salary_structures", "payroll_runs", "payroll_items",
        "inventory_stock", "boms", "sales_orders", "production_orders",
    ]
    total = 0
    for c in collections:
        result = await db[c].delete_many({"_seed": SEED_TAG})
        if result.deleted_count > 0:
            print(f"  [CLEANUP] {c}: removed {result.deleted_count} docs")
            total += result.deleted_count
    print(f"\n[CLEANUP DONE] Removed {total} real-world seed documents.")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
async def main():
    parser = argparse.ArgumentParser(description="Opti Matrix ERP Real-World Data Seeding Script")
    parser.add_argument("--cleanup", action="store_true", help="Remove all seeded real-world data")
    args = parser.parse_args()

    verify_environment_safety()

    client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB_NAME]
    emp_col = db["employees"]

    try:
        if args.cleanup:
            await run_cleanup(db)
            return

        print("=" * 65)
        print("Opti Matrix ERP - Real-World Data Seeding")
        print("=" * 65)

        print("\n[1/12] Categories...")
        await seed_categories(db)

        print("\n[2/12] UoM Master...")
        await seed_uoms(db)

        print("\n[3/12] Warehouses...")
        wh_id_map = await seed_warehouses(db)

        print("\n[4/12] Raw Materials...")
        rm_id_map = await seed_raw_materials(db)

        print("\n[5/12] Finished Products...")
        fp_id_map = await seed_finished_products(db)

        print("\n[6/12] Customers...")
        cust_id_map = await seed_customers(db)

        print("\n[7/12] Vendors...")
        vendor_id_map = await seed_vendors(db)

        print("\n[8/12] Chart of Accounts...")
        await seed_accounts(db)

        print("\n[9/12] Shift Configurations...")
        await seed_shift_configs(db)

        print("\n[10/12] Bills of Material (BOMs)...")
        bom_id_map = await seed_boms(db, rm_id_map, fp_id_map)

        print("\n[11/12] Inventory Opening Stock...")
        await seed_inventory(db, rm_id_map, fp_id_map, wh_id_map)

        print("\n[12/12] HR, Payroll, Sales, Finance & Production...")
        print("  -> Salary Structures")
        await seed_salary_structures(db, emp_col)
        print("  -> Attendance (30 days)")
        await seed_attendance(db, emp_col)
        print("  -> Leave Applications")
        await seed_leave_applications(db, emp_col)
        print("  -> Payroll Run")
        await seed_payroll_run(db, emp_col)
        print("  -> Sales Orders")
        await seed_sales_orders(db, cust_id_map, fp_id_map)
        print("  -> Customer Invoices")
        await seed_invoices(db, cust_id_map)
        print("  -> Supplier Bills")
        await seed_supplier_bills(db, vendor_id_map)
        print("  -> Operational Expenses")
        await seed_expenses(db)
        print("  -> Production Orders")
        await seed_production_orders(db, fp_id_map, bom_id_map, wh_id_map)

        print("\n" + "=" * 65)
        print("SEEDING COMPLETE!")
        print("=" * 65)
        print("\nCollection counts after seeding:")
        for cname in ["master_categories","master_uoms","master_warehouses","master_raw_materials",
                       "master_finished_products","master_customers","master_vendors",
                       "finance_accounts","hr_shift_configs","boms","inventory_stock",
                       "payroll_salary_structures","hr_attendance","hr_leaves",
                       "payroll_runs","payroll_items","sales_orders",
                       "finance_invoices","finance_bills","finance_expenses","production_orders"]:
            count = await db[cname].count_documents({})
            if count > 0:
                print(f"  {cname}: {count} documents")

    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())

