# Opti Matrix ERP - Production Deployment & Operations Guide

## 1. Environment Architecture & Configuration

The ERP system consists of three coordinated tiers:
1. **Frontend**: Next.js 16 (App Router, Tailwind CSS, TypeScript, Turbopack) running on port `3000`.
2. **Backend**: FastAPI 0.143 (Python 3.12 / 3.14 async runtime, Pydantic V2, Motor) running on port `8000`.
3. **Database**: MongoDB 8.0 (Replica Set / Standalone with WiredTiger storage engine) on port `27017`.

---

## 2. Environment Variables Specification

### Backend (`backend/.env`)
| Variable | Description | Recommended Production Value |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Deployment environment | `production` |
| `HOST` | Bind host | `0.0.0.0` |
| `PORT` | Bind port | `8000` |
| `PROJECT_NAME` | Application Name | `Opti Matrix ERP` |
| `API_V1_PREFIX` | API Route Prefix | `/api/v1` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `LOG_JSON_FORMAT` | Structured JSON log output | `true` |
| `MONGODB_URI` | MongoDB Connection String | `mongodb://<user>:<password>@mongodb:27017/?authSource=admin` |
| `MONGODB_DB_NAME` | Database Name | `RG_erp` |
| `MONGODB_MIN_POOL_SIZE` | Minimum connection pool | `10` |
| `MONGODB_MAX_POOL_SIZE` | Maximum connection pool | `100` |
| `SESSION_COOKIE_NAME` | Cookie identifier for user session | `RG_session` |
| `SESSION_MAX_AGE_SECONDS` | Maximum session lifespan | `28800` (8 hours) |
| `SESSION_IDLE_TIMEOUT_SECONDS` | Inactivity logout threshold | `3600` (1 hour) |
| `CSRF_COOKIE_NAME` | Double-submit CSRF cookie | `RG_csrf` |
| `CSRF_HEADER_NAME` | Client CSRF header | `X-CSRF-Token` |
| `ALLOWED_CORS_ORIGINS` | Trusted frontend origins | `["https://erp.RGmachines.com"]` |

### Frontend (`frontend/.env.production`)
| Variable | Description | Recommended Production Value |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | Public API endpoint for browser calls | `https://api.RGmachines.com/api/v1` |
| `NEXT_PUBLIC_APP_ENV` | Application environment indicator | `production` |
| `INTERNAL_BACKEND_URL` | Docker internal network proxy | `http://backend:8000` |
| `PORT` | Next.js server port | `3000` |

---

## 3. Docker Deployment Procedures

### Pre-requisites
- Docker Engine $\ge 24.0$
- Docker Compose $\ge 2.20$
- Minimum hardware recommendation: 4 vCPU, 8 GB RAM, 50 GB SSD

### Step 1: Clone and Configure Secrets
```bash
git clone <repository_url> RG-erp
cd RG-erp
cp backend/.env.example backend/.env
# Update backend/.env with production credentials
```

### Step 2: Build and Launch Containers
```bash
docker compose -f infrastructure/docker-compose.yml build
docker compose -f infrastructure/docker-compose.yml up -d
```

### Step 3: Verify Container Health & Initial Login
```bash
docker compose -f infrastructure/docker-compose.yml ps
# Verify all services report 'healthy' or 'running'
curl -f http://localhost:8000/api/v1/health/ready
curl -f http://localhost:3000
```

### Initial Super Admin (Owner) Credentials
Upon initial startup and database seeding, the system provisions the bootstrap Owner account:
- **Username / Identifier**: `admin` (or `admin@rgtech.com`)
- **Default Password**: `admin123`
- **Role**: `SUPER_ADMIN`
- **Assigned Units**: `BOTH` (`Unit_1` & `Unit_2`)

---

## 4. Database Backup & Disaster Recovery

### Automated Daily Backups
The automated script creates a compressed `.gz` archive and prunes old backups according to retention policies.
```bash
# Run manual backup
BACKUP_DIR=/var/backups/RG_erp ./infrastructure/backup.sh

# Recommended Crontab entry (Runs daily at 02:00 AM UTC):
0 2 * * * cd /opt/RG-erp && ./infrastructure/backup.sh >> /var/log/RG_backup.log 2>&1
```

### Restoration Procedure
```bash
# Verify archive integrity and restore into target database
./infrastructure/restore.sh /var/backups/RG_erp/RG_erp_backup_20261011_020000.gz --drop
```

---

## 5. Security & Hardening Checklist

- [x] **Argon2id Password Hashing**: Passwords are never stored in plaintext. High-assurance Argon2id parameters enforced.
- [x] **Session Storage Hashing**: Session tokens are hashed with SHA-256 before storage in MongoDB; cookie tokens cannot be replayed even if the database is exposed.
- [x] **HttpOnly & Secure Cookies**: Cookies enforce `HttpOnly`, `SameSite=Lax`, and `Secure=True` in production.
- [x] **Double-Submit CSRF Protection**: Every mutating HTTP request (`POST`, `PUT`, `DELETE`) requires `X-CSRF-Token`.
- [x] **Facility Scoping**: Every query validates `unit_id` against user authorization (`Unit_1`, `Unit_2`, or `BOTH`).
- [x] **Accounting Immutability**: Journal entries cannot be edited or deleted once posted; countervailing reversals must be posted.
- [x] **QC Payment Hold Enforcement**: Vendor bills with active QC issues cannot be paid until an authorized release is recorded.
- [x] **Non-Root Containers**: Backend runs as UID 1001 `appuser`; Frontend runs as UID 1001 `nextjs`.
