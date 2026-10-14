# ADR 0015: Phase 15 - Final QA, Security Review, and Production Deployment Readiness

## Status
Accepted

## Context
Opti Matrix ERP encompasses 15 development phases covering Multi-Tenant Facility Scoping (`Unit 1` and `Unit 2`), Master Data, CRM, Sales & Dispatch, Inventory & Ledger Movements, Bill of Materials, Production Planning & WIP, Quality Control & Vendor Hold Enforcement, Scrap Wastage & Power Downtime, HR & Payroll, Double-Entry Finance & Accounting, Cross-Module Analytical Reports, and Auditable Excel Migration. Phase 15 is the culmination: conducting a thorough security and QA audit, verifying end-to-end integration across all subsystems, testing deployment containers, validating backup/restore procedures, and creating the definitive production release guide.

## Decisions

### 1. Unified Authentication, Sessions & RBAC
- Single shared login endpoint (`/api/v1/auth/login`) issues an HttpOnly, SameSite=Lax session cookie.
- Cryptographically secure session tokens hashed using SHA-256 before storage in MongoDB (`sessions` collection).
- Passwords hashed using Argon2id with high-assurance parameters (`time_cost=3`, `memory_cost=65536`, `parallelism=4`).
- Strict Role-Based Access Control (RBAC) enforced at FastAPI dependency layer across all 18 endpoint routers (`orders`, `inventory`, `bom`, `production`, `qc`, `wastage`, `power`, `crm`, `hr`, `payroll`, `attendance`, `sales`, `finance`, `reports`, `master`, `users`, `roles`, `audit`).
- Facility isolation strictly validated: users cannot view or manipulate records belonging to a facility they are not authorized for (`Unit_1` vs `Unit_2` vs corporate `BOTH`).

### 2. Workflow Integrity & Concurrency Guards
- **Sales-to-Dispatch-to-Inventory**: Packing slips reconcile against sales orders. Over-dispatch and double-deductions are prevented through state guards and atomic stock movements in `inventory_repository`.
- **BOM-to-Production-to-WIP**: Version-locked BOM snapshots are preserved on production orders. Material issuance and WIP receipts reconcile directly with ledger transactions.
- **QC & Payment Holds**: QC inspections enforce hold statuses (`PASSED`, `FAILED`, `QUARANTINED`). Vendor payments are hard-blocked by `finance_repository` if linked bills have active QC holds, until authorized release is recorded.
- **Attendance-to-Payroll-to-Accounting**: Attendance shifts flow into payroll runs. Once approved and posted, payroll generates balanced double-entry vouchers in the General Ledger.
- **Double-Entry Balancing**: All journal vouchers strictly enforce $\sum \text{Debit} = \sum \text{Credit}$. Silent edits or deletes are barred; corrections require offsetting reversal vouchers.

### 3. Production Infrastructure & Operations
- **Containerization**:
  - `infrastructure/docker/backend.Dockerfile`: Multi-stage build on Python 3.12-slim running unprivileged `appuser`.
  - `infrastructure/docker/frontend.Dockerfile`: Multi-stage build on Node 22-alpine running unprivileged `nextjs` user with standalone Next.js bundle tracing.
  - `infrastructure/docker-compose.yml`: Coordinates MongoDB 8.0, FastAPI backend, and Next.js frontend with isolated internal bridge networks and healthchecks.
- **Automated Backup & Restore**:
  - `infrastructure/backup.sh`: Creates compressed, timestamped `mongodump` archives with configurable retention pruning.
  - `infrastructure/restore.sh`: Verified restoration script with safety confirmation and optional collection dropping.
- **Secret & Logging Policies**:
  - Zero hardcoded production secrets.
  - Structured JSON logging (`python-json-logger`) masking sensitive credentials and session hashes.

## Verification
- 54/54 backend regression tests passed in `backend/.venv/bin/pytest -v`.
- Next.js 16 frontend production build compiled cleanly across all 30 routes (`npm run build`).
- `npx tsc --noEmit` verified with 0 type errors.
