"""
Opti Matrix ERP — Employee Task Seeding Script
File: backend/scripts/seed_employee_tasks.py

Provisions 4-5 domain-specific tasks for every employee across all departments,
with realistic priorities, statuses (PENDING, IN_PROGRESS, SUBMITTED_FOR_REVIEW, COMPLETED),
due dates, linked reporting officers, and completion evidence.
"""

import sys
import os
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.schemas.task import TaskPriority, TaskStatus
import motor.motor_asyncio
from bson import ObjectId

NOW = datetime.now(timezone.utc)

def due(days: int) -> str:
    return (NOW + timedelta(days=days)).strftime("%Y-%m-%d")

def created_ts(days_ago: int) -> datetime:
    return NOW - timedelta(days=days_ago)

EMPLOYEE_TASKS_DATA: Dict[str, List[Dict[str, Any]]] = {
    # ----------------------------------------------------
    # Production Department
    # ----------------------------------------------------
    "rahulsharma@rgtech.com": [
        {
            "title": "Finalize Weekly Production Schedule for Unit 1 ENV-100 & ENV-200",
            "description": "Align CNC machining hours, assembly station allocations, and shift schedules with active sales order delivery commitments for week 42.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(3),
            "days_ago": 2,
        },
        {
            "title": "Machine Downtime Root-Cause Analysis for CNC Milling Station #2",
            "description": "Investigate spindle vibration alert and coolant pressure drop that caused a 4-hour production stoppage during shift 1.",
            "priority": TaskPriority.URGENT.value,
            "status": TaskStatus.SUBMITTED_FOR_REVIEW.value,
            "due_date": due(1),
            "days_ago": 3,
            "completion_note": "Spindle bearing vibration root-cause identified and logged. Temporary bypass installed; scheduled overhaul aligned with maintenance team.",
            "completion_evidence": "RCA-CNC02-WK41.pdf",
        },
        {
            "title": "Review and Sign Off Multi-Level BOM Revisions for PKG-300 Packaging Line",
            "description": "Verify component gross quantity and scrap allowances with design engineering before engineering change order (ECO) release.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-2),
            "days_ago": 6,
            "completion_note": "BOM-PKG300-R1 reviewed and approved. Component quantities reconciled with mechanical CAD models.",
            "completion_evidence": "ECO-2026-PKG-08",
            "reviewed_by": "Ritesh Gajjar",
            "review_feedback": "Approved. Production engineering may proceed with revised specifications.",
        },
        {
            "title": "Conduct Scrap & Wastage Variance Audit with Quality Team",
            "description": "Compare theoretical scrap allowances against actual weighed metal turnings and plate trimming rejects for September batches.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.PENDING.value,
            "due_date": due(5),
            "days_ago": 1,
        },
        {
            "title": "Implement Preventive Maintenance Schedule with Technical Team",
            "description": "Establish monthly greasing, pneumatic filter cleaning, and hydraulic fluid checks for all heavy machinery in Unit 1.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(8),
            "days_ago": 4,
        },
    ],
    "amitpatel@rgtech.com": [
        {
            "title": "Daily Shop-Floor WIP Balancing and Machine Operator Shift Allocation",
            "description": "Allocate certified operators to Lathe, CNC Milling, and Assembly bays for Morning and General shifts. Balance stage buffers.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(1),
            "days_ago": 1,
        },
        {
            "title": "Verify Raw Material Issue Slips from Store A for Batch #PRD-202610-001",
            "description": "Cross-check MS plates 6mm and 10mm weight and heat numbers against material issue requisition voucher.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-1),
            "days_ago": 4,
            "completion_note": "All 1800kg of MS Plate 6mm received in bay; verified heat certificate matches purchase order.",
            "completion_evidence": "MIS-2026-10492",
            "reviewed_by": "Rahul Sharma",
            "review_feedback": "Good job verifying heat certificates. Authorized for cutting.",
        },
        {
            "title": "Tooling Wear & Tear Inspection for Lathe Machines #4 and #5",
            "description": "Inspect carbide turning inserts and tool holders. Replace chipped cutting edges to prevent surface roughness on rotor shafts.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.PENDING.value,
            "due_date": due(4),
            "days_ago": 2,
        },
        {
            "title": "Resolve Power-Cut Stoppage Protocol Log for Unit 1 Emergency Generator",
            "description": "Record exact diesel generator cut-in time, fuel consumed, and machine re-homing sequence during the 45-minute utility outage.",
            "priority": TaskPriority.URGENT.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-3),
            "days_ago": 5,
            "completion_note": "DG cut-in logged at 14:12; 18 liters diesel consumed; zero part damage occurred during transition.",
            "completion_evidence": "DG-LOG-20261008",
        },
        {
            "title": "Conduct End-of-Shift Production Output Entry & Scrap Logging",
            "description": "Log finished sub-assemblies and record metal turning weight in kilograms in the ERP production module before shift handover.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.SUBMITTED_FOR_REVIEW.value,
            "due_date": due(2),
            "days_ago": 1,
            "completion_note": "4 completed envelope folding feed-heads logged; 42kg mild steel scrap transferred to scrap bay.",
            "completion_evidence": "SHIFT-HANDOVER-U1-OCT12",
        },
    ],

    # ----------------------------------------------------
    # Quality Control
    # ----------------------------------------------------
    "nehamodi@rgtech.com": [
        {
            "title": "Validate First Article Inspection (FAI) Report for ENV-200 Rotor Shafts",
            "description": "Inspect run-out, concentricity, surface finish (Ra 0.8), and keyway dimensions for the newly machined rotor shafts.",
            "priority": TaskPriority.URGENT.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-1),
            "days_ago": 3,
            "completion_note": "All 12 dimensions within ±0.015mm tolerance. Certificate of Compliance signed off.",
            "completion_evidence": "QC-FAI-ENV200-089",
            "reviewed_by": "Ritesh Gajjar",
            "review_feedback": "Quality standards verified and approved.",
        },
        {
            "title": "Conduct Supplier Quality Audit on Jindal Steel Mild Steel Plates 6mm",
            "description": "Inspect test certificates for yield strength, elongation, and ultrasonic sound testing against IS:2062 specifications.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(3),
            "days_ago": 2,
        },
        {
            "title": "Establish Non-Conformance Report (NCR) for Bearing Batch #6205-B",
            "description": "Document radial clearance anomalies identified on 15 units of deep groove ball bearings during incoming sampling.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.SUBMITTED_FOR_REVIEW.value,
            "due_date": due(2),
            "days_ago": 2,
            "completion_note": "NCR drafted with digital micrometer measurement logs and supplier notification dispatch.",
            "completion_evidence": "NCR-2026-034.pdf",
        },
        {
            "title": "Calibrate Digital Vernier Calipers and Micrometers in QC Lab",
            "description": "Perform periodic calibration using master gauge blocks (Grade 0) and update laboratory calibration registry tags.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-4),
            "days_ago": 7,
            "completion_note": "8 Vernier calipers and 4 outside micrometers calibrated; calibration stickers affixed.",
            "completion_evidence": "CAL-CERT-OCT-2026",
        },
        {
            "title": "Review Weekly Rejection Trends and Scrap Categorization Report",
            "description": "Categorize scrap causes into Machining Deviation, Material Defect, Operator Error, and Tool Wear for management KPI dashboard.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.PENDING.value,
            "due_date": due(6),
            "days_ago": 1,
        },
    ],
    "vikasverma@rgtech.com": [
        {
            "title": "Incoming Inspection of 200kg Welding Electrodes from Indian Welding",
            "description": "Check AWS E6013 classification marking, moisture packaging integrity, and electrode diameter concentricity.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-2),
            "days_ago": 4,
            "completion_note": "Flux coating intact; zero moisture absorption observed. Batch accepted for welding shop.",
            "completion_evidence": "INSP-RM-WELD-202610",
        },
        {
            "title": "Perform Hardness & Tensile Testing on CI Body Castings (Lot #CG-409)",
            "description": "Perform Brinell hardness test (HBW 10/3000) on machine body casting mounting feet and bearing housings.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(2),
            "days_ago": 1,
        },
        {
            "title": "Dimensional Verification of Envelope Folding Knives against Drawing DWG-ENV-100-R3",
            "description": "Measure cutting angle bevel (45°), thickness, and mounting hole pitch on high-carbon steel knives.",
            "priority": TaskPriority.URGENT.value,
            "status": TaskStatus.SUBMITTED_FOR_REVIEW.value,
            "due_date": due(1),
            "days_ago": 2,
            "completion_note": "Knives verified with optical comparator. Bevel angle and hardness (58 HRC) conform to drawings.",
            "completion_evidence": "QC-KNIFE-INSP-992",
        },
        {
            "title": "Pre-Dispatch Inspection and Packaging Clearance for Order #SO-202610-001",
            "description": "Verify machine serial numbers, protective rust-preventive oil coating, and spare kit box inclusions before crate sealing.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.PENDING.value,
            "due_date": due(4),
            "days_ago": 1,
        },
    ],

    # ----------------------------------------------------
    # Inventory & Purchase
    # ----------------------------------------------------
    "sureshraina@rgtech.com": [
        {
            "title": "Conduct Monthly Physical Stock Audit in Raw Material Store A (WH-U1-RM01)",
            "description": "Physically count mild steel plates, structural channels, and round bars. Compare physical weights against ERP ledger.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(4),
            "days_ago": 2,
        },
        {
            "title": "Authorize Purchase Reorder for MS Plate 10mm Reaching Safety Threshold",
            "description": "Trigger reorder for 3000kg MS Plate 10mm as stock on hand dropped below minimum safety buffer of 800kg.",
            "priority": TaskPriority.URGENT.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-1),
            "days_ago": 3,
            "completion_note": "PO-2026-088 approved and transmitted to Jindal Steel with delivery commitment in 5 business days.",
            "completion_evidence": "PO-2026-088-APPROVED",
            "reviewed_by": "Ritesh Gajjar",
            "review_feedback": "Purchase order approved under standard commercial credit terms.",
        },
        {
            "title": "Reconcile Opening Balances for High-Value AC Induction Motors",
            "description": "Audit physical inventory of 0.5 HP and 1 HP motors in Warehouse B. Verify manufacturer serial numbers.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-3),
            "days_ago": 6,
            "completion_note": "All 35 units of 0.5 HP and 28 units of 1 HP motors physically tagged and verified.",
            "completion_evidence": "INV-AUDIT-ELEC-01",
        },
        {
            "title": "Optimize Rack Utilization and FIFO Tagging in Central Spares Depot",
            "description": "Reorganize fast-moving mechanical bearings and seals to bottom tiers to reduce picking time and improve ergonomics.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.PENDING.value,
            "due_date": due(7),
            "days_ago": 1,
        },
        {
            "title": "Evaluate Supplier Lead Times and Safety Stock Parameters for Q4",
            "description": "Analyze delivery performance and on-time in-full (OTIF) metrics for major raw material vendors over past 6 months.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.SUBMITTED_FOR_REVIEW.value,
            "due_date": due(3),
            "days_ago": 3,
            "completion_note": "OTIF metrics compiled; safety stocks for steel plates adjusted up 15% due to port logistics delays.",
            "completion_evidence": "SUPPLIER-LEAD-TIME-Q4.xlsx",
        },
    ],
    "dineshkarthik@rgtech.com": [
        {
            "title": "Bin Card Updating and Daily Goods Receipt Note (GRN) Verification",
            "description": "Post goods receipt notes for incoming consignments and update physical bin cards in Raw Material Store B.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(2),
            "days_ago": 1,
        },
        {
            "title": "Prepare Staging Kits for Tomorrow's ENV-MINI Assembly Batch",
            "description": "Kit motors, bearings, capacitors, rubber gaskets, and fasteners according to BOM-ENVMINI-R1 picklist.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-1),
            "days_ago": 2,
            "completion_note": "Full assembly kit prepared in Staging Bin #K-04; transferred to Unit 2 assembly line supervisor.",
            "completion_evidence": "KIT-SLIP-ENVMINI-22",
        },
        {
            "title": "Isolate and Tag Damaged Rubber Gaskets in Quarantine Bay",
            "description": "Identify 40 meters of deformed rubber gasket strip; mark with red quarantine tag to prevent assembly issuance.",
            "priority": TaskPriority.URGENT.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-3),
            "days_ago": 5,
            "completion_note": "Material isolated in Bay-Z; quarantine tag #Q-882 attached and notified QC team.",
            "completion_evidence": "QUARANTINE-TAG-882",
        },
        {
            "title": "Perform Cycle Count on Ball Bearings 6205 ZZ in Warehouse U2-RM02",
            "description": "Count all sealed boxes and individual units in Bin #B-12. Compare physical count against ERP stock of 150 units.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.PENDING.value,
            "due_date": due(3),
            "days_ago": 1,
        },
    ],

    # ----------------------------------------------------
    # Sales & CRM
    # ----------------------------------------------------
    "priyashah@rgtech.com": [
        {
            "title": "Finalize Annual Machine Supply Contract with National Paper Industries",
            "description": "Negotiate payment terms, delivery milestones, and AMC coverage for 4 custom automated envelope making machines.",
            "priority": TaskPriority.URGENT.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(3),
            "days_ago": 2,
        },
        {
            "title": "Review Q3 Sales Targets and Customer Payment Realization Matrix",
            "description": "Analyze booked orders versus delivered machines and reconcile customer advance milestones against credit limits.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-2),
            "days_ago": 5,
            "completion_note": "Q3 performance deck finalized: ₹78.4 Lakhs in machine deliveries booked; ₹18.5 Lakhs collected.",
            "completion_evidence": "SALES-Q3-SUMMARY-DECK",
            "reviewed_by": "Ritesh Gajjar",
            "review_feedback": "Commendable sales realization. Keep close follow-up on outstanding payments.",
        },
        {
            "title": "Prepare Technical Quotation for 2 Units of Carton Packer PKG-300",
            "description": "Calculate machine configuration cost, customized conveyor extension charges, and GST invoice projection for Delhi Packaging.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.SUBMITTED_FOR_REVIEW.value,
            "due_date": due(2),
            "days_ago": 2,
            "completion_note": "Commercial proposal with 45-day warranty and commissioning clauses submitted for final review.",
            "completion_evidence": "QUOT-2026-DELHI-PKG",
        },
        {
            "title": "Follow Up with Bengaluru Office Supplies for Advance Payment Release",
            "description": "Coordinate with client procurement head to release 30% advance on Order #SO-202610-001 before machine release.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-1),
            "days_ago": 3,
            "completion_note": "RTGS payment receipt of ₹3,35,946 received and confirmed with finance department.",
            "completion_evidence": "UTR-HDFC-9920148812",
        },
        {
            "title": "Conduct Monthly CRM Pipeline Review and Sales Forecast Update",
            "description": "Review prospective inquiries, site inspection requests, and lead conversion rates in CRM module for November.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.PENDING.value,
            "due_date": due(6),
            "days_ago": 1,
        },
    ],
    "rohangupta@rgtech.com": [
        {
            "title": "Lead Qualification and Technical Demo Scheduling for Gujarat Paper Mills",
            "description": "Contact inquiry from trade expo; explain technical envelope folding speed (100 vs 200 env/min) and schedule factory visit.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(2),
            "days_ago": 1,
        },
        {
            "title": "Follow Up on Outstanding Quotation for Delhi Packaging Solutions",
            "description": "Engage procurement contact regarding technical clarification on electrical specifications and motor horsepower.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-2),
            "days_ago": 4,
            "completion_note": "Clarified that single-phase 230V motor is standard; revised quotation sent.",
            "completion_evidence": "EMAIL-DELHI-PKG-OCT08",
        },
        {
            "title": "Collect Signed Delivery Challan and Customer Feedback for SO-202609-001",
            "description": "Obtain signed and stamped consignee copy of delivery challan from Ravi Stationery Pvt Ltd for finance billing archive.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-3),
            "days_ago": 6,
            "completion_note": "Signed delivery receipt uploaded; customer rated commissioning 5/5 stars.",
            "completion_evidence": "SIGNED-POD-RAVI-STAT",
        },
        {
            "title": "Update Customer Contact Database and Commercial Payment Terms",
            "description": "Update active phone numbers, GSTIN registration addresses, and key decision maker emails across 7 master accounts.",
            "priority": TaskPriority.LOW.value,
            "status": TaskStatus.PENDING.value,
            "due_date": due(5),
            "days_ago": 1,
        },
    ],

    # ----------------------------------------------------
    # Dispatch & Logistics
    # ----------------------------------------------------
    "sanjayrawat@rgtech.com": [
        {
            "title": "Coordinate Heavy Freight Trailer Booking for ENV-200 to Hyderabad",
            "description": "Hire low-bed trailer with hydraulic ramp and air suspension for safe transport of 2.5-ton automated envelope machine.",
            "priority": TaskPriority.URGENT.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(2),
            "days_ago": 1,
        },
        {
            "title": "Verify Wooden Crate Export Packaging and Moisture Sealing Standards",
            "description": "Inspect ISPM-15 heat-treated wooden crates, VCI anti-rust poly-wrapping, and silica gel desiccant packs.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-1),
            "days_ago": 3,
            "completion_note": "Crate inspection completed for Machine ENV-100; packing sign-off approved.",
            "completion_evidence": "CRATE-SIGN-OFF-U1-09",
            "reviewed_by": "Ritesh Gajjar",
            "review_feedback": "Packaging standards meet transit protection requirements.",
        },
        {
            "title": "Review Transporter Rate Contracts and Transit Insurance Coverage",
            "description": "Compare per-kilometer freight quotations and verify marine transit open policy cover note validity for Q4.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-4),
            "days_ago": 7,
            "completion_note": "Transit insurance policy renewed with New India Assurance up to ₹2 Crore cover.",
            "completion_evidence": "POLICY-NIA-2026-TRANSIT",
        },
        {
            "title": "Reconcile Pending E-Way Bills with Billing Department for Dispatch Clearance",
            "description": "Ensure Part-B vehicle details are generated within statutory timelines to prevent tax detention en route.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.SUBMITTED_FOR_REVIEW.value,
            "due_date": due(1),
            "days_ago": 2,
            "completion_note": "E-way bills generated for 3 dispatches; vehicle registration numbers confirmed with fleet operator.",
            "completion_evidence": "EWAY-RECON-WK41.pdf",
        },
        {
            "title": "Supervise Container Stuffing and Lashing Inspection for Unit 1 Yard",
            "description": "Verify high-tensile polyester ratchet lashing and corner buffer blocks before trailer departure from factory gate.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.PENDING.value,
            "due_date": due(4),
            "days_ago": 1,
        },
    ],
    "karanmalhotra@rgtech.com": [
        {
            "title": "Generate Packing Slips and Barcode Shipping Labels for SO-202610-003",
            "description": "Print tamper-evident barcode labels for main machine crate, toolbox accessory carton, and electrical control panel box.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-1),
            "days_ago": 2,
            "completion_note": "Packing slip #PS-202610-003 created; QR code shipping labels affixed to all 3 packages.",
            "completion_evidence": "PS-202610-003-LABELS",
        },
        {
            "title": "Coordinate Loading Sequence with Crane Operators in Finished Goods Bay",
            "description": "Safely rig machine lifting eye-bolts and coordinate 5-ton overhead gantry crane for trailer placement.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(1),
            "days_ago": 1,
        },
        {
            "title": "Track In-Transit Consignment GPS Status for Mumbai Delivery",
            "description": "Monitor live GPS feed for truck MH-04-GP-1204 en route to National Paper Industries; confirm estimated arrival time.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-2),
            "days_ago": 3,
            "completion_note": "Consignment safely delivered at client Saki Vihar facility; proof of delivery received.",
            "completion_evidence": "GPS-POD-MH04GP1204",
        },
        {
            "title": "Maintain Gate Pass and Transporter Delivery Acknowledgement Register",
            "description": "Reconcile security out-pass serial numbers with daily dispatch logbook and driver signature sheets.",
            "priority": TaskPriority.LOW.value,
            "status": TaskStatus.PENDING.value,
            "due_date": due(4),
            "days_ago": 1,
        },
    ],

    # ----------------------------------------------------
    # Billing & Finance
    # ----------------------------------------------------
    "ananyaiyer@rgtech.com": [
        {
            "title": "File Monthly GST Output (GSTR-1) and Reconcile Input Tax Credit (GSTR-2B)",
            "description": "Reconcile outward tax invoices with e-invoicing portal and verify eligible GST input tax credits on supplier bills.",
            "priority": TaskPriority.URGENT.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(2),
            "days_ago": 2,
        },
        {
            "title": "Review Outstanding Receivables Aging Report (>45 Days Overdue)",
            "description": "Flag overdue customer balances and coordinate reminder statements with sales department for credit recovery.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-2),
            "days_ago": 5,
            "completion_note": "Receivables aging report compiled: ₹4.8 Lakhs recovered this week; balance accounts on notice.",
            "completion_evidence": "AR-AGING-REPORT-OCT",
            "reviewed_by": "Ritesh Gajjar",
            "review_feedback": "Sound financial oversight. Continue rigorous debtor follow-up.",
        },
        {
            "title": "Authorize Commercial Tax Invoices for Week 41 Machine Deliveries",
            "description": "Validate HSN codes (84411000 for envelope machines), CGST/SGST vs IGST splits, and customer billing GSTIN.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-1),
            "days_ago": 3,
            "completion_note": "Invoices INV-202610-001 and INV-202610-002 signed and dispatched to clients.",
            "completion_evidence": "TAX-INV-WK41-SIGNED",
        },
        {
            "title": "Conduct Quarterly Cost-Center Budget vs Actual Variance Review",
            "description": "Analyze manufacturing overhead variances, direct labor overtime costs, and electricity consumption per machine unit.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.SUBMITTED_FOR_REVIEW.value,
            "due_date": due(3),
            "days_ago": 3,
            "completion_note": "Cost-center variance report finalized. Material costs were 2.3% below budget due to bulk procurement.",
            "completion_evidence": "BUDGET-VARIANCE-Q3.xlsx",
        },
        {
            "title": "Coordinate with External Statutory Auditors for Half-Yearly Financials",
            "description": "Prepare bank balance confirmations, fixed asset schedules, and physical stock certificate for auditor verification.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.PENDING.value,
            "due_date": due(8),
            "days_ago": 1,
        },
    ],
    "manishtiwari@rgtech.com": [
        {
            "title": "Daily Bank Reconciliation of HDFC and SBI Current Operating Accounts",
            "description": "Match cleared bank statement credits against customer ERP receipts and reconcile auto-debited supplier cheques.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-1),
            "days_ago": 2,
            "completion_note": "HDFC and SBI bank books reconciled with zero unadjusted differences as of yesterday.",
            "completion_evidence": "BRS-HDFC-SBI-OCT11",
        },
        {
            "title": "Process Vendor Supplier Bill Vouchers with 3-Way GRN Match",
            "description": "Verify purchase order rate, storekeeper goods receipt note quantity, and vendor tax invoice amounts before booking payables.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(2),
            "days_ago": 1,
        },
        {
            "title": "Verify Petty Cash Vouchers and Shift Maintenance Imprest Balances",
            "description": "Audit plant maintenance emergency cash vouchers, fuel chits, and factory canteen provisions.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-3),
            "days_ago": 5,
            "completion_note": "Petty cash book audited; ₹18,450 vouchers cleared and reimbursed to factory cashier.",
            "completion_evidence": "PETTY-CASH-AUDIT-09",
        },
        {
            "title": "Compute Monthly TDS Deductions on Contractor and Professional Payments",
            "description": "Calculate Section 194C and 194J tax deductions for factory maintenance and security contractor bills.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.PENDING.value,
            "due_date": due(5),
            "days_ago": 1,
        },
    ],

    # ----------------------------------------------------
    # HR & Administration
    # ----------------------------------------------------
    "kavitadeshmukh@rgtech.com": [
        {
            "title": "Process and Authorize October Payroll Disbursement across Unit 1 & Unit 2",
            "description": "Verify working day calculations, employee overtime hours, professional tax, and PF/ESI deductions for all 19 staff.",
            "priority": TaskPriority.URGENT.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(3),
            "days_ago": 2,
        },
        {
            "title": "Conduct Performance Review and Probation Sign-off for Technical Trainees",
            "description": "Review supervisor feedback ratings and skills evaluation for trainee machine operators completing 6 months.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-2),
            "days_ago": 5,
            "completion_note": "Probation confirmation letters issued for 2 technicians following satisfactory supervisor assessment.",
            "completion_evidence": "PROB-CONFIRM-2026-OCT",
            "reviewed_by": "Ritesh Gajjar",
            "review_feedback": "Probation confirmations approved. Good talent retention focus.",
        },
        {
            "title": "Audit Factory Act Statutory Compliance & PF/ESI Challan Filings",
            "description": "Verify electronic challan cum returns (ECR) for Provident Fund and ESI portal payments within statutory deadline.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-4),
            "days_ago": 7,
            "completion_note": "PF ECR challan of ₹92,400 and ESI challan paid and filed on EPFO portal.",
            "completion_evidence": "EPFO-CHALLAN-ACK-SEP26",
        },
        {
            "title": "Implement Shop-Floor Safety and PPE Gear Training Workshop",
            "description": "Organize certified industrial safety training covering eye protection, steel-toe shoes, ear plugs, and fire extinguisher use.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.SUBMITTED_FOR_REVIEW.value,
            "due_date": due(4),
            "days_ago": 2,
            "completion_note": "Workshop curriculum finalized with National Safety Council certified trainer; scheduled for Saturday.",
            "completion_evidence": "SAFETY-WORKSHOP-CURRICULUM",
        },
        {
            "title": "Review Employee Leave Applications and Biometric Punch Regularization",
            "description": "Review pending earned and medical leave applications in HR module; resolve unrecorded biometric gate punches.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.PENDING.value,
            "due_date": due(5),
            "days_ago": 1,
        },
    ],
    "deepakjoshi@rgtech.com": [
        {
            "title": "Audit Daily Biometric Punch Discrepancies and Mark Absenteeism",
            "description": "Reconcile Unit 1 and Unit 2 biometric turnstile logs with shift roster; identify late arrivals and unpunched exits.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-1),
            "days_ago": 2,
            "completion_note": "Daily attendance verified; 3 punch regularizations approved by department supervisors.",
            "completion_evidence": "ATTENDANCE-AUDIT-OCT11",
        },
        {
            "title": "Complete Onboarding Document Verification for New Assembly Fitters",
            "description": "Verify Aadhaar cards, bank passbooks, previous experience letters, and conduct background check verification.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(2),
            "days_ago": 1,
        },
        {
            "title": "Issue Employee ID Cards and Health Insurance E-Cards",
            "description": "Print RFID proximity employee badges and register enrolled staff under corporate group mediclaim policy.",
            "priority": TaskPriority.LOW.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-3),
            "days_ago": 6,
            "completion_note": "RFID cards issued; Mediclaim policy portal enrollment acknowledged.",
            "completion_evidence": "INSURANCE-ENROLLMENT-08",
        },
        {
            "title": "Reconcile Overtime Hours Register with Production Shift In-charge",
            "description": "Audit physical overtime token slips against machine operating logbook hours for weekend fabrication shifts.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.PENDING.value,
            "due_date": due(4),
            "days_ago": 1,
        },
    ],

    # ----------------------------------------------------
    # Maintenance & Technical
    # ----------------------------------------------------
    "rameshsolanki@rgtech.com": [
        {
            "title": "Overhaul Spindle Bearings and Lubrication Lines of Milling CNC-01",
            "description": "Dismantle high-speed spindle assembly; flush old grease, install matched pair of angular contact bearings, and set preload.",
            "priority": TaskPriority.URGENT.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(2),
            "days_ago": 2,
        },
        {
            "title": "Inspect Unit 1 Main Power Transformer and Earth Resistance Testing",
            "description": "Measure earth pit resistance with calibrated megger test; verify transformer oil dielectric breakdown voltage (>30 kV).",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-2),
            "days_ago": 5,
            "completion_note": "Earth pits measured at 1.8 Ohms (within 2 Ohm limit). Transformer oil BDV tested at 38 kV.",
            "completion_evidence": "EARTH-TEST-CERT-OCT2026",
            "reviewed_by": "Ritesh Gajjar",
            "review_feedback": "Electrical safety inspection verified and archived.",
        },
        {
            "title": "Prepare Annual Spares Requirement Forecast for Critical Machine Drives",
            "description": "Identify long lead-time imported servo amplifiers, drive belts, and magnetic encoders to maintain safety stock.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-4),
            "days_ago": 8,
            "completion_note": "Annual spares catalog compiled; list forwarded to procurement manager for budget approval.",
            "completion_evidence": "CRITICAL-SPARES-2027.xlsx",
        },
        {
            "title": "Resolve Hydraulic Pressure Fluctuation on Sheet Metal Shearing Line",
            "description": "Inspect proportional relief valve and pilot check valves; bleed air from main hydraulic cylinders.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.SUBMITTED_FOR_REVIEW.value,
            "due_date": due(2),
            "days_ago": 2,
            "completion_note": "Relief valve seat cleaned and seals replaced. System holding stable 180 bar working pressure.",
            "completion_evidence": "MAINT-HYD-JOB-091",
        },
        {
            "title": "Calibrate Compressor Air Pressure Regulators and Pneumatic Valves",
            "description": "Service central rotary screw compressor; replace oil separator filter element and set line pressure to 7.2 bar.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.PENDING.value,
            "due_date": due(6),
            "days_ago": 1,
        },
    ],
    "chetanprajapati@rgtech.com": [
        {
            "title": "Clean and Refill Coolant Oil Reservoirs on Lathe Machines #1 to #6",
            "description": "Skim tramp oil from emulsion reservoirs, test coolant concentration (6-8% on refractometer), and top up Servo-cut S.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-1),
            "days_ago": 3,
            "completion_note": "Coolant tanks cleaned and refilled with 7% concentration; pH tested stable at 9.0.",
            "completion_evidence": "COOLANT-LOG-OCT10",
        },
        {
            "title": "Inspect Conveyor Belt Tension and Motor V-Belts in Packaging Section",
            "description": "Check belt alignment, tension deflection (10mm), and pulley groove wear across Unit 2 assembly line.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(2),
            "days_ago": 1,
        },
        {
            "title": "Replace Worn Carbon Brushes on Overhead EOT Crane Hoist Motor",
            "description": "Inspect slip-ring commutator surface and replace 4 units of carbon brushes to prevent arcing.",
            "priority": TaskPriority.URGENT.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-3),
            "days_ago": 5,
            "completion_note": "Carbon brushes replaced; commutator polished with fine sandpaper; hoist tested under 3-ton proof load.",
            "completion_evidence": "CRANE-HOIST-JOB-44",
        },
        {
            "title": "Daily Log Entry for DG Set Fuel Levels and Battery Voltage Check",
            "description": "Record morning diesel fuel level in storage tank, starter battery terminal voltage (24V DC), and radiator coolant level.",
            "priority": TaskPriority.LOW.value,
            "status": TaskStatus.PENDING.value,
            "due_date": due(3),
            "days_ago": 1,
        },
    ],

    # ----------------------------------------------------
    # Inventory & Purchase (Mayank Gajjar)
    # ----------------------------------------------------
    "mayan@rgtech.com": [
        {
            "title": "Issue RFQ for 15 MT Mild Steel Plates to Approved Vendor List",
            "description": "Prepare detailed RFQ specification for MS Plate 6mm and 10mm IS:2062; solicit commercial quotes with 30-day credit terms.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.IN_PROGRESS.value,
            "due_date": due(3),
            "days_ago": 2,
        },
        {
            "title": "Negotiate Freight Rates with Gujarat Logistics for Inward Consignments",
            "description": "Review ton-per-kilometer haulage rates for raw material transit between Hazira steel plant and Unit 1 facility.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-2),
            "days_ago": 4,
            "completion_note": "Secured 8% volume discount on dedicated 16-ton truckloads; revised rate sheet archived.",
            "completion_evidence": "FREIGHT-AGREEMENT-2026",
            "reviewed_by": "Suresh Raina",
            "review_feedback": "Favorable freight terms negotiated. Approved.",
        },
        {
            "title": "Track Purchase Order Status for Precision Ball Bearings with SKF India",
            "description": "Expedite dispatch of 100 units 6205 ZZ ball bearings needed for upcoming ENV-100 manufacturing batch.",
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.SUBMITTED_FOR_REVIEW.value,
            "due_date": due(1),
            "days_ago": 2,
            "completion_note": "SKF confirmed consignment dispatched via Blue Dart AWB #7719204481; ETA tomorrow.",
            "completion_evidence": "TRACKING-AWB-SKF-7719",
        },
        {
            "title": "Resolve Invoice Price Discrepancy on Reliance Petro Lubricants Bill",
            "description": "Reconcile ₹4,200 difference between PO contracted rate and billed invoice amount for cutting oil drums.",
            "priority": TaskPriority.MEDIUM.value,
            "status": TaskStatus.COMPLETED.value,
            "due_date": due(-3),
            "days_ago": 6,
            "completion_note": "Supplier issued credit note CN-2026-991 for ₹4,200 to correct rate discrepancy.",
            "completion_evidence": "CREDIT-NOTE-RIL-991",
        },
        {
            "title": "Establish Backup Vendor for Industrial Synthetic Grey Enamel Paint",
            "description": "Evaluate sample panels from Asian Paints and Berger Paints for chemical resistance and drying time on CI castings.",
            "priority": TaskPriority.LOW.value,
            "status": TaskStatus.PENDING.value,
            "due_date": due(7),
            "days_ago": 1,
        },
    ],
}

# Mapping: department employees to their designated reporting officer
REPORTING_OFFICERS_MAP: Dict[str, str] = {
    # Managers report directly to Owner / Super Admin
    "rahulsharma@rgtech.com": "admin@rgtech.com",
    "nehamodi@rgtech.com": "admin@rgtech.com",
    "sureshraina@rgtech.com": "admin@rgtech.com",
    "priyashah@rgtech.com": "admin@rgtech.com",
    "sanjayrawat@rgtech.com": "admin@rgtech.com",
    "ananyaiyer@rgtech.com": "admin@rgtech.com",
    "kavitadeshmukh@rgtech.com": "admin@rgtech.com",
    "rameshsolanki@rgtech.com": "admin@rgtech.com",

    # Supervisors and specialists report to their respective department managers
    "amitpatel@rgtech.com": "rahulsharma@rgtech.com",
    "vikasverma@rgtech.com": "nehamodi@rgtech.com",
    "dineshkarthik@rgtech.com": "sureshraina@rgtech.com",
    "mayan@rgtech.com": "sureshraina@rgtech.com",
    "rohangupta@rgtech.com": "priyashah@rgtech.com",
    "karanmalhotra@rgtech.com": "sanjayrawat@rgtech.com",
    "manishtiwari@rgtech.com": "ananyaiyer@rgtech.com",
    "deepakjoshi@rgtech.com": "kavitadeshmukh@rgtech.com",
    "chetanprajapati@rgtech.com": "rameshsolanki@rgtech.com",
}


async def seed_tasks():
    client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB_NAME]

    users_col = db["users"]
    emp_col = db["employees"]
    tasks_col = db["tasks"]

    # Map users by email
    users_list = await users_col.find({"is_active": True}).to_list(length=100)
    user_map = {u["email"].lower(): u for u in users_list}

    # Map employees by email
    emps_list = await emp_col.find({"is_active": True}).to_list(length=100)
    emp_map = {e.get("email", "").lower(): e for e in emps_list}

    print("=" * 65)
    print("Opti Matrix ERP — Seeding 4 to 5 Tasks for Every Employee")
    print("=" * 65)

    # Clean existing tasks created by this seed to make script idempotent
    await tasks_col.delete_many({"_seed": "employee_tasks_v1"})

    task_counter = 1
    total_created = 0

    for email, tasks in EMPLOYEE_TASKS_DATA.items():
        user = user_map.get(email.lower())
        if not user:
            print(f"[SKIP] User account not found for: {email}")
            continue

        emp = emp_map.get(email.lower(), {})
        officer_email = REPORTING_OFFICERS_MAP.get(email.lower(), "admin@rgtech.com")
        officer_user = user_map.get(officer_email.lower())

        officer_name = (
            officer_user.get("full_name") if officer_user
            else "Ritesh Gajjar"
        )
        officer_id = str(officer_user["_id"]) if officer_user else str(user["_id"])

        user_name = user.get("full_name") or emp.get("full_name") or email
        user_code = user.get("employee_code") or emp.get("code") or "EMP-GEN"
        unit_id = emp.get("unit_id") or "Unit_1"
        if unit_id not in ["Unit_1", "Unit_2"]:
            unit_id = "Unit_1"

        print(f"\n[{user_name} ({user_code}) — {email}]")
        print(f"  Reporting To: {officer_name} ({officer_email})")

        for t in tasks:
            task_num = f"TSK-2026-{task_counter:04d}"
            task_counter += 1

            created_time = created_ts(t.get("days_ago", 2))
            is_done = t["status"] in [TaskStatus.COMPLETED.value, TaskStatus.SUBMITTED_FOR_REVIEW.value]
            submitted_time = created_time + timedelta(hours=18) if is_done else None
            reviewed_time = submitted_time + timedelta(hours=6) if t["status"] == TaskStatus.COMPLETED.value else None

            doc = {
                "_seed": "employee_tasks_v1",
                "task_number": task_num,
                "title": t["title"],
                "description": t["description"],
                "priority": t["priority"],
                "status": t["status"],
                "due_date": t["due_date"],

                # Reporting Officer
                "reporting_officer_id": officer_id,
                "reporting_officer_name": officer_name,
                "reporting_officer_email": officer_email,

                # Creator Employee
                "created_by_id": str(user["_id"]),
                "created_by_code": user_code,
                "created_by_name": user_name,
                "created_by_email": email,

                # Metadata & Workflow
                "attachments": [t["completion_evidence"]] if t.get("completion_evidence") else [],
                "source_module": "task_management",
                "unit_id": unit_id,
                "created_at": created_time,
                "updated_at": reviewed_time or submitted_time or created_time,

                # Submission details
                "submitted_at": submitted_time,
                "submitted_by": user_name if is_done else None,
                "completion_note": t.get("completion_note"),
                "completion_evidence": t.get("completion_evidence"),

                # Review details
                "reviewed_at": reviewed_time,
                "reviewed_by": t.get("reviewed_by") if t["status"] == TaskStatus.COMPLETED.value else None,
                "review_feedback": t.get("review_feedback") if t["status"] == TaskStatus.COMPLETED.value else None,
            }

            await tasks_col.insert_one(doc)
            total_created += 1
            status_flag = f"[{t['status']}]"
            print(f"  - {task_num} {status_flag:24s} : {t['title'][:55]}...")

    print("\n" + "=" * 65)
    print(f"[SUCCESS] Seeded {total_created} tasks across {len(EMPLOYEE_TASKS_DATA)} employees!")
    print(f"Total tasks in database now: {await tasks_col.count_documents({})}")
    print("=" * 65)

    client.close()


if __name__ == "__main__":
    asyncio.run(seed_tasks())
