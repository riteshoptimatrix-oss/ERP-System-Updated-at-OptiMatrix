# 0009. Phase 9: Production Planning and Work-in-Progress (WIP)

Date: 2026-10-10  
Status: Accepted

## Context
Opti Matrix requires structured production planning and work-in-progress (WIP) tracking across both manufacturing units (`Unit 1` and `Unit 2`).
Key operational mandates include:
1. Production planning and order generation linked to approved BOM revisions and specific manufacturing units.
2. Verified material availability and reservation checks prior to issuing raw materials.
3. Strict material issue mechanics deducting physical inventory via auditable stock movements to prevent duplicate issues.
4. Comprehensive WIP tracking through real-time shop floor production output and rejection logs.
5. Automated finished goods receipt into inventory upon completion of production batches.
6. Quantitative variance reporting between standard BOM gross requirements and actual shop-floor material consumption.

## Decisions

### 1. Invariant BOM Revision Snapshots
Every production order points to an explicit, approved BOM revision (`bom_revision_id` and `bom_version`). The planned component requirements are permanently snapshot on the order, isolating the production run from future BOM changes or revisions.

### 2. Dual-Step Material Fulfillment: Reservation & Issue
- **Reservation**: Material requirements are validated against real warehouse stock balances. Quantities are held under `inventory_stock.reserved_quantity` to prevent stock race conditions.
- **Issue**: Material issue (`POST /api/v1/production/orders/{id}/issue-materials`) executes atomic stock deductions (`POST /api/v1/inventory/movements`) with movement type `PRODUCTION_ISSUE`. Duplicate issues on the same production order are strictly rejected.

### 3. Progressive Output Logging & Finished Goods Receipts
Shop floor teams log produced quantities and rejected scrap progressively (`POST /api/v1/production/orders/{id}/output`). When output is logged:
- Produced units can be received directly into finished goods inventory with movement type `PRODUCTION_RECEIPT`.
- Production order status transitions cleanly through `DRAFT -> CONFIRMED -> IN_PROGRESS -> COMPLETED` (or `CANCELLED`).

### 4. Variance Analysis and Reconciliation
Variance calculation calculates:
$$\text{Expected Consumption} = \text{BOM Gross Req} \times \frac{\text{Actual Produced Qty}}{\text{Planned Qty}}$$
$$\text{Variance} = \text{Actual Issued Qty} - \text{Expected Consumption}$$
Highlighting material waste and excess consumption without altering stock retrospectively.

## Consequences
- Guaranteed audit trail for all raw material issues and finished goods receipts.
- Concurrency and duplicate-issue prevention via MongoDB state guards.
- All 40 backend automated tests pass and Next.js frontend builds cleanly.
