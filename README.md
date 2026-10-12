# RG Tech Manufacturing ERP

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16.4+-black.svg?logo=next.js)](https://nextjs.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-8.0+-47A248.svg?logo=mongodb)](https://mongodb.com/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-4.0+-38B2AC.svg?logo=tailwind-css)](https://tailwindcss.com/)

Production-grade Manufacturing ERP system for **RG Tech**, operating two primary industrial manufacturing units:
- **Unit 1**: Heavy Machining, Boring, Milling, and Fabrication.
- **Unit 2**: Finishing, Precision Sub-assembly, Quality Control, and Dispatch.

---

## Repository Structure

```
.
├── frontend/                     # Next.js 16 App Router application
│   ├── public/                   # Static web assets
│   ├── src/
│   │   ├── app/                  # App Router pages, layouts, error boundaries
│   │   ├── components/           # UI primitives & layout framing
│   │   ├── features/             # Modular feature slices (system-status, etc.)
│   │   ├── hooks/                # Global React hooks
│   │   ├── lib/                  # Environment validation & utilities
│   │   ├── services/             # Typed API clients
│   │   ├── types/                # TypeScript shared types
│   │   └── styles/               # Global styling
│   ├── tests/                    # Frontend tests
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── eslint.config.mjs
│   └── .env.example
├── backend/                      # Python FastAPI application
│   ├── app/
│   │   ├── api/                  # Versioned API routes (v1 endpoints)
│   │   ├── core/                 # Config, structured logging, errors
│   │   ├── database/             # Async Motor / MongoDB manager & session
│   │   ├── middleware/           # Correlation ID & request logging
│   │   ├── models/               # Domain models
│   │   ├── schemas/              # Pydantic v2 schemas
│   │   ├── repositories/         # Async MongoDB repositories
│   │   ├── services/             # Domain business services
│   │   └── main.py               # Application factory & lifespan
│   ├── tests/                    # Pytest test suite
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── .env.example
├── infrastructure/               # Container & orchestration configurations
│   ├── docker/
│   │   ├── backend.Dockerfile
│   │   └── frontend.Dockerfile
│   └── docker-compose.yml
├── docs/                         # Technical documentation
│   ├── architecture.md           # Architecture specification
│   ├── development-setup.md      # Setup, commands & operations
│   └── decisions/                # Architecture Decision Records (ADRs)
├── .gitignore
├── .dockerignore
└── README.md
```

---

## Quickstart

### 1. Docker Compose (Full Stack)
```bash
cd infrastructure
docker compose up -d --build
```
- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Probe: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- Readiness Probe: [http://localhost:8000/api/v1/health/ready](http://localhost:8000/api/v1/health/ready)

### 2. Native Local Development

#### Backend:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

#### Frontend:
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

---

## Verification & Automated Tests

- **Backend Pytest**:
  ```bash
  cd backend && PYTHONPATH=. .venv/bin/pytest -v
  ```
- **Frontend Quality & Build**:
  ```bash
  cd frontend
  npm run lint
  npx tsc --noEmit
  npm run build
  ```

---

## Phase 1 Status

Phase 1 (Foundation) has been successfully implemented and verified:
- [x] Next.js App Router with strict TypeScript and Tailwind CSS
- [x] FastAPI with async MongoDB manager, lifespan handling, and correlation IDs
- [x] Liveness (`/api/v1/health`) and Readiness (`/api/v1/health/ready`) probes
- [x] Structured JSON logging & centralized exception handling
- [x] Docker multi-stage builds and Docker Compose
- [x] Comprehensive documentation and test suite
"# ERP-System-Updated-at-OptiMatrix" 
