# 10 — Production Runbook & Operational Procedures



## Production System Runbook



This document defines standard operating procedures for deploying, maintaining, and monitoring VeriField Nexus in production environments.



---



## 1. Local & Production Server Health Checks



### Backend FastAPI Server

```bash

# Health check endpoint

curl -i http://127.0.0.1:8000/health



# Expected Response:

# HTTP/1.1 200 OK

# {"status":"healthy","app":"VeriField Nexus","version":"1.0.0"}

```



### Frontend Next.js Server

```bash

# Web Dashboard route check

curl -i http://127.0.0.1:3000/dashboard



# Production build check

npm --prefix dashboard run build

```



---



## 2. Background Process Execution



- **Backend Start Command**: `npm run backend:dev` (runs `uvicorn app.main:app --reload --port 8000`)

- **Dashboard Start Command**: `npm run dashboard:dev` (runs `next dev --port 3000`)



---



## 3. Database Migration & Schema Verification



If database schema updates are required:

```bash

# Apply automatic schema migrations

python3 -c "import asyncio; from app.main import lifespan; print('Schema synced')"

```



---



## 4. Multi-Tenant Incident Recovery



If an organization reports data access anomalies:

1. Verify `organization_id` on the user record in `users`.

2. Inspect query logs in `backend.log` for tenancy scoping (`WHERE organization_id = ...`).

3. Flush application cache to ensure fresh JWT tenancy decoding.
