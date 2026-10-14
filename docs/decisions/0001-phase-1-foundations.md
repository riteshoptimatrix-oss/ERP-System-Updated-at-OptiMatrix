# ADR 0001: Phase 1 Foundations Architecture & Technology Choices

## Status
Accepted

## Context
Opti Matrix operates two manufacturing facilities (Unit 1 & Unit 2) and currently tracks plant activities using multiple disconnected spreadsheet registers.
Phase 1 requires establishing a high-assurance, production-oriented application foundation for the new Manufacturing ERP system.

## Decisions

### 1. Technology Stack
- **Frontend**: Next.js 16 with App Router, React 19, strict TypeScript, Tailwind CSS, Turbopack, and Docker standalone output.
  - *Rationale*: Server-side rendering provides high initial load performance, strong SEO for enterprise portals, and strict typing ensures consistency across complex manufacturing models.
- **Backend**: Python FastAPI with Pydantic v2 settings and validation, asynchronous Motor/PyMongo driver, and Pytest.
  - *Rationale*: FastAPI provides high throughput, automatic OpenAPI documentation, async I/O compatibility, and strict type safety.
- **Database**: MongoDB with async driver.
  - *Rationale*: Dynamic schema support accommodating varied manufacturing BOM structures, inspection attributes, machine logs, and multi-tenant facility data.

### 2. Liveness vs. Readiness Probes
- `GET /api/v1/health` (Liveness) checks process responsiveness only.
- `GET /api/v1/health/ready` (Readiness) performs active downstream pinging (`adminCommand('ping')`) to verify database availability.
  - *Rationale*: Decoupling liveness from external dependencies prevents container orchestrators from restarting application processes when a database experiences transient latency or downtime.

### 3. Centralized Error Masking & Secret Protection
- Unhandled server exceptions are trapped in middleware and exception handlers to emit structured JSON error envelopes with correlation IDs (`X-Correlation-ID`). Internal stack traces and database credentials are explicitly masked from clients.

### 4. Multi-Unit Data Modeling
- Plant separation (`Unit 1` vs `Unit 2`) will be governed by indexed facility identifiers (`unit_id`) on all manufacturing collections. Multi-document transactions will use MongoDB replica-set sessions.

## Consequences
- Clean separation between frontend UI and backend services.
- Enterprise-grade traceability across requests via correlation IDs.
- Zero boilerplate required for starting Phase 2 business modules.
