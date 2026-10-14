# 0006. Sales Order Management, Packing Slips, and Dispatch Architecture

Date: 2026-10-10
Status: Accepted

## Context
Phase 6 implements the core order-to-cash operational execution for Opti Matrix across its two manufacturing units (`Unit 1` and `Unit 2`):
1. Sales order capture linked to verified Customer Master records and Finished Product Master catalog.
2. Complete order state lifecycle: `DRAFT` -> `SUBMITTED` -> `CONFIRMED` -> `PARTIALLY_DISPATCHED` -> `DISPATCHED` / `CANCELLED`.
3. Packing slip generation referencing specific sales orders and tracking crate/pallet package counts and weights.
4. Goods dispatch recording supporting multi-part partial dispatches, transporter details (carrier, vehicle number, LR/consignment number, driver contact), and strict over-dispatch prevention.
5. Inventory stock contract: per requirements, stock balances are never fabricated or deducted directly via sales order/dispatch transactions. An explicit contract service verifies availability safely.
6. Role-based workflow controls (`orders:read`, `orders:create`, `orders:update`, `sales:read`, `sales:create`, `sales:post`).

## Decisions

### 1. Document Modeling and Sequence Generation
- Sales Orders stored in `sales_orders` with atomic sequence `SO-YYYY-XXXX`.
- Packing Slips stored in `packing_slips` with atomic sequence `PS-YYYY-XXXX`.
- Dispatches stored in `dispatch_records` with atomic sequence `DSP-YYYY-XXXX`.
- Lifecycle audits stored in `order_activities` linked by `order_id`.

### 2. Over-Dispatch and Partial Shipments Reconciliation
- When a dispatch is posted:
  - Each dispatch line item is checked against the line item's remaining balance (`quantity - dispatched_quantity`).
  - Attempting to ship even 0.01 units more than the remaining balance results in a 400 Bad Request error.
  - Upon successful dispatch, the order line item's `dispatched_quantity` is atomically incremented.
  - If cumulative dispatched quantity across all lines equals total ordered quantity, order status transitions to `DISPATCHED`.
  - If partially dispatched, order status transitions to `PARTIALLY_DISPATCHED`.
  - Orders that have had any goods dispatched cannot be cancelled.

### 3. Inventory Integration Contract
- `InventoryIntegrationContract` implemented in `app.services.inventory_contract`.
- Performs read-only stock checks. If an inventory balance ledger exists, it verifies available stock against required quantities; if unpopulated, it gracefully reports `UNTRACKED` without blocking or fabricating false numbers, and never writes direct mutations to stock balances.

### 4. Frontend Application Layer
- Next.js 16 App Router screens in `frontend/src/app/orders/`:
  - `page.tsx`: Sales Order hub with KPI cards, status filters, search, and dynamic line-item builder modal.
  - `[id]/page.tsx`: Order detail screen with ordered item reconciliation, packing slip generation modal, goods dispatch modal, cancellation modal, and activity timeline.

## Consequences
- Clean audit trail of commercial commitments vs. shop-floor logistics.
- Total prevention of duplicate postings and accidental over-shipping.
- Separation of concerns: Sales Orders and Dispatches prepare records without prematurely corrupting future raw material or inventory ledgers.
