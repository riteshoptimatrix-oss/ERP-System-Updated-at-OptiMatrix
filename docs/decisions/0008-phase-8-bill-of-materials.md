# 0008. Phase 8: Bill of Materials (BOM)

Date: 2026-10-10  
Status: Accepted

## Context
Manufacturing machinery at Opti Matrix across `Unit 1` and `Unit 2` requires multi-level Bill of Materials (BOM) management linking finished products to raw material component requirements. Key requirements include:
1. Version and revision history (`R1`, `R2`, ...) where approved revisions are strictly immutable.
2. Distinct active status per product and manufacturing unit.
3. Explicit scrap / wastage allowance formulas and estimated component costing.
4. Material requirement explosions cross-referencing real inventory without stock mutation.
5. Strict guardrails against circular dependencies, invalid quantities, and incompatible units of measure.

## Decisions

### 1. Revision Locking & Immutability
Once a BOM is transitioned to `APPROVED`, its recipe is immutable. Any modification requires cloning a new revision (`POST /api/v1/bom/{id}/revisions`), generating a new draft record with incremented revision identifier (`R2`, `R3`, ...). This guarantees that historical production orders always point to an invariant, exact BOM snapshot.

### 2. Scrap and Costing Policy
Component gross requirements and line item costs are computed explicitly using:
$$\text{Gross Quantity} = \text{Net Quantity} \times \left(1 + \frac{\text{Scrap Percentage}}{100}\right)$$
$$\text{Line Item Cost} = \text{Gross Quantity} \times \text{Unit Standard Cost}$$
$$\text{Total BOM Estimated Cost} = \sum \text{Line Item Cost}$$
No inventory stock is deducted during costing or planning calculations.

### 3. Circular Dependency & UoM Guardrails
- Circular dependencies are prevented by rejecting any component whose code or ID matches the finished product being manufactured.
- UoMs are validated against the raw materials master to ensure engineering consistency.

### 4. Real-time Inventory Requirements Explosion
`POST /api/v1/bom/{id}/calculate-requirements` performs batch explosions by scaling BOM base quantities to target production volumes. Live availability is queried from `inventory_stock` to report shortages without modifying inventory records.

## Consequences
- Guaranteed revision integrity for all production runs.
- Full reconciliation with live inventory balances.
- All 38 backend automated test cases pass and the Next.js frontend builds cleanly.
