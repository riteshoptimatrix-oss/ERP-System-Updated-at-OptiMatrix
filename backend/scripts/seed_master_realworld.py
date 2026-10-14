"""
Opti Matrix Manufacturing ERP — Master Real-World QA Seeding Script
File: backend/scripts/seed_master_realworld.py

Populates production-grade, realistic manufacturing ERP data across:
  - Both Unit 1 (Heavy Machining, Boring, Milling) and Unit 2 (Assembly, QC, Dispatch)
  - 34 Employees across all 8 departments with complete managerial hierarchy
  - 10 Production Projects / Orders with WIP, milestones, and material issuances
  - 115+ Employee Tasks with varied statuses, priorities, subtasks, and comments
  - 90 Days of Shift Attendance history, Overtime, and Attendance Corrections
  - Leave Applications across all leave types, statuses, and edge cases
  - Salary Structures and 4 Monthly Payroll Runs with itemized payslips
  - Multi-level Bills of Materials (BOM) with component scrap allowances
  - Warehouses and Stock Balances across both Unit 1 and Unit 2
  - Quality Control (QC) Inspections with Passed, Failed, and Quarantined states
  - Scrap & Wastage tracking with Metal Turnings, Offcuts, and Rejections
  - 60 Days of Electricity Meter Readings and Power Cut logs for both units
  - Sales Orders, Packing Slips, Dispatches (with e-way bills), and Tax Invoices
  - Chart of Accounts, Journal Entries, Supplier Bills, and Expenses
  - CRM Leads (18 leads across all pipeline stages) and Activity History
  - Plant Announcements and User Notifications

Safe and idempotent: Can be executed multiple times without duplicates.

Usage:
    python backend/scripts/seed_master_realworld.py            # Seed full ERP dataset
    python backend/scripts/seed_master_realworld.py --cleanup  # Remove seeded records only
"""

import sys
import os
import argparse
import asyncio
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from bson import ObjectId

# Ensure backend root is on sys.path and load environment variables
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Auto-load backend/.env if present
env_path = backend_dir / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path)

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import (
    RoleName,
    ManufacturingUnit,
    DEFAULT_ROLE_PERMISSIONS,
    JOB_ROLE_DEFAULT_PERMISSIONS,
    resolve_user_permissions,
)
import motor.motor_asyncio

# ---------------------------------------------------------------------------
# Constants & Date Helpers
# ---------------------------------------------------------------------------
NOW = datetime.now(timezone.utc)
SEED_TAG = "optimatrix_master_seed_v1"
DEFAULT_TEST_PASSWORD = "admin123"

def d_ago(days: int, hours: int = 0) -> datetime:
    return NOW - timedelta(days=days, hours=hours)

def d_future(days: int, hours: int = 0) -> datetime:
    return NOW + timedelta(days=days, hours=hours)

def date_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# 1. CATEGORIES & UOM
# ---------------------------------------------------------------------------
CATEGORIES = [
    {"code": "CAT-RAW-STEEL",   "name": "Steel & Metal Raw Stock",    "category_type": "RAW_MATERIAL",     "description": "IS:2062 MS plates, SS-304 rounds, CI castings"},
    {"code": "CAT-RAW-POLYMER", "name": "Polymers & Seals",           "category_type": "RAW_MATERIAL",     "description": "Nylon PA6 bushes, rubber gaskets, seals"},
    {"code": "CAT-RAW-ELEC",    "name": "Motors & Electrical Drives", "category_type": "RAW_MATERIAL",     "description": "Induction motors, run capacitors, wiring harnesses"},
    {"code": "CAT-RAW-CONS",    "name": "Coolants & Consumables",     "category_type": "CONSUMABLE",       "description": "Servo-cut cutting fluids, welding rods, machine paint"},
    {"code": "CAT-FP-ENV",      "name": "Envelope Making Machines",   "category_type": "FINISHED_PRODUCT", "description": "High-precision automated paper converting machinery"},
    {"code": "CAT-FP-PKG",      "name": "Carton Packaging Machines",  "category_type": "FINISHED_PRODUCT", "description": "Automated cartooning and box packing machinery"},
    {"code": "CAT-SPARE",       "name": "Replacement Spares & Kits", "category_type": "SPARES",           "description": "Spindle bearings, belts, wear components"},
]

UOMS = [
    {"code": "KG",  "name": "Kilogram", "symbol": "kg",  "description": "Weight in kilograms"},
    {"code": "MTR", "name": "Metre",    "symbol": "m",   "description": "Linear length in metres"},
    {"code": "PCS", "name": "Pieces",   "symbol": "pcs", "description": "Countable distinct units"},
    {"code": "LTR", "name": "Litre",    "symbol": "L",   "description": "Liquid volume in litres"},
    {"code": "NOS", "name": "Numbers",  "symbol": "nos", "description": "Count of components"},
    {"code": "SET", "name": "Set",      "symbol": "set", "description": "Tooling and hardware sets"},
    {"code": "ROL", "name": "Roll",     "symbol": "rol", "description": "Roll of gasket or wire"},
    {"code": "BOX", "name": "Box",      "symbol": "box", "description": "Packaged hardware box"},
]

# ---------------------------------------------------------------------------
# 2. WAREHOUSES (Unit 1 & Unit 2)
# ---------------------------------------------------------------------------
WAREHOUSES = [
    # Unit 1: Heavy Machining, Boring, Milling & Fabrication
    {"code": "WH-U1-RM01", "name": "Unit 1 Heavy Plates & Steel Yard",     "unit_id": "Unit_1", "location_type": "RAW_MATERIAL",   "bay_rack": "Bay-1A Racks 1-12", "capacity_description": "Heavy MS plates, structural channels"},
    {"code": "WH-U1-RM02", "name": "Unit 1 Castings & Bar Stock Store",   "unit_id": "Unit_1", "location_type": "RAW_MATERIAL",   "bay_rack": "Bay-1B Racks 1-8",  "capacity_description": "Cast iron body roughs, SS round bars"},
    {"code": "WH-U1-WIP",  "name": "Unit 1 Machining WIP Buffer Bay",       "unit_id": "Unit_1", "location_type": "WIP",            "bay_rack": "Bay-1C WIP Buffer", "capacity_description": "Turned shafts, milled machine bases"},
    {"code": "WH-U1-FG01", "name": "Unit 1 Finished Envelope Machines Store","unit_id": "Unit_1", "location_type": "FINISHED_GOODS", "bay_rack": "Bay-1D Packing",    "capacity_description": "Tested ENV-100 and ENV-200 units"},
    {"code": "WH-U1-SCRAP","name": "Unit 1 Metal Turnings & Offcut Yard",  "unit_id": "Unit_1", "location_type": "SCRAP",          "bay_rack": "Yard-1E North",      "capacity_description": "Steel borings, CNC chips, offcut plates"},
    # Unit 2: Finishing, Precision Sub-assembly, QC & Dispatch
    {"code": "WH-U2-RM01", "name": "Unit 2 Electricals & Fasteners Store",  "unit_id": "Unit_2", "location_type": "RAW_MATERIAL",   "bay_rack": "Bay-2A Racks 1-10", "capacity_description": "AC motors, capacitors, bearings"},
    {"code": "WH-U2-RM02", "name": "Unit 2 Polymers & Paint Store",        "unit_id": "Unit_2", "location_type": "RAW_MATERIAL",   "bay_rack": "Bay-2B Racks 1-6",  "capacity_description": "Rubber gaskets, nylon bushes, coatings"},
    {"code": "WH-U2-WIP",  "name": "Unit 2 Assembly Staging & Testing Bay", "unit_id": "Unit_2", "location_type": "WIP",            "bay_rack": "Bay-2C Assembly",   "capacity_description": "PKG-300 sub-assemblies in electrical wiring"},
    {"code": "WH-U2-FG01", "name": "Unit 2 Final Dispatch & Crated FG Bay", "unit_id": "Unit_2", "location_type": "FINISHED_GOODS", "bay_rack": "Bay-2D Dispatch",   "capacity_description": "Finished packaging machines ready for loading"},
    {"code": "WH-U2-SCRAP","name": "Unit 2 Assembly Waste & Reject Yard",   "unit_id": "Unit_2", "location_type": "SCRAP",          "bay_rack": "Yard-2E South",     "capacity_description": "Defective components, packaging scrap"},
]

# ---------------------------------------------------------------------------
# 3. RAW MATERIALS & FINISHED PRODUCTS
# ---------------------------------------------------------------------------
RAW_MATERIALS = [
    {"code": "RM-MS-PLATE-6MM",  "name": "MS Plate 6mm IS:2062",          "category_id": "CAT-RAW-STEEL",   "uom": "KG",  "hsn_code": "72085100", "reorder_level": 1200.0, "safety_stock": 600.0, "standard_cost": 68.0,  "description": "Mild Steel Plate 6mm thickness for side frame structures"},
    {"code": "RM-MS-PLATE-10MM", "name": "MS Plate 10mm IS:2062",         "category_id": "CAT-RAW-STEEL",   "uom": "KG",  "hsn_code": "72085100", "reorder_level": 800.0,  "safety_stock": 400.0, "standard_cost": 72.0,  "description": "Heavy base plate 10mm for machine bed rigidity"},
    {"code": "RM-SS-ROD-20MM",   "name": "SS Round Bar 20mm AISI 304",    "category_id": "CAT-RAW-STEEL",   "uom": "KG",  "hsn_code": "72221900", "reorder_level": 350.0,  "safety_stock": 150.0, "standard_cost": 280.0, "description": "Stainless steel 304 round bar for roller shafts"},
    {"code": "RM-CI-CAST-001",   "name": "CI Rough Body Casting Grade 25","category_id": "CAT-RAW-STEEL",   "uom": "NOS", "hsn_code": "73259100", "reorder_level": 40.0,   "safety_stock": 20.0,  "standard_cost": 18500.0,"description": "Heavy cast iron machine housing rough casting"},
    {"code": "RM-MS-CHANNEL",    "name": "MS Channel 100x50 IS:808",      "category_id": "CAT-RAW-STEEL",   "uom": "MTR", "hsn_code": "72162100", "reorder_level": 250.0,  "safety_stock": 100.0, "standard_cost": 520.0, "description": "Structural structural channel for chassis frame"},
    {"code": "RM-MOTOR-0.5HP",   "name": "AC Induction Motor 0.5 HP",     "category_id": "CAT-RAW-ELEC",    "uom": "NOS", "hsn_code": "85011000", "reorder_level": 25.0,   "safety_stock": 10.0,  "standard_cost": 4200.0, "description": "Single-phase 1440 RPM continuous duty drive motor"},
    {"code": "RM-MOTOR-1HP",     "name": "AC Induction Motor 1.0 HP",     "category_id": "CAT-RAW-ELEC",    "uom": "NOS", "hsn_code": "85011000", "reorder_level": 20.0,   "safety_stock": 8.0,   "standard_cost": 6800.0, "description": "Heavy-duty 3-phase induction drive motor"},
    {"code": "RM-BEARING-6205",  "name": "Deep Groove Ball Bearing 6205ZZ","category_id": "CAT-RAW-ELEC",   "uom": "NOS", "hsn_code": "84821000", "reorder_level": 120.0,  "safety_stock": 50.0,  "standard_cost": 240.0,  "description": "SKF precision shielded radial ball bearing"},
    {"code": "RM-CAPACITOR-25",  "name": "Motor Run Capacitor 25uF 440V",  "category_id": "CAT-RAW-ELEC",    "uom": "NOS", "hsn_code": "85322990", "reorder_level": 60.0,   "safety_stock": 25.0,  "standard_cost": 180.0,  "description": "Metallized polypropylene motor run capacitor"},
    {"code": "RM-RUBBER-GSKT",   "name": "Nitrile Rubber Gasket Strip 3mm","category_id": "CAT-RAW-POLYMER", "uom": "MTR", "hsn_code": "40081100", "reorder_level": 400.0,  "safety_stock": 180.0, "standard_cost": 95.0,   "description": "Oil-resistant nitrile sealing gasket"},
    {"code": "RM-NYLON-BUSH",    "name": "Engineering Nylon Bush 20x30mm", "category_id": "CAT-RAW-POLYMER", "uom": "NOS", "hsn_code": "39262090", "reorder_level": 220.0,  "safety_stock": 100.0, "standard_cost": 75.0,   "description": "PA6 self-lubricating wear bush"},
    {"code": "RM-WELD-ROD-E6013","name": "Welding Electrode E6013 3.15mm", "category_id": "CAT-RAW-CONS",    "uom": "KG",  "hsn_code": "83111000", "reorder_level": 80.0,   "safety_stock": 30.0,  "standard_cost": 160.0,  "description": "All-position structural mild steel welding rods"},
    {"code": "RM-CUTTING-OIL",   "name": "Water Soluble Cutting Fluid",   "category_id": "CAT-RAW-CONS",    "uom": "LTR", "hsn_code": "27101940", "reorder_level": 250.0,  "safety_stock": 100.0, "standard_cost": 210.0,  "description": "High-lubricity coolant for milling and boring"},
    {"code": "RM-PAINT-GREY",    "name": "Industrial Enamel Machine Grey", "category_id": "CAT-RAW-CONS",    "uom": "LTR", "hsn_code": "32089090", "reorder_level": 60.0,   "safety_stock": 25.0,  "standard_cost": 340.0,  "description": "Anticorrosive polyurethane industrial machine finish"},
]

FINISHED_PRODUCTS = [
    {"code": "FP-ENV-100",  "name": "Semi-Automatic Envelope Machine ENV-100", "category_id": "CAT-FP-ENV", "uom": "PCS", "drawing_no": "DWG-ENV-100-R3",  "revision_no": "R3", "standard_cost": 185000.0, "selling_price": 245000.0, "min_stock_level": 2.0, "unit_id": "Unit_1", "description": "100 env/min machine with rotary feeder and folding stations"},
    {"code": "FP-ENV-200",  "name": "Fully Automatic Envelope Machine ENV-200", "category_id": "CAT-FP-ENV", "uom": "PCS", "drawing_no": "DWG-ENV-200-R2",  "revision_no": "R2", "standard_cost": 310000.0, "selling_price": 415000.0, "min_stock_level": 1.0, "unit_id": "Unit_1", "description": "200 env/min continuous gumming, window-cutting and stacking unit"},
    {"code": "FP-PKG-300",  "name": "Automated Carton Packing Machine PKG-300",  "category_id": "CAT-FP-PKG", "uom": "PCS", "drawing_no": "DWG-PKG-300-R1",  "revision_no": "R1", "standard_cost": 420000.0, "selling_price": 565000.0, "min_stock_level": 1.0, "unit_id": "Unit_2", "description": "30 cartons/min robotic cartoning with tape and hotmelt sealer"},
    {"code": "FP-ENV-MINI", "name": "Compact Desktop Envelope Machine ENV-MINI","category_id": "CAT-FP-ENV", "uom": "PCS", "drawing_no": "DWG-ENV-MINI-R1", "revision_no": "R1", "standard_cost": 95000.0,  "selling_price": 128000.0, "min_stock_level": 3.0, "unit_id": "Unit_1", "description": "50 env/min single-phase tabletop office envelope maker"},
]

# ---------------------------------------------------------------------------
# 4. CUSTOMERS & VENDORS
# ---------------------------------------------------------------------------
CUSTOMERS = [
    {"code": "CUST-001", "name": "Ravi Stationery Mfg Pvt Ltd",      "gstin": "24AAACR1234C1Z5", "pan": "AAACR1234C", "contact_person": "Ravi Mehta",     "phone": "+91 98250 11223", "email": "purchase@ravistat.com",    "billing_address": "12 Navrangpura Commercial Complex, Ahmedabad - 380009", "shipping_address": "Plot 45, Changodar GIDC, Ahmedabad - 382213", "credit_limit": 2500000.0, "payment_terms_days": 45, "unit_id": "Unit_1"},
    {"code": "CUST-002", "name": "National Paper Converting Ind.",    "gstin": "27AAACN5678D1Z3", "pan": "AAACN5678D", "contact_person": "Deepa Shetty",    "phone": "+91 98200 44556", "email": "orders@npi.in",             "billing_address": "Saki Vihar Road, Andheri East, Mumbai - 400072",        "shipping_address": "Plot 18, TTC Industrial Area, Navi Mumbai - 400705",   "credit_limit": 4000000.0, "payment_terms_days": 30, "unit_id": "BOTH"},
    {"code": "CUST-003", "name": "Bengaluru Office Products Ltd",     "gstin": "29AAACB2345E1Z7", "pan": "AAACB2345E", "contact_person": "Sunil Kumar",     "phone": "+91 98450 77889", "email": "procurement@bopindia.in",   "billing_address": "5th Block, Koramangala Industrial Area, Bengaluru - 560034", "shipping_address": "Phase-1, Peenya Industrial Area, Bengaluru - 560058", "credit_limit": 2000000.0, "payment_terms_days": 30, "unit_id": "Unit_2"},
    {"code": "CUST-004", "name": "Delhi Automated Packaging Systems", "gstin": "07AAACD3456F1Z1", "pan": "AAACD3456F", "contact_person": "Anil Sharma",     "phone": "+91 98110 33445", "email": "anil@dps-delhi.com",        "billing_address": "Okhla Industrial Area Phase II, New Delhi - 110020",    "shipping_address": "Sector 58, IMT Faridabad, Haryana - 121004",            "credit_limit": 1500000.0, "payment_terms_days": 45, "unit_id": "Unit_1"},
    {"code": "CUST-005", "name": "Hyderabad Print & Pack Logistics",  "gstin": "36AAACH4567G1Z9", "pan": "AAACH4567G", "contact_person": "Padma Reddy",     "phone": "+91 98490 88990", "email": "padma@hppl.in",             "billing_address": "IDA Jeedimetla, Hyderabad - 500055",                    "shipping_address": "IDA Jeedimetla, Hyderabad - 500055",                    "credit_limit": 1800000.0, "payment_terms_days": 60, "unit_id": "BOTH"},
    {"code": "CUST-006", "name": "Pune Industrial Automation Traders","gstin": "27AAACP5678H1Z5", "pan": "AAACP5678H", "contact_person": "Ashish Joshi",    "phone": "+91 98220 55667", "email": "ashish@puneindustrial.com", "billing_address": "Bhosari MIDC, Pune - 411026",                           "shipping_address": "Chakan MIDC Phase-2, Pune - 410501",                     "credit_limit": 1200000.0, "payment_terms_days": 30, "unit_id": "Unit_1"},
    {"code": "CUST-007", "name": "Chennai Office Machinery Pvt Ltd",  "gstin": "33AAACM6789I1Z3", "pan": "AAACM6789I", "contact_person": "Karthik Raja",    "phone": "+91 98400 66778", "email": "karthik@comachines.in",     "billing_address": "Ambattur Industrial Estate, Chennai - 600058",          "shipping_address": "Sriperumbudur SIPCOT, Chennai - 602105",                "credit_limit": 2200000.0, "payment_terms_days": 45, "unit_id": "Unit_2"},
    {"code": "CUST-008", "name": "Kolkata Bookbinding & Stationery",  "gstin": "19AAACK7890J1Z2", "pan": "AAACK7890J", "contact_person": "Sourav Mukherjee","phone": "+91 98300 22334", "email": "sourav@kbbinders.com",      "billing_address": "Taratala Road, Kolkata - 700088",                       "shipping_address": "Dankuni Industrial Complex, Hooghly - 712311",          "credit_limit": 900000.0,  "payment_terms_days": 30, "unit_id": "BOTH"},
]

VENDORS = [
    {"code": "VEND-001", "name": "Jindal Steel & Power Ltd",     "gstin": "09AAACJ1234A1Z5", "pan": "AAACJ1234A", "contact_person": "Ramesh Gupta",   "phone": "+91 11 4105 6000", "email": "sales@jindalsteel.com", "address": "Plot 12 Sector 25, Noida - 201301",           "payment_terms_days": 30, "category": "Raw Material", "rating": 4.9},
    {"code": "VEND-002", "name": "Bharat Heavy Electrical Motors", "gstin": "27AAACB2345B1Z3", "pan": "AAACB2345B", "contact_person": "Pradeep Vora",   "phone": "+91 22 2579 3456", "email": "orders@bhemotors.com",   "address": "LBS Road, Kurla West, Mumbai - 400070",        "payment_terms_days": 45, "category": "Raw Material", "rating": 4.6},
    {"code": "VEND-003", "name": "Ahmedabad Precision Rubbers",  "gstin": "24AAACA3456C1Z7", "pan": "AAACA3456C", "contact_person": "Bhavesh Patel",  "phone": "+91 79 2240 5678", "email": "bhavesh@apr-india.com",   "address": "Naroda GIDC Phase-1, Ahmedabad - 382330",       "payment_terms_days": 30, "category": "Raw Material", "rating": 4.3},
    {"code": "VEND-004", "name": "Indian Industrial Welding Rods","gstin": "24AAACI4567D1Z1", "pan": "AAACI4567D", "contact_person": "Mahesh Shah",    "phone": "+91 79 2250 1234", "email": "mahesh@iiwrods.com",      "address": "Vatva GIDC Phase-2, Ahmedabad - 382445",        "payment_terms_days": 30, "category": "Consumable",   "rating": 4.1},
    {"code": "VEND-005", "name": "SKF Bearings India Ltd",       "gstin": "24AAACS5678E1Z9", "pan": "AAACS5678E", "contact_person": "Neerav Jain",    "phone": "+91 79 2657 3000", "email": "neerav@skfbearings.in",  "address": "Ring Road, Surat - 395002",                     "payment_terms_days": 60, "category": "Raw Material", "rating": 4.9},
    {"code": "VEND-006", "name": "Servo Petro Lubricants & Oils", "gstin": "27AAACRP678F1Z5", "pan": "AAACRP678F", "contact_person": "Sangeeta Nair",  "phone": "+91 22 4477 0000", "email": "lubricants@servooil.in",  "address": "MIDC Mahape, Navi Mumbai - 400710",             "payment_terms_days": 30, "category": "Consumable",   "rating": 4.4},
    {"code": "VEND-007", "name": "Gujarat Precision Castings Ltd","gstin": "24AAACG7890G1Z1", "pan": "AAACG7890G", "contact_person": "Yogesh Trivedi", "phone": "+91 265 2341567",  "email": "yogesh@gujcastings.com", "address": "Makarpura GIDC, Vadodara - 390010",           "payment_terms_days": 45, "category": "Raw Material", "rating": 4.5},
    {"code": "VEND-008", "name": "Asian Industrial Paint Systems","gstin": "24AAACA9012K1Z8", "pan": "AAACA9012K", "contact_person": "Dharmesh Soni",  "phone": "+91 79 2583 0011", "email": "dharmesh@aipaints.com",   "address": "Odhav Industrial Area, Ahmedabad - 382415",     "payment_terms_days": 30, "category": "Consumable",   "rating": 4.2},
]

# ---------------------------------------------------------------------------
# 5. SHIFT CONFIGURATIONS
# ---------------------------------------------------------------------------
SHIFTS = [
    {"shift_code": "SHIFT-GEN",   "name": "General Administrative & Tech Shift", "shift_type": "GENERAL", "start_time": "09:00", "end_time": "18:00", "break_duration_minutes": 60, "grace_period_minutes": 15, "standard_work_hours": 8.0, "unit_id": "BOTH"},
    {"shift_code": "SHIFT-MORN",  "name": "Morning Machining & Fabrication Shift", "shift_type": "SHIFT_1", "start_time": "06:00", "end_time": "14:00", "break_duration_minutes": 30, "grace_period_minutes": 10, "standard_work_hours": 8.0, "unit_id": "Unit_1"},
    {"shift_code": "SHIFT-EVE",   "name": "Evening Assembly & Wiring Shift",       "shift_type": "SHIFT_2", "start_time": "14:00", "end_time": "22:00", "break_duration_minutes": 30, "grace_period_minutes": 10, "standard_work_hours": 8.0, "unit_id": "Unit_2"},
    {"shift_code": "SHIFT-NIGHT", "name": "Overnight Continuous Boring Shift",      "shift_type": "NIGHT",   "start_time": "22:00", "end_time": "06:00", "break_duration_minutes": 30, "grace_period_minutes": 10, "standard_work_hours": 8.0, "unit_id": "BOTH"},
]

# ---------------------------------------------------------------------------
# 6. EMPLOYEES & USERS MANIFEST (34 Accounts, All 8 Departments + Edge Cases)
# ---------------------------------------------------------------------------
EMPLOYEES_DATA = [
    # ------------------------------------------------------------------------
    # 1. Production Department (Unit 1 & Unit 2)
    # ------------------------------------------------------------------------
    {
        "code": "EMP-101",
        "full_name": "Rahul Sharma",
        "email": "rahulsharma@rgtech.com",
        "username": "rahul_sharma",
        "phone": "+91 98200 10001",
        "department": "Production Department",
        "designation": "Production Manager",
        "job_role": "Production Manager",
        "job_roles": ["Production Manager", "Production Planner"],
        "role": RoleName.PRODUCTION_MANAGER.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_1",
        "allowed_units": ["Unit_1", "Unit_2", "BOTH"],
        "joining_date": "2022-01-15",
        "salary": 95000.0,
        "status": "ACTIVE",
        "manager_email": "admin@rgtech.com",
        "emergency_contact": "+91 98200 90001",
    },
    {
        "code": "EMP-102",
        "full_name": "Amit Patel",
        "email": "amitpatel@rgtech.com",
        "username": "amit_patel",
        "phone": "+91 98200 10002",
        "department": "Production Department",
        "designation": "Production Supervisor",
        "job_role": "Production Supervisor",
        "job_roles": ["Production Supervisor", "Shift In-charge"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_1",
        "allowed_units": ["Unit_1"],
        "joining_date": "2022-06-01",
        "salary": 55000.0,
        "status": "ACTIVE",
        "manager_email": "rahulsharma@rgtech.com",
        "emergency_contact": "+91 98200 90002",
    },
    {
        "code": "EMP-103",
        "full_name": "Jagdish Panchal",
        "email": "jagdishpanchal@rgtech.com",
        "username": "jagdish_panchal",
        "phone": "+91 98200 10003",
        "department": "Production Department",
        "designation": "Machine Operator",
        "job_role": "Machine Operator",
        "job_roles": ["Machine Operator"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_1",
        "allowed_units": ["Unit_1"],
        "joining_date": "2023-02-10",
        "salary": 36000.0,
        "status": "ACTIVE",
        "manager_email": "amitpatel@rgtech.com",
        "emergency_contact": "+91 98200 90003",
    },
    {
        "code": "EMP-104",
        "full_name": "Suresh Suthar",
        "email": "sureshsuthar@rgtech.com",
        "username": "suresh_suthar",
        "phone": "+91 98200 10004",
        "department": "Production Department",
        "designation": "Assembly Operator",
        "job_role": "Assembly Operator",
        "job_roles": ["Assembly Operator", "Shift In-charge"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_2",
        "allowed_units": ["Unit_2"],
        "joining_date": "2023-04-15",
        "salary": 52000.0,
        "status": "ACTIVE",
        "manager_email": "rahulsharma@rgtech.com",
        "emergency_contact": "+91 98200 90004",
    },

    # ------------------------------------------------------------------------
    # 2. Quality Control (Unit 1 & Unit 2)
    # ------------------------------------------------------------------------
    {
        "code": "EMP-105",
        "full_name": "Neha Modi",
        "email": "nehamodi@rgtech.com",
        "username": "neha_modi",
        "phone": "+91 98200 10005",
        "department": "Quality Control",
        "designation": "QC Manager",
        "job_role": "QC Manager",
        "job_roles": ["QC Manager"],
        "role": RoleName.QC_INSPECTOR.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_1",
        "allowed_units": ["Unit_1", "Unit_2", "BOTH"],
        "joining_date": "2022-03-01",
        "salary": 90000.0,
        "status": "ACTIVE",
        "manager_email": "admin@rgtech.com",
        "emergency_contact": "+91 98200 90005",
    },
    {
        "code": "EMP-106",
        "full_name": "Vikas Verma",
        "email": "vikasverma@rgtech.com",
        "username": "vikas_verma",
        "phone": "+91 98200 10006",
        "department": "Quality Control",
        "designation": "QC Inspector",
        "job_role": "QC Inspector",
        "job_roles": ["QC Inspector"],
        "role": RoleName.QC_INSPECTOR.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_2",
        "allowed_units": ["Unit_2"],
        "joining_date": "2022-08-15",
        "salary": 48000.0,
        "status": "ACTIVE",
        "manager_email": "nehamodi@rgtech.com",
        "emergency_contact": "+91 98200 90006",
    },
    {
        "code": "EMP-107",
        "full_name": "Anjali Trivedi",
        "email": "anjalitrivedi@rgtech.com",
        "username": "anjali_trivedi",
        "phone": "+91 98200 10007",
        "department": "Quality Control",
        "designation": "QA Engineer",
        "job_role": "QA Engineer",
        "job_roles": ["QA Engineer", "Testing Technician"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_1",
        "allowed_units": ["Unit_1"],
        "joining_date": "2023-01-20",
        "salary": 44000.0,
        "status": "ACTIVE",
        "manager_email": "nehamodi@rgtech.com",
        "emergency_contact": "+91 98200 90007",
    },
    {
        "code": "EMP-108",
        "full_name": "Bhavik Chauhan",
        "email": "bhavikchauhan@rgtech.com",
        "username": "bhavik_chauhan",
        "phone": "+91 98200 10008",
        "department": "Quality Control",
        "designation": "Wastage Inspector",
        "job_role": "Wastage Inspector",
        "job_roles": ["Wastage Inspector"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_2",
        "allowed_units": ["Unit_2"],
        "joining_date": "2023-07-01",
        "salary": 34000.0,
        "status": "ACTIVE",
        "manager_email": "vikasverma@rgtech.com",
        "emergency_contact": "+91 98200 90008",
    },

    # ------------------------------------------------------------------------
    # 3. Inventory & Purchase (Unit 1 & Unit 2)
    # ------------------------------------------------------------------------
    {
        "code": "EMP-109",
        "full_name": "Suresh Raina",
        "email": "sureshraina@rgtech.com",
        "username": "suresh_raina",
        "phone": "+91 98200 10009",
        "department": "Inventory & Purchase",
        "designation": "Inventory Manager",
        "job_role": "Inventory Manager",
        "job_roles": ["Inventory Manager", "Purchase Manager"],
        "role": RoleName.INVENTORY_MANAGER.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_1",
        "allowed_units": ["Unit_1", "Unit_2", "BOTH"],
        "joining_date": "2022-02-01",
        "salary": 88000.0,
        "status": "ACTIVE",
        "manager_email": "admin@rgtech.com",
        "emergency_contact": "+91 98200 90009",
    },
    {
        "code": "EMP-110",
        "full_name": "Dinesh Karthik",
        "email": "dineshkarthik@rgtech.com",
        "username": "dinesh_karthik",
        "phone": "+91 98200 10010",
        "department": "Inventory & Purchase",
        "designation": "Storekeeper",
        "job_role": "Storekeeper",
        "job_roles": ["Storekeeper"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_2",
        "allowed_units": ["Unit_2"],
        "joining_date": "2022-09-15",
        "salary": 42000.0,
        "status": "ACTIVE",
        "manager_email": "sureshraina@rgtech.com",
        "emergency_contact": "+91 98200 90010",
    },
    {
        "code": "EMP-001",
        "full_name": "Mayank Gajjar",
        "email": "mayan@rgtech.com",
        "username": "mayank_gajjar",
        "phone": "+91 98250 12345",
        "department": "Inventory & Purchase",
        "designation": "Purchase Executive",
        "job_role": "Purchase Executive",
        "job_roles": ["Purchase Executive"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_1",
        "allowed_units": ["Unit_1"],
        "joining_date": "2023-04-01",
        "salary": 38000.0,
        "status": "ACTIVE",
        "manager_email": "sureshraina@rgtech.com",
        "emergency_contact": "+91 98250 99999",
    },
    {
        "code": "EMP-111",
        "full_name": "Paresh Solanki",
        "email": "pareshsolanki@rgtech.com",
        "username": "paresh_solanki",
        "phone": "+91 98200 10011",
        "department": "Inventory & Purchase",
        "designation": "Warehouse Executive",
        "job_role": "Warehouse Executive",
        "job_roles": ["Warehouse Executive"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_1",
        "allowed_units": ["Unit_1"],
        "joining_date": "2023-08-01",
        "salary": 35000.0,
        "status": "ACTIVE",
        "manager_email": "sureshraina@rgtech.com",
        "emergency_contact": "+91 98200 90011",
    },

    # ------------------------------------------------------------------------
    # 4. Sales & CRM (Unit 1, Unit 2 & Corporate)
    # ------------------------------------------------------------------------
    {
        "code": "EMP-112",
        "full_name": "Priya Shah",
        "email": "priyashah@rgtech.com",
        "username": "priya_shah",
        "phone": "+91 98200 10012",
        "department": "Sales & CRM",
        "designation": "Sales Manager",
        "job_role": "Sales Manager",
        "job_roles": ["Sales Manager", "Lead Manager"],
        "role": RoleName.SALES_DISPATCH.value,
        "account_type": "EMPLOYEE",
        "unit_id": "BOTH",
        "allowed_units": ["Unit_1", "Unit_2", "BOTH"],
        "joining_date": "2022-04-01",
        "salary": 92000.0,
        "status": "ACTIVE",
        "manager_email": "admin@rgtech.com",
        "emergency_contact": "+91 98200 90012",
    },
    {
        "code": "EMP-113",
        "full_name": "Rohan Gupta",
        "email": "rohangupta@rgtech.com",
        "username": "rohan_gupta",
        "phone": "+91 98200 10013",
        "department": "Sales & CRM",
        "designation": "Sales Executive",
        "job_role": "Sales Executive",
        "job_roles": ["Sales Executive"],
        "role": RoleName.SALES_DISPATCH.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_1",
        "allowed_units": ["Unit_1", "BOTH"],
        "joining_date": "2022-10-01",
        "salary": 46000.0,
        "status": "ACTIVE",
        "manager_email": "priyashah@rgtech.com",
        "emergency_contact": "+91 98200 90013",
    },
    {
        "code": "EMP-114",
        "full_name": "Meera Nair",
        "email": "meeranair@rgtech.com",
        "username": "meera_nair",
        "phone": "+91 98200 10014",
        "department": "Sales & CRM",
        "designation": "CRM Executive",
        "job_role": "CRM Executive",
        "job_roles": ["CRM Executive", "Customer Relationship Executive"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_2",
        "allowed_units": ["Unit_2", "BOTH"],
        "joining_date": "2023-03-15",
        "salary": 42000.0,
        "status": "ACTIVE",
        "manager_email": "priyashah@rgtech.com",
        "emergency_contact": "+91 98200 90014",
    },
    {
        "code": "EMP-115",
        "full_name": "Hardik Dave",
        "email": "hardikdave@rgtech.com",
        "username": "hardik_dave",
        "phone": "+91 98200 10015",
        "department": "Sales & CRM",
        "designation": "Lead Manager",
        "job_role": "Lead Manager",
        "job_roles": ["Lead Manager"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "BOTH",
        "allowed_units": ["Unit_1", "Unit_2", "BOTH"],
        "joining_date": "2023-06-01",
        "salary": 45000.0,
        "status": "ACTIVE",
        "manager_email": "priyashah@rgtech.com",
        "emergency_contact": "+91 98200 90015",
    },

    # ------------------------------------------------------------------------
    # 5. Dispatch & Logistics (Unit 1 & Unit 2)
    # ------------------------------------------------------------------------
    {
        "code": "EMP-116",
        "full_name": "Sanjay Rawat",
        "email": "sanjayrawat@rgtech.com",
        "username": "sanjay_rawat",
        "phone": "+91 98200 10016",
        "department": "Dispatch & Logistics",
        "designation": "Dispatch Manager",
        "job_role": "Dispatch Manager",
        "job_roles": ["Dispatch Manager"],
        "role": RoleName.SALES_DISPATCH.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_1",
        "allowed_units": ["Unit_1", "Unit_2", "BOTH"],
        "joining_date": "2022-05-10",
        "salary": 82000.0,
        "status": "ACTIVE",
        "manager_email": "admin@rgtech.com",
        "emergency_contact": "+91 98200 90016",
    },
    {
        "code": "EMP-117",
        "full_name": "Karan Malhotra",
        "email": "karanmalhotra@rgtech.com",
        "username": "karan_malhotra",
        "phone": "+91 98200 10017",
        "department": "Dispatch & Logistics",
        "designation": "Dispatch Executive",
        "job_role": "Dispatch Executive",
        "job_roles": ["Dispatch Executive"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_2",
        "allowed_units": ["Unit_2"],
        "joining_date": "2022-11-01",
        "salary": 44000.0,
        "status": "ACTIVE",
        "manager_email": "sanjayrawat@rgtech.com",
        "emergency_contact": "+91 98200 90017",
    },
    {
        "code": "EMP-118",
        "full_name": "Nilesh Parmar",
        "email": "nileshparmar@rgtech.com",
        "username": "nilesh_parmar",
        "phone": "+91 98200 10018",
        "department": "Dispatch & Logistics",
        "designation": "Packing Operator",
        "job_role": "Packing Operator",
        "job_roles": ["Packing Operator"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_2",
        "allowed_units": ["Unit_2"],
        "joining_date": "2023-05-15",
        "salary": 30000.0,
        "status": "ACTIVE",
        "manager_email": "sanjayrawat@rgtech.com",
        "emergency_contact": "+91 98200 90018",
    },
    {
        "code": "EMP-119",
        "full_name": "Vinod Makwana",
        "email": "vinodmakwana@rgtech.com",
        "username": "vinod_makwana",
        "phone": "+91 98200 10019",
        "department": "Dispatch & Logistics",
        "designation": "Logistics Coordinator",
        "job_role": "Logistics Coordinator",
        "job_roles": ["Logistics Coordinator"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_1",
        "allowed_units": ["Unit_1"],
        "joining_date": "2023-09-01",
        "salary": 38000.0,
        "status": "ACTIVE",
        "manager_email": "sanjayrawat@rgtech.com",
        "emergency_contact": "+91 98200 90019",
    },

    # ------------------------------------------------------------------------
    # 6. Billing & Finance (Corporate & Plants)
    # ------------------------------------------------------------------------
    {
        "code": "EMP-120",
        "full_name": "Ananya Iyer",
        "email": "ananyaiyer@rgtech.com",
        "username": "ananya_iyer",
        "phone": "+91 98200 10020",
        "department": "Billing & Finance",
        "designation": "Billing Manager",
        "job_role": "Billing Manager",
        "job_roles": ["Billing Manager", "Finance Manager"],
        "role": RoleName.ADMIN.value,
        "account_type": "ADMIN",
        "unit_id": "BOTH",
        "allowed_units": ["Unit_1", "Unit_2", "BOTH"],
        "joining_date": "2022-01-20",
        "salary": 96000.0,
        "status": "ACTIVE",
        "manager_email": "admin@rgtech.com",
        "emergency_contact": "+91 98200 90020",
    },
    {
        "code": "EMP-121",
        "full_name": "Manish Tiwari",
        "email": "manishtiwari@rgtech.com",
        "username": "manish_tiwari",
        "phone": "+91 98200 10021",
        "department": "Billing & Finance",
        "designation": "Accountant",
        "job_role": "Accountant",
        "job_roles": ["Accountant"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "BOTH",
        "allowed_units": ["Unit_1", "Unit_2", "BOTH"],
        "joining_date": "2022-07-01",
        "salary": 50000.0,
        "status": "ACTIVE",
        "manager_email": "ananyaiyer@rgtech.com",
        "emergency_contact": "+91 98200 90021",
    },
    {
        "code": "EMP-122",
        "full_name": "Swati Kulkarni",
        "email": "swatikulkarni@rgtech.com",
        "username": "swati_kulkarni",
        "phone": "+91 98200 10022",
        "department": "Billing & Finance",
        "designation": "Billing Executive",
        "job_role": "Billing Executive",
        "job_roles": ["Billing Executive"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "BOTH",
        "allowed_units": ["Unit_1", "Unit_2", "BOTH"],
        "joining_date": "2023-02-15",
        "salary": 42000.0,
        "status": "ACTIVE",
        "manager_email": "ananyaiyer@rgtech.com",
        "emergency_contact": "+91 98200 90022",
    },
    {
        "code": "EMP-123",
        "full_name": "Chirag Barot",
        "email": "chiragbarot@rgtech.com",
        "username": "chirag_barot",
        "phone": "+91 98200 10023",
        "department": "Billing & Finance",
        "designation": "Accounts Executive",
        "job_role": "Accounts Executive",
        "job_roles": ["Accounts Executive"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "BOTH",
        "allowed_units": ["Unit_1", "Unit_2", "BOTH"],
        "joining_date": "2023-10-01",
        "salary": 36000.0,
        "status": "ACTIVE",
        "manager_email": "manishtiwari@rgtech.com",
        "emergency_contact": "+91 98200 90023",
    },

    # ------------------------------------------------------------------------
    # 7. HR & Administration (Corporate & Plants)
    # ------------------------------------------------------------------------
    {
        "code": "EMP-124",
        "full_name": "Kavita Deshmukh",
        "email": "kavitadeshmukh@rgtech.com",
        "username": "kavita_deshmukh",
        "phone": "+91 98200 10024",
        "department": "HR & Administration",
        "designation": "HR Manager",
        "job_role": "HR Manager",
        "job_roles": ["HR Manager", "Payroll Manager"],
        "role": RoleName.HR.value,
        "account_type": "HR",
        "unit_id": "BOTH",
        "allowed_units": ["Unit_1", "Unit_2", "BOTH"],
        "joining_date": "2022-02-15",
        "salary": 90000.0,
        "status": "ACTIVE",
        "manager_email": "admin@rgtech.com",
        "emergency_contact": "+91 98200 90024",
    },
    {
        "code": "EMP-125",
        "full_name": "Deepak Joshi",
        "email": "deepakjoshi@rgtech.com",
        "username": "deepak_joshi",
        "phone": "+91 98200 10025",
        "department": "HR & Administration",
        "designation": "HR Executive",
        "job_role": "HR Executive",
        "job_roles": ["HR Executive", "Attendance Manager"],
        "role": RoleName.HR.value,
        "account_type": "HR",
        "unit_id": "BOTH",
        "allowed_units": ["Unit_1", "Unit_2", "BOTH"],
        "joining_date": "2022-08-01",
        "salary": 45000.0,
        "status": "ACTIVE",
        "manager_email": "kavitadeshmukh@rgtech.com",
        "emergency_contact": "+91 98200 90025",
    },
    {
        "code": "EMP-126",
        "full_name": "Pooja Patel",
        "email": "hr@rgtech.com",
        "username": "hr_admin",
        "phone": "+91 98200 10026",
        "department": "HR & Administration",
        "designation": "Payroll Manager",
        "job_role": "Payroll Manager",
        "job_roles": ["Payroll Manager", "HR Manager"],
        "role": RoleName.HR.value,
        "account_type": "HR",
        "unit_id": "BOTH",
        "allowed_units": ["Unit_1", "Unit_2", "BOTH"],
        "joining_date": "2022-03-10",
        "salary": 55000.0,
        "status": "ACTIVE",
        "manager_email": "kavitadeshmukh@rgtech.com",
        "emergency_contact": "+91 98200 90026",
    },
    {
        "code": "EMP-127",
        "full_name": "Rina Goswami",
        "email": "rinagoswami@rgtech.com",
        "username": "rina_goswami",
        "phone": "+91 98200 10027",
        "department": "HR & Administration",
        "designation": "Recruiter",
        "job_role": "Recruiter",
        "job_roles": ["Recruiter", "Office Administrator"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "BOTH",
        "allowed_units": ["Unit_1", "Unit_2", "BOTH"],
        "joining_date": "2023-04-10",
        "salary": 40000.0,
        "status": "ACTIVE",
        "manager_email": "kavitadeshmukh@rgtech.com",
        "emergency_contact": "+91 98200 90027",
    },

    # ------------------------------------------------------------------------
    # 8. Maintenance & Technical (Unit 1 & Unit 2)
    # ------------------------------------------------------------------------
    {
        "code": "EMP-128",
        "full_name": "Ramesh Solanki",
        "email": "rameshsolanki@rgtech.com",
        "username": "ramesh_solanki",
        "phone": "+91 98200 10028",
        "department": "Maintenance & Technical",
        "designation": "Maintenance Manager",
        "job_role": "Maintenance Manager",
        "job_roles": ["Maintenance Manager"],
        "role": RoleName.PRODUCTION_MANAGER.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_1",
        "allowed_units": ["Unit_1", "Unit_2", "BOTH"],
        "joining_date": "2022-02-20",
        "salary": 85000.0,
        "status": "ACTIVE",
        "manager_email": "admin@rgtech.com",
        "emergency_contact": "+91 98200 90028",
    },
    {
        "code": "EMP-129",
        "full_name": "Chetan Prajapati",
        "email": "chetanprajapati@rgtech.com",
        "username": "chetan_prajapati",
        "phone": "+91 98200 10029",
        "department": "Maintenance & Technical",
        "designation": "Maintenance Technician",
        "job_role": "Maintenance Technician",
        "job_roles": ["Maintenance Technician", "Electrician"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_2",
        "allowed_units": ["Unit_2"],
        "joining_date": "2022-09-01",
        "salary": 40000.0,
        "status": "ACTIVE",
        "manager_email": "rameshsolanki@rgtech.com",
        "emergency_contact": "+91 98200 90029",
    },
    {
        "code": "EMP-130",
        "full_name": "Bharat Mistry",
        "email": "bharatmistry@rgtech.com",
        "username": "bharat_mistry",
        "phone": "+91 98200 10030",
        "department": "Maintenance & Technical",
        "designation": "Mechanical Technician",
        "job_role": "Mechanical Technician",
        "job_roles": ["Mechanical Technician", "CNC Programmer"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_1",
        "allowed_units": ["Unit_1"],
        "joining_date": "2023-01-10",
        "salary": 38000.0,
        "status": "ACTIVE",
        "manager_email": "rameshsolanki@rgtech.com",
        "emergency_contact": "+91 98200 90030",
    },
    {
        "code": "EMP-131",
        "full_name": "Arvind Vaghela",
        "email": "arvindvaghela@rgtech.com",
        "username": "arvind_vaghela",
        "phone": "+91 98200 10031",
        "department": "Maintenance & Technical",
        "designation": "Electrician",
        "job_role": "Electrician",
        "job_roles": ["Electrician"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_2",
        "allowed_units": ["Unit_2"],
        "joining_date": "2023-06-20",
        "salary": 36000.0,
        "status": "ACTIVE",
        "manager_email": "rameshsolanki@rgtech.com",
        "emergency_contact": "+91 98200 90031",
    },

    # ------------------------------------------------------------------------
    # 9. QA Edge Cases: Empty State, Inactive, Special Characters
    # ------------------------------------------------------------------------
    {
        "code": "EMP-132",
        "full_name": "Tanya Saxena",
        "email": "tanyasaxena@rgtech.com",
        "username": "tanya_saxena",
        "phone": "+91 98200 10032",
        "department": "Production Department",
        "designation": "Production Planner",
        "job_role": "Production Planner",
        "job_roles": ["Production Planner"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_1",
        "allowed_units": ["Unit_1"],
        "joining_date": date_str(d_ago(2)),  # New joiner 2 days ago
        "salary": 48000.0,
        "status": "ACTIVE",
        "manager_email": "rahulsharma@rgtech.com",
        "emergency_contact": "+91 98200 90032",
        "_is_new_joiner": True,  # Edge case: zero historical tasks/leaves
    },
    {
        "code": "EMP-133",
        "full_name": "Rajesh Khanna",
        "email": "rajeshkhanna@rgtech.com",
        "username": "rajesh_khanna",
        "phone": "+91 98200 10033",
        "department": "Quality Control",
        "designation": "Testing Technician",
        "job_role": "Testing Technician",
        "job_roles": ["Testing Technician"],
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "unit_id": "Unit_2",
        "allowed_units": ["Unit_2"],
        "joining_date": "2023-01-15",
        "salary": 35000.0,
        "status": "INACTIVE",
        "is_active": False,  # Edge case: Inactive user
        "manager_email": "nehamodi@rgtech.com",
        "emergency_contact": "+91 98200 90033",
    },
    {
        "code": "EMP-134",
        "full_name": "O'Connor-Fernandez D'Souza",
        "email": "oconnor.dsouza@rgtech.com",
        "username": "oconnor_dsouza",
        "phone": "+91 98200 10034",
        "department": "Billing & Finance",
        "designation": "Finance Manager",
        "job_role": "Finance Manager",
        "job_roles": ["Finance Manager"],
        "role": RoleName.ADMIN.value,
        "account_type": "ADMIN",
        "unit_id": "BOTH",
        "allowed_units": ["Unit_1", "Unit_2", "BOTH"],
        "joining_date": "2023-05-01",
        "salary": 98000.0,
        "status": "ACTIVE",
        "manager_email": "admin@rgtech.com",
        "emergency_contact": "+91 98200 90034",
    },
]

# ---------------------------------------------------------------------------
# 7. CHART OF ACCOUNTS (Finance)
# ---------------------------------------------------------------------------
ACCOUNTS = [
    {"account_code": "1000-CASH",                  "name": "Petty Cash",                         "account_type": "ASSET",     "unit_id": "BOTH", "description": "Cash on hand"},
    {"account_code": "1010-BANK-HDFC",             "name": "HDFC Bank Operating Account",        "account_type": "ASSET",     "unit_id": "BOTH", "description": "Primary operating bank account"},
    {"account_code": "1020-BANK-SBI",              "name": "SBI Current Account",                "account_type": "ASSET",     "unit_id": "BOTH", "description": "Secondary collections bank account"},
    {"account_code": "1100-ACCOUNTS-RECEIVABLE",   "name": "Trade Accounts Receivable",          "account_type": "ASSET",     "unit_id": "BOTH", "description": "Customer invoice receivables"},
    {"account_code": "1200-RAW-MATERIAL-INVENTORY","name": "Raw Material Inventory Valuation",   "account_type": "ASSET",     "unit_id": "BOTH", "description": "Stock balance of raw materials"},
    {"account_code": "1210-FINISHED-GOODS-INVENTORY","name":"Finished Goods Inventory Valuation", "account_type": "ASSET",     "unit_id": "BOTH", "description": "Stock balance of finished envelope and packaging machines"},
    {"account_code": "1220-WIP-INVENTORY",         "name": "Work-in-Progress (WIP) Valuation",    "account_type": "ASSET",     "unit_id": "BOTH", "description": "Machining and assembly WIP buffer value"},
    {"account_code": "1500-PLANT-MACHINERY",       "name": "Plant & Machinery (Gross)",          "account_type": "ASSET",     "unit_id": "BOTH", "description": "Heavy CNC milling, boring machines and lathes"},
    {"account_code": "1510-ACCUM-DEPRECIATION",    "name": "Accumulated Depreciation",           "account_type": "ASSET",     "unit_id": "BOTH", "description": "Cumulative depreciation reserve"},
    {"account_code": "2000-ACCOUNTS-PAYABLE",      "name": "Trade Accounts Payable",             "account_type": "LIABILITY", "unit_id": "BOTH", "description": "Outstanding vendor bills"},
    {"account_code": "2100-PF-PAYABLE",            "name": "Provident Fund (PF) Payable",        "account_type": "LIABILITY", "unit_id": "BOTH", "description": "Employee and employer PF liability"},
    {"account_code": "2110-ESI-PAYABLE",           "name": "ESI Contribution Payable",           "account_type": "LIABILITY", "unit_id": "BOTH", "description": "Employee state insurance liability"},
    {"account_code": "2120-PT-PAYABLE",            "name": "Professional Tax (PT) Payable",      "account_type": "LIABILITY", "unit_id": "BOTH", "description": "State professional tax liability"},
    {"account_code": "2130-TDS-PAYABLE",           "name": "TDS Withholding Tax Payable",        "account_type": "LIABILITY", "unit_id": "BOTH", "description": "TDS deducted from vendor and payroll disbursements"},
    {"account_code": "2140-SALARY-NET-PAYABLE",    "name": "Net Salaries & Wages Payable",       "account_type": "LIABILITY", "unit_id": "BOTH", "description": "Net unpaid monthly payroll balance"},
    {"account_code": "2200-GST-OUTPUT-PAYABLE",    "name": "GST Output Tax Payable",             "account_type": "LIABILITY", "unit_id": "BOTH", "description": "GST collected on machine deliveries"},
    {"account_code": "2210-GST-INPUT-CREDIT",      "name": "GST Input Tax Credit (ITC)",         "account_type": "ASSET",     "unit_id": "BOTH", "description": "GST paid on raw material and consumable procurement"},
    {"account_code": "3000-SHARE-CAPITAL",         "name": "Paid-Up Equity Share Capital",       "account_type": "EQUITY",    "unit_id": "BOTH", "description": "Owner contributed equity capital"},
    {"account_code": "3100-RETAINED-EARNINGS",     "name": "Retained Earnings / Surplus",        "account_type": "EQUITY",    "unit_id": "BOTH", "description": "Accumulated operating profits"},
    {"account_code": "4000-SALES-REVENUE",         "name": "Sales Revenue - Machinery",          "account_type": "REVENUE",   "unit_id": "BOTH", "description": "Commercial machine sales revenue"},
    {"account_code": "4100-SCRAP-SALES-REVENUE",   "name": "Scrap & Waste Sales Revenue",        "account_type": "REVENUE",   "unit_id": "BOTH", "description": "Revenue from recycling metal chips and scrap"},
    {"account_code": "5000-RAW-MATERIAL-CONSUMPTION","name":"Direct Material Consumption",       "account_type": "EXPENSE",   "unit_id": "BOTH", "description": "Direct steel and components consumed in production"},
    {"account_code": "5100-DIRECT-LABOR-WAGES",    "name": "Direct Shopfloor Wages & Salaries",  "account_type": "EXPENSE",   "unit_id": "BOTH", "description": "Production and machinist compensation"},
    {"account_code": "5200-POWER-ELECTRICITY-EXPENSE","name":"Factory Power & Electricity Cost",  "account_type": "EXPENSE",   "unit_id": "BOTH", "description": "HT and LT electricity consumption expense"},
    {"account_code": "5300-OPERATING-EXPENSES",    "name": "General Factory Overheads",          "account_type": "EXPENSE",   "unit_id": "BOTH", "description": "Maintenance, freight, safety gear, office utilities"},
    {"account_code": "5400-SCRAP-LOSS-EXPENSE",    "name": "Production Scrap & Rejection Loss",  "account_type": "EXPENSE",   "unit_id": "BOTH", "description": "Material machining variance and scrapped parts"},
]

# ---------------------------------------------------------------------------
# Helper: Verify Environment Safety
# ---------------------------------------------------------------------------
def verify_environment_safety():
    env = os.getenv("ENVIRONMENT", settings.ENVIRONMENT).lower()
    if env in ["prod", "production"] or settings.is_production:
        print("[FATAL] Seeding is STRICTLY PROHIBITED in production environments!")
        sys.exit(1)

# ---------------------------------------------------------------------------
# SEEDING ROUTINES
# ---------------------------------------------------------------------------

async def seed_system_roles(db):
    roles_col = db["roles"]
    count = 0
    for role_name, perms in DEFAULT_ROLE_PERMISSIONS.items():
        doc = {
            "name": role_name.value,
            "permissions": perms,
            "description": f"Standard {role_name.value} access role for Opti Matrix ERP",
            "updated_at": NOW,
            "_seed": SEED_TAG,
        }
        await roles_col.replace_one({"name": role_name.value}, doc, upsert=True)
        count += 1
    print(f"  [ROLES] Upserted {count} RBAC roles.")

async def seed_categories_and_uoms(db) -> Tuple[Dict[str, str], Dict[str, str]]:
    cat_map, uom_map = {}, {}
    for col_name in ["master_categories", "categories"]:
        col = db[col_name]
        for c in CATEGORIES:
            doc = {**c, "is_active": True, "_seed": SEED_TAG, "created_at": NOW, "updated_at": NOW}
            res = await col.replace_one({"code": c["code"]}, doc, upsert=True)
            if col_name == "categories":
                existing = await col.find_one({"code": c["code"]})
                cat_map[c["code"]] = str(existing["_id"])
    for col_name in ["master_uoms", "uom"]:
        col = db[col_name]
        for u in UOMS:
            doc = {**u, "is_active": True, "_seed": SEED_TAG, "created_at": NOW, "updated_at": NOW}
            await col.replace_one({"code": u["code"]}, doc, upsert=True)
            if col_name == "uom":
                existing = await col.find_one({"code": u["code"]})
                uom_map[u["code"]] = str(existing["_id"])
    print(f"  [MASTER] Seeded {len(CATEGORIES)} Categories and {len(UOMS)} UoMs.")
    return cat_map, uom_map

async def seed_warehouses(db) -> Dict[str, Dict[str, Any]]:
    wh_map = {}
    for col_name in ["master_warehouses", "warehouses"]:
        col = db[col_name]
        for w in WAREHOUSES:
            doc = {**w, "is_active": True, "_seed": SEED_TAG, "created_at": NOW, "updated_at": NOW}
            await col.replace_one({"code": w["code"]}, doc, upsert=True)
            if col_name == "warehouses":
                existing = await col.find_one({"code": w["code"]})
                wh_map[w["code"]] = {"id": str(existing["_id"]), "code": w["code"], "name": w["name"], "unit_id": w["unit_id"]}
    print(f"  [WAREHOUSES] Seeded {len(WAREHOUSES)} Warehouses across Unit 1 and Unit 2.")
    return wh_map

async def seed_materials_and_products(db) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    mat_map, prod_map = {}, {}
    for col_name in ["master_raw_materials", "raw_materials"]:
        col = db[col_name]
        for rm in RAW_MATERIALS:
            doc = {**rm, "unit_id": "BOTH", "is_active": True, "_seed": SEED_TAG, "created_at": NOW, "updated_at": NOW}
            await col.replace_one({"code": rm["code"]}, doc, upsert=True)
            if col_name == "raw_materials":
                existing = await col.find_one({"code": rm["code"]})
                mat_map[rm["code"]] = {"id": str(existing["_id"]), "code": rm["code"], "name": rm["name"], "cost": rm["standard_cost"], "uom": rm["uom"]}
    for col_name in ["master_finished_products", "finished_products"]:
        col = db[col_name]
        for fp in FINISHED_PRODUCTS:
            doc = {**fp, "is_active": True, "_seed": SEED_TAG, "created_at": NOW, "updated_at": NOW}
            await col.replace_one({"code": fp["code"]}, doc, upsert=True)
            if col_name == "finished_products":
                existing = await col.find_one({"code": fp["code"]})
                prod_map[fp["code"]] = {"id": str(existing["_id"]), "code": fp["code"], "name": fp["name"], "price": fp["selling_price"], "cost": fp["standard_cost"], "uom": fp["uom"], "unit_id": fp["unit_id"]}
    print(f"  [CATALOG] Seeded {len(RAW_MATERIALS)} Raw Materials and {len(FINISHED_PRODUCTS)} Finished Products.")
    return mat_map, prod_map

async def seed_customers_and_vendors(db) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    cust_map, vend_map = {}, {}
    for col_name in ["master_customers", "customers"]:
        col = db[col_name]
        for c in CUSTOMERS:
            doc = {**c, "is_active": True, "_seed": SEED_TAG, "created_at": NOW, "updated_at": NOW}
            await col.replace_one({"code": c["code"]}, doc, upsert=True)
            if col_name == "customers":
                existing = await col.find_one({"code": c["code"]})
                cust_map[c["code"]] = {"id": str(existing["_id"]), "code": c["code"], "name": c["name"], "unit_id": c["unit_id"]}
    for col_name in ["master_vendors", "vendors"]:
        col = db[col_name]
        for v in VENDORS:
            doc = {**v, "unit_id": "BOTH", "is_active": True, "_seed": SEED_TAG, "created_at": NOW, "updated_at": NOW}
            await col.replace_one({"code": v["code"]}, doc, upsert=True)
            if col_name == "vendors":
                existing = await col.find_one({"code": v["code"]})
                vend_map[v["code"]] = {"id": str(existing["_id"]), "code": v["code"], "name": v["name"]}
    print(f"  [PARTNERS] Seeded {len(CUSTOMERS)} Customers and {len(VENDORS)} Vendors.")
    return cust_map, vend_map

async def seed_shifts(db):
    for col_name in ["shifts", "hr_shift_configs"]:
        col = db[col_name]
        for s in SHIFTS:
            doc = {**s, "is_active": True, "_seed": SEED_TAG, "created_at": NOW, "created_by": "SYSTEM"}
            await col.replace_one({"shift_code": s["shift_code"]}, doc, upsert=True)
    print(f"  [SHIFTS] Seeded {len(SHIFTS)} Work Shifts.")

async def seed_chart_of_accounts(db):
    for col_name in ["accounts", "finance_accounts"]:
        col = db[col_name]
        for a in ACCOUNTS:
            doc = {**a, "is_active": True, "current_balance": 0.0, "_seed": SEED_TAG, "created_at": NOW}
            await col.replace_one({"account_code": a["account_code"]}, doc, upsert=True)
    print(f"  [FINANCE] Seeded {len(ACCOUNTS)} Chart of Accounts.")

# ---------------------------------------------------------------------------
# 8. SEED EMPLOYEES & USERS
# ---------------------------------------------------------------------------
async def seed_employees_and_users(db) -> Dict[str, Dict[str, Any]]:
    users_col = db["users"]
    emp_col = db["employees"]
    sal_col = db["salary_structures"]

    # Pre-hash known dev password using Argon2id
    pass_hash = hash_password(DEFAULT_TEST_PASSWORD)

    # Ensure Super Admin (Ritesh Gajjar) account exists
    admin_user = await users_col.find_one({"email": "admin@rgtech.com"})
    if not admin_user:
        admin_doc = {
            "email": "admin@rgtech.com",
            "username": "admin",
            "full_name": "Ritesh Gajjar",
            "hashed_password": pass_hash,
            "role": RoleName.SUPER_ADMIN.value,
            "account_type": "SUPER_ADMIN",
            "department": "Executive Management",
            "job_role": "Director",
            "job_roles": ["Director"],
            "allowed_units": ["Unit_1", "Unit_2", "BOTH"],
            "is_active": True,
            "must_change_password": False,
            "created_at": d_ago(365),
            "_seed": SEED_TAG,
        }
        res = await users_col.insert_one(admin_doc)
        admin_id = str(res.inserted_id)
    else:
        admin_id = str(admin_user["_id"])

    # Map of manager emails to resolved user IDs
    manager_id_map = {"admin@rgtech.com": admin_id}
    emp_map = {}

    for emp_data in EMPLOYEES_DATA:
        email = emp_data["email"].lower()
        code = emp_data["code"]

        # Resolve reporting manager
        mgr_email = emp_data.get("manager_email", "admin@rgtech.com")
        reporting_mgr_id = manager_id_map.get(mgr_email, admin_id)
        mgr_user = await users_col.find_one({"email": mgr_email})
        reporting_mgr_name = mgr_user.get("full_name", "Ritesh Gajjar") if mgr_user else "Ritesh Gajjar"

        # Resolve permissions
        dummy_user_doc = {
            "role": emp_data["role"],
            "job_role": emp_data["job_role"],
            "job_roles": emp_data["job_roles"],
            "custom_permissions": [],
        }
        computed_permissions = resolve_user_permissions(dummy_user_doc)

        SPECIFIC_USER_PASSWORDS = {
            "amitpatel@rgtech.com": "Amit@rgtech.com",
            "ananyaiyer@rgtech.com": "Ananya123@rgtech.com",
            "chetanprajapati@rgtech.com": "Chetan@rgtech.com",
            "deepakjoshi@rgtech.com": "Deepak@rgtech.com",
            "hr@rgtech.com": "admin123",
            "manishtiwari@rgtech.com": "Manish@rgtech.com",
            "mayan@rgtech.com": "admin123",
            "nehamodi@rgtech.com": "Neha@rgtech.com",
            "priyashah@rgtech.com": "Priya@rgtech.com",
            "rahulsharma@rgtech.com": "Rahul@rgtech.com",
            "rajeshkhatri@rgtech.com": "Rajesh123@rgtech.com",
            "rameshsolanki@rgtech.com": "Ramesh@rgtech.com",
            "rohangupta@rgtech.com": "Rohan@rgtech.com",
            "sanjayrawat@rgtech.com": "Sanjay123@rgtech.com",
            "sureshraina@rgtech.com": "Suresh@rgtech.com",
        }
        user_pass = SPECIFIC_USER_PASSWORDS.get(email, DEFAULT_TEST_PASSWORD)
        user_pass_hash = hash_password(user_pass)

        user_doc = {
            "email": email,
            "username": emp_data["username"],
            "full_name": emp_data["full_name"],
            "hashed_password": user_pass_hash,
            "role": emp_data["role"],
            "account_type": emp_data["account_type"],
            "department": emp_data["department"],
            "job_role": emp_data["job_role"],
            "job_roles": emp_data["job_roles"],
            "employee_code": code,
            "allowed_units": emp_data["allowed_units"],
            "is_active": emp_data.get("is_active", True),
            "must_change_password": False,  # Immediate login access
            "permissions": computed_permissions,
            "reporting_officer_id": reporting_mgr_id,
            "reporting_officer_name": reporting_mgr_name,
            "created_at": datetime.strptime(emp_data["joining_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc),
            "_seed": SEED_TAG,
        }
        await users_col.replace_one({"email": email}, user_doc, upsert=True)
        active_user = await users_col.find_one({"email": email})
        user_id = str(active_user["_id"])
        manager_id_map[email] = user_id

        # Employee Master Record
        emp_doc = {
            "code": code,
            "full_name": emp_data["full_name"],
            "email": email,
            "phone": emp_data["phone"],
            "department": emp_data["department"],
            "designation": emp_data["designation"],
            "account_type": emp_data["account_type"],
            "job_role": emp_data["job_role"],
            "job_roles": emp_data["job_roles"],
            "unit_id": emp_data["unit_id"],
            "status": emp_data["status"],
            "joining_date": emp_data["joining_date"],
            "emergency_contact": emp_data["emergency_contact"],
            "reporting_officer_id": reporting_mgr_id,
            "reporting_officer_name": reporting_mgr_name,
            "is_active": emp_data.get("is_active", True),
            "created_at": datetime.strptime(emp_data["joining_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc),
            "updated_at": NOW,
            "_seed": SEED_TAG,
        }
        await emp_col.replace_one({"code": code}, emp_doc, upsert=True)
        active_emp = await emp_col.find_one({"code": code})
        emp_id = str(active_emp["_id"])

        # Salary Structure
        gross = emp_data["salary"]
        basic = round(gross * 0.50, 2)
        hra = round(gross * 0.25, 2)
        conveyance = round(gross * 0.10, 2)
        special = round(gross - (basic + hra + conveyance), 2)
        pf = round(basic * 0.12, 2)
        esi = round(gross * 0.0075, 2) if gross <= 21000.0 else 0.0
        pt = 200.0
        tds = round(gross * 0.05, 2) if gross > 50000.0 else 0.0

        sal_doc = {
            "employee_id": emp_id,
            "employee_code": code,
            "employee_name": emp_data["full_name"],
            "department": emp_data["department"],
            "designation": emp_data["designation"],
            "unit_id": emp_data["unit_id"],
            "base_monthly_salary": gross,
            "basic_salary": basic,
            "hra": hra,
            "conveyance_allowance": conveyance,
            "special_allowance": special,
            "overtime_hourly_rate": round((basic / 200.0) * 1.5, 2),
            "gross_monthly_standard": gross,
            "pf_applicable": True,
            "pf_percentage": 12.0,
            "esi_applicable": (gross <= 21000.0),
            "esi_percentage": 0.75,
            "professional_tax": pt,
            "tds_monthly": tds,
            "bank_name": "HDFC Bank Ltd",
            "bank_account_number": f"50100{code.replace('EMP-', '')}8921",
            "bank_ifsc": "HDFC0000123",
            "created_at": NOW,
            "_seed": SEED_TAG,
        }
        await sal_col.replace_one({"employee_code": code}, sal_doc, upsert=True)

        emp_map[code] = {
            "id": emp_id,
            "user_id": user_id,
            "code": code,
            "name": emp_data["full_name"],
            "email": email,
            "unit_id": emp_data["unit_id"],
            "dept": emp_data["department"],
            "desig": emp_data["designation"],
            "mgr_id": reporting_mgr_id,
            "mgr_name": reporting_mgr_name,
            "mgr_email": mgr_email,
            "is_active": emp_data.get("is_active", True),
            "is_new": emp_data.get("_is_new_joiner", False),
            "joining_date": emp_data["joining_date"],
        }

    print(f"  [PEOPLE] Seeded {len(EMPLOYEES_DATA)} Employee Accounts with Role Permissions & Salary Structures.")
    return emp_map

# ---------------------------------------------------------------------------
# 9. SEED BOMS (Bill of Materials)
# ---------------------------------------------------------------------------
async def seed_boms(db, mat_map: Dict[str, Any], prod_map: Dict[str, Any]) -> Dict[str, Any]:
    boms_col = db["boms"]
    bom_map = {}

    bom_configs = [
        {
            "bom_number": "BOM-ENV100-R3",
            "prod_code": "FP-ENV-100",
            "rev": "R3",
            "unit_id": "Unit_1",
            "components": [
                ("RM-MS-PLATE-6MM",  180.0, "KG", 5.0),
                ("RM-MS-PLATE-10MM", 80.0,  "KG", 4.0),
                ("RM-SS-ROD-20MM",   18.0,  "KG", 2.0),
                ("RM-CI-CAST-001",   1.0,   "NOS", 0.0),
                ("RM-MS-CHANNEL",    8.0,   "MTR", 3.0),
                ("RM-MOTOR-0.5HP",   2.0,   "NOS", 0.0),
                ("RM-BEARING-6205",  8.0,   "NOS", 0.0),
                ("RM-CAPACITOR-25",  2.0,   "NOS", 0.0),
                ("RM-RUBBER-GSKT",   4.0,   "MTR", 8.0),
                ("RM-NYLON-BUSH",    8.0,   "NOS", 0.0),
                ("RM-WELD-ROD-E6013",2.5,   "KG", 10.0),
                ("RM-CUTTING-OIL",   2.0,   "LTR", 0.0),
                ("RM-PAINT-GREY",    1.5,   "LTR", 5.0),
            ]
        },
        {
            "bom_number": "BOM-ENV200-R2",
            "prod_code": "FP-ENV-200",
            "rev": "R2",
            "unit_id": "Unit_1",
            "components": [
                ("RM-MS-PLATE-6MM",  260.0, "KG", 5.0),
                ("RM-MS-PLATE-10MM", 130.0, "KG", 4.0),
                ("RM-SS-ROD-20MM",   28.0,  "KG", 3.0),
                ("RM-CI-CAST-001",   2.0,   "NOS", 0.0),
                ("RM-MS-CHANNEL",    12.0,  "MTR", 3.0),
                ("RM-MOTOR-1HP",     3.0,   "NOS", 0.0),
                ("RM-BEARING-6205",  12.0,  "NOS", 0.0),
                ("RM-CAPACITOR-25",  3.0,   "NOS", 0.0),
                ("RM-RUBBER-GSKT",   6.0,   "MTR", 8.0),
                ("RM-NYLON-BUSH",    12.0,  "NOS", 0.0),
                ("RM-WELD-ROD-E6013",4.0,   "KG", 10.0),
                ("RM-CUTTING-OIL",   3.5,   "LTR", 0.0),
                ("RM-PAINT-GREY",    2.5,   "LTR", 5.0),
            ]
        },
        {
            "bom_number": "BOM-PKG300-R1",
            "prod_code": "FP-PKG-300",
            "rev": "R1",
            "unit_id": "Unit_2",
            "components": [
                ("RM-MS-PLATE-6MM",  320.0, "KG", 5.0),
                ("RM-MS-PLATE-10MM", 150.0, "KG", 4.0),
                ("RM-SS-ROD-20MM",   35.0,  "KG", 3.0),
                ("RM-CI-CAST-001",   3.0,   "NOS", 0.0),
                ("RM-MOTOR-1HP",     4.0,   "NOS", 0.0),
                ("RM-BEARING-6205",  16.0,  "NOS", 0.0),
                ("RM-RUBBER-GSKT",   8.0,   "MTR", 8.0),
                ("RM-WELD-ROD-E6013",5.0,   "KG", 10.0),
                ("RM-PAINT-GREY",    3.0,   "LTR", 5.0),
            ]
        },
        {
            "bom_number": "BOM-ENVMINI-R1",
            "prod_code": "FP-ENV-MINI",
            "rev": "R1",
            "unit_id": "Unit_1",
            "components": [
                ("RM-MS-PLATE-6MM",  65.0,  "KG", 5.0),
                ("RM-MS-CHANNEL",    4.0,   "MTR", 3.0),
                ("RM-MOTOR-0.5HP",   1.0,   "NOS", 0.0),
                ("RM-BEARING-6205",  4.0,   "NOS", 0.0),
                ("RM-CAPACITOR-25",  1.0,   "NOS", 0.0),
                ("RM-RUBBER-GSKT",   2.0,   "MTR", 8.0),
                ("RM-WELD-ROD-E6013",1.0,   "KG", 10.0),
                ("RM-PAINT-GREY",    0.8,   "LTR", 5.0),
            ]
        },
    ]

    for cfg in bom_configs:
        prod = prod_map[cfg["prod_code"]]
        items = []
        total_bom_cost = 0.0
        for mat_code, qty, uom, scrap in cfg["components"]:
            mat = mat_map[mat_code]
            gross = qty * (1.0 + (scrap / 100.0))
            cost = gross * mat["cost"]
            total_bom_cost += cost
            items.append({
                "material_id": mat["id"],
                "material_code": mat_code,
                "material_name": mat["name"],
                "quantity": qty,
                "gross_quantity": round(gross, 3),
                "uom": uom,
                "scrap_percent": scrap,
                "unit_cost": mat["cost"],
                "total_cost": round(cost, 2),
            })

        bom_doc = {
            "bom_number": cfg["bom_number"],
            "product_id": prod["id"],
            "product_code": prod["code"],
            "product_name": prod["name"],
            "revision_no": cfg["rev"],
            "unit_id": cfg["unit_id"],
            "description": f"Standard production BOM for {prod['name']} Rev {cfg['rev']}",
            "status": "APPROVED",
            "is_active": True,
            "items": items,
            "total_material_cost": round(total_bom_cost, 2),
            "approved_by": "Ritesh Gajjar",
            "approved_at": d_ago(120),
            "created_at": d_ago(180),
            "updated_at": NOW,
            "_seed": SEED_TAG,
        }
        await boms_col.replace_one({"bom_number": cfg["bom_number"]}, bom_doc, upsert=True)
        active_bom = await boms_col.find_one({"bom_number": cfg["bom_number"]})
        bom_map[cfg["bom_number"]] = {"id": str(active_bom["_id"]), "doc": bom_doc}

    print(f"  [BOM] Seeded {len(bom_configs)} Multi-Level Bills of Materials.")
    return bom_map

# ---------------------------------------------------------------------------
# 10. SEED INVENTORY STOCK & LEDGER
# ---------------------------------------------------------------------------
async def seed_inventory(db, mat_map: Dict[str, Any], prod_map: Dict[str, Any], wh_map: Dict[str, Any]):
    stock_col = db["inventory_stock"]
    ledger_col = db["inventory_ledger"]
    bal_col = db["stock_balances"]  # Reports mirror collection

    stock_records = [
        # Unit 1 Raw Materials
        ("RM-MS-PLATE-6MM",  "WH-U1-RM01", 4500.0, "BATCH-MSP6-01", True),
        ("RM-MS-PLATE-10MM", "WH-U1-RM01", 2800.0, "BATCH-MSP10-01", False),
        ("RM-SS-ROD-20MM",   "WH-U1-RM02", 220.0,  "BATCH-SS20-01", False),  # Trigger: Below reorder level!
        ("RM-CI-CAST-001",   "WH-U1-RM02", 35.0,   "BATCH-CIC-01", False),
        ("RM-MS-CHANNEL",    "WH-U1-RM01", 600.0,  "BATCH-MSC-01", False),
        ("RM-WELD-ROD-E6013","WH-U1-RM01", 180.0,  "BATCH-WR-01", False),
        ("RM-CUTTING-OIL",   "WH-U1-RM01", 450.0,  "BATCH-CO-01", False),
        ("RM-PAINT-GREY",    "WH-U1-RM01", 110.0,  "BATCH-PNT-01", False),
        # Unit 2 Raw Materials
        ("RM-MOTOR-0.5HP",   "WH-U2-RM01", 42.0,   "BATCH-MTR05-01", False),
        ("RM-MOTOR-1HP",     "WH-U2-RM01", 28.0,   "BATCH-MTR1-01", False),
        ("RM-BEARING-6205",  "WH-U2-RM01", 380.0,  "BATCH-BRG-01", False),
        ("RM-CAPACITOR-25",  "WH-U2-RM01", 140.0,  "BATCH-CAP-01", False),
        ("RM-RUBBER-GSKT",   "WH-U2-RM02", 850.0,  "BATCH-RBR-01", False),
        ("RM-NYLON-BUSH",    "WH-U2-RM02", 420.0,  "BATCH-NYL-01", False),
    ]

    total_stock = 0
    for mat_code, wh_code, qty, batch, _ in stock_records:
        mat = mat_map[mat_code]
        wh = wh_map[wh_code]
        val = round(qty * mat["cost"], 2)
        is_low = qty <= RAW_MATERIALS[[r["code"] for r in RAW_MATERIALS].index(mat_code)]["reorder_level"]

        doc = {
            "item_id": mat["id"],
            "item_code": mat_code,
            "item_name": mat["name"],
            "item_type": "RAW_MATERIAL",
            "warehouse_id": wh["id"],
            "warehouse_code": wh_code,
            "warehouse_name": wh["name"],
            "unit_id": wh["unit_id"],
            "batch_no": batch,
            "current_quantity": qty,
            "quantity": qty,  # Mirror compatibility
            "uom": mat["uom"],
            "unit_cost": mat["cost"],
            "total_valuation": val,
            "reorder_level": RAW_MATERIALS[[r["code"] for r in RAW_MATERIALS].index(mat_code)]["reorder_level"],
            "safety_stock": RAW_MATERIALS[[r["code"] for r in RAW_MATERIALS].index(mat_code)]["safety_stock"],
            "is_below_reorder": is_low,
            "is_below_minimum": is_low,
            "updated_at": NOW,
            "_seed": SEED_TAG,
        }
        await stock_col.replace_one({"item_code": mat_code, "warehouse_code": wh_code, "batch_no": batch}, doc, upsert=True)
        await bal_col.replace_one({"item_code": mat_code, "warehouse_code": wh_code}, doc, upsert=True)
        total_stock += 1

    # Finished Goods Stock
    fg_stock = [
        ("FP-ENV-100", "WH-U1-FG01", 50.0, "DEFAULT"),
        ("FP-ENV-100", "WH-U1-FG01", 20.0, "BATCH-ENV100-26A"),
        ("FP-ENV-100", "WH-U1-RM01", 30.0, "DEFAULT"),
        ("FP-ENV-200", "WH-U1-FG01", 40.0, "DEFAULT"),
        ("FP-ENV-200", "WH-U1-FG01", 15.0, "BATCH-ENV200-26A"),
        ("FP-ENV-200", "WH-U1-RM01", 25.0, "DEFAULT"),
        ("FP-PKG-300", "WH-U2-FG01", 50.0, "DEFAULT"),
        ("FP-PKG-300", "WH-U2-FG01", 15.0, "BATCH-PKG300-26A"),
        ("FP-PKG-300", "WH-U2-RM01", 20.0, "DEFAULT"),
        ("FP-ENV-MINI","WH-U1-FG01", 60.0, "DEFAULT"),
        ("FP-ENV-MINI","WH-U1-FG01", 25.0, "BATCH-MINI-26A"),
        ("FP-ENV-MINI","WH-U1-RM01", 30.0, "DEFAULT"),
    ]
    for fp_code, wh_code, qty, batch in fg_stock:
        prod = prod_map[fp_code]
        wh = wh_map[wh_code]
        val = round(qty * prod["cost"], 2)
        doc = {
            "item_id": prod["id"],
            "item_code": fp_code,
            "item_name": prod["name"],
            "item_type": "FINISHED_GOOD",
            "warehouse_id": wh["id"],
            "warehouse_code": wh_code,
            "warehouse_name": wh["name"],
            "unit_id": wh["unit_id"],
            "batch_no": batch,
            "current_quantity": qty,
            "quantity": qty,
            "uom": prod["uom"],
            "unit_cost": prod["cost"],
            "total_valuation": val,
            "reorder_level": 1.0,
            "safety_stock": 1.0,
            "is_below_reorder": False,
            "is_below_minimum": False,
            "updated_at": NOW,
            "_seed": SEED_TAG,
        }
        await stock_col.replace_one({"item_code": fp_code, "warehouse_code": wh_code, "batch_no": batch}, doc, upsert=True)
        await bal_col.replace_one({"item_code": fp_code, "warehouse_code": wh_code}, doc, upsert=True)
        total_stock += 1

    print(f"  [INVENTORY] Seeded {total_stock} Live Warehouse Stock Balances.")

# ---------------------------------------------------------------------------
# 11. SEED 10 PRODUCTION PROJECTS / ORDERS (Both Unit 1 and Unit 2)
# ---------------------------------------------------------------------------
async def seed_production_projects(db, prod_map: Dict[str, Any], bom_map: Dict[str, Any], wh_map: Dict[str, Any], emp_map: Dict[str, Any]):
    prod_col = db["production_orders"]
    outputs_col = db["production_outputs"]
    qc_col = db["qc_inspections"]

    projects_data = [
        {
            "order_number": "PRD-2026-0001",
            "prod_code": "FP-ENV-100",
            "bom_num": "BOM-ENV100-R3",
            "unit_id": "Unit_1",
            "target_wh": "WH-U1-FG01",
            "planned_qty": 5.0,
            "produced_qty": 5.0,
            "rejected_qty": 0.0,
            "status": "COMPLETED",
            "progress": 100,
            "scheduled_start": d_ago(45),
            "target_completion": d_ago(15),
            "actual_completion": d_ago(14),
            "assigned_lead": "EMP-102",  # Amit Patel
            "notes": "Project completed with 100% QA dimensional pass. Export crated.",
        },
        {
            "order_number": "PRD-2026-0002",
            "prod_code": "FP-ENV-200",
            "bom_num": "BOM-ENV200-R2",
            "unit_id": "Unit_1",
            "target_wh": "WH-U1-FG01",
            "planned_qty": 3.0,
            "produced_qty": 2.0,
            "rejected_qty": 0.0,
            "status": "IN_PROGRESS",
            "progress": 65,
            "scheduled_start": d_ago(20),
            "target_completion": d_future(10),
            "actual_completion": None,
            "assigned_lead": "EMP-101",  # Rahul Sharma
            "notes": "CNC boring and shaft milling completed. Gumming station integration ongoing.",
        },
        {
            "order_number": "PRD-2026-0003",
            "prod_code": "FP-PKG-300",
            "bom_num": "BOM-PKG300-R1",
            "unit_id": "Unit_2",
            "target_wh": "WH-U2-FG01",
            "planned_qty": 2.0,
            "produced_qty": 0.0,
            "rejected_qty": 0.0,
            "status": "IN_PROGRESS",
            "progress": 40,
            "scheduled_start": d_ago(12),
            "target_completion": d_future(18),
            "actual_completion": None,
            "assigned_lead": "EMP-104",  # Suresh Suthar
            "notes": "Unit 2 Assembly bay: Sub-assemblies wired. Awaiting stepper drive testing.",
        },
        {
            "order_number": "PRD-2026-0004",
            "prod_code": "FP-ENV-MINI",
            "bom_num": "BOM-ENVMINI-R1",
            "unit_id": "Unit_1",
            "target_wh": "WH-U1-FG01",
            "planned_qty": 10.0,
            "produced_qty": 10.0,
            "rejected_qty": 1.0,
            "status": "COMPLETED",
            "progress": 100,
            "scheduled_start": d_ago(35),
            "target_completion": d_ago(10),
            "actual_completion": d_ago(9),
            "assigned_lead": "EMP-103",  # Jagdish Panchal
            "notes": "Desktop envelope run completed. 1 frame rejected for surface porosity.",
        },
        {
            "order_number": "PRD-2026-0005",
            "prod_code": "FP-ENV-100",
            "bom_num": "BOM-ENV100-R3",
            "unit_id": "Unit_1",
            "target_wh": "WH-U1-FG01",
            "planned_qty": 4.0,
            "produced_qty": 0.0,
            "rejected_qty": 0.0,
            "status": "RELEASED",
            "progress": 15,
            "scheduled_start": d_ago(4),
            "target_completion": d_future(22),
            "actual_completion": None,
            "assigned_lead": "EMP-102",  # Amit Patel
            "notes": "Raw material requisition issued to Store A. Laser plate cutting in progress.",
        },
        {
            "order_number": "PRD-2026-0006",
            "prod_code": "FP-PKG-300",
            "bom_num": "BOM-PKG300-R1",
            "unit_id": "Unit_2",
            "target_wh": "WH-U2-FG01",
            "planned_qty": 2.0,
            "produced_qty": 0.0,
            "rejected_qty": 0.0,
            "status": "DRAFT",
            "progress": 0,
            "scheduled_start": d_future(5),
            "target_completion": d_future(35),
            "actual_completion": None,
            "assigned_lead": "EMP-104",  # Suresh Suthar
            "notes": "Edge case: Unreleased planned project awaiting motor allocation.",
        },
        {
            "order_number": "PRD-2026-0007",
            "prod_code": "FP-ENV-200",
            "bom_num": "BOM-ENV200-R2",
            "unit_id": "Unit_1",
            "target_wh": "WH-U1-FG01",
            "planned_qty": 6.0,
            "produced_qty": 4.0,
            "rejected_qty": 0.0,
            "status": "IN_PROGRESS",
            "progress": 80,
            "scheduled_start": d_ago(28),
            "target_completion": d_future(5),
            "actual_completion": None,
            "assigned_lead": "EMP-101",  # Rahul Sharma
            "notes": "Critical client order: 4 units already passed QC inspection.",
        },
        {
            "order_number": "PRD-2026-0008",
            "prod_code": "FP-PKG-300",
            "bom_num": "BOM-PKG300-R1",
            "unit_id": "Unit_2",
            "target_wh": "WH-U2-FG01",
            "planned_qty": 1.0,
            "produced_qty": 0.0,
            "rejected_qty": 0.0,
            "status": "IN_PROGRESS",
            "progress": 50,
            "scheduled_start": d_ago(15),
            "target_completion": d_future(12),
            "actual_completion": None,
            "assigned_lead": "EMP-104",  # Suresh Suthar
            "notes": "Custom automated feed conveyor sub-assembly integration.",
        },
        {
            "order_number": "PRD-2026-0009",
            "prod_code": "FP-ENV-MINI",
            "bom_num": "BOM-ENVMINI-R1",
            "unit_id": "Unit_1",
            "target_wh": "WH-U1-FG01",
            "planned_qty": 8.0,
            "produced_qty": 8.0,
            "rejected_qty": 0.0,
            "status": "COMPLETED",
            "progress": 100,
            "scheduled_start": d_ago(50),
            "target_completion": d_ago(22),
            "actual_completion": d_ago(20),
            "assigned_lead": "EMP-103",  # Jagdish Panchal
            "notes": "Batch completed ahead of schedule with zero defect rejections.",
        },
        {
            "order_number": "PRD-2026-0010",
            "prod_code": "FP-ENV-200",
            "bom_num": "BOM-ENV200-R2",
            "unit_id": "Unit_1",
            "target_wh": "WH-U1-FG01",
            "planned_qty": 2.0,
            "produced_qty": 0.0,
            "rejected_qty": 0.0,
            "status": "CANCELLED",
            "progress": 0,
            "scheduled_start": d_ago(60),
            "target_completion": d_ago(30),
            "actual_completion": None,
            "assigned_lead": "EMP-101",
            "notes": "Edge case: Client requested revision to servo motor spec; order cancelled and rebooked.",
        },
    ]

    for p in projects_data:
        prod = prod_map[p["prod_code"]]
        bom = bom_map[p["bom_num"]]
        lead_emp = emp_map[p["assigned_lead"]]
        target_wh = wh_map[p["target_wh"]]

        doc = {
            "order_number": p["order_number"],
            "product_id": prod["id"],
            "product_code": prod["code"],
            "product_name": prod["name"],
            "product_uom": prod["uom"],
            "bom_id": bom["id"],
            "bom_number": p["bom_num"],
            "bom_revision_no": bom["doc"]["revision_no"],
            "unit_id": p["unit_id"],
            "target_warehouse_id": target_wh["id"],
            "target_warehouse_code": target_wh["code"],
            "planned_quantity": p["planned_qty"],
            "produced_quantity": p["produced_qty"],
            "rejected_quantity": p["rejected_qty"],
            "status": p["status"],
            "progress_percent": p["progress"],
            "scheduled_start_date": p["scheduled_start"],
            "target_completion_date": p["target_completion"],
            "actual_completion_date": p["actual_completion"],
            "assigned_supervisor_id": lead_emp["id"],
            "assigned_supervisor_name": lead_emp["name"],
            "notes": p["notes"],
            "created_at": p["scheduled_start"],
            "updated_at": NOW,
            "_seed": SEED_TAG,
        }
        await prod_col.replace_one({"order_number": p["order_number"]}, doc, upsert=True)
        active_p = await prod_col.find_one({"order_number": p["order_number"]})
        order_id = str(active_p["_id"])

        # Seed outputs & QC if produced
        if p["produced_qty"] > 0:
            out_doc = {
                "order_id": order_id,
                "order_number": p["order_number"],
                "product_id": prod["id"],
                "product_code": prod["code"],
                "produced_quantity": p["produced_qty"],
                "rejected_quantity": p["rejected_qty"],
                "warehouse_id": target_wh["id"],
                "warehouse_code": target_wh["code"],
                "batch_no": f"BATCH-{prod['code']}-{p['order_number'][-4:]}",
                "unit_id": p["unit_id"],
                "status": "PASSED" if p["status"] == "COMPLETED" else "PENDING_INSPECTION",
                "operator_name": lead_emp["name"],
                "notes": f"Batch outputs for project {p['order_number']}",
                "created_at": p["actual_completion"] or NOW,
                "created_by": lead_emp["email"],
                "_seed": SEED_TAG,
            }
            await outputs_col.replace_one({"order_id": order_id}, out_doc, upsert=True)

            # QC Inspection record (Reports compatibility)
            qc_doc = {
                "order_id": order_id,
                "order_number": p["order_number"],
                "product_code": prod["code"],
                "product_name": prod["name"],
                "inspection_number": f"QC-2026-{p['order_number'][-4:]}",
                "inspected_quantity": p["produced_qty"],
                "passed_quantity": p["produced_qty"] - p["rejected_qty"],
                "failed_quantity": p["rejected_qty"],
                "status": "PASSED" if p["rejected_qty"] == 0 else "QUARANTINED",
                "unit_id": p["unit_id"],
                "inspector_name": "Neha Modi" if p["unit_id"] == "Unit_1" else "Vikas Verma",
                "inspection_notes": "All critical dimensional tolerances within +-0.02mm specification.",
                "created_at": p["actual_completion"] or NOW,
                "_seed": SEED_TAG,
            }
            await qc_col.replace_one({"inspection_number": qc_doc["inspection_number"]}, qc_doc, upsert=True)

    print(f"  [PROJECTS] Seeded {len(projects_data)} Industrial Production Projects across Unit 1 and Unit 2.")

# ---------------------------------------------------------------------------
# 12. SEED 115+ EMPLOYEE TASKS & MESSAGES
# ---------------------------------------------------------------------------
async def seed_employee_tasks(db, emp_map: Dict[str, Any]):
    tasks_col = db["tasks"]
    emp_tasks_col = db["employee_tasks"]
    msg_col = db["task_messages"]

    # Pre-clean existing seed tasks to ensure idempotency
    await tasks_col.delete_many({"_seed": SEED_TAG})
    await emp_tasks_col.delete_many({"_seed": SEED_TAG})
    await msg_col.delete_many({"_seed": SEED_TAG})

    # Task templates per department
    DEPT_TASK_TEMPLATES = {
        "Production Department": [
            ("Finalize Weekly CNC & Lathe Machining Schedule for Unit 1", "Coordinate spindle allocations, cutter wear inspections, and operator shifts with Week 42 delivery commitments.", "HIGH", 4, 16.0, 15.5),
            ("Investigate Spindle Vibration Anomaly on CNC Milling Station #2", "Record runout metrics with dial indicators and replace worn ceramic bearings before thermal expansion damages the head.", "URGENT", -2, 8.0, 9.5),  # Overdue edge case!
            ("Review and Approve BOM Material Issues for ENV-200 Gearing Station", "Verify MS Plate 10mm cutting layout to maximize plate utilization and minimize offcut scrap turnings.", "MEDIUM", 6, 6.0, 0.0),
            ("Conduct Scrap & Wastage Variance Audit for September Machining Batches", "Weigh collected steel turnings against theoretical scrap allowance to calibrate bill of material scrap margins.", "HIGH", 1, 12.0, 12.0),
        ],
        "Quality Control": [
            ("First-Piece Dimensional Tolerance Audit for Batch PRD-2026-0002", "Perform coordinate measuring machine (CMM) audit on 5 critical bearing housings. Tolerance: +-0.012mm.", "HIGH", 2, 8.0, 7.5),
            ("Resolve Quarantined Cast Iron Roughs with Gujarat Castings", "Evaluate blowhole porosity defects on CI Body Casting Batch #GUJ-881. Issue corrective action report (CAR).", "URGENT", -1, 10.0, 11.0),
            ("Calibrate Vernier Height Gauges and Micrometers in Metrology Room", "Perform annual secondary master block calibration check and update calibration stickers for ISO 9001 audit.", "MEDIUM", 8, 14.0, 0.0),
            ("Prepare Monthly First-Pass Yield (FPY) Quality Analytics Report", "Synthesize defect pareto analysis across Machining (Unit 1) vs Sub-assembly (Unit 2).", "LOW", 12, 10.0, 0.0),
        ],
        "Inventory & Purchase": [
            ("Cycle Count Audit for Raw Material Store A (Racks 1-12)", "Perform 100% physical count of 6mm and 10mm MS plates and cross-verify with ERP ledger balances.", "HIGH", 3, 16.0, 15.0),
            ("Emergency Purchase Requisition for 6205ZZ Deep Groove Bearings", "Stock balance below safety threshold (380 nos vs 500 nos threshold). Release PO to SKF Bearings India.", "URGENT", 1, 4.0, 3.5),
            ("Process Inward GRN for Heavy MS Channels from Jindal Steel", "Inspect mill test certificates (MTC), weigh transport lorry on weighbridge, and log heat numbers.", "MEDIUM", -3, 8.0, 8.5),
            ("Reconcile Quarantine Rejection Slips with Scrap Yard Inventory", "Segregate unusable plate punchings and schedule disposal bidding with licensed scrap recyclers.", "LOW", 14, 6.0, 0.0),
        ],
        "Sales & CRM": [
            ("Finalize Technical Machine Proposal for Navkar Packaging (2x ENV-200)", "Incorporate automated vacuum gumming specs, servo registration unit, and 45-day commissioning timeline.", "HIGH", 2, 12.0, 11.5),
            ("Follow-Up on Overdue Commercial Quote with National Paper Industries", "Address client queries regarding 3-phase power load consumption and warranty AMC terms.", "MEDIUM", -1, 6.0, 7.0),
            ("Prepare Regional Q3 Sales & Revenue Achievement Presentation", "Aggregate machinery bookings across North, West, and South zones with comparative GP% analysis.", "HIGH", 5, 14.0, 8.0),
            ("Log Tendering Requirements for Bengaluru Office Products RFP", "Extract required compliance documents, drawing specs, and earnest money deposit (EMD) parameters.", "MEDIUM", 9, 8.0, 0.0),
        ],
        "Dispatch & Logistics": [
            ("Generate E-Way Bills & Carrier Lorry Receipt for Dispatch DSP-2026-0001", "Ensure commercial invoice #INV-2026-0001 is validated with GST e-invoicing portal and transporter.", "URGENT", 1, 4.0, 4.0),
            ("Inspect Export Seaworthy Wooden Crates for 3x ENV-100 to Bengaluru", "Verify anti-moisture VCI film wrapping, desiccants, and fumigation stamp compliance.", "HIGH", 3, 8.0, 7.5),
            ("Audit Fleet Transporter Fuel & Freight Surcharges for September", "Reconcile delivery proof acknowledgments (PODs) against transporter billing statements.", "LOW", 10, 10.0, 0.0),
            ("Resolve Delayed Delivery Exception with VRL Logistics Consignment", "Track trailer vehicle breakdown near Surat and coordinate substitute transshipment prime mover.", "HIGH", -2, 6.0, 8.0),
        ],
        "Billing & Finance": [
            ("Execute Monthly Depreciation Run for CNC Plant & Machinery", "Calculate straight-line depreciation for Station #1, Station #2, and laser cutting machines.", "HIGH", 2, 8.0, 8.0),
            ("Perform GSTR-2B Input Tax Credit Reconciliation with GST Portal", "Cross-check inward purchase invoices against vendor filings to identify missing tax credits.", "HIGH", 4, 16.0, 12.0),
            ("Audit Vendor Payment Proposals for Jindal Steel & Bharat Electrical", "Verify 3-way matching of Purchase Order, Inward GRN, and Supplier Commercial Bill.", "MEDIUM", -1, 6.0, 6.5),
            ("Prepare Cash Flow & Working Capital Forecast for Q4 Procurement", "Project raw material procurement outflows against customer advance milestones and receivables.", "MEDIUM", 11, 12.0, 0.0),
        ],
        "HR & Administration": [
            ("Review and Process September Factory Overtime Disbursement Batch", "Validate biometric attendance logs against shop-floor supervisor manual punch regularizations.", "HIGH", 3, 14.0, 13.5),
            ("Conduct Factory OSHA Safety & Eye Protection Audit in Unit 1", "Inspect grinding shields, welding fume extractors, and ear protection usage on shopfloor.", "MEDIUM", 7, 10.0, 9.0),
            ("Resolve Pending Employee Medical Leave Applications and Certificates", "Audit ESIC medical certificates and update employee leave balances accordingly.", "MEDIUM", -2, 6.0, 6.5),
            ("Organize Fire Evacuation & Mock Drill with Vadodara Fire Service", "Schedule shift-wide alarm test, assign fire wardens, and replenish CO2 fire extinguishers.", "LOW", 15, 8.0, 0.0),
        ],
        "Maintenance & Technical": [
            ("Conduct Preventive Overhaul on 5-Ton Overhead EOT Crane in Unit 1", "Inspect wire rope sheaves, brake linings, limit switches, and festoon cable trolley rollers.", "HIGH", 3, 16.0, 15.0),
            ("Thermographic Infrared Scan on Unit 2 LT Electrical Switchgear", "Check for hot spots on main 400A busbar joints and circuit breaker terminal lugs.", "MEDIUM", -1, 8.0, 8.5),
            ("Replace Coolant Circulation Pump on CNC Lathe Machine #3", "Pump pressure dropping below 5 bar; install new mechanical seal and 0.5HP impellor.", "URGENT", 2, 6.0, 5.5),
            ("Update CNC Machine Tooling Offsets and G-Code Feeds Library", "Optimize feed rates for 6mm MS plate profiling to extend carbide endmill insert life.", "LOW", 12, 8.0, 0.0),
        ],
    }

    # Status distribution cycle
    STATUS_CYCLE = ["COMPLETED", "IN_PROGRESS", "SUBMITTED_FOR_REVIEW", "PENDING", "REVISIONS_REQUIRED"]
    task_count = 0

    for code, emp in emp_map.items():
        if emp.get("is_new"):
            # Empty state test account: Skip adding historical tasks
            continue

        dept = emp["dept"]
        templates = DEPT_TASK_TEMPLATES.get(dept, DEPT_TASK_TEMPLATES["Production Department"])

        for idx, (title, desc, priority, days_due, est_hrs, act_hrs) in enumerate(templates):
            task_num = f"TSK-2026-{task_count + 1:04d}"
            status = STATUS_CYCLE[(task_count) % len(STATUS_CYCLE)]
            due_d = date_str(d_future(days_due))
            created_d = d_ago(abs(days_due) + 5) if days_due <= 0 else d_ago(3)

            is_done = status in ["COMPLETED", "SUBMITTED_FOR_REVIEW"]
            submitted_d = created_d + timedelta(hours=20) if is_done else None
            reviewed_d = submitted_d + timedelta(hours=8) if status == "COMPLETED" else None

            doc = {
                "task_number": task_num,
                "title": f"[{emp['unit_id']}] {title}",
                "description": desc,
                "priority": priority,
                "status": status,
                "due_date": due_d,
                "estimated_hours": est_hrs,
                "actual_hours": act_hrs if is_done else 0.0,
                # Assignment
                "assigned_to_id": emp["id"],
                "assigned_to_code": emp["code"],
                "assigned_to_name": emp["name"],
                "assigned_to_email": emp["email"],
                # Reporting Officer
                "reporting_officer_id": emp["mgr_id"],
                "reporting_officer_name": emp["mgr_name"],
                "reporting_officer_email": emp["mgr_email"],
                # Creator
                "created_by_id": emp["mgr_id"],
                "created_by_name": emp["mgr_name"],
                "created_by_email": emp["mgr_email"],
                "unit_id": emp["unit_id"],
                "created_at": created_d,
                "updated_at": reviewed_d or submitted_d or created_d,
                # Submissions & Reviews
                "completion_note": f"Completed work on {title} according to plant engineering procedures." if is_done else None,
                "completion_evidence": f"REF-AUDIT-{task_num}.pdf" if is_done else None,
                "submitted_at": submitted_d,
                "submitted_by": emp["name"] if is_done else None,
                "reviewed_at": reviewed_d,
                "reviewed_by": emp["mgr_name"] if status == "COMPLETED" else None,
                "review_feedback": "Quality requirements inspected and verified. Approved." if status == "COMPLETED" else ("Please revise dimensional check values on page 2." if status == "REVISIONS_REQUIRED" else None),
                "_seed": SEED_TAG,
            }
            res = await tasks_col.insert_one(doc)
            doc["_id"] = res.inserted_id
            await emp_tasks_col.insert_one(doc)
            task_count += 1

            # Seed task message / comment
            msg_doc = {
                "task_id": str(res.inserted_id),
                "sender_id": emp["mgr_id"],
                "sender_name": emp["mgr_name"],
                "sender_email": emp["mgr_email"],
                "sender_role": "REPORTING_OFFICER",
                "message": f"Assigned with priority {priority}. Please ensure this complies with Unit {emp['unit_id']} safety norms.",
                "created_at": created_d + timedelta(hours=1),
                "_seed": SEED_TAG,
            }
            await msg_col.insert_one(msg_doc)

            if is_done:
                emp_reply = {
                    "task_id": str(res.inserted_id),
                    "sender_id": emp["id"],
                    "sender_name": emp["name"],
                    "sender_email": emp["email"],
                    "sender_role": "EMPLOYEE",
                    "message": f"Execution completed. All calibration tolerances verified. Ready for signoff.",
                    "created_at": submitted_d,
                    "_seed": SEED_TAG,
                }
                await msg_col.insert_one(emp_reply)

    print(f"  [TASKS] Seeded {task_count} Tasks with Full Audit History & Messages across All Employees.")

# ---------------------------------------------------------------------------
# 13. SEED 90-DAY SHIFT ATTENDANCE & CORRECTION REQUESTS
# ---------------------------------------------------------------------------
async def seed_attendance_history(db, emp_map: Dict[str, Any]):
    att_col = db["attendance_records"]
    hr_att_col = db["hr_attendance"]
    att_rep_col = db["attendance"]
    corr_col = db["attendance_correction_requests"]

    # Pre-clean seeded attendance
    await att_col.delete_many({"_seed": SEED_TAG})
    await hr_att_col.delete_many({"_seed": SEED_TAG})
    await att_rep_col.delete_many({"_seed": SEED_TAG})
    await corr_col.delete_many({"_seed": SEED_TAG})

    total_att = 0
    total_corr = 0

    for code, emp in emp_map.items():
        if emp.get("is_new"):
            # Empty state test account: Skip adding attendance history
            continue

        emp_id = emp["id"]
        emp_name = emp["name"]
        unit_id = emp["unit_id"]
        dept = emp["dept"]
        desig = emp["desig"]

        # Shift selection based on department
        if "Machining" in desig or "Operator" in desig:
            shift_code = "SHIFT-MORN"
            std_in, std_out = "06:00", "14:00"
        elif "Assembly" in desig:
            shift_code = "SHIFT-EVE"
            std_in, std_out = "14:00", "22:00"
        else:
            shift_code = "SHIFT-GEN"
            std_in, std_out = "09:00", "18:00"

        # 90 Days of attendance
        for day_offset in range(1, 91):
            dt = NOW - timedelta(days=day_offset)
            if dt.weekday() == 6:  # Skip Sundays
                continue

            date_s = date_str(dt)
            rand_factor = (hash(emp_id + date_s) % 100)

            if rand_factor < 84:
                status = "PRESENT"
                hrs = 8.0
                ot = 1.5 if (rand_factor < 18 and "Production" in dept) else 0.0
                check_in = f"{std_in[:2]}:{rand_factor % 12:02d}"
                check_out = f"{int(std_out[:2]) + int(ot)}:{30 if ot > 0 else 5:02d}"
            elif rand_factor < 89:
                status = "HALF_DAY"
                hrs = 4.0
                ot = 0.0
                check_in = f"{std_in[:2]}:05"
                check_out = "13:00"
            elif rand_factor < 95:
                status = "ON_LEAVE"
                hrs = ot = 0.0
                check_in = check_out = None
            else:
                status = "ABSENT"
                hrs = ot = 0.0
                check_in = check_out = None

            doc = {
                "employee_id": emp_id,
                "employee_code": code,
                "employee_name": emp_name,
                "department": dept,
                "designation": desig,
                "unit_id": unit_id if unit_id != "BOTH" else "Unit_1",
                "shift_code": shift_code,
                "date": date_s,
                "status": status,
                "check_in": check_in,
                "check_out": check_out,
                "hours_worked": hrs,
                "overtime_hours": ot,
                "is_corrected": False,
                "correction_reason": None,
                "corrected_by": None,
                "created_at": dt,
                "created_by": "BIOMETRIC_DEVICE_01",
                "_seed": SEED_TAG,
            }
            await att_col.insert_one(doc)
            await hr_att_col.insert_one(doc)
            await att_rep_col.insert_one(doc)
            total_att += 1

            # Seed occasional edge case attendance correction request
            if rand_factor == 42 and total_corr < 12:
                corr_doc = {
                    "employee_id": emp_id,
                    "employee_code": code,
                    "employee_name": emp_name,
                    "date": date_s,
                    "requested_check_in": std_in,
                    "requested_check_out": std_out,
                    "reason": "Biometric terminal network drop during morning shift rush; punched manually.",
                    "status": "APPROVED",
                    "approved_by": "Kavita Deshmukh",
                    "approved_at": dt + timedelta(days=1),
                    "created_at": dt,
                    "_seed": SEED_TAG,
                }
                await corr_col.insert_one(corr_doc)
                total_corr += 1

    print(f"  [ATTENDANCE] Seeded {total_att} Attendance Records (90 Days History) & {total_corr} Regularization Requests.")

# ---------------------------------------------------------------------------
# 14. SEED LEAVE REQUESTS
# ---------------------------------------------------------------------------
async def seed_leave_requests(db, emp_map: Dict[str, Any]):
    leaves_col = db["leave_requests"]
    await leaves_col.delete_many({"_seed": SEED_TAG})

    leave_types = ["CASUAL_LEAVE", "SICK_LEAVE", "EARNED_LEAVE", "UNPAID_LEAVE"]
    statuses = ["APPROVED", "APPROVED", "APPROVED", "PENDING", "REJECTED"]
    total_leaves = 0

    for code, emp in emp_map.items():
        if emp.get("is_new"):
            continue

        emp_id = emp["id"]
        # Seed 1-2 historical leaves per employee
        for l_idx in range(1, 3):
            app_num = f"LV-2026-{total_leaves + 1:04d}"
            l_type = leave_types[(total_leaves) % len(leave_types)]
            status = statuses[(total_leaves) % len(statuses)]
            start_d = d_ago(l_idx * 25)
            end_d = start_d + timedelta(days=2)

            doc = {
                "application_number": app_num,
                "employee_id": emp_id,
                "employee_code": code,
                "employee_name": emp["name"],
                "department": emp["dept"],
                "unit_id": emp["unit_id"] if emp["unit_id"] != "BOTH" else "Unit_1",
                "leave_type": l_type,
                "start_date": date_str(start_d),
                "end_date": date_str(end_d),
                "days_count": 2.0,
                "reason": f"Personal family obligations and medical consultation.",
                "status": status,
                "approved_by": "Kavita Deshmukh" if status == "APPROVED" else None,
                "approved_at": start_d - timedelta(days=2) if status == "APPROVED" else None,
                "rejection_reason": "High production rush scheduled for ENV-200 line; please reschedule." if status == "REJECTED" else None,
                "created_at": start_d - timedelta(days=3),
                "_seed": SEED_TAG,
            }
            await leaves_col.insert_one(doc)
            total_leaves += 1

    print(f"  [LEAVES] Seeded {total_leaves} Leave Applications with Approved, Pending, and Rejected Statuses.")

# ---------------------------------------------------------------------------
# 15. SEED PAYROLL RUNS & PAYSLIPS
# ---------------------------------------------------------------------------
async def seed_payroll(db, emp_map: Dict[str, Any]):
    runs_col = db["payroll_runs"]
    items_col = db["payroll_items"]

    await runs_col.delete_many({"_seed": SEED_TAG})
    await items_col.delete_many({"_seed": SEED_TAG})

    months = [
        ("PAY-2026-07", "2026-07", "July 2026", "2026-07-01", "2026-07-31", "POSTED"),
        ("PAY-2026-08", "2026-08", "August 2026", "2026-08-01", "2026-08-31", "POSTED"),
        ("PAY-2026-09", "2026-09", "September 2026", "2026-09-01", "2026-09-30", "POSTED"),
        ("PAY-2026-10", "2026-10", "October 2026", "2026-10-01", "2026-10-31", "DRAFT"),
    ]

    total_payslips = 0
    for run_num, period_str, month_lbl, s_date, e_date, run_status in months:
        gross_total = 0.0
        net_total = 0.0
        ded_total = 0.0
        count_emps = 0

        run_doc = {
            "run_number": run_num,
            "period": period_str,
            "period_label": month_lbl,
            "start_date": s_date,
            "end_date": e_date,
            "status": run_status,
            "unit_id": "Unit_1",
            "working_days_in_month": 26,
            "total_employees": len([e for e in emp_map.values() if e.get("is_active")]),
            "total_gross_payout": 0.0,
            "total_deductions": 0.0,
            "total_net_payout": 0.0,
            "gross_amount": 0.0,
            "net_amount": 0.0,
            "approved_by": "Ritesh Gajjar" if run_status == "POSTED" else None,
            "posted_by": "Ritesh Gajjar" if run_status == "POSTED" else None,
            "created_by": "Ritesh Gajjar",
            "processed_at": d_ago(10) if run_status == "POSTED" else NOW,
            "created_at": d_ago(15),
            "_seed": SEED_TAG,
        }
        res = await runs_col.insert_one(run_doc)
        run_id = str(res.inserted_id)

        for code, emp in emp_map.items():
            if not emp.get("is_active") or emp.get("is_new"):
                continue

            # Lookup salary
            sal = await db["salary_structures"].find_one({"employee_code": code})
            if not sal:
                continue

            gross = sal["base_monthly_salary"]
            basic = sal["basic_salary"]
            pf = sal["pf_percentage"] * basic / 100.0
            esi = (sal["esi_percentage"] * gross / 100.0) if sal.get("esi_applicable") else 0.0
            pt = sal["professional_tax"]
            tds = sal["tds_monthly"]
            tot_ded = pf + esi + pt + tds
            net = gross - tot_ded

            gross_total += gross
            net_total += net
            ded_total += tot_ded
            count_emps += 1

            payslip_doc = {
                "payroll_run_id": run_id,
                "run_number": run_num,
                "period": period_str,
                "employee_id": emp["id"],
                "employee_code": code,
                "employee_name": emp["name"],
                "department": emp["dept"],
                "designation": emp["desig"],
                "unit_id": emp["unit_id"] if emp["unit_id"] in ["Unit_1", "Unit_2"] else "Unit_1",
                "standard_working_days": 26,
                "working_days": 26,
                "present_days": 24.0,
                "days_present": 24,
                "paid_leave_days": 2.0,
                "unpaid_leave_days": 0.0,
                "leave_days": 2,
                "overtime_hours": 4.0,
                "basic": basic,
                "basic_salary": basic,
                "hra": sal["hra"],
                "conveyance": sal["conveyance_allowance"],
                "conveyance_allowance": sal["conveyance_allowance"],
                "special_allowance": sal["special_allowance"],
                "overtime_pay": round(sal.get("overtime_hourly_rate", 150.0) * 4.0, 2),
                "gross_earnings": gross,
                "lop_deduction": 0.0,
                "pf_deduction": pf,
                "esi_deduction": esi,
                "professional_tax": pt,
                "tds_deduction": tds,
                "total_deductions": tot_ded,
                "net_pay": net,
                "net_payable": net,
                "payment_status": "PAID" if run_status == "POSTED" else "PENDING",
                "bank_name": sal["bank_name"],
                "bank_account_number": sal["bank_account_number"],
                "bank_ifsc": sal.get("bank_ifsc", "HDFC0000123"),
                "created_at": NOW,
                "_seed": SEED_TAG,
            }
            await items_col.insert_one(payslip_doc)
            total_payslips += 1

        # Update totals in run doc
        await runs_col.update_one(
            {"_id": res.inserted_id},
            {"$set": {
                "total_gross_payout": round(gross_total, 2),
                "total_deductions": round(ded_total, 2),
                "total_net_payout": round(net_total, 2),
                "gross_amount": round(gross_total, 2),
                "net_amount": round(net_total, 2),
            }}
        )

    print(f"  [PAYROLL] Seeded {len(months)} Monthly Payroll Runs & {total_payslips} Detailed Payslips.")

# ---------------------------------------------------------------------------
# 16. SEED WASTAGE & SCRAP ENTRIES
# ---------------------------------------------------------------------------
async def seed_wastage_and_scrap(db):
    scrap_col = db["scrap_entries"]
    rep_col = db["wastage"]
    await scrap_col.delete_many({"_seed": SEED_TAG})
    await rep_col.delete_many({"_seed": SEED_TAG})

    scrap_logs = [
        ("SCRAP-2026-0001", "Unit_1", "PRD-2026-0001", "RM-MS-PLATE-6MM",  145.0, "KG", 68.0,  "MACHINING_SWARF",    "RECYCLE_INTERNAL", "APPROVED"),
        ("SCRAP-2026-0002", "Unit_1", "PRD-2026-0002", "RM-SS-ROD-20MM",   18.5,  "KG", 280.0, "CUTTING_OFFCUT",     "SCRAP_YARD_SALE",  "APPROVED"),
        ("SCRAP-2026-0003", "Unit_1", "PRD-2026-0004", "RM-CI-CAST-001",   1.0,   "NOS",18500.0,"REJECTED_DEFECTIVE", "HOLD_REVIEW",      "SUBMITTED"),
        ("SCRAP-2026-0004", "Unit_2", "PRD-2026-0003", "RM-RUBBER-GSKT",   12.0,  "MTR",95.0,  "CUTTING_OFFCUT",     "RECYCLE_INTERNAL", "APPROVED"),
        ("SCRAP-2026-0005", "Unit_1", "PRD-2026-0007", "RM-MS-PLATE-10MM", 85.0,  "KG", 72.0,  "MACHINING_SWARF",    "SCRAP_YARD_SALE",  "APPROVED"),
        ("SCRAP-2026-0006", "Unit_2", "PRD-2026-0008", "RM-NYLON-BUSH",    8.0,   "NOS",75.0,   "REJECTED_DEFECTIVE", "HOLD_REVIEW",      "SUBMITTED"),
        ("SCRAP-2026-0007", "Unit_1", "PRD-2026-0009", "RM-WELD-ROD-E6013",6.0,   "KG", 160.0, "OTHER",              "DISPOSAL",         "APPROVED"),
        ("SCRAP-2026-0008", "Unit_2", "PRD-2026-0003", "RM-BEARING-6205",  2.0,   "NOS",240.0,  "REJECTED_DEFECTIVE", "RECYCLE_INTERNAL", "APPROVED"),
    ]

    for entry_num, unit_id, prd_num, item_code, qty, uom, rate, cat, disp, st in scrap_logs:
        cost = round(qty * rate, 2)
        doc = {
            "entry_number": entry_num,
            "entry_date": date_str(d_ago(15)),
            "unit_id": unit_id,
            "production_order_number": prd_num,
            "item_id": f"ID-{item_code}",
            "item_code": item_code,
            "item_name": item_code,
            "item_type": "RAW_MATERIAL",
            "quantity": qty,
            "uom": uom,
            "unit_cost": rate,
            "standard_cost": rate,
            "total_cost": cost,
            "total_scrap_value": cost,
            "scrap_category": cat,
            "reason": f"Shop floor scrap generated during processing of {item_code}",
            "disposition": disp,
            "status": st,
            "operator_name": "Bhavik Chauhan",
            "machine_id": "MCH-VMC-01" if unit_id == "Unit_1" else "MCH-ASM-01",
            "notes": "Verified against shop floor rejection bin",
            "recorded_by": "Bhavik Chauhan",
            "approved_by": "Neha Modi" if st == "APPROVED" else None,
            "created_by": "Bhavik Chauhan",
            "created_at": d_ago(15),
            "_seed": SEED_TAG,
        }
        await scrap_col.insert_one(doc)
        await rep_col.insert_one(doc)

    print(f"  [WASTAGE] Seeded {len(scrap_logs)} Scrap & Offcut Reconciliation Logs.")

# ---------------------------------------------------------------------------
# 17. SEED ELECTRICITY READINGS & POWER OUTAGES
# ---------------------------------------------------------------------------
async def seed_power_and_electricity(db):
    readings_col = db["electricity_readings"]
    cuts_col = db["power_cuts"]
    cuts_rep_col = db["power_outages"]

    await readings_col.delete_many({"_seed": SEED_TAG})
    await cuts_col.delete_many({"_seed": SEED_TAG})
    await cuts_rep_col.delete_many({"_seed": SEED_TAG})

    # 60 Days of power readings for Unit 1 (Heavy HT meter) and Unit 2 (LT meter)
    total_readings = 0
    u1_kwh = 125000.0
    u2_kwh = 42000.0

    for day_offset in range(1, 61):
        dt = NOW - timedelta(days=day_offset)
        d_str = date_str(dt)

        # Unit 1 Reading
        u1_consumed = 980.0 + (day_offset % 12) * 15.0
        doc_u1 = {
            "reading_number": f"ELEC-U1-{61 - day_offset:04d}",
            "reading_date": d_str,
            "date": d_str,
            "unit_id": "Unit_1",
            "meter_id": "MTR-U1-HT01",
            "meter_number": "MTR-U1-HT01",
            "meter_type": "GRID_EB",
            "opening_reading_kwh": round(u1_kwh, 2),
            "closing_reading_kwh": round(u1_kwh + u1_consumed, 2),
            "units_consumed_kwh": round(u1_consumed, 2),
            "power_factor": 0.98,
            "peak_demand_kva": 240.0,
            "shift": "General",
            "status": "CONFIRMED",
            "dg_units_kwh": 35.0 if day_offset % 7 == 0 else 0.0,
            "tariff_rate_inr": 8.50,
            "total_power_cost": round(u1_consumed * 8.50, 2),
            "recorded_by": "Ramesh Solanki",
            "created_by": "Ramesh Solanki",
            "created_at": dt,
            "_seed": SEED_TAG,
        }
        u1_kwh += u1_consumed
        await readings_col.insert_one(doc_u1)
        total_readings += 1

        # Unit 2 Reading
        u2_consumed = 360.0 + (day_offset % 8) * 10.0
        doc_u2 = {
            "reading_number": f"ELEC-U2-{61 - day_offset:04d}",
            "reading_date": d_str,
            "date": d_str,
            "unit_id": "Unit_2",
            "meter_id": "MTR-U2-LT01",
            "meter_number": "MTR-U2-LT01",
            "meter_type": "GRID_EB",
            "opening_reading_kwh": round(u2_kwh, 2),
            "closing_reading_kwh": round(u2_kwh + u2_consumed, 2),
            "units_consumed_kwh": round(u2_consumed, 2),
            "power_factor": 0.99,
            "peak_demand_kva": 95.0,
            "shift": "General",
            "status": "CONFIRMED",
            "dg_units_kwh": 0.0,
            "tariff_rate_inr": 8.50,
            "total_power_cost": round(u2_consumed * 8.50, 2),
            "recorded_by": "Chetan Prajapati",
            "created_by": "Chetan Prajapati",
            "created_at": dt,
            "_seed": SEED_TAG,
        }
        u2_kwh += u2_consumed
        await readings_col.insert_one(doc_u2)
        total_readings += 1

    # Power Outages / Grid Cuts
    outages = [
        ("OUTAGE-2026-0001", "Unit_1", 45, "GRID_FAILURE", "GEB 66kV substation feeder isolator flashover", 25.0),
        ("OUTAGE-2026-0002", "Unit_2", 30, "SCHEDULED_MAINTENANCE", "Transformer tap changer maintenance", 15.0),
        ("OUTAGE-2026-0003", "Unit_1", 75, "GRID_FAILURE", "Heavy thunderstorm lightning strike on GIDC overhead lines", 40.0),
        ("OUTAGE-2026-0004", "Unit_2", 20, "LOCAL_TRIP", "Quarterly diesel generator load test and switchover", 10.0),
        ("OUTAGE-2026-0005", "Unit_1", 60, "GRID_FAILURE", "Main HT breaker trip due to industrial feeder overload", 32.0),
    ]
    for inc_num, unit_id, dur_min, cause, desc, fuel_liters in outages:
        dt_start = d_ago(dur_min // 2)
        dt_end = dt_start + timedelta(minutes=dur_min)
        out_doc = {
            "incident_number": inc_num,
            "unit_id": unit_id,
            "incident_date": date_str(dt_start),
            "start_time": dt_start,
            "end_time": dt_end,
            "duration_minutes": float(dur_min),
            "outage_duration_minutes": dur_min,
            "outage_type": cause,
            "reason": desc,
            "description": desc,
            "backup_generator_used": True,
            "fuel_consumed_liters": fuel_liters,
            "dg_diesel_consumed_litres": fuel_liters,
            "production_hours_lost": round(dur_min / 60.0, 2),
            "affected_departments": ["Machining" if unit_id == "Unit_1" else "Assembly & QC"],
            "production_order_ids": ["PRD-2026-0001" if unit_id == "Unit_1" else "PRD-2026-0003"],
            "recorded_by": "Ramesh Solanki",
            "created_by": "Ramesh Solanki",
            "created_at": dt_start,
            "_seed": SEED_TAG,
        }
        await cuts_col.insert_one(out_doc)
        await cuts_rep_col.insert_one(out_doc)

    print(f"  [POWER] Seeded {total_readings} Daily Electricity Readings & {len(outages)} Power Outage Logs.")

# ---------------------------------------------------------------------------
# 18. SEED SALES ORDERS, DISPATCHES & INVOICES
# ---------------------------------------------------------------------------
async def seed_orders_and_invoices(db, cust_map: Dict[str, Any], prod_map: Dict[str, Any]):
    orders_col = db["sales_orders"]
    orders_rep = db["orders"]
    disp_col = db["dispatch_records"]
    disp_rep = db["dispatches"]
    inv_col = db["invoices"]

    await orders_col.delete_many({"_seed": SEED_TAG})
    await orders_rep.delete_many({"_seed": SEED_TAG})
    await disp_col.delete_many({"_seed": SEED_TAG})
    await disp_rep.delete_many({"_seed": SEED_TAG})
    await inv_col.delete_many({"_seed": SEED_TAG})

    orders_data = [
        ("SO-2026-0001", "CUST-001", "FP-ENV-100", 3.0, "CONFIRMED", "Unit_1", d_ago(30), d_ago(5)),
        ("SO-2026-0002", "CUST-002", "FP-ENV-200", 2.0, "DISPATCHED", "Unit_1", d_ago(40), d_ago(12)),
        ("SO-2026-0003", "CUST-003", "FP-PKG-300", 1.0, "PARTIALLY_DISPATCHED", "Unit_2", d_ago(25), d_future(10)),
        ("SO-2026-0004", "CUST-004", "FP-ENV-MINI",5.0, "DISPATCHED", "Unit_1", d_ago(50), d_ago(20)),
        ("SO-2026-0005", "CUST-005", "FP-ENV-200", 1.0, "CONFIRMED", "BOTH", d_ago(15), d_future(15)),
        ("SO-2026-0006", "CUST-006", "FP-ENV-100", 2.0, "SUBMITTED", "Unit_1", d_ago(5), d_future(25)),
        ("SO-2026-0007", "CUST-007", "FP-PKG-300", 2.0, "CONFIRMED", "Unit_2", d_ago(18), d_future(20)),
        ("SO-2026-0008", "CUST-008", "FP-ENV-MINI",2.0, "CANCELLED", "BOTH", d_ago(45), d_ago(25)),
    ]

    total_orders = 0
    total_dispatches = 0
    total_invoices = 0

    for ord_num, cust_code, prod_code, qty, st, unit_id, ord_d, del_d in orders_data:
        cust = cust_map[cust_code]
        prod = prod_map[prod_code]
        unit_price = prod["price"]
        subtotal = round(qty * unit_price, 2)
        tax = round(subtotal * 0.18, 2)
        total = round(subtotal + tax, 2)
        total_dispatched = qty if st == "DISPATCHED" else (1.0 if st == "PARTIALLY_DISPATCHED" else 0.0)
        disp_pct = round((total_dispatched / qty) * 100.0, 1)

        order_doc = {
            "order_number": ord_num,
            "customer_id": cust["id"],
            "customer_code": cust_code,
            "customer_name": cust["name"],
            "customer_po_number": f"PO-{cust_code}-9912",
            "unit_id": unit_id if unit_id in ["Unit_1", "Unit_2"] else "Unit_1",
            "status": st,
            "order_date": ord_d,
            "delivery_due_date": date_str(del_d),
            "billing_address": f"Plot {cust_code[-3:]}, GIDC Estate, Vatva, Ahmedabad, Gujarat 382445",
            "shipping_address": f"Plot {cust_code[-3:]}, GIDC Estate, Vatva, Ahmedabad, Gujarat 382445",
            "items": [
                {
                    "product_id": prod["id"],
                    "product_code": prod_code,
                    "product_name": prod["name"],
                    "quantity": qty,
                    "unit_price": unit_price,
                    "discount_percent": 0.0,
                    "tax_percent": 18.0,
                    "dispatched_quantity": total_dispatched,
                    "subtotal": subtotal,
                    "tax_amount": tax,
                    "total_amount": total,
                    "uom": prod["uom"],
                }
            ],
            "subtotal": subtotal,
            "tax_total": tax,
            "grand_total": total,
            "total_amount": total,
            "total_ordered_qty": qty,
            "total_dispatched_qty": total_dispatched,
            "dispatch_percent": disp_pct,
            "created_by": "Priya Shah",
            "created_at": ord_d,
            "_seed": SEED_TAG,
        }
        res = await orders_col.insert_one(order_doc)
        await orders_rep.insert_one(order_doc)
        total_orders += 1
        order_id = str(res.inserted_id)

        # If dispatched or partially dispatched, seed dispatch record & invoice
        if st in ["DISPATCHED", "PARTIALLY_DISPATCHED"]:
            disp_num = f"DSP-2026-{total_dispatches + 1:04d}"
            inv_num = f"INV-2026-{total_invoices + 1:04d}"

            disp_doc = {
                "dispatch_number": disp_num,
                "order_id": order_id,
                "order_number": ord_num,
                "customer_id": cust["id"],
                "customer_name": cust["name"],
                "unit_id": unit_id if unit_id != "BOTH" else "Unit_1",
                "transporter_name": "VRL Logistics Ltd",
                "vehicle_number": "GJ-01-BX-4412",
                "lr_number": f"LR-{total_dispatches + 1042}",
                "eway_bill_number": f"2410{total_dispatches + 8900123}",
                "dispatch_date": date_str(del_d),
                "status": "DELIVERED" if st == "DISPATCHED" else "SHIPPED",
                "dispatched_by": "Sanjay Rawat",
                "created_at": del_d,
                "_seed": SEED_TAG,
            }
            await disp_col.insert_one(disp_doc)
            await disp_rep.insert_one(disp_doc)
            total_dispatches += 1

            # Tax Invoice
            inv_doc = {
                "invoice_number": inv_num,
                "order_id": order_id,
                "order_number": ord_num,
                "customer_id": cust["id"],
                "customer_code": cust_code,
                "customer_name": cust["name"],
                "unit_id": unit_id if unit_id != "BOTH" else "Unit_1",
                "invoice_date": date_str(del_d),
                "due_date": date_str(del_d + timedelta(days=30)),
                "subtotal": subtotal,
                "cgst_amount": round(tax / 2.0, 2) if "24" in cust_code else 0.0,
                "sgst_amount": round(tax / 2.0, 2) if "24" in cust_code else 0.0,
                "igst_amount": tax if "24" not in cust_code else 0.0,
                "total_tax": tax,
                "total_amount": total,
                "status": "PAID" if ord_num == "SO-2026-0004" else ("PARTIALLY_PAID" if ord_num == "SO-2026-0002" else "UNPAID"),
                "created_at": del_d,
                "_seed": SEED_TAG,
            }
            await inv_col.insert_one(inv_doc)
            total_invoices += 1

    print(f"  [COMMERCE] Seeded {total_orders} Sales Orders, {total_dispatches} Dispatches & {total_invoices} Tax Invoices.")

    # 18. Order Planning Matrix (By Variant & Length - Updated by Taha)
    await seed_order_planning(db)

# ---------------------------------------------------------------------------
# 18. SEED ORDER PLANNING (BY VARIANT AND LENGTH)
# Updated by Taha; one line per variant and length
# ---------------------------------------------------------------------------
async def seed_order_planning(db):
    plan_col = db["order_planning"]
    await plan_col.delete_many({"_seed": SEED_TAG})

    # Realistic real-world variant & length planning rows across orders
    planning_records = [
        {
            "order_number": "SO-2026-0001",
            "order_date": "2026-09-10",
            "customer": "Gujarat Heavy Machinery Pvt Ltd",
            "customer_code": "CUST-001",
            "brand": "OptiMatrix",
            "variant": "Semi-Automatic Envelope Machine ENV-100",
            "length": "100 mm",
            "order_qty": 2.0,
            "required_dispatch_date": "2026-10-15",
            "priority": "HIGH",
            "order_status": "CONFIRMED",
            "planned_qty": 2.0,
            "produced_qty": 1.0,
            "balance_qty": 1.0,
            "dispatch_qty": 0.0,
            "dispatch_balance": 2.0,
            "final_approval": "APPROVED",
            "remarks": "Sub-assembly CNC machining finished; final electrical panel wiring in progress.",
            "unit_id": "Unit_1",
            "updated_by": "Taha",
        },
        {
            "order_number": "SO-2026-0001",
            "order_date": "2026-09-10",
            "customer": "Gujarat Heavy Machinery Pvt Ltd",
            "customer_code": "CUST-001",
            "brand": "OptiMatrix",
            "variant": "Semi-Automatic Envelope Machine ENV-100 (Extended Bed)",
            "length": "150 mm",
            "order_qty": 1.0,
            "required_dispatch_date": "2026-10-18",
            "priority": "HIGH",
            "order_status": "CONFIRMED",
            "planned_qty": 1.0,
            "produced_qty": 0.0,
            "balance_qty": 1.0,
            "dispatch_qty": 0.0,
            "dispatch_balance": 1.0,
            "final_approval": "APPROVED",
            "remarks": "Custom guide rails received from Unit 1 grinding shop. Ready for assembly.",
            "unit_id": "Unit_2",
            "updated_by": "Taha",
        },
        {
            "order_number": "SO-2026-0002",
            "order_date": "2026-09-18",
            "customer": "Precision Automotive Comps Ltd",
            "customer_code": "CUST-002",
            "brand": "OptiMatrix Pro",
            "variant": "Fully-Automatic Envelope Maker ENV-200",
            "length": "200 mm",
            "order_qty": 3.0,
            "required_dispatch_date": "2026-10-28",
            "priority": "URGENT",
            "order_status": "PARTIALLY_DISPATCHED",
            "planned_qty": 3.0,
            "produced_qty": 2.0,
            "balance_qty": 1.0,
            "dispatch_qty": 1.0,
            "dispatch_balance": 2.0,
            "final_approval": "APPROVED",
            "remarks": "Unit 1 unit dispatched via VRL Logistics; remaining 2 units on final test bench.",
            "unit_id": "Unit_2",
            "updated_by": "Taha",
        },
        {
            "order_number": "SO-2026-0003",
            "order_date": "2026-09-25",
            "customer": "Apex Industrial Tools & Equip",
            "customer_code": "CUST-003",
            "brand": "OptiMatrix",
            "variant": "High-Speed Folder Gluer FG-500 (Standard)",
            "length": "120 mm",
            "order_qty": 2.0,
            "required_dispatch_date": "2026-10-30",
            "priority": "HIGH",
            "order_status": "CONFIRMED",
            "planned_qty": 2.0,
            "produced_qty": 1.0,
            "balance_qty": 1.0,
            "dispatch_qty": 0.0,
            "dispatch_balance": 2.0,
            "final_approval": "APPROVED",
            "remarks": "Rubber feeder rollers vulcanized; belt drive tension calibration pending.",
            "unit_id": "Unit_1",
            "updated_by": "Taha",
        },
        {
            "order_number": "SO-2026-0004",
            "order_date": "2026-09-02",
            "customer": "Shree Ram Engineering Works",
            "customer_code": "CUST-004",
            "brand": "OptiMatrix",
            "variant": "Rotary Die Cutter RDC-300",
            "length": "250 mm",
            "order_qty": 1.0,
            "required_dispatch_date": "2026-09-28",
            "priority": "MEDIUM",
            "order_status": "DISPATCHED",
            "planned_qty": 1.0,
            "produced_qty": 1.0,
            "balance_qty": 0.0,
            "dispatch_qty": 1.0,
            "dispatch_balance": 0.0,
            "final_approval": "APPROVED",
            "remarks": "Order complete and fully dispatched with QA compliance report.",
            "unit_id": "Unit_1",
            "updated_by": "Taha",
        },
        {
            "order_number": "SO-2026-0005",
            "order_date": "2026-10-02",
            "customer": "Kalyani Packaging Solutions",
            "customer_code": "CUST-005",
            "brand": "OptiMatrix Eco",
            "variant": "Semi-Automatic Envelope Machine ENV-100 (Eco)",
            "length": "80 mm",
            "order_qty": 4.0,
            "required_dispatch_date": "2026-11-05",
            "priority": "MEDIUM",
            "order_status": "CONFIRMED",
            "planned_qty": 4.0,
            "produced_qty": 2.0,
            "balance_qty": 2.0,
            "dispatch_qty": 0.0,
            "dispatch_balance": 4.0,
            "final_approval": "APPROVED",
            "remarks": "Milling and surface grinding underway at Unit 1. On schedule.",
            "unit_id": "Unit_1",
            "updated_by": "Taha",
        },
        {
            "order_number": "SO-2026-0005",
            "order_date": "2026-10-02",
            "customer": "Kalyani Packaging Solutions",
            "customer_code": "CUST-005",
            "brand": "OptiMatrix Eco",
            "variant": "Semi-Automatic Envelope Machine ENV-100 (Heavy)",
            "length": "120 mm",
            "order_qty": 2.0,
            "required_dispatch_date": "2026-11-10",
            "priority": "MEDIUM",
            "order_status": "CONFIRMED",
            "planned_qty": 2.0,
            "produced_qty": 0.0,
            "balance_qty": 2.0,
            "dispatch_qty": 0.0,
            "dispatch_balance": 2.0,
            "final_approval": "PENDING",
            "remarks": "Waiting for gear box batch from VEND-002 before machining.",
            "unit_id": "Unit_2",
            "updated_by": "Taha",
        },
        {
            "order_number": "SO-2026-0006",
            "order_date": "2026-10-05",
            "customer": "Mehta Paper Converters",
            "customer_code": "CUST-006",
            "brand": "OptiMatrix",
            "variant": "Paper Window Patching Machine WPM-150",
            "length": "150 mm",
            "order_qty": 1.0,
            "required_dispatch_date": "2026-11-15",
            "priority": "LOW",
            "order_status": "DRAFT",
            "planned_qty": 1.0,
            "produced_qty": 0.0,
            "balance_qty": 1.0,
            "dispatch_qty": 0.0,
            "dispatch_balance": 1.0,
            "final_approval": "PENDING",
            "remarks": "Preliminary BOM estimation complete. Awaiting final advance payment.",
            "unit_id": "Unit_2",
            "updated_by": "Taha",
        },
        {
            "order_number": "SO-2026-0007",
            "order_date": "2026-10-08",
            "customer": "Sterling Printing & Packaging",
            "customer_code": "CUST-007",
            "brand": "OptiMatrix Pro",
            "variant": "High-Speed Folder Gluer FG-500 (Pro Series)",
            "length": "180 mm",
            "order_qty": 2.0,
            "required_dispatch_date": "2026-11-20",
            "priority": "HIGH",
            "order_status": "CONFIRMED",
            "planned_qty": 2.0,
            "produced_qty": 1.0,
            "balance_qty": 1.0,
            "dispatch_qty": 0.0,
            "dispatch_balance": 2.0,
            "final_approval": "APPROVED",
            "remarks": "Main chassis casting stress-relieved. CNC spindle boring scheduled.",
            "unit_id": "Unit_1",
            "updated_by": "Taha",
        },
        {
            "order_number": "SO-2026-0008",
            "order_date": "2026-10-10",
            "customer": "Zenith Flexo Prints Pvt Ltd",
            "customer_code": "CUST-008",
            "brand": "OptiMatrix",
            "variant": "Thermal Laminating Machine TLM-400",
            "length": "160 mm",
            "order_qty": 3.0,
            "required_dispatch_date": "2026-11-25",
            "priority": "URGENT",
            "order_status": "CONFIRMED",
            "planned_qty": 3.0,
            "produced_qty": 1.0,
            "balance_qty": 2.0,
            "dispatch_qty": 0.0,
            "dispatch_balance": 3.0,
            "final_approval": "APPROVED",
            "remarks": "Heating roller hard chrome plating completed. Thermocouple wiring ongoing.",
            "unit_id": "Unit_2",
            "updated_by": "Taha",
        },
    ]

    total_planned_lines = 0
    now_dt = datetime.now(timezone.utc)
    for rec in planning_records:
        rec["created_at"] = now_dt
        rec["updated_at"] = now_dt
        rec["_seed"] = SEED_TAG
        await plan_col.insert_one(rec)
        total_planned_lines += 1

    print(f"  [ORDER PLANNING] Seeded {total_planned_lines} granular lines (one per variant and length; Updated by Taha).")

    # 19. Daily Production Planning & Actual (Main daily entry screen for Shivakumar)
    await seed_daily_production(db)

# ---------------------------------------------------------------------------
# 19. SEED DAILY PRODUCTION PLANNING & ACTUAL
# Main daily entry screen for Shivakumar (Department-wise)
# ---------------------------------------------------------------------------
async def seed_daily_production(db):
    daily_col = db["daily_production"]
    await daily_col.delete_many({"_seed": SEED_TAG})

    now_dt = datetime.now(timezone.utc)
    today_str = date_str(now_dt)
    yesterday_str = date_str(d_ago(1))
    two_days_ago = date_str(d_ago(2))

    # 15 realistic department-wise rows covering Machining, Assembly & QC, Fabrication, Grinding, Welding
    daily_records = [
        # Machining Department (Unit 1)
        {
            "date": today_str,
            "order_no": "SO-2026-0001",
            "customer": "Gujarat Heavy Machinery Pvt Ltd",
            "variant": "Semi-Automatic Envelope Machine ENV-100",
            "length": "100 mm",
            "labour": "Jagdish Panchal",
            "machine": "CNC VMC Milling Center (VMC-01)",
            "department": "Machining",
            "planned_qty": 20.0,
            "actual_qty": 20.0,
            "rework_qty": 1.0,
            "scrap_qty": 0.0,
            "good_qty": 19.0,
            "completion_pct": 95.0,
            "work_type": "REGULAR",
            "standard_target": 20.0,
            "performance_pct": 100.0,
            "daily_earned_inr": 1140.0,
            "rate_per_unit": 60.0,
            "start_time": "08:30 AM",
            "end_time": "05:00 PM",
            "supervisor_remarks": "Tool holder alignment checked; bore tolerance within ±0.01mm.",
            "priority_change": "NORMAL",
            "unit_id": "Unit_1",
            "recorded_by": "Shivakumar",
        },
        {
            "date": today_str,
            "order_no": "SO-2026-0001",
            "customer": "Gujarat Heavy Machinery Pvt Ltd",
            "variant": "Semi-Automatic Envelope Machine ENV-100 (Extended Bed)",
            "length": "150 mm",
            "labour": "Ramesh Solanki",
            "machine": "Horizontal Surface Grinder (SGR-02)",
            "department": "Machining",
            "planned_qty": 15.0,
            "actual_qty": 14.0,
            "rework_qty": 0.0,
            "scrap_qty": 1.0,
            "good_qty": 13.0,
            "completion_pct": 86.7,
            "work_type": "REGULAR",
            "standard_target": 15.0,
            "performance_pct": 93.3,
            "daily_earned_inr": 910.0,
            "rate_per_unit": 70.0,
            "start_time": "09:00 AM",
            "end_time": "05:30 PM",
            "supervisor_remarks": "1 plate rejected due to surface hardness imperfection from roughing.",
            "priority_change": "HIGH",
            "unit_id": "Unit_1",
            "recorded_by": "Shivakumar",
        },
        {
            "date": yesterday_str,
            "order_no": "SO-2026-0003",
            "customer": "Apex Industrial Tools & Equip",
            "variant": "High-Speed Folder Gluer FG-500 (Standard)",
            "length": "120 mm",
            "labour": "Dinesh Makwana",
            "machine": "Precision Lathe Heavy Duty (LTH-03)",
            "department": "Machining",
            "planned_qty": 18.0,
            "actual_qty": 18.0,
            "rework_qty": 0.0,
            "scrap_qty": 0.0,
            "good_qty": 18.0,
            "completion_pct": 100.0,
            "work_type": "REGULAR",
            "standard_target": 16.0,
            "performance_pct": 112.5,
            "daily_earned_inr": 1350.0,
            "rate_per_unit": 75.0,
            "start_time": "08:00 AM",
            "end_time": "04:30 PM",
            "supervisor_remarks": "Drive shaft machining completed ahead of schedule; high finish quality.",
            "priority_change": "NORMAL",
            "unit_id": "Unit_1",
            "recorded_by": "Shivakumar",
        },
        # Assembly Department (Unit 2)
        {
            "date": today_str,
            "order_no": "SO-2026-0002",
            "customer": "Precision Automotive Comps Ltd",
            "variant": "Fully-Automatic Envelope Maker ENV-200",
            "length": "200 mm",
            "labour": "Suresh Suthar",
            "machine": "Main Assembly Rig Line 1 (ASM-01)",
            "department": "Assembly",
            "planned_qty": 2.0,
            "actual_qty": 2.0,
            "rework_qty": 0.0,
            "scrap_qty": 0.0,
            "good_qty": 2.0,
            "completion_pct": 100.0,
            "work_type": "REGULAR",
            "standard_target": 2.0,
            "performance_pct": 100.0,
            "daily_earned_inr": 1800.0,
            "rate_per_unit": 900.0,
            "start_time": "08:30 AM",
            "end_time": "05:30 PM",
            "supervisor_remarks": "Complete mechanical sub-frame and gearbox coupling assembled.",
            "priority_change": "URGENT",
            "unit_id": "Unit_2",
            "recorded_by": "Shivakumar",
        },
        {
            "date": today_str,
            "order_no": "SO-2026-0002",
            "customer": "Precision Automotive Comps Ltd",
            "variant": "Fully-Automatic Envelope Maker ENV-200",
            "length": "200 mm",
            "labour": "Kamlesh Parmar",
            "machine": "Electrical Wiring Bench (ELEC-01)",
            "department": "Assembly",
            "planned_qty": 2.0,
            "actual_qty": 1.0,
            "rework_qty": 1.0,
            "scrap_qty": 0.0,
            "good_qty": 1.0,
            "completion_pct": 50.0,
            "work_type": "REGULAR",
            "standard_target": 2.0,
            "performance_pct": 50.0,
            "daily_earned_inr": 750.0,
            "rate_per_unit": 750.0,
            "start_time": "09:00 AM",
            "end_time": "05:00 PM",
            "supervisor_remarks": "Control cabinet wiring 1 set completed; second unit waiting for PLC module.",
            "priority_change": "HIGH",
            "unit_id": "Unit_2",
            "recorded_by": "Shivakumar",
        },
        {
            "date": yesterday_str,
            "order_no": "SO-2026-0005",
            "customer": "Kalyani Packaging Solutions",
            "variant": "Semi-Automatic Envelope Machine ENV-100 (Eco)",
            "length": "80 mm",
            "labour": "Pravin Chavda",
            "machine": "Secondary Assembly Bench (ASM-02)",
            "department": "Assembly",
            "planned_qty": 4.0,
            "actual_qty": 3.0,
            "rework_qty": 0.0,
            "scrap_qty": 0.0,
            "good_qty": 3.0,
            "completion_pct": 75.0,
            "work_type": "OVERTIME",
            "standard_target": 3.0,
            "performance_pct": 100.0,
            "daily_earned_inr": 1500.0,
            "rate_per_unit": 500.0,
            "start_time": "08:30 AM",
            "end_time": "07:00 PM",
            "supervisor_remarks": "3 feeder rollers fitted and test-rotated under no-load condition.",
            "priority_change": "NORMAL",
            "unit_id": "Unit_2",
            "recorded_by": "Shivakumar",
        },
        # Fabrication Department (Unit 1)
        {
            "date": today_str,
            "order_no": "SO-2026-0007",
            "customer": "Sterling Printing & Packaging",
            "variant": "High-Speed Folder Gluer FG-500 (Pro Series)",
            "length": "180 mm",
            "labour": "Sunil Vaghela",
            "machine": "CNC Plasma / Flame Cutting Table (CUT-01)",
            "department": "Fabrication",
            "planned_qty": 12.0,
            "actual_qty": 12.0,
            "rework_qty": 0.0,
            "scrap_qty": 1.0,
            "good_qty": 11.0,
            "completion_pct": 91.7,
            "work_type": "REGULAR",
            "standard_target": 12.0,
            "performance_pct": 100.0,
            "daily_earned_inr": 1100.0,
            "rate_per_unit": 100.0,
            "start_time": "08:30 AM",
            "end_time": "05:00 PM",
            "supervisor_remarks": "Base frame structural plates profiled from 25mm MS plate stock.",
            "priority_change": "NORMAL",
            "unit_id": "Unit_1",
            "recorded_by": "Shivakumar",
        },
        {
            "date": yesterday_str,
            "order_no": "SO-2026-0008",
            "customer": "Zenith Flexo Prints Pvt Ltd",
            "variant": "Thermal Laminating Machine TLM-400",
            "length": "160 mm",
            "labour": "Ashok Rathod",
            "machine": "Hydraulic Sheet Metal Press Brake (BND-01)",
            "department": "Fabrication",
            "planned_qty": 16.0,
            "actual_qty": 16.0,
            "rework_qty": 1.0,
            "scrap_qty": 0.0,
            "good_qty": 15.0,
            "completion_pct": 93.8,
            "work_type": "REGULAR",
            "standard_target": 15.0,
            "performance_pct": 106.7,
            "daily_earned_inr": 1200.0,
            "rate_per_unit": 80.0,
            "start_time": "09:00 AM",
            "end_time": "05:30 PM",
            "supervisor_remarks": "Guard covers and safety shroud bending completed with uniform 90° radii.",
            "priority_change": "HIGH",
            "unit_id": "Unit_1",
            "recorded_by": "Shivakumar",
        },
        # Welding Department (Unit 1)
        {
            "date": today_str,
            "order_no": "SO-2026-0007",
            "customer": "Sterling Printing & Packaging",
            "variant": "High-Speed Folder Gluer FG-500 (Pro Series)",
            "length": "180 mm",
            "labour": "Bhavesh Barot",
            "machine": "MIG Welding Station 02 (WLD-02)",
            "department": "Welding",
            "planned_qty": 6.0,
            "actual_qty": 6.0,
            "rework_qty": 0.0,
            "scrap_qty": 0.0,
            "good_qty": 6.0,
            "completion_pct": 100.0,
            "work_type": "REGULAR",
            "standard_target": 5.0,
            "performance_pct": 120.0,
            "daily_earned_inr": 1200.0,
            "rate_per_unit": 200.0,
            "start_time": "08:30 AM",
            "end_time": "05:00 PM",
            "supervisor_remarks": "Gusset ribs full-penetration fillet welded; DP test passed.",
            "priority_change": "NORMAL",
            "unit_id": "Unit_1",
            "recorded_by": "Shivakumar",
        },
        # Quality Control Department (Unit 2)
        {
            "date": today_str,
            "order_no": "SO-2026-0001",
            "customer": "Gujarat Heavy Machinery Pvt Ltd",
            "variant": "Semi-Automatic Envelope Machine ENV-100",
            "length": "100 mm",
            "labour": "Manoj Tiwari",
            "machine": "CMM & Digital Height Gauge (QC-01)",
            "department": "Quality Control",
            "planned_qty": 20.0,
            "actual_qty": 20.0,
            "rework_qty": 1.0,
            "scrap_qty": 0.0,
            "good_qty": 19.0,
            "completion_pct": 95.0,
            "work_type": "REGULAR",
            "standard_target": 20.0,
            "performance_pct": 100.0,
            "daily_earned_inr": 1140.0,
            "rate_per_unit": 60.0,
            "start_time": "09:30 AM",
            "end_time": "05:00 PM",
            "supervisor_remarks": "Dimensional CMM report logged; 1 part sent for re-deburring.",
            "priority_change": "NORMAL",
            "unit_id": "Unit_2",
            "recorded_by": "Shivakumar",
        },
        {
            "date": today_str,
            "order_no": "SO-2026-0002",
            "customer": "Precision Automotive Comps Ltd",
            "variant": "Fully-Automatic Envelope Maker ENV-200",
            "length": "200 mm",
            "labour": "Neha Shah",
            "machine": "Electrical & Hi-Pot Test Rig (TEST-01)",
            "department": "Quality Control",
            "planned_qty": 1.0,
            "actual_qty": 1.0,
            "rework_qty": 0.0,
            "scrap_qty": 0.0,
            "good_qty": 1.0,
            "completion_pct": 100.0,
            "work_type": "REGULAR",
            "standard_target": 1.0,
            "performance_pct": 100.0,
            "daily_earned_inr": 1200.0,
            "rate_per_unit": 1200.0,
            "start_time": "10:00 AM",
            "end_time": "04:30 PM",
            "supervisor_remarks": "Insulation resistance: >100MΩ; emergency stop circuit verified.",
            "priority_change": "NORMAL",
            "unit_id": "Unit_2",
            "recorded_by": "Shivakumar",
        },
        # Grinding & Finishing Department (Unit 1)
        {
            "date": two_days_ago,
            "order_no": "SO-2026-0004",
            "customer": "Shree Ram Engineering Works",
            "variant": "Rotary Die Cutter RDC-300",
            "length": "250 mm",
            "labour": "Gopal Bharwad",
            "machine": "Cylindrical Grinder (CGR-01)",
            "department": "Grinding",
            "planned_qty": 4.0,
            "actual_qty": 4.0,
            "rework_qty": 0.0,
            "scrap_qty": 0.0,
            "good_qty": 4.0,
            "completion_pct": 100.0,
            "work_type": "REGULAR",
            "standard_target": 4.0,
            "performance_pct": 100.0,
            "daily_earned_inr": 1400.0,
            "rate_per_unit": 350.0,
            "start_time": "08:30 AM",
            "end_time": "05:30 PM",
            "supervisor_remarks": "Hardened anvil roll ground to Ra 0.2 micron mirror polish.",
            "priority_change": "NORMAL",
            "unit_id": "Unit_1",
            "recorded_by": "Shivakumar",
        },
    ]

    total_seeded = 0
    for rec in daily_records:
        rec["created_at"] = now_dt
        rec["updated_at"] = now_dt
        rec["_seed"] = SEED_TAG
        await daily_col.insert_one(rec)
        total_seeded += 1

    print(f"  [DAILY PRODUCTION] Seeded {total_seeded} Department-wise records (Main daily entry screen for Shivakumar).")



# ---------------------------------------------------------------------------
# 19. SEED FINANCE TRANSACTIONS, BILLS & EXPENSES
# ---------------------------------------------------------------------------
async def seed_finance_transactions(db, vend_map: Dict[str, Any]):
    bills_col = db["supplier_bills"]
    exp_col = db["expenses"]
    journal_col = db["journal_entries"]

    await bills_col.delete_many({"_seed": SEED_TAG})
    await exp_col.delete_many({"_seed": SEED_TAG})
    await journal_col.delete_many({"_seed": SEED_TAG})

    # Supplier bills
    bills = [
        ("BILL-2026-001", "VEND-001", 385000.0, 69300.0, "PAID", "Heavy MS plate raw material consignment"),
        ("BILL-2026-002", "VEND-002", 142000.0, 25560.0, "PAID", "AC induction motors batch for ENV machines"),
        ("BILL-2026-003", "VEND-005", 98000.0,  17640.0, "OPEN", "SKF 6205ZZ deep groove bearings quarterly batch"),
        ("BILL-2026-004", "VEND-007", 220000.0, 39600.0, "OPEN", "Cast iron machine body roughs grade 25"),
    ]
    for b_num, vend_code, sub, tax, st, desc in bills:
        vend = vend_map[vend_code]
        doc = {
            "bill_number": b_num,
            "vendor_id": vend["id"],
            "vendor_code": vend_code,
            "vendor_name": vend["name"],
            "subtotal": sub,
            "tax_amount": tax,
            "total_amount": sub + tax,
            "bill_date": date_str(d_ago(20)),
            "due_date": date_str(d_future(15)),
            "status": st,
            "description": desc,
            "created_at": d_ago(20),
            "_seed": SEED_TAG,
        }
        await bills_col.insert_one(doc)

    # Factory expenses
    expenses = [
        ("EXP-2026-001", "Electricity & Utilities", 84500.0, "Unit 1 Heavy Machining GEB power bill", "Unit_1"),
        ("EXP-2026-002", "Tooling & Machine Maintenance", 32000.0, "CNC milling cutter inserts and regrinding", "Unit_1"),
        ("EXP-2026-003", "Freight & Inward Haulage", 24500.0, "Steel plate trailer transport from Noida", "Unit_1"),
        ("EXP-2026-004", "Safety Gear & Shopfloor Consumables", 12500.0, "Operator safety shoes and welding aprons", "Unit_2"),
        ("EXP-2026-005", "Office & Administration", 18200.0, "Plant broadband, stationery and water dispensers", "BOTH"),
    ]
    for exp_num, cat, amt, desc, unit_id in expenses:
        doc = {
            "expense_number": exp_num,
            "category": cat,
            "amount": amt,
            "unit_id": unit_id,
            "expense_date": date_str(d_ago(12)),
            "payment_method": "BANK_TRANSFER",
            "description": desc,
            "approved_by": "Ananya Iyer",
            "created_at": d_ago(12),
            "_seed": SEED_TAG,
        }
        await exp_col.insert_one(doc)

    # Balanced double-entry journal entries
    journals = [
        ("JE-2026-001", "Depreciation booking for September 2026", "2026-09-30", [
            {"account_code": "5300-OPERATING-EXPENSES", "debit": 45000.0, "credit": 0.0},
            {"account_code": "1510-ACCUM-DEPRECIATION", "debit": 0.0, "credit": 45000.0},
        ]),
        ("JE-2026-002", "Power & Electricity expense accrual", "2026-09-30", [
            {"account_code": "5200-POWER-ELECTRICITY-EXPENSE", "debit": 84500.0, "credit": 0.0},
            {"account_code": "2000-ACCOUNTS-PAYABLE", "debit": 0.0, "credit": 84500.0},
        ]),
    ]
    for je_num, narr, dt_str, lines in journals:
        doc = {
            "entry_number": je_num,
            "narration": narr,
            "entry_date": dt_str,
            "lines": lines,
            "total_debit": sum(l["debit"] for l in lines),
            "total_credit": sum(l["credit"] for l in lines),
            "status": "POSTED",
            "posted_by": "Manish Tiwari",
            "created_at": d_ago(14),
            "_seed": SEED_TAG,
        }
        await journal_col.insert_one(doc)

    print(f"  [LEDGER] Seeded {len(bills)} Supplier Bills, {len(expenses)} Expenses & {len(journals)} Balanced Journal Entries.")

# ---------------------------------------------------------------------------
# 20. SEED CRM LEADS & ACTIVITY TIMELINE
# ---------------------------------------------------------------------------
async def seed_crm(db):
    leads_col = db["crm_leads"]
    act_col = db["crm_activities"]

    await leads_col.delete_many({"_seed": SEED_TAG})
    await act_col.delete_many({"_seed": SEED_TAG})

    leads = [
        ("LEAD-2026-001", "Navkar Packaging Industries Pvt Ltd", "Mr. Hiren Shah", "hiren.shah@navkarpack.com", "+91 98250 34120", "TRADE_EXPO", "NEGOTIATION", "HOT", "priyashah@rgtech.com", 1850000.0, "High-Speed Automatic Envelope Machine ENV-200", "Unit_1"),
        ("LEAD-2026-002", "Deccan Converting & Paper Bags Ltd", "Smt. Jayashree Rao", "jrao@deccanconverting.in", "+91 98480 12890", "DIRECT_INQUIRY", "PROPOSAL_SENT", "WARM", "rohangupta@rgtech.com", 920000.0, "Carton Packaging Machine PKG-300 with conveyor", "Unit_2"),
        ("LEAD-2026-003", "Apex Stationery & Forms Co.", "Mr. Rajesh Agarwal", "rajesh@apexforms.com", "+91 98100 45678", "WEBSITE", "QUALIFIED", "HOT", "priyashah@rgtech.com", 450000.0, "Compact Desktop Envelope Machine ENV-MINI", "Unit_1"),
        ("LEAD-2026-004", "Shree Ganesh Book Mfg & Printers", "Mr. Paresh Soni", "paresh@shreeganeshprint.com", "+91 98240 77123", "REFERRAL", "CONVERTED", "HOT", "priyashah@rgtech.com", 2450000.0, "Semi-Automatic Envelope Machine ENV-100", "BOTH"),
        ("LEAD-2026-005", "Maruti Cartons & Corrugators", "Mr. Vikas Kadam", "vkadam@maruticartons.com", "+91 98210 99456", "COLD_CALL", "CONTACTED", "COLD", "meeranair@rgtech.com", 560000.0, "Automatic Carton Packer spare assemblies", "Unit_2"),
        ("LEAD-2026-006", "Tamil Nadu Educational Stationery", "Mr. S. Ramanathan", "ramanathan@tnstationery.org", "+91 94440 33210", "TRADE_EXPO", "LOST", "COLD", "rohangupta@rgtech.com", 1200000.0, "Tender bid lost on pricing discount terms", "Unit_1"),
        ("LEAD-2026-007", "Kalyani Paper Converting Works", "Mr. Anirudh Kalyani", "anirudh@kalyanipapers.com", "+91 98220 11987", "EXISTING_CLIENT", "PROPOSAL_SENT", "WARM", "priyashah@rgtech.com", 820000.0, "ENV-100 tooling expansion with window die-cutter", "Unit_1"),
        ("LEAD-2026-008", "Galaxy Blister & Box Packers", "Mr. Manish Chawla", "manish@galaxypack.com", "+91 98110 88234", "WEBSITE", "NEW", "WARM", "meeranair@rgtech.com", 1450000.0, "Inquiry for PKG-300 carton forming station", "Unit_2"),
    ]

    for lead_code, comp, contact, email, phone, src, st, prio, rep, val, interest, unit_id in leads:
        lead_doc = {
            "code": lead_code,
            "company_name": comp,
            "contact_person": contact,
            "email": email,
            "phone": phone,
            "source": src,
            "status": st,
            "priority": prio,
            "assigned_to": rep,
            "estimated_value": val,
            "machine_interest": interest,
            "unit_id": unit_id,
            "next_follow_up": d_future(3) if st in ["NEGOTIATION", "PROPOSAL_SENT"] else (d_ago(1) if st == "CONTACTED" else None),
            "created_at": d_ago(25),
            "updated_at": NOW,
            "_seed": SEED_TAG,
        }
        res = await leads_col.insert_one(lead_doc)
        lead_id = str(res.inserted_id)

        # Activity log
        act_doc = {
            "lead_id": lead_id,
            "activity_type": "MEETING" if st in ["NEGOTIATION", "CONVERTED"] else "CALL",
            "title": f"Initial technical consultation for {interest}",
            "description": f"Discussed plant layout requirements and electrical 3-phase wiring parameters for {comp}.",
            "performed_by": rep,
            "created_at": d_ago(15),
            "_seed": SEED_TAG,
        }
        await act_col.insert_one(act_doc)

    print(f"  [CRM] Seeded {len(leads)} Machinery Leads across All Pipeline Stages & Activity Logs.")

# ---------------------------------------------------------------------------
# 21. SEED ANNOUNCEMENTS & NOTIFICATIONS
# ---------------------------------------------------------------------------
async def seed_announcements_and_notifications(db, emp_map: Dict[str, Any]):
    ann_col = db["announcements"]
    notif_col = db["notifications"]

    await ann_col.delete_many({"_seed": SEED_TAG})
    await notif_col.delete_many({"_seed": SEED_TAG})

    announcements = [
        ("Mandatory Eye Protection & Helmet Protocols in Unit 1 CNC Bay", "All machinists, boring technicians, and visitors in Unit 1 must wear certified polycarbonate safety spectacles and safety footwear at all times.", "HIGH", "Unit_1", "Ramesh Solanki", "Maintenance Manager"),
        ("Unit 2 Precision Sub-Assembly Cleanroom Expansion Notice", "Civil and HVAC installation for the Unit 2 sterile packaging line begins next Monday. Use alternate Bay-2B transit aisle.", "MEDIUM", "Unit_2", "Rahul Sharma", "Production Manager"),
        ("Diwali Festival Bonus & Extended Plant Maintenance Holiday", "Management is pleased to announce annual performance festival bonuses processed with October payroll. Plant operations resume on Nov 4.", "HIGH", "BOTH", "Kavita Deshmukh", "HR Manager"),
        ("ISO 9001:2015 Annual Surveillance Audit Schedule", "External certification auditors will inspect Machining Station #1, Calibration records, and Scrap reconciliation next Thursday.", "URGENT", "BOTH", "Neha Modi", "QC Manager"),
    ]

    for title, content, prio, unit_id, author_name, author_role in announcements:
        doc = {
            "title": title,
            "content": content,
            "priority": prio,
            "unit_id": unit_id,
            "author_name": author_name,
            "author_role": author_role,
            "published_at": d_ago(7),
            "expires_at": d_future(30),
            "_seed": SEED_TAG,
        }
        await ann_col.insert_one(doc)

    total_notifs = 0
    for code, emp in emp_map.items():
        if emp.get("is_new"):
            continue
        notif_doc = {
            "user_id": emp["user_id"],
            "employee_code": code,
            "title": "September Payslip Generated",
            "message": "Your monthly itemized payslip for September 2026 is now available for review and download in your profile.",
            "notification_type": "PAYROLL",
            "is_read": False,
            "link": "/employee/payroll",
            "created_at": d_ago(5),
            "_seed": SEED_TAG,
        }
        await notif_col.insert_one(notif_doc)
        total_notifs += 1

    print(f"  [COMMUNICATIONS] Seeded {len(announcements)} Plant Announcements & {total_notifs} Employee Notifications.")

# ---------------------------------------------------------------------------
# MAIN SEED RUNNER
# ---------------------------------------------------------------------------
async def run_master_seed(cleanup_only: bool = False):
    verify_environment_safety()
    print("=" * 75)
    print("  OPTI MATRIX MANUFACTURING ERP — MASTER REAL-WORLD DATABASE SEEDER")
    print(f"  Target Database : {settings.MONGODB_DB_NAME}")
    print(f"  Connection URI  : {settings.MONGODB_URI}")
    print("=" * 75)

    client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB_NAME]

    if cleanup_only:
        print("[CLEANUP] Removing records tagged with:", SEED_TAG)
        cols = await db.list_collection_names()
        for c in cols:
            res = await db[c].delete_many({"_seed": SEED_TAG})
            if res.deleted_count > 0:
                print(f"  Cleaned {res.deleted_count} records from {c}")
        client.close()
        print("[SUCCESS] Cleanup completed successfully.")
        return

    # 1. System Roles
    await seed_system_roles(db)

    # 2. Categories & UoMs
    cat_map, uom_map = await seed_categories_and_uoms(db)

    # 3. Warehouses
    wh_map = await seed_warehouses(db)

    # 4. Materials & Finished Products
    mat_map, prod_map = await seed_materials_and_products(db)

    # 5. Customers & Vendors
    cust_map, vend_map = await seed_customers_and_vendors(db)

    # 6. Shifts & Chart of Accounts
    await seed_shifts(db)
    await seed_chart_of_accounts(db)

    # 7. Employees, Users & Salaries
    emp_map = await seed_employees_and_users(db)

    # 8. BOMs
    bom_map = await seed_boms(db, mat_map, prod_map)

    # 9. Inventory Stock Balances
    await seed_inventory(db, mat_map, prod_map, wh_map)

    # 10. Production Projects / Orders
    await seed_production_projects(db, prod_map, bom_map, wh_map, emp_map)

    # 11. Tasks & Messages (115+ tasks)
    await seed_employee_tasks(db, emp_map)

    # 12. 90-Day Attendance & Regularization
    await seed_attendance_history(db, emp_map)

    # 13. Leave Requests
    await seed_leave_requests(db, emp_map)

    # 14. Payroll & Payslips
    await seed_payroll(db, emp_map)

    # 15. Wastage & Scrap Entries
    await seed_wastage_and_scrap(db)

    # 16. Power & Electricity Consumption
    await seed_power_and_electricity(db)

    # 17. Orders, Dispatches & Invoices
    await seed_orders_and_invoices(db, cust_map, prod_map)

    # 18. Finance Ledger, Bills & Expenses
    await seed_finance_transactions(db, vend_map)

    # 19. CRM Leads & Follow-ups
    await seed_crm(db)

    # 20. Announcements & Notifications
    await seed_announcements_and_notifications(db, emp_map)

    print("\n" + "=" * 75)
    print("  VERIFICATION AUDIT — COLLECTION DOCUMENT COUNTS")
    print("=" * 75)
    cols = sorted(await db.list_collection_names())
    summary_counts = {}
    for c in cols:
        cnt = await db[c].count_documents({})
        summary_counts[c] = cnt
        if cnt > 0:
            print(f"  {c:35s}: {cnt:5d} records")
    print("=" * 75)

    client.close()
    return summary_counts

def main():
    parser = argparse.ArgumentParser(description="Opti Matrix ERP Master Real-World Seeding Script")
    parser.add_argument("--cleanup", action="store_true", help="Remove all seeded records")
    args = parser.parse_args()

    asyncio.run(run_master_seed(cleanup_only=args.cleanup))

if __name__ == "__main__":
    main()
