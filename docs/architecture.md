# Opti Matrix Manufacturing ERP Architecture Documentation

## 1. System Overview

Opti Matrix operates two manufacturing divisions:
- **Unit 1**: Heavy Machining, Boring, Milling, and primary steel fabrication.
- **Unit 2**: Finishing, Precision Sub-assembly, Quality Inspection, and Final Dispatch.

The **RG ERP** is architected to unify all spreadsheet-based registers and legacy manual tracking into a single, high-availability, responsive web and API platform.

```
                  ┌────────────────────────────────────────────────────────┐
                  │               Client Browsers & Terminals              │
                  └───────────────────────────┬────────────────────────────┘
                                              │ HTTP / JSON
                                              ▼
                  ┌────────────────────────────────────────────────────────┐
                  │                 Next.js 16 App Router                  │
                  │         TypeScript (Strict), Tailwind CSS, SSR         │
                  └───────────────────────────┬────────────────────────────┘
                                              │ REST / JSON (Correlated)
                                              ▼
                  ┌────────────────────────────────────────────────────────┐
                  │                  FastAPI Application                   │
                  │  Lifespan Management, JSON Logging, Centralized Errors │
                  └───────────────────────────┬────────────────────────────┘
                                              │ Async Driver (Motor / PyMongo)
                                              ▼
                  ┌────────────────────────────────────────────────────────┐
                  │                   MongoDB Database                     │
                  │        Replica-Set Prepared, WiredTiger Engine         │
                  └────────────────────────────────────────────────────────┘
```

---

## 2. Frontend Architecture (`frontend/`)

### 2.1 Core Technologies
- **Framework**: Next.js 16 (App Router) with React 19.
- **Language**: TypeScript with strict mode enabled.
- **Styling**: Tailwind CSS with custom responsive UI tokens.
- **Tooling**: ESLint 9, Turbopack, standalone Docker container output.

### 2.2 Directory Responsibility
- `src/app/`: App router routes (`page.tsx`), layouts (`layout.tsx`), boundary fallbacks (`error.tsx`, `loading.tsx`, `not-found.tsx`).
- `src/components/ui/`: Dumb, reusable primitive UI components (`Button`, `Card`, `Badge`).
- `src/components/layout/`: Global UI frame (`Header`, `Footer`).
- `src/features/`: Domain-oriented feature modules (e.g., `system-status` in Phase 1, `orders`, `inventory`, `bom`, `production` in Phase 2+). Each feature encapsulates its own presentation components, hooks, and local state.
- `src/services/`: HTTP API clients (`api-client.ts`) providing typed envelopes, timeouts, and error handling.
- `src/lib/`: Environment validation (`env.ts`) and common utilities (`utils.ts`).
- `src/types/`: Shared TypeScript data contracts and API interfaces.
- `src/styles/`: Global stylesheets and CSS design system rules.

### 2.3 Security Guarantees
- Client-side code never receives database connection strings, server secrets, or internal auth keys.
- Runtime environment validation actively inspects client variables for accidental leaks.

---

## 3. Backend Architecture (`backend/`)

### 3.1 Core Technologies
- **Framework**: FastAPI (Python 3.12+).
- **Settings**: Pydantic v2 `BaseSettings` reading environment variables with strict validation.
- **Database Driver**: `motor` (asynchronous PyMongo wrapper) with connection pooling and timeouts.
- **Testing**: `pytest` and `pytest-asyncio` with `httpx.AsyncClient`.

### 3.2 Directory Responsibility
- `app/api/v1/endpoints/`: Route handlers for API endpoints (e.g., `health.py`).
- `app/api/v1/router.py`: Unified API v1 router.
- `app/core/config.py`: Centralized environment settings (`Settings`).
- `app/core/logging.py`: Structured JSON log formatter emitting machine-readable logs.
- `app/core/errors.py`: Centralized exception handlers masking raw stack traces and preventing secret exposure.
- `app/database/mongodb.py`: Connection pool manager (`MongoDBManager`) managing startup connect and shutdown disconnect.
- `app/database/session.py`: FastAPI dependency (`get_db`) yielding the active database handle.
- `app/middleware/correlation.py`: Request tracing middleware propagating `X-Correlation-ID`.
- `app/middleware/logging.py`: Access log middleware tracking method, path, status, and duration in milliseconds.
- `app/repositories/base.py`: Generic asynchronous CRUD repository pattern preparing collections for clean data abstraction.
- `app/schemas/`: Typed Pydantic request and response contracts.

### 3.3 Health & Readiness Semantics
- **Liveness Probe** (`GET /api/v1/health`):
  - Returns `200 OK` with `status: "healthy"` as long as the Python process is alive.
  - Does NOT test downstream database availability to avoid cascading restart storms in orchestration layers (Kubernetes / ECS).
- **Readiness Probe** (`GET /api/v1/health/ready`):
  - Actively checks MongoDB connectivity via `adminCommand('ping')`.
  - Returns `200 OK` with `status: "ready"` if MongoDB is reachable.
  - Returns `503 Service Unavailable` with `status: "not_ready"` and detailed dependency breakdown when MongoDB is disconnected.

---

## 4. Multi-Unit Data Modeling Strategy

Opti Matrix operates **Unit 1** and **Unit 2**.
To allow unified operations with plant-level isolation:
1. Every manufacturing collection (Orders, Production Batches, Inventory, Machines) will include an indexed `unit_id` or `facility_code` field (`"Unit_1"` | `"Unit_2"`).
2. Repositories will support multi-tenant query filters scoped to either plant or corporate consolidated views.
3. Common master records (such as BOM items, Standard Operating Procedures, and Customer Accounts) are shared, while work-in-progress (WIP) and machine logs remain isolated.

---

## 5. Architectural Conventions for Future Modules

When implementing Phase 2 and subsequent modules:
1. **Never import UI components directly into database logic or vice-versa**.
2. **Feature Isolation**: Place new backend routers under `app/api/v1/endpoints/<module>.py`, schemas under `app/schemas/<module>.py`, services under `app/services/<module>.py`, and repositories under `app/repositories/<module>.py`.
3. **Frontend Features**: Place UI components under `frontend/src/features/<module>/components/` and custom hooks under `frontend/src/features/<module>/hooks/`.
4. **Transactions**: Any multi-document mutation (such as transferring stock from Unit 1 to Unit 2, or updating inventory upon order dispatch) must use MongoDB sessions:
   ```python
   async with await client.start_session() as session:
       async with session.start_transaction():
           await repo_a.update(..., session=session)
           await repo_b.update(..., session=session)
   ```
