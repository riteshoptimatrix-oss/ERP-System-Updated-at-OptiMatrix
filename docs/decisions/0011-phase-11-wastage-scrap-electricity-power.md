# 0011. Phase 11: Wastage, Scrap, Electricity, and Power-Cut Tracking

Date: 2026-10-10  
Status: Accepted

## Context
Manufacturing precision machinery at RG Tech across facilities (`Unit 1` and `Unit 2`) produces physical material scrap and is subject to grid power outages and utility fluctuations. Key operational mandates include:
1. Daily shop-floor scrap and wastage logging categorized by reason, UoM, and material item.
2. Association of scrap records with specific production orders and manufacturing units.
3. Strict separation of machine downtime (outage duration) from physical scrap loss.
4. Valuation of scrap loss using standard component costs from the Raw Materials Master without invented rates or arbitrary tariffs.
5. Reconciling planned scrap allowances (defined in the approved BOM revision) against actual shop-floor scrap records.
6. Electricity meter readings recording opening/closing values and net kWh consumption with arithmetic validation.
7. Power outage tracking calculating duration in minutes, backup generator runtime, diesel consumption, and affected production lines while preventing overlapping outage records.
8. Idempotency and duplicate prevention for daily submissions.

## Decisions

### 1. Separation of Downtime vs. Material Scrap
- **Scrap Tracking**: Managed under collection `scrap_entries` and module `wastage`. Captures physical material loss (e.g. `MACHINING_SWARF`, `CUTTING_OFFCUT`, `REJECTED_DEFECTIVE`), measured in physical UoMs (`KG`, `PCS`, `NOS`) with standard costing.
- **Power & Downtime**: Managed under collection `power_cuts` and module `power`. Captures temporal machine and line downtime (in minutes/hours), grid failures, generator switchover, and diesel fuel consumed.

### 2. Standard Costing Grounding
Scrap entries lookup `standard_cost` directly from the Raw Materials Master or Finished Products Master at recording time. No arbitrary tariffs, market scrap rates, or simulated telemetry are invented:
$$\text{Total Scrap Loss} = \text{Scrap Quantity} \times \text{Standard Unit Cost}$$

### 3. Planned vs. Actual Wastage Reconciliation
The reconciliation endpoint calculates:
$$\text{Planned Scrap Qty} = \text{Total Standard Req} \times \left(\frac{\text{BOM Scrap \%}}{100}\right)$$
$$\text{Scrap Variance} = \text{Actual Approved Scrap} - \text{Planned Scrap Qty}$$
$$\text{Cost Variance} = \text{Actual Scrap Cost} - \text{Planned Scrap Cost}$$
This enables plant managers to detect component-level excess material consumption against approved engineering standards.

### 4. Overlap and Arithmetic Guards
- Meter readings validate: $\text{Closing Reading} \ge \text{Opening Reading}$, computing $\text{Units Consumed} = \text{Closing} - \text{Opening}$. Duplicate readings for the same unit, meter, date, and shift are rejected.
- Power cuts validate: $\text{End Time} > \text{Start Time}$. Overlapping power cut intervals for the same facility are strictly prevented.
- Duplicate scrap entries matching the same `(production_order_id, item_code, scrap_category, entry_date)` are rejected to eliminate accidental double clicks on shop-floor tablets.

## Consequences
- Traceable, auditable records for material waste and energy downtime.
- Full reconciliation with live production orders and BOM recipes.
- Zero regressions across the ERP suite; all 44 backend pytest test cases pass and the Next.js production build succeeds with all 24 routes prerendered.
