# ADR 0002: Single Login and Role-Based Access Control (RBAC) Architecture

## Status
Accepted

## Context
The entire RG Tech Manufacturing ERP requires **ONE shared authentication system and ONE login page**.
All users across all manufacturing operations (Sales, Inventory, BOM, Production, QC, Wastage, Power, HR, Payroll, Finance) authenticate through the same entrypoint. Following authentication, access to modules, actions, and specific plants (Unit 1 vs Unit 2) must be strictly governed by role and permission assignments.

## Decisions

### 1. Password Hashing with Argon2id
- Implemented using `argon2-cffi` with standard RFC parameters: memory_cost=65536 KiB, time_cost=3 iterations, parallelism=4 lanes.
- Constant-time verification is performed. Dummy hashes are evaluated when accounts do not exist to prevent timing attacks.

### 2. Unified Single Login Flow
- Endpoint: `POST /api/v1/auth/login`.
- Emits a secure, `HttpOnly`, `SameSite=Lax`, path-scoped (`/`) session cookie containing a cryptographically strong 256-bit URL-safe token.
- Raw session tokens are never stored in the database; only SHA-256 hashes are persisted in the `sessions` collection.
- Credentials and session tokens are strictly prohibited from `localStorage` or `sessionStorage`.

### 3. Session Expiration & Invalidation
- Absolute lifetime: 8 hours (`SESSION_MAX_AGE_SECONDS = 28800`).
- Rolling inactivity timeout: 1 hour (`SESSION_IDLE_TIMEOUT_SECONDS = 3600`).
- Explicit revocation via `POST /api/v1/auth/logout`.
- Automated session revocation when user accounts are deactivated.

### 4. CSRF Protection
- Double-submit cookie verification (`RG_csrf` cookie + `X-CSRF-Token` header) enforced on all state-changing endpoints (`POST`, `PUT`, `PATCH`, `DELETE`).

### 5. Multi-Unit Plant Isolation (Unit 1 & Unit 2)
- Users are assigned `allowed_units` (`Unit_1`, `Unit_2`, or `BOTH`).
- Every protected operation enforces `require_unit_access`, preventing personnel scoped to Unit 1 from querying or mutating Unit 2 data.

### 6. Shared Authenticated App Shell & Dynamic Sidebar
- Next.js `AppShell` wrapping the authenticated application.
- Navigation sidebar dynamically renders only routes for which the active user has `read` permissions.
- Facility toggle allows multi-unit users to switch their active working plant.

## Consequences
- Single unified identity across the entire company.
- Defense-in-depth: frontend hides unauthorized UI, while the FastAPI backend independently verifies permissions on every request.
- Deactivated accounts are blocked in real time.
