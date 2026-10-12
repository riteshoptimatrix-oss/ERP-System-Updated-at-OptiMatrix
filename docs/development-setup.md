# Development Setup & Operations Guide

This guide details local development and containerized Docker setup for the RG Tech ERP.

---

## 1. Prerequisites

- **Python**: 3.12+ (tested with Python 3.14)
- **Node.js**: v20+ (tested with Node.js v24 LTS)
- **Package Managers**: `pip` and `npm`
- **Database / Containers**: MongoDB 7.0+ or Docker with Docker Compose

---

## 2. Quickstart with Docker Compose

To start the complete stack (MongoDB + FastAPI + Next.js):

```bash
# 1. Navigate to infrastructure folder
cd infrastructure

# 2. Start services in background
docker compose up -d --build

# 3. View live logs
docker compose logs -f

# 4. Stop services
docker compose down
```

### Access Points:
- **Frontend Web UI**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Backend**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Liveness Probe**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- **Readiness Probe**: [http://localhost:8000/api/v1/health/ready](http://localhost:8000/api/v1/health/ready)
- **MongoDB**: `localhost:27017`

---

## 3. Local Native Development Setup

### 3.1 Backend (FastAPI)

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env from template
cp .env.example .env

# Run FastAPI development server with auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3.2 Frontend (Next.js)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create .env from template
cp .env.example .env.local

# Run Next.js development server
npm run dev
```

The application will be live at `http://localhost:3000`.

---

## 4. Running Automated Tests

### 4.1 Backend Test Suite

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest -v
```

Tests verify:
- Liveness probe (`/api/v1/health`)
- Readiness probe with connected DB (`/api/v1/health/ready` -> 200)
- Readiness probe with disconnected DB (`/api/v1/health/ready` -> 503)
- Traceability & correlation ID propagation (`X-Correlation-ID`)
- Internal exception masking & secret protection
- CORS origin parser & configuration validation

### 4.2 Frontend Code Quality & Build Checks

```bash
cd frontend

# 1. ESLint check
npm run lint

# 2. Strict TypeScript type check
npx tsc --noEmit

# 3. Production build
npm run build
```

---

## 5. MongoDB Local Replica Set Setup (For Multi-Document Transactions)

MongoDB requires a replica set configuration to support multi-document ACID transactions. In production or local staging:

```bash
# Run MongoDB with replica set name
mongod --replSet rs0 --dbpath /data/db --bind_ip 0.0.0.0

# In mongosh, initiate the replica set:
mongosh --eval "rs.initiate()"
```

In connection strings, use:
```
MONGODB_URI=mongodb://localhost:27017/?replicaSet=rs0
```

---

## 6. Troubleshooting

- **Frontend cannot connect to Backend**:
  - Verify backend is running on `http://localhost:8000`.
  - Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local` matches the backend address.
  - Verify CORS origins in `backend/.env` includes `http://localhost:3000`.
- **Backend returns 503 on `/health/ready`**:
  - MongoDB is not reachable. Check whether MongoDB process is running and verify `MONGODB_URI`.
- **Correlation ID not received**:
  - Check browser network inspector for `X-Correlation-ID` response header.
