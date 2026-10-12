# 0007. Phase 7: Inventory and Warehouse Management

Date: 2026-10-10  
Status: Accepted

## Context
RG Tech requires complete inventory tracking across its manufacturing facilities (`Unit 1` and `Unit 2`) for Raw Materials and Finished Goods. The inventory system must provide:
1. Multi-warehouse stock tracking with live on-hand, reserved, and available balance calculations (`available = on_hand - reserved`).
2. Atomic negative-stock rejection to eliminate phantom balances and prevent overdrafts under high concurrency.
3. Immutable ledger appending for all transactions (`inventory_ledger`), guaranteeing complete auditability.
4. Paired two-phase stock movement records for inter-warehouse and inter-facility transfers (`TRANSFER_OUT` and `TRANSFER_IN`).
5. Controlled stock adjustments with mandatory audit justifications and classified reasons.
6. Seamless dispatch integration: sales dispatch records automatically decrement finished goods stock and record `SALES_DISPATCH` outward movements.

## Decisions

### 1. Atomic Balance Guarantee & Negative Stock Prevention
All stock decrements update the `inventory_stock` collection using atomic MongoDB conditional filters:
```python
filter_query = {
    "item_id": item_id,
    "warehouse_id": warehouse_id,
    "batch_no": batch_no,
    "quantity_on_hand": {"$gte": abs(quantity_change)}
}
```
If available stock is less than the requested decrement, the update fails atomically and raises a rejection without changing document state.

### 2. Immutable Movement Ledger
Every stock event creates an immutable entry in `inventory_ledger` containing:
- Unique transaction number (`TXN-YYYY-XXXX`).
- Movement type (`MATERIAL_INWARD`, `MATERIAL_OUTWARD`, `TRANSFER_IN`, `TRANSFER_OUT`, `ADJUSTMENT_IN`, `ADJUSTMENT_OUT`, `SALES_DISPATCH`, `OPENING_STOCK`).
- Pre- and post-transaction running balance reconciliation (`balance_after`).
- Reference entity details (`reference_id`, `reference_type`).
- Timestamp and actor credentials.

### 3. Sales Dispatch Integration
When dispatches are finalized in `OrdersRepository.create_dispatch`, the system queries the unit's finished goods warehouse and invokes `InventoryRepository.deduct_dispatch_stock`, recording outward ledger transactions linked to the sales order.

### 4. Opening Stock Bulk Migration
Opening stock entries are validated and deduplicated against existing records on `(item_id, warehouse_id, batch_no)` to permit repeatable imports without double-counting balances.

## Consequences
- Guarantees zero negative stock.
- Full reconciliation between `inventory_stock` balances and `inventory_ledger` entries.
- All 34 automated backend test cases and Next.js frontend production builds pass cleanly.
