# RG Tech ERP - Release Notes v1.0.0 (Phase 1–15 Production Release)

## Release Overview
**Version**: 1.0.0-GA  
**Target Architecture**: RG Tech Dual-Facility Industrial Machinery ERP (`Unit 1` and `Unit 2`)  
**Deployment Date**: October 2026  

---

## 1. Modules Delivered & Verified

1. **Authentication, Sessions & RBAC**:
   - Single unified login with Argon2id password hashing and SHA-256 session token hashing.
   - Granular RBAC supporting 8 operational roles across 18 modules.
   - Dual-facility data isolation for `Unit 1`, `Unit 2`, and corporate `BOTH`.
2. **Master Data Hub**:
   - Customer, Vendor, Employee, Finished Product, Raw Material, Warehouse, Category, and UoM management with duplicate prevention.
3. **CRM & Lead Management**:
   - Lead pipeline tracking, follow-ups, and one-click duplicate-safe conversion to Customer Master.
4. **Sales Orders & Dispatch**:
   - Order lifecycle tracking, packing slip generation, and partial dispatch reconciliation.
5. **Inventory & Warehouse Ledger**:
   - Real-time stock movements, audit ledger, inter-warehouse transfers, negative stock rejection, and low-stock alerts.
6. **Bill of Materials (BOM)**:
   - Multi-level BOM creation, circular dependency prevention, version locks, approved revisions, and cost rollups.
7. **Production Planning & WIP**:
   - Production orders, scheduled start/end dates, material requirement calculations, reservation/issuance, and WIP receipts.
8. **Quality Control & Non-Conformance**:
   - Inward, in-process, and finished goods inspections, non-conformance reports, and hold-release workflows.
9. **Wastage, Scrap & Power Outage Tracking**:
   - Daily scrap logging, cause categorization, power outage start/end records, and downtime duration calculations.
10. **HR, Attendance & Payroll**:
    - Shift assignments, attendance tracking, leave requests, overtime calculation, approved salary posting, and immutable payroll runs.
11. **Finance, Accounts & Double-Entry Ledger**:
    - Standard Chart of Accounts (COA), Customer Invoices (AR), Supplier Bills (AP), QC payment hold enforcement, payment disbursements, and balanced journal vouchers (\(\sum \text{Debit} = \sum \text{Credit}\)).
12. **Reports, Analytics & Excel Migration**:
    - Comprehensive cross-module reports across 12 operational domains with date-range/unit filters and CSV/Excel exports.
    - Safe Excel migration studio with standard template downloads, dry-run validation, duplicate checks, and idempotent commits.

---

## 2. QA & Security Audit Summary

- **Automated Tests**:
  - Total automated test cases executed: **54**
  - Total tests passed: **54** (100% pass rate)
  - Pytest execution time: **42.66s**
- **Security Audit**:
  - Zero hardcoded credentials or unmasked secrets in logs.
  - HttpOnly and SameSite=Lax session cookies.
  - Mandatory CSRF protection on all state-altering operations.
  - Multi-tenant facility isolation verified.
- **Frontend Quality**:
  - TypeScript compilation: **0 errors** (`npx tsc --noEmit`).
  - Next.js production build: **30/30 routes compiled** with standalone server output tracing.

---

## 3. Known Limitations & Production Notes

1. **MongoDB Transactions**:
   - In single-node development mode without a replica set, atomic updates use document-level atomic operators (`find_one_and_update`, `$inc`, `$push`). For high-concurrency multi-document ACID transactions across collections in production, MongoDB **must** be initialized as a Replica Set.
2. **PDF Payslip & Invoice Export**:
   - Invoices, packing slips, and payslips are currently rendered natively on the web with print-friendly CSS and downloadable as Excel/CSV. Direct PDF generation via Headless Chromium can be added in a future enhancement.
3. **Live Deployment Guard**:
   - Containers are built and verified locally. Live production deployment to remote staging/cloud infrastructure requires operational approval and credential provisioning as detailed in the Deployment Guide.
