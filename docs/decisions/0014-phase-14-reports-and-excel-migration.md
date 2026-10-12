# ADR 0014: Phase 14 - Reports, Cross-Module Analytics, and Auditable Excel Migration

## Status
Accepted

## Context
RG Tech operates across two manufacturing plants (`Unit 1` and `Unit 2`) producing industrial machinery. To support operational decisions, leadership and plant managers require real-time reporting across sales, orders, dispatches, stock ledger, BOM versions, production orders, WIP, quality inspections, scrap wastage, power downtime, workforce attendance, payroll runs, and double-entry financial journals. Furthermore, migrating legacy Excel workbooks must ensure data integrity without risking accidental overwrites or data loss.

## Decisions

### 1. Cross-Module Reporting Engine
- Implemented `ReportsRepository` (`backend/app/repositories/reports_repository.py`) supporting 12 analytics modules:
  1. Sales & Invoiced Receivables (`invoices`)
  2. Sales Orders (`orders`)
  3. Dispatches & Packing Slips (`dispatches`)
  4. Inventory Stock Balances & Valuation (`stock_balances`)
  5. Bill of Materials Revisions (`boms`)
  6. Production Orders & WIP (`production_orders`)
  7. Quality Control Inspections & Holds (`qc_inspections`)
  8. Wastage & Daily Scrap (`wastage`)
  9. Machine Downtime & Power Outages (`power_outages`)
  10. HR Attendance & Shifts (`attendance`)
  11. Payroll Runs & Net Disbursements (`payroll_runs`)
  12. Financial General Ledger & Journals (`journal_entries`)
- **Strict Reconciliation**: Metric cards and summary rows reflect real transaction aggregations rather than estimated proxies.
- **Exporting**: Supports streaming exports to CSV (`text/csv`) and pre-formatted Excel `.xlsx` spreadsheets styled with headers and column auto-sizing using `openpyxl`.

### 2. Auditable Excel Migration Pipeline
- Implemented `ExcelImportRepository` (`backend/app/repositories/import_repository.py`) using a 4-stage pipeline:
  1. **Standard Template Generation**: Pre-formatted `.xlsx` templates for 9 target entities (Customers, Vendors, Raw Materials, Finished Goods, Employees, Warehouses, Categories, UoMs, Opening Stock).
  2. **File Parsing & Header Normalization**: Handles case-insensitive and spacing variations in column titles across `.xlsx` and `.csv`.
  3. **Dry-Run Validation**: Validates mandatory fields, unit enums, foreign keys, and duplicate codes against existing MongoDB collections. Flags cell-level discrepancies with exact row numbers without touching production collections.
  4. **Authorized Batch Commit**: Requires explicit confirmation and an idempotency token (`batch_token`). Commits valid rows atomically and records an immutable batch record in `import_batches`.

### 3. Frontend Architecture
- `src/app/reports/page.tsx`: Single-page analytical portal with 12 module tabs, KPI cards, date-range pickers, facility switcher, and instant CSV/XLSX export triggers.
- `src/app/master/import/page.tsx`: Excel Migration Studio featuring template downloads, file drag-and-drop, validation results table, duplicate counters, and batch history logs.

## Consequences
- Reports enforce role-based access control (`reports:read`, `reports:export`) and facility scoping.
- Historical data migration is safe, testable, and completely transparent with zero chance of silent record overwriting.
