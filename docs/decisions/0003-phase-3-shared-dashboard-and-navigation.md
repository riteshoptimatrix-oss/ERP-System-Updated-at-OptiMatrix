# ADR 0003: Phase 3 Shared ERP Dashboard, Navigation & Multi-Unit Context

## Status
Accepted

## Context
RG Tech operates two manufacturing facilities: Unit 1 and Unit 2. Users authenticate via a single corporate login system (Phase 2) and must only access modules, metrics, and data relevant to their role and authorized facility assignments.

Phase 3 requires:
1. A unified responsive application shell with collapsible desktop/mobile navigation drawers.
2. An authorized facility selector (`Unit_1` vs `Unit_2`) with automatic fallback and authorization validation.
3. Breadcrumb navigation derived dynamically from the current route.
4. Permission-aware dashboard cards aggregating data across 8 operational pillars (Orders, Dispatch, Stock, Production, QC, Wastage, Attendance, Approvals).
5. Dynamic KPI access control: returning empty or masked values for modules outside a user's permissions, rather than failing the entire request.
6. Honest representations: no fake hardcoded numbers; clean zero-count states with helpful empty state calls to action.
7. Reusable presentation primitives: DataTable with sorting/filtering, Dialog modals with keyboard trap/escape handlers, FilterBar shop-floor toolbars, and EmptyState views.

## Decisions

### 1. Unified AppShell & Navigation Architecture
- Created `frontend/src/components/layout/AppShell.tsx` as a shared client component wrapping all authenticated pages.
- Embedded `Sidebar.tsx` with role/permission filtering across all 12 modules. Items the user lacks permission to access are hidden completely.
- Implemented mobile drawer behavior using overlay backdrops and hamburger toggle triggers in `Header.tsx`.

### 2. Unit Context Management
- Integrated `UnitContext` via React Context and `localStorage` persistence, defaulting to `Unit_1` if authorized, or `Unit_2` if authorized only for Unit 2.
- Unit selector in the top header is restricted to units the authenticated user is authorized for (`allowed_units`).
- When switching facilities, dashboard KPIs and audit feeds re-query the backend scoped to `unit_id`.

### 3. Permission-Aware Dashboard KPI Aggregation
- Implemented `GET /api/v1/dashboard/summary` in FastAPI with unit parameter validation against `current_user.allowed_units`.
- Enforces permission checks per KPI category:
  - If a user has `orders:read`, orders metric is populated; otherwise, marked `unauthorized=True`.
  - Same pattern applies for dispatch, inventory, production, quality control, scrap/wastage, and attendance.
- Added `GET /api/v1/dashboard/activity` providing recent audit events for the active unit.

### 4. Shop-Floor UX and Tablet Support
- Styled for high-contrast visibility on shop-floor tablets and ruggedized touch terminals.
- Reusable `DataTable`, `FilterBar`, and `Dialog` components are designed with large touch targets, accessible ARIA attributes, and responsive scroll containers.

## Consequences
- Single, consistent layout across all future business modules (Phase 4+).
- Clean separation between layout chrome and page content.
- Strict multi-unit isolation enforced on both frontend and backend.
