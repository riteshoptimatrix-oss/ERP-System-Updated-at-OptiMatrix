"""
Opti Matrix ERP — CRM & Leads Real-World Data Seeding Script
File: backend/scripts/seed_crm_data.py

Seeds comprehensive, realistic manufacturing CRM data:
  - 18 realistic industrial machinery leads across all stages (NEW, CONTACTED, QUALIFIED,
    PROPOSAL_SENT, NEGOTIATION, CONVERTED, LOST)
  - Priorities: HOT, WARM, COLD
  - Sources: TRADE_EXPO, DIRECT_INQUIRY, WEBSITE, REFERRAL, COLD_CALL, EXISTING_CLIENT
  - Facilities: Unit_1, Unit_2, and BOTH
  - Realistic follow-ups: Due Today, Overdue, and Upcoming
  - Rich activity history (calls, meetings, site visits, technical notes, status changes)
  - Project Hub material requirements (BOM) linked to high-value leads
  - Customer Master conversion links for converted leads

Usage:
    python scripts/seed_crm_data.py            # Seed CRM data
    python scripts/seed_crm_data.py --cleanup  # Remove seeded CRM data only
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
from app.repositories.crm_repository import CrmRepository
import motor.motor_asyncio
from bson import ObjectId

NOW = datetime.now(timezone.utc)
SEED_TAG = "realworld_crm_seed_v1"

# Sales representatives
REP_PRIYA = "priyashah@rgtech.com"       # Sales Manager
REP_ROHAN = "rohangupta@rgtech.com"     # Sales Executive
REP_ADMIN = "admin@rgtech.com"          # Head of Sales / Director

def days_ago(d: int, hours: int = 0) -> datetime:
    return NOW - timedelta(days=d, hours=hours)

def future_days(d: int, hours: int = 0) -> datetime:
    return NOW + timedelta(days=d, hours=hours)

# ---------------------------------------------------------------------------
# 18 Real-World Machinery & Converting Leads
# ---------------------------------------------------------------------------
LEADS_DATA: List[Dict[str, Any]] = [
    {
        "code": "LEAD-2026-0001",
        "company_name": "Navkar Packaging Industries Pvt Ltd",
        "contact_person": "Mr. Hiren Shah",
        "email": "hiren.shah@navkarpack.com",
        "phone": "+91 98250 34120",
        "source": "TRADE_EXPO",
        "status": "NEGOTIATION",
        "priority": "HOT",
        "assigned_to": REP_PRIYA,
        "estimated_value": 1850000.0,
        "machine_interest": "High-Speed Automatic Envelope Machine ENV-200 (180 pcs/min)",
        "unit_id": "Unit_1",
        # Follow-up due today in 2 hours
        "next_follow_up": future_days(0, 2),
        "created_days_ago": 18,
        "notes": (
            "Expanding commercial courier envelope manufacturing capacity at Changodar plant. "
            "Customer requested payment terms: 10% advance, 80% against pre-dispatch inspection, "
            "and 10% post-commissioning. Negotiating inclusion of 1 set extra rotary cutting dies "
            "and 1-year complimentary AMC."
        ),
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 18,
                "summary": "Met at PlastIndia 2026 Exhibition Booth",
                "details": "Client visited booth and witnessed live speed trial of ENV-200. Expressed urgent capex need for Q4 expansion.",
                "user": REP_PRIYA,
            },
            {
                "type": "CALL",
                "days_ago": 14,
                "summary": "Technical Discussion on Paper GSM & Peel-and-Seal",
                "details": "Reviewed paper feeding parameters for 70-140 GSM kraft paper and hot-melt silicone release tape applicator module.",
                "user": REP_PRIYA,
            },
            {
                "type": "SITE_VISIT",
                "days_ago": 9,
                "summary": "Factory Inspection at Changodar Facility",
                "details": "Visited client manufacturing unit. Inspected 3-phase 415V power infrastructure, pneumatic lines, and machine layout footprint.",
                "user": REP_PRIYA,
            },
            {
                "type": "EMAIL",
                "days_ago": 5,
                "summary": "Submitted Revised Proposal Rev-02 with Tooling Package",
                "details": "Sent official techno-commercial offer totaling ₹18.5L including 2 standard folding dies and digital counter unit.",
                "user": REP_PRIYA,
            },
            {
                "type": "CALL",
                "days_ago": 1,
                "summary": "Commercial Negotiation with Managing Director",
                "details": "Discussion with Mr. Hiren Shah on payment milestones and transit insurance. Final decision meeting scheduled for today.",
                "user": REP_PRIYA,
            },
        ],
        "materials": [
            {"item_code": "RM-MS-PLATE-10MM", "description": "MS Plate 10mm IS:2062 for Main Frame", "qty": 420.0, "uom": "KG", "rate": 85.0, "notes": "Heavy bed frame"},
            {"item_code": "RM-SS-ROD-20MM", "description": "SS 304 Drive Roller Shafts", "qty": 65.0, "uom": "KG", "rate": 280.0, "notes": "High precision ground"},
            {"item_code": "RM-CI-CAST-001", "description": "CI Main Cam & Bearing Housing Casting", "qty": 2.0, "uom": "NOS", "rate": 42000.0, "notes": "Stress relieved"},
            {"item_code": "ELEC-SERVO-01", "description": "Delta 1.5kW AC Servo Motor & Drive", "qty": 3.0, "uom": "NOS", "rate": 38000.0, "notes": "Feeding synchronization"},
            {"item_code": "PLC-TOUCH-PANEL", "description": "Siemens 7-inch Touch HMI & S7-1200 PLC", "qty": 1.0, "uom": "NOS", "rate": 65000.0, "notes": "Pre-programmed software"},
        ],
    },
    {
        "code": "LEAD-2026-0002",
        "company_name": "Zenith Pharmaceuticals Ltd - Packaging Div.",
        "contact_person": "Dr. Arvind Trivedi",
        "email": "arvind.trivedi@zenithpharma.co.in",
        "phone": "+91 98160 55410",
        "source": "DIRECT_INQUIRY",
        "status": "PROPOSAL_SENT",
        "priority": "HOT",
        "assigned_to": REP_PRIYA,
        "estimated_value": 2400000.0,
        "machine_interest": "Automated Carton Packing Machine PKG-300 with SS-304 Cladding",
        "unit_id": "Unit_1",
        # Follow-up due today in 4 hours
        "next_follow_up": future_days(0, 4),
        "created_days_ago": 12,
        "notes": (
            "Pharma secondary carton packaging line for blister strips. Requires cGMP compliance, "
            "SS-304 exterior grade panels, and 21 CFR Part 11 electronic batch logging. Proposal "
            "submitted with DQ/IQ/OQ validation protocols."
        ),
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 12,
                "summary": "RFQ Received via Corporate Portal",
                "details": "Technical tender inquiry received for automated secondary cartoner for Baddi formulation unit.",
                "user": REP_PRIYA,
            },
            {
                "type": "CALL",
                "days_ago": 9,
                "summary": "Pharma Validation & Compliance Alignment",
                "details": "Clarified DQ/IQ/OQ qualification document requirements and optical character recognition (OCR) inspection camera module.",
                "user": REP_PRIYA,
            },
            {
                "type": "EMAIL",
                "days_ago": 4,
                "summary": "Formal Techno-Commercial Proposal PKG-300-GMP Dispatched",
                "details": "Submitted complete quotation ₹24.0L with electrical schematics, utility consumption data, and 6-week FAT schedule.",
                "user": REP_PRIYA,
            },
        ],
        "materials": [
            {"item_code": "RM-SS-PLATE-4MM", "description": "SS 304 Food/Pharma Grade Cladding Plates", "qty": 280.0, "uom": "KG", "rate": 310.0, "notes": "Buffed 240 grit finish"},
            {"item_code": "RM-MS-PLATE-10MM", "description": "Mild Steel Base Structure IS:2062", "qty": 350.0, "uom": "KG", "rate": 85.0, "notes": "Anti-vibration base"},
            {"item_code": "PNEUM-CYL-FESTO", "description": "Festo Pneumatic Cylinder & Valve Manifold", "qty": 8.0, "uom": "NOS", "rate": 7800.0, "notes": "Cleanroom compliant"},
        ],
    },
    {
        "code": "LEAD-2026-0003",
        "company_name": "Shree Ganesh Paper Products",
        "contact_person": "Mr. Bhavesh Patel",
        "email": "b.patel@shreeganeshpaper.com",
        "phone": "+91 98241 87654",
        "source": "WEBSITE",
        "status": "QUALIFIED",
        "priority": "WARM",
        "assigned_to": REP_ROHAN,
        "estimated_value": 850000.0,
        "machine_interest": "Automatic Envelope Machine ENV-100 with Window Patcher",
        "unit_id": "Unit_1",
        # Follow-up due today in 5 hours
        "next_follow_up": future_days(0, 5),
        "created_days_ago": 10,
        "notes": (
            "Specialized bank statement and utility bill envelope manufacturer in Sachin GIDC Surat. "
            "Needs transparent BOPP film window patch unit. Budget verified at ₹8.5L. Plant electrical "
            "and air compressor capacities are verified."
        ),
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 10,
                "summary": "Inquiry Registered via Website",
                "details": "Client submitted query looking for compact envelope machine with window cutting attachment.",
                "user": REP_ROHAN,
            },
            {
                "type": "CALL",
                "days_ago": 7,
                "summary": "Technical Needs & Paper Sizes Discovery",
                "details": "Discussed standard sizes 9x4 inches and 10x4.5 inches. Verified paper grammage 75 to 100 GSM.",
                "user": REP_ROHAN,
            },
            {
                "type": "EMAIL",
                "days_ago": 3,
                "summary": "Shared High-Resolution Video Demo of ENV-100",
                "details": "Sent operating video and technical datasheet. Client requested formal budgetary quote.",
                "user": REP_ROHAN,
            },
        ],
    },
    {
        "code": "LEAD-2026-0004",
        "company_name": "Apex Converting & Automation LLP",
        "contact_person": "Mr. Sandeep Desai",
        "email": "sandeep.desai@apexconverting.com",
        "phone": "+91 98795 12040",
        "source": "REFERRAL",
        "status": "NEGOTIATION",
        "priority": "HOT",
        "assigned_to": REP_PRIYA,
        "estimated_value": 3200000.0,
        "machine_interest": "Integrated Packaging & Carton Line PKG-300 + Robotic Case Erector",
        "unit_id": "Unit_2",
        # Follow-up due today in 3 hours
        "next_follow_up": future_days(0, 3),
        "created_days_ago": 21,
        "notes": (
            "Referred by Mr. Ravi Sharma (Ravi Stationery CUST-001). Turnkey packaging automation line "
            "for industrial fasteners and FMCG cartons. Final round of negotiations regarding warranty "
            "extension from 12 to 24 months and AMC terms."
        ),
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 21,
                "summary": "Executive Referral Received",
                "details": "Direct introduction from Ravi Stationery Managing Director. Client planning capital expansion.",
                "user": REP_PRIYA,
            },
            {
                "type": "MEETING",
                "days_ago": 16,
                "summary": "Plant Technical Audit at Makarpura GIDC",
                "details": "Priya Shah and senior design engineer audited client packaging shop floor and conveyor links.",
                "user": REP_PRIYA,
            },
            {
                "type": "EMAIL",
                "days_ago": 11,
                "summary": "Turnkey Proposal Rev-01 Dispatched",
                "details": "Detailed proposal ₹32.0L covering automated in-feed, carton erecting, and glue dispensing.",
                "user": REP_PRIYA,
            },
            {
                "type": "CALL",
                "days_ago": 4,
                "summary": "Commercial Negotiation on Payment Milestones",
                "details": "Discussed bank guarantee against advance payment. Client agreed to 20% advance upon PO signoff.",
                "user": REP_PRIYA,
            },
        ],
        "materials": [
            {"item_code": "RM-MS-PLATE-10MM", "description": "Structural Plate 10mm Base Frame", "qty": 650.0, "uom": "KG", "rate": 85.0, "notes": "Heavy conveyor frame"},
            {"item_code": "RM-SS-ROD-20MM", "description": "SS Ground Shafts & Rollers", "qty": 110.0, "uom": "KG", "rate": 280.0, "notes": "Drive mechanism"},
            {"item_code": "ELEC-SERVO-01", "description": "Delta 2.0kW Servo Motors", "qty": 4.0, "uom": "NOS", "rate": 45000.0, "notes": "Synchronized indexer"},
        ],
    },
    {
        "code": "LEAD-2026-0005",
        "company_name": "Modern Stationery & Print Pack",
        "contact_person": "Mr. Nilesh Kothari",
        "email": "nilesh.kothari@modernstationery.in",
        "phone": "+91 98201 67890",
        "source": "TRADE_EXPO",
        "status": "PROPOSAL_SENT",
        "priority": "HOT",
        "assigned_to": REP_ROHAN,
        "estimated_value": 1420000.0,
        "machine_interest": "Automatic Envelope Making Machine ENV-200 Standard",
        "unit_id": "Unit_1",
        # Follow-up overdue: was due yesterday
        "next_follow_up": days_ago(1, 4),
        "created_days_ago": 15,
        "notes": (
            "Proposal submitted 5 days ago. Follow-up was due yesterday to confirm client purchase "
            "committee approval. Urgent call required to avoid losing momentum against competitors."
        ),
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 15,
                "summary": "Met at PackPlus Mumbai Stall",
                "details": "Discussed replacing 2 outdated semi-automatic machines with one high-speed ENV-200.",
                "user": REP_ROHAN,
            },
            {
                "type": "CALL",
                "days_ago": 11,
                "summary": "Capacity & Speed Requirement Finalized",
                "details": "Client target is 160 envelopes/minute on 80 GSM paper with water-based glue.",
                "user": REP_ROHAN,
            },
            {
                "type": "EMAIL",
                "days_ago": 6,
                "summary": "Sent Comprehensive Quotation Rev-01",
                "details": "Quotation submitted for ₹14.20L with 4-week delivery commitment and free operator training.",
                "user": REP_ROHAN,
            },
        ],
    },
    {
        "code": "LEAD-2026-0006",
        "company_name": "Pragati Graphics & Box Makers",
        "contact_person": "Mr. K. R. Venkatesh",
        "email": "venkatesh@pragatigraphics.in",
        "phone": "+91 98450 33211",
        "source": "COLD_CALL",
        "status": "CONTACTED",
        "priority": "WARM",
        "assigned_to": REP_ROHAN,
        "estimated_value": 780000.0,
        "machine_interest": "Envelope Making Machine ENV-100 with Gumming Unit",
        "unit_id": "Unit_2",
        # Follow-up overdue: was due 2 days ago
        "next_follow_up": days_ago(2, 2),
        "created_days_ago": 8,
        "notes": (
            "Client interested in replacing manual table gumming with automated ENV-100 line. "
            "Catalogue dispatched. Follow-up was due 2 days ago to verify sample paper tests."
        ),
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 8,
                "summary": "Cold Outreach to Peenya Industrial Cluster",
                "details": "Telephonic outreach to established commercial box maker in Peenya Bangalore.",
                "user": REP_ROHAN,
            },
            {
                "type": "CALL",
                "days_ago": 6,
                "summary": "Introduction & Needs Evaluation",
                "details": "Spoke with proprietor Mr. Venkatesh. Expressed willingness to automate gumming section.",
                "user": REP_ROHAN,
            },
            {
                "type": "EMAIL",
                "days_ago": 4,
                "summary": "Dispatched Machine Specifications & Pricing Range",
                "details": "Emailed catalog of ENV-100 and technical specification sheet.",
                "user": REP_ROHAN,
            },
        ],
    },
    {
        "code": "LEAD-2026-0007",
        "company_name": "Surya Printpack & Envelopes",
        "contact_person": "Mr. M. S. Reddy",
        "email": "ms.reddy@suryaprintpack.com",
        "phone": "+91 98490 89123",
        "source": "WEBSITE",
        "status": "QUALIFIED",
        "priority": "WARM",
        "assigned_to": REP_PRIYA,
        "estimated_value": 1150000.0,
        "machine_interest": "High-Speed Envelope Machine ENV-200 with Silicone Tape Unit",
        "unit_id": "Unit_1",
        # Follow-up overdue: was due 2 days ago
        "next_follow_up": days_ago(2, 6),
        "created_days_ago": 14,
        "notes": (
            "Manufacturing security mailers for telecom and bank delivery. Needs automated release "
            "liner silicone tape applicator. Follow-up overdue by 2 days."
        ),
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 14,
                "summary": "Web Form Lead Logged",
                "details": "Inquiry received from Cherlapally IDA, Hyderabad.",
                "user": REP_PRIYA,
            },
            {
                "type": "CALL",
                "days_ago": 10,
                "summary": "Technical Discussion on Release Tape Unit",
                "details": "Clarified tape feed synchronization with main drive encoder to prevent tape slipping.",
                "user": REP_PRIYA,
            },
        ],
    },
    {
        "code": "LEAD-2026-0008",
        "company_name": "Universal Carton Box & Packaging",
        "contact_person": "Mr. Anil Batra",
        "email": "anil.batra@universalcarton.com",
        "phone": "+91 98110 44321",
        "source": "TRADE_EXPO",
        "status": "CONVERTED",
        "priority": "HOT",
        "assigned_to": REP_PRIYA,
        "estimated_value": 1750000.0,
        "machine_interest": "Automated Carton Packing Machine PKG-300 with Conveyor System",
        "unit_id": "Unit_2",
        "next_follow_up": None,
        "created_days_ago": 30,
        "notes": (
            "Deal closed! 30% advance received via RTGS. Converted to Customer Master CUST-008. "
            "Production order scheduled at Unit-2 facility. Delivery targeted within 4 weeks."
        ),
        "converted_customer_code": "CUST-008",
        "converted_customer_name": "Universal Carton Box & Packaging",
        "converted_days_ago": 5,
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 30,
                "summary": "Lead Initiated at PrintPack India Expo",
                "details": "Client visited booth and evaluated PKG-300 cartoner for corrugated mono-cartons.",
                "user": REP_PRIYA,
            },
            {
                "type": "CALL",
                "days_ago": 24,
                "summary": "Technical Specification Refinement",
                "details": "Reviewed carton dimensions (150x80x40mm up to 300x200x120mm) and speed requirement.",
                "user": REP_PRIYA,
            },
            {
                "type": "SITE_VISIT",
                "days_ago": 16,
                "summary": "Client Site Inspection at Udyog Vihar Gurugram",
                "details": "Engineering team inspected factory floor plan and layout alignment with current conveyors.",
                "user": REP_PRIYA,
            },
            {
                "type": "EMAIL",
                "days_ago": 9,
                "summary": "Submitted Final Commercial Contract",
                "details": "Sent agreement with payment milestones, 12-month standard warranty, and FAT checklist.",
                "user": REP_PRIYA,
            },
            {
                "type": "STATUS_CHANGE",
                "days_ago": 5,
                "summary": "Converted to Permanent Customer Master (CUST-008)",
                "details": "Advance payment of ₹5,25,000 received. Account converted and handed over to Production team.",
                "user": REP_PRIYA,
            },
        ],
        "materials": [
            {"item_code": "RM-MS-PLATE-10MM", "description": "Mild Steel 10mm Base Bedding", "qty": 380.0, "uom": "KG", "rate": 85.0, "notes": "Frame construction"},
            {"item_code": "RM-CI-CAST-001", "description": "CI Main Cam & Support Housing", "qty": 2.0, "uom": "NOS", "rate": 42000.0, "notes": "Casting component"},
            {"item_code": "RM-SS-ROD-20MM", "description": "SS Roller Shafts Ground", "qty": 55.0, "uom": "KG", "rate": 280.0, "notes": "Feed guide"},
        ],
    },
    {
        "code": "LEAD-2026-0009",
        "company_name": "Balaji Paper Converters",
        "contact_person": "Mr. Santosh Jadhav",
        "email": "s.jadhav@balajiconverters.com",
        "phone": "+91 98220 99881",
        "source": "EXISTING_CLIENT",
        "status": "CONVERTED",
        "priority": "HOT",
        "assigned_to": REP_ROHAN,
        "estimated_value": 1300000.0,
        "machine_interest": "High-Speed Automatic Envelope Making Machine ENV-200",
        "unit_id": "Unit_1",
        "next_follow_up": None,
        "created_days_ago": 25,
        "notes": (
            "Second machine expansion order from established converting client in Bhosari Pune. "
            "Contract finalized. Converted to Customer Master CUST-009."
        ),
        "converted_customer_code": "CUST-009",
        "converted_customer_name": "Balaji Paper Converters",
        "converted_days_ago": 3,
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 25,
                "summary": "Expansion Inbound Call from Existing Partner",
                "details": "Client requested second production line identical to their existing Unit-1 ENV-200 machine.",
                "user": REP_ROHAN,
            },
            {
                "type": "CALL",
                "days_ago": 15,
                "summary": "Delivery Timeline & Upgraded Touchscreen HMI Review",
                "details": "Client requested upgraded color touchscreen panel with multi-language operator guidance.",
                "user": REP_ROHAN,
            },
            {
                "type": "STATUS_CHANGE",
                "days_ago": 3,
                "summary": "Converted to Customer Master (CUST-009)",
                "details": "PO released and advance received. Converted to Customer account for order fulfillment.",
                "user": REP_ROHAN,
            },
        ],
    },
    {
        "code": "LEAD-2026-0010",
        "company_name": "Kavita Paper Mart & Stationery",
        "contact_person": "Mr. Ramesh Agarwal",
        "email": "ramesh@kavitapaper.com",
        "phone": "+91 94140 22345",
        "source": "COLD_CALL",
        "status": "LOST",
        "priority": "COLD",
        "assigned_to": REP_ROHAN,
        "estimated_value": 420000.0,
        "machine_interest": "Mini Desktop Envelope Machine ENV-MINI",
        "unit_id": "Unit_1",
        "next_follow_up": None,
        "created_days_ago": 20,
        "notes": (
            "Prospect opted for a refurbished second-hand machine from a local trader due to "
            "immediate budget ceiling of ₹2.2 Lakhs. Contact retained for future spare parts and tooling."
        ),
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 20,
                "summary": "Cold Call Lead Created",
                "details": "Initial telephone contact made during Jaipur print cluster outreach.",
                "user": REP_ROHAN,
            },
            {
                "type": "CALL",
                "days_ago": 13,
                "summary": "Budget Discussion & Second-Hand Competitor Comparison",
                "details": "Customer indicated tight capital budget constraint. Evaluated options for entry-level machine.",
                "user": REP_ROHAN,
            },
            {
                "type": "STATUS_CHANGE",
                "days_ago": 7,
                "summary": "Opportunity Marked as LOST",
                "details": "Customer purchased local refurbished machine. Documented feedback for product management.",
                "user": REP_ROHAN,
            },
        ],
    },
    {
        "code": "LEAD-2026-0011",
        "company_name": "Falcon Express Logistics & Mailers",
        "contact_person": "Mr. Vikram Sehgal",
        "email": "vikram.sehgal@falconexpress.in",
        "phone": "+91 98101 77650",
        "source": "DIRECT_INQUIRY",
        "status": "NEW",
        "priority": "HOT",
        "assigned_to": REP_PRIYA,
        "estimated_value": 2150000.0,
        "machine_interest": "High-Speed Envelope Line ENV-200 with Tamper-Evident Tape Unit",
        "unit_id": "Unit_1",
        # Follow-up upcoming tomorrow
        "next_follow_up": future_days(1, 2),
        "created_days_ago": 2,
        "notes": (
            "National courier and logistics firm in Faridabad establishing in-house tamper-proof "
            "document envelope production line. High volume potential of 500,000 pouches per month."
        ),
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 2,
                "summary": "Direct RFQ Received from Corporate Supply Chain VP",
                "details": "Formal RFQ received through sales@rgtech.com for high-speed automated security mailer machine.",
                "user": REP_PRIYA,
            },
            {
                "type": "EMAIL",
                "days_ago": 1,
                "summary": "Introductory Email & Technical Questionnaire Dispatched",
                "details": "Sent equipment overview and questionnaire to map daily throughput and film/paper specifications.",
                "user": REP_PRIYA,
            },
        ],
    },
    {
        "code": "LEAD-2026-0012",
        "company_name": "Evergreen Eco-Friendly Packaging",
        "contact_person": "Ms. Soundarya Natarajan",
        "email": "soundarya@evergreenpack.in",
        "phone": "+91 98422 66789",
        "source": "WEBSITE",
        "status": "NEW",
        "priority": "WARM",
        "assigned_to": REP_ROHAN,
        "estimated_value": 650000.0,
        "machine_interest": "Envelope Making Machine ENV-100 for Kraft & Recycled Paper",
        "unit_id": "Unit_2",
        # Follow-up upcoming tomorrow
        "next_follow_up": future_days(1, 5),
        "created_days_ago": 1,
        "notes": (
            "Eco-friendly startup in Coimbatore SIDCO manufacturing recycled seed-paper and unbleached "
            "brown kraft paper seed mailers. Testing compatibility with 140 GSM rough textured paper."
        ),
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 1,
                "summary": "Website Inquiry Submitted from Tamil Nadu Region",
                "details": "Prospect submitted query requesting technical data for handling rough textured kraft paper.",
                "user": REP_ROHAN,
            },
        ],
    },
    {
        "code": "LEAD-2026-0013",
        "company_name": "Mahalaxmi Box & Carton Industries",
        "contact_person": "Mr. Rajeshwar Raut",
        "email": "raut@mahalaxmibox.com",
        "phone": "+91 98230 44556",
        "source": "REFERRAL",
        "status": "NEW",
        "priority": "WARM",
        "assigned_to": REP_ADMIN,
        "estimated_value": 1580000.0,
        "machine_interest": "Carton Packing Machine PKG-300 Heavy Duty",
        "unit_id": "Unit_2",
        # Follow-up upcoming in 2 days
        "next_follow_up": future_days(2, 3),
        "created_days_ago": 3,
        "notes": (
            "Referred by Mr. Ashish at Pune Industrial Traders (CUST-006). Client wants automated "
            "carton folder-gluer line for Hingna MIDC Nagpur plant. Scheduled intro call."
        ),
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 3,
                "summary": "Customer Referral Logged from Pune Industrial Traders",
                "details": "Ashish from Pune Industrial referred their close associate expanding corrugated carton plant.",
                "user": REP_ADMIN,
            },
        ],
    },
    {
        "code": "LEAD-2026-0014",
        "company_name": "Deluxe Paper Bags & Envelopes",
        "contact_person": "Mr. Mansukhbhai Vora",
        "email": "mansukh.vora@deluxepack.in",
        "phone": "+91 98252 88990",
        "source": "DIRECT_INQUIRY",
        "status": "CONTACTED",
        "priority": "WARM",
        "assigned_to": REP_ROHAN,
        "estimated_value": 520000.0,
        "machine_interest": "Mini Envelope Machine ENV-MINI with Custom Die Plates",
        "unit_id": "Unit_1",
        # Follow-up upcoming in 3 days
        "next_follow_up": future_days(3, 4),
        "created_days_ago": 6,
        "notes": (
            "Established wedding card envelope manufacturer in Aji GIDC Rajkot. Interested in "
            "ENV-MINI with fast changeover tooling dies for metallic and textured art paper."
        ),
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 6,
                "summary": "Direct Call Inquiry Received",
                "details": "Owner called our sales desk seeking compact machine for high-gsm wedding covers.",
                "user": REP_ROHAN,
            },
            {
                "type": "CALL",
                "days_ago": 3,
                "summary": "Detailed Discussion on Tooling Changeover & Creasing",
                "details": "Explained quick 15-minute die change system and pre-creasing rotary wheels.",
                "user": REP_ROHAN,
            },
        ],
    },
    {
        "code": "LEAD-2026-0015",
        "company_name": "Sai Krishna Commercial Printers",
        "contact_person": "Mr. S. Raghavan",
        "email": "s.raghavan@saikrishnaprint.com",
        "phone": "+91 98400 55112",
        "source": "TRADE_EXPO",
        "status": "CONTACTED",
        "priority": "WARM",
        "assigned_to": REP_ROHAN,
        "estimated_value": 940000.0,
        "machine_interest": "Envelope Machine ENV-100 with Automatic Feeder",
        "unit_id": "Unit_2",
        # Follow-up upcoming in 4 days
        "next_follow_up": future_days(4, 2),
        "created_days_ago": 7,
        "notes": (
            "Commercial printing press in Guindy Chennai. Evaluating upgrade from semi-manual "
            "paper feeding to vacuum suction automated continuous feeder."
        ),
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 7,
                "summary": "Met at PrintExpo Chennai Stall",
                "details": "Client visited stall and inspected ENV-100 bottom suction feeder mechanism.",
                "user": REP_ROHAN,
            },
            {
                "type": "CALL",
                "days_ago": 4,
                "summary": "Compressor & Electrical Load Clarification",
                "details": "Provided air consumption CFM ratings and vacuum blower electrical specs.",
                "user": REP_ROHAN,
            },
        ],
    },
    {
        "code": "LEAD-2026-0016",
        "company_name": "Maruti Offset & Packaging Works",
        "contact_person": "Mr. Dinesh Sharma",
        "email": "dinesh@marutioffset.in",
        "phone": "+91 98270 33441",
        "source": "WEBSITE",
        "status": "QUALIFIED",
        "priority": "WARM",
        "assigned_to": REP_PRIYA,
        "estimated_value": 1280000.0,
        "machine_interest": "Automatic Envelope Making Machine ENV-200 Standard Model",
        "unit_id": "Unit_1",
        # Follow-up upcoming in 5 days
        "next_follow_up": future_days(5, 3),
        "created_days_ago": 11,
        "notes": (
            "Central India printing enterprise in Sanwer Road Indore. SIDBI MSME machinery loan pre-approved. "
            "3-phase electrical connection and plant space ready. Preparing formal commercial offer."
        ),
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 11,
                "summary": "Online RFQ Submitted",
                "details": "Inquiry submitted for Indore commercial printing unit expanding into stationery converting.",
                "user": REP_PRIYA,
            },
            {
                "type": "CALL",
                "days_ago": 8,
                "summary": "Financial Qualification & Factory Readiness",
                "details": "Verified bank capex sanction and shop floor readiness. Space allocated: 30x15 ft.",
                "user": REP_PRIYA,
            },
            {
                "type": "EMAIL",
                "days_ago": 3,
                "summary": "Dispatched Foundation Drawings & Civil Layout Guide",
                "details": "Sent civil foundation requirements and electrical power cabling schematics.",
                "user": REP_PRIYA,
            },
        ],
    },
    {
        "code": "LEAD-2026-0017",
        "company_name": "Krishna Valley Paper Mills Ltd",
        "contact_person": "Mr. Pranav Joshi",
        "email": "pranav.joshi@krishnavalleypaper.com",
        "phone": "+91 98255 11223",
        "source": "EXISTING_CLIENT",
        "status": "PROPOSAL_SENT",
        "priority": "WARM",
        "assigned_to": REP_ADMIN,
        "estimated_value": 2850000.0,
        "machine_interest": "High-Speed Rotary Die-Cutting Unit & Slitter Rewinder Line",
        "unit_id": "BOTH",
        # Follow-up upcoming in 6 days
        "next_follow_up": future_days(6, 4),
        "created_days_ago": 16,
        "notes": (
            "Paper mill converting division in GIDC Vapi. Comprehensive quotation submitted for "
            "custom rotary die cutter and heavy-duty slitter rewinder. Board review scheduled next week."
        ),
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 16,
                "summary": "Executive Inbound Call from Vapi Mill Head",
                "details": "Discussion with Mr. Pranav Joshi regarding slitter line for heavy kraft paper reels.",
                "user": REP_ADMIN,
            },
            {
                "type": "MEETING",
                "days_ago": 12,
                "summary": "Technical Discussion at Opti Matrix Unit-1 Facility",
                "details": "Client technical team visited Unit-1 facility in Ahmedabad to review CNC machining precision.",
                "user": REP_ADMIN,
            },
            {
                "type": "EMAIL",
                "days_ago": 5,
                "summary": "Dispatched Techno-Commercial Offer Rev-01",
                "details": "Comprehensive quotation ₹28.5L with performance guarantee of 250 metres/minute web speed.",
                "user": REP_ADMIN,
            },
        ],
    },
    {
        "code": "LEAD-2026-0018",
        "company_name": "Arihant Envelope & Stationery Mfg",
        "contact_person": "Mr. Pradeep Jain",
        "email": "pradeep.jain@arihantenvelope.com",
        "phone": "+91 98310 77889",
        "source": "DIRECT_INQUIRY",
        "status": "NEGOTIATION",
        "priority": "HOT",
        "assigned_to": REP_PRIYA,
        "estimated_value": 1620000.0,
        "machine_interest": "High-Speed Envelope Machine ENV-200 with Window & Peel-Seal Unit",
        "unit_id": "Unit_1",
        # Follow-up upcoming in 3 days
        "next_follow_up": future_days(3, 2),
        "created_days_ago": 14,
        "notes": (
            "Premier stationery brand in Burrabazar / Howrah Kolkata. Final round of negotiations. "
            "Client requested inclusion of transit insurance and complimentary 5-day on-site operator training."
        ),
        "activities": [
            {
                "type": "NOTE",
                "days_ago": 14,
                "summary": "Direct Inquiry from Eastern Region Association",
                "details": "Major envelope manufacturer in West Bengal reached out for capacity expansion.",
                "user": REP_PRIYA,
            },
            {
                "type": "CALL",
                "days_ago": 10,
                "summary": "Technical Scope & Tooling Alignment",
                "details": "Finalized envelope dimensions (SE-10, SE-11, and DL sizes) and window film thickness.",
                "user": REP_PRIYA,
            },
            {
                "type": "EMAIL",
                "days_ago": 6,
                "summary": "Sent Final Negotiation Commercial Proposal",
                "details": "Revised quotation ₹16.20L submitted including complete tooling set and digital counter.",
                "user": REP_PRIYA,
            },
            {
                "type": "CALL",
                "days_ago": 2,
                "summary": "Commercial Finalization Discussion with Director",
                "details": "Spoke with Director Mr. Pradeep Jain. Concurred on 15% advance and 12-month spare parts warranty.",
                "user": REP_PRIYA,
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Converted Customers to Ensure in Master Data
# ---------------------------------------------------------------------------
CONVERTED_CUSTOMERS = [
    {
        "code": "CUST-008",
        "name": "Universal Carton Box & Packaging",
        "gstin": "06AABCU9876Q1ZG",
        "pan": "AABCU9876Q",
        "contact_person": "Mr. Anil Batra",
        "phone": "+91 98110 44321",
        "email": "anil.batra@universalcarton.com",
        "billing_address": "Plot 45, Udyog Vihar Phase 4, Gurugram, Haryana 122016",
        "shipping_address": "Plot 45, Udyog Vihar Phase 4, Gurugram, Haryana 122016",
        "credit_limit": 1500000.0,
        "payment_terms_days": 30,
        "unit_id": "Unit_2",
        "is_active": True,
    },
    {
        "code": "CUST-009",
        "name": "Balaji Paper Converters",
        "gstin": "27AABCB5432R1ZF",
        "pan": "AABCB5432R",
        "contact_person": "Mr. Santosh Jadhav",
        "phone": "+91 98220 99881",
        "email": "s.jadhav@balajiconverters.com",
        "billing_address": "Sector 10, Plot 88, Bhosari MIDC, Pune, Maharashtra 411026",
        "shipping_address": "Sector 10, Plot 88, Bhosari MIDC, Pune, Maharashtra 411026",
        "credit_limit": 1200000.0,
        "payment_terms_days": 30,
        "unit_id": "Unit_1",
        "is_active": True,
    },
]


async def cleanup_crm_data(db: motor.motor_asyncio.AsyncIOMotorDatabase) -> None:
    """Safely remove previously seeded CRM records."""
    print("[CLEANUP] Cleaning up existing seeded CRM data...")
    res_leads = await db["crm_leads"].delete_many({"seed_tag": SEED_TAG})
    res_act = await db["crm_activities"].delete_many({"seed_tag": SEED_TAG})
    res_mat = await db["crm_lead_materials"].delete_many({"seed_tag": SEED_TAG})
    res_cust = await db["customers"].delete_many({"seed_tag": SEED_TAG})
    print(
        f"   Removed: {res_leads.deleted_count} leads, {res_act.deleted_count} activities, "
        f"{res_mat.deleted_count} materials, {res_cust.deleted_count} customer masters."
    )


async def seed_crm_data(db: motor.motor_asyncio.AsyncIOMotorDatabase) -> None:
    """Seed comprehensive CRM leads, activities, materials, and customer links."""
    print("[START] Seeding Real-World CRM & Leads Data...")

    # 1. Clean existing seeded data
    await cleanup_crm_data(db)

    # 2. Insert Converted Customer Master records first to get their IDs
    customer_id_map: Dict[str, str] = {}
    now_ts = datetime.now(timezone.utc)

    for cust in CONVERTED_CUSTOMERS:
        existing = await db["customers"].find_one({"code": cust["code"]})
        if existing:
            customer_id_map[cust["code"]] = str(existing["_id"])
            print(f"   [INFO] Customer {cust['code']} already exists (ID: {existing['_id']})")
        else:
            cust_doc = {
                **cust,
                "seed_tag": SEED_TAG,
                "created_at": now_ts - timedelta(days=5),
                "created_by": REP_ADMIN,
                "updated_at": now_ts - timedelta(days=5),
                "updated_by": REP_ADMIN,
            }
            res = await db["customers"].insert_one(cust_doc)
            customer_id_map[cust["code"]] = str(res.inserted_id)
            print(f"   [OK] Created Converted Customer Master: {cust['code']} - {cust['name']}")

    # 3. Seed Leads and their nested activities & materials
    seeded_leads_count = 0
    seeded_activities_count = 0
    seeded_materials_count = 0

    for lead_data in LEADS_DATA:
        lead_id = ObjectId()
        code = lead_data["code"]
        created_at = days_ago(lead_data.get("created_days_ago", 10))
        updated_at = days_ago(1)

        # Conversion metadata if converted
        converted_cust_id = None
        converted_at = None
        if lead_data.get("status") == "CONVERTED":
            cust_code = lead_data.get("converted_customer_code")
            if cust_code and cust_code in customer_id_map:
                converted_cust_id = customer_id_map[cust_code]
            converted_at = days_ago(lead_data.get("converted_days_ago", 3))

        lead_doc = {
            "_id": lead_id,
            "code": code,
            "company_name": lead_data["company_name"],
            "contact_person": lead_data["contact_person"],
            "email": lead_data.get("email"),
            "phone": lead_data["phone"],
            "source": lead_data["source"],
            "status": lead_data["status"],
            "priority": lead_data["priority"],
            "assigned_to": lead_data.get("assigned_to"),
            "estimated_value": float(lead_data.get("estimated_value", 0.0)),
            "machine_interest": lead_data.get("machine_interest"),
            "unit_id": lead_data.get("unit_id", "BOTH"),
            "next_follow_up": lead_data.get("next_follow_up"),
            "notes": lead_data.get("notes"),
            "converted_customer_id": converted_cust_id,
            "converted_at": converted_at,
            "created_at": created_at,
            "created_by": lead_data.get("assigned_to") or REP_ADMIN,
            "updated_at": updated_at,
            "updated_by": lead_data.get("assigned_to") or REP_ADMIN,
            "seed_tag": SEED_TAG,
        }

        await db["crm_leads"].insert_one(lead_doc)
        seeded_leads_count += 1

        # Seed activities for this lead
        activities = lead_data.get("activities", [])
        for act in activities:
            act_created_at = days_ago(act.get("days_ago", 1))
            act_doc = {
                "lead_id": str(lead_id),
                "activity_type": act["type"],
                "summary": act["summary"],
                "details": act.get("details"),
                "created_at": act_created_at,
                "created_by": act.get("user") or REP_ADMIN,
                "seed_tag": SEED_TAG,
            }
            await db["crm_activities"].insert_one(act_doc)
            seeded_activities_count += 1

        # Seed Project Hub materials for this lead if any
        materials = lead_data.get("materials", [])
        for mat in materials:
            qty = float(mat.get("qty", 1.0))
            rate = float(mat.get("rate", 0.0))
            total = round(qty * rate, 2)
            mat_doc = {
                "lead_id": str(lead_id),
                "lead_code": code,
                "item_code": mat["item_code"],
                "description": mat["description"],
                "required_quantity": qty,
                "uom": mat.get("uom", "NOS"),
                "estimated_unit_cost": rate,
                "total_estimated_cost": total,
                "required_date": (NOW + timedelta(days=15)).strftime("%Y-%m-%d"),
                "status": "ALLOCATED",
                "notes": mat.get("notes"),
                "created_at": created_at,
                "created_by": lead_data.get("assigned_to") or REP_ADMIN,
                "seed_tag": SEED_TAG,
            }
            await db["crm_lead_materials"].insert_one(mat_doc)
            seeded_materials_count += 1

    print(
        f"[OK] Successfully seeded {seeded_leads_count} Leads, "
        f"{seeded_activities_count} Activities, and {seeded_materials_count} Project BOM Materials."
    )

    # 4. Validate through CrmRepository dashboard summary
    repo = CrmRepository(db)
    summary_all = await repo.get_dashboard_summary()
    summary_u1 = await repo.get_dashboard_summary(unit_id="Unit_1")
    summary_u2 = await repo.get_dashboard_summary(unit_id="Unit_2")

    print("\n" + "=" * 60)
    print("CRM DASHBOARD METRICS VERIFICATION")
    print("=" * 60)
    print(f"Total Leads:               {summary_all['total_leads']}")
    print(f"Active Pipeline Leads:     {summary_all['active_leads']}")
    print(f"Hot Prospects:             {summary_all['hot_leads']}")
    print(f"Converted Clients:         {summary_all['converted_leads']}")
    print(f"Conversion Rate:           {summary_all['conversion_rate_percentage']}%")
    print(f"Follow-ups Due Today:      {summary_all['follow_ups_due_today']}")
    print(f"Follow-ups Overdue:        {summary_all['follow_ups_overdue']}")
    print(f"Pipeline by Status:        {summary_all['pipeline_by_status']}")
    print("-" * 60)
    print(f"Unit 1 - Total Leads:      {summary_u1['total_leads']} (Active: {summary_u1['active_leads']}, Hot: {summary_u1['hot_leads']})")
    print(f"Unit 2 - Total Leads:      {summary_u2['total_leads']} (Active: {summary_u2['active_leads']}, Hot: {summary_u2['hot_leads']})")
    print("=" * 60 + "\n")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed real-world CRM & Leads data.")
    parser.add_argument("--cleanup", action="store_true", help="Remove seeded CRM data only.")
    args = parser.parse_args()

    client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB_NAME]

    try:
        if args.cleanup:
            await cleanup_crm_data(db)
        else:
            await seed_crm_data(db)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
