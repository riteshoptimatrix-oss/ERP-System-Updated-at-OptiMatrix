# ADR 0004: Phase 4 Master Data Management

## Status
Accepted

## Context
RG Tech operates across two manufacturing facilities: Unit 1 and Unit 2. To eliminate legacy spreadsheet registers and manual tracking, the ERP requires a resilient, audited, and strictly-typed Master Data Management system.

Phase 4 requires:
1. Customer master
2. Supplier & vendor master
3. Employee master
4. Finished-product master
5. Raw-material master
6. Unit-of-measure (UoM) master
7. Warehouse and storage-location master
8. Product and material categories
9. Validated CRUD operations, search, pagination, sorting, filters, duplicate prevention, audit history, and permission checks for every module.
10. Downloadable Excel/CSV import templates for legacy data onboarding without inventing fake business records.
11. Unit associations and isolation where applicable.

## Decisions

### 1. Unified Master Repository Pattern
- Implemented `MasterRepository` extending `BaseRepository` in `backend/app/repositories/master_repository.py`.
- Enforces duplicate prevention by verifying unique codes before inserting or updating records, returning `409 Conflict`.
- Stamped all mutations with standard audit fields (`created_at`, `created_by`, `updated_at`, `updated_by`).
- Built case-insensitive regex search spanning codes, names, and descriptions.

### 2. Multi-Unit Scoping and Permissions
- Added `ModuleName.MASTER` with standard permissions (`master:read`, `master:create`, `master:update`).
- Facility-bound entities (warehouses, employees, raw materials, products) support `unit_id` scoping (`Unit_1`, `Unit_2`, `BOTH`).
- Strict 403 Forbidden enforcement on cross-facility parameter tampering if a user is not authorized for that facility.

### 3. Template-Driven Legacy Migration
- Implemented `GET /api/v1/master/{entity}/template` generating UTF-8 CSV import schemas with headers and canonical example records for all 8 entities.
- Ensures no fake or fabricated business records exist in production while giving operators the exact templates required to import legacy Excel sheets.

### 4. Next.js Frontend Architecture
- Built `/master` Master Data Hub organizing all 8 pillars with direct template download buttons and permission-masked access.
- Built dedicated CRUD screens with `DataTable`, `FilterBar`, and `Dialog` modals across all 8 modules:
  - `/master/customers`
  - `/master/vendors`
  - `/master/employees`
  - `/master/products`
  - `/master/materials`
  - `/master/uom`
  - `/master/warehouses`
  - `/master/categories`

## Consequences
- Foundation for Bills of Materials (BOM), Inventory Management, and Production Tracking (Phase 5+) is fully established with verified master entity foreign keys.
- Production databases remain clean of dummy test data.
