# 0005. CRM and Lead Management Architecture

Date: 2026-10-10
Status: Accepted

## Context
Opti Matrix requires a CRM and Lead Management system for managing incoming machinery inquiries across its two manufacturing units (Unit 1 & Unit 2). Key business requirements:
1. Capture inquiries from various sources (Direct Inquiry, Trade Expo, Website, Referral, Cold Outreach, Existing Clients).
2. Track lead stage progression (`NEW` -> `CONTACTED` -> `QUALIFIED` -> `PROPOSAL_SENT` -> `NEGOTIATION` -> `CONVERTED` / `LOST`).
3. Schedule follow-ups, logging interactions (calls, meetings, emails, site visits, notes).
4. Prevent duplicate leads using company name and contact phone.
5. Provide one-click conversion of qualified leads into Customer Master records (`customers` collection) without duplicating customer codes or customer data.
6. Enforce strict single-login RBAC via `crm:read`, `crm:create`, `crm:update`.
7. Scope visibility to authorized manufacturing units (Unit 1, Unit 2, or Both).

## Decisions

### 1. Document Schema and Sequence Code Strategy
- Sequence generator: `LEAD-YYYY-XXXX` generated dynamically per year via atomic counters in `counters` collection.
- Indices: Unique compound index on `code`, with single and compound indexes on `company_name`, `phone`, `status`, `priority`, `unit_id`, and `next_follow_up`.
- Interaction Timeline: Activities stored in `crm_activities` collection linked by `lead_id`.

### 2. Duplicate Prevention and Customer Conversion Integration
- Creation duplicate guard: Case-insensitive check on `company_name` + `phone` for non-closed leads. If active matching lead exists, 409 Conflict is returned.
- Conversion to Customer Master: `convert_lead_to_customer` delegates creation directly to `MasterRepository.create_record('customers', payload)`. This guarantees that all Customer Master invariants, validations, duplicate code guards, and audit timestamps are respected. Upon conversion:
  - Lead `status` is set to `CONVERTED`.
  - Lead `converted_customer_id` is updated to the newly created Customer ID.
  - Conversion activity is logged into `crm_activities`.

### 3. Frontend Architecture
- Next.js 16 App Router in `frontend/src/app/crm/`.
  - `page.tsx`: Pipeline dashboard with KPI metric cards, stage filtering, quick follow-up shortcuts (Today / Overdue), search, and new lead creation modal.
  - `[id]/page.tsx`: Lead profile with interactive pipeline stage switcher, machinery requirements card, interaction timeline, activity logging modal, and Customer Master conversion modal.
- Root layout utilizes React `<Suspense>` boundary wrapping `AuthProvider` to support streaming and avoid SSR client hook blocking.

## Consequences
- Clean separation between active CRM leads and official Master Data customer records.
- Zero duplication of customer master creation logic.
- Fully typed end-to-end contracts between FastAPI schemas and TypeScript interfaces.
- Seamless, audited transition from sales lead to commercial customer.
