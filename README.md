# VeriField Nexus

VeriField Nexus is a enterprise Climate Infrastructure Operating System (CIOS) and digital Measurement, Reporting, and Verification (dMRV) platform designed for climate project developers, project operators, carbon registries, and enterprise auditors.

The platform provides multi-tenant project scoping, role-based governance, automated field activity verification, cryptographic evidence hashing, and methodology-driven quantification across clean energy and carbon removal asset classes.

---

## Architecture Overview

```
Field Capture (Mobile / Web PWA / IoT Telemetry)
                        ↓
FastAPI Domain Services & Ingestion Queue
                        ↓
Deterministic Trust Engine & AI-Assisted Anomaly Classifier
                        ↓
PostgreSQL / Supabase Multi-Tenant Ledger
                        ↓
Next.js Executive Dashboard & Audit Verification Interface
```

VeriField Nexus connects physical field data collection to audit-ready climate reporting:
1. **Field Capture**: Mobile Flutter application and Web PWA designed for offline-first data capture, collecting GPS coordinates, camera evidence, and device telemetry.
2. **Verification & Trust Engine**: Automated FastAPI engine that checks location boundaries, evaluates SHA-256 image hashes for duplicate detection, applies methodology calculation rules, and classifies activities into canonical verification pipeline stages.
3. **Multi-Tenant Persistence**: PostgreSQL database (managed via Supabase in production or local PostgreSQL) enforcing organization-level tenant isolation, audit logging, and role-based access control.
4. **Executive Dashboard**: Next.js 16 web interface featuring GIS spatial mapping, verification queues, anomaly investigation workflows, and executive analytics.

---

## Core Platform Capabilities

### 1. Digital MRV & Field Data Capture
- **Multi-Sensor Telemetry Ingestion**: Supports direct data ingestion from solar inverters, smart meters, EV chargers, biochar kilns, and mobile survey apps.
- **Cryptographic Evidence Hashing**: Computes SHA-256 hashes of submitted images and documents to detect duplicate evidence and prevent double-counting.
- **Spatial GPS Validation**: Validates submission coordinates against project boundary polygons (GeoJSON) and sovereign jurisdiction frameworks.
- **Offline-First Operation**: Mobile app and PWA queue activities locally when offline, automatically syncing payloads when network connectivity is restored.

### 2. Verification Pipeline & Trust Classifier
Activities submitted to the platform pass through a mutually-exclusive 5-stage verification pipeline based on activity status and trust score metrics:

- `PENDING`: Newly submitted activity awaiting automated evaluation.
- `AI_VERIFIED`: Automated trust evaluation passed (Trust Score $\ge 80.0$) with zero anomaly flags.
- `MANUAL_REVIEW`: Boundary trust score (Trust Score between $70.0$ and $79.0$) or flagged status requiring human auditor review.
- `FLAGGED`: Low trust score (Trust Score $< 70.0$) or explicit anomaly detected (GPS mismatch, duplicate image hash, suspicious hours).
- `APPROVED`: Auditor or administrator manually approved the activity for credit issuance or reporting.

### 3. Sector Methodology Engines
The platform supports 4 canonical methodology families:
- **Clean Cookstoves (`COOKSTOVES`)**: Tracks household beneficiary onboarding, stove distribution, thermal efficiency %, daily usage hours, and biomass fuel displacement.
- **Hybrid Energy & Solar (`HYBRID_ENERGY`)**: Monitors solar generation telemetry (kWh), battery storage capacity, and backup diesel generator displacement.
- **Biochar Carbon Removal (`BIOCHAR`)**: Tracks feedstock weight, pyrolysis temperature, residence time, fixed carbon %, molar H/C ratio, and net CO2e removal.
- **EV Mobility (`EV_MOBILITY`)**: Monitors fleet charging sessions, kWh consumption, battery state-of-health %, and displaced ICE transport distance.

### 4. AI & Intelligence Layer
- **Deterministic Trust Engine**: Calculates objective trust scores ($0.0 - 100.0$) based on spatial accuracy, time-window validity, and historical submission patterns.
- **AI-Assisted Anomaly Detection**: Identifies potential data tampering, out-of-bounds telemetry, and duplicate submissions for auditor inspection.
- **RAG & Knowledge Memory (Optional)**: Includes a Retrieval-Augmented Generation (RAG) document indexer (`backend/app/domains/ai_orchestrator`) for searching climate methodology specifications. *Note: External LLM provider integration (OpenRouter/OpenAI/Gemini) is optional; deterministic trust engine and core verification functionality execute independently without external AI API keys.*

### 5. Enterprise Governance & Security
- **8 Access Control Roles**:
  - `SUPER_ADMIN`: Full system governance, Account 360 inspection, tenant management, user lifecycle controls.
  - `ORG_ADMIN`: Organization-scoped administration, project configuration, team management.
  - `AUDITOR` / `THIRD_PARTY_AUDITOR`: Verification queue review, evidence audit, anomaly resolution.
  - `COMPLIANCE_OFFICER`: Regulatory framework reporting and Article 6 / national registry compliance.
  - `PROJECT_MANAGER`: Operational oversight of projects, assets, and field teams.
  - `FIELD_AGENT`: Field data capture, household survey collection, asset installation logging.
  - `REGULATOR`: Read-only access to sovereign jurisdiction reports and audit trails.
- **Multi-Tenant Isolation**: Strict organization-level data scoping across all API endpoints and database queries.
- **Authentication**: JWT-based session handling, optional Multi-Factor Authentication (MFA - TOTP/WebAuthn), and Enterprise Single Sign-On (SSO - SAML/OIDC).
- **Audit Logging**: Immutable event logging for administrative actions, password resets, role modifications, and verification decisions.
- **Email Notifications Status**: Transactional email notifications (user registration welcome, super-admin account approval, password setup links) are explicitly **DEFERRED** until a production-owned domain and Resend sender identity are configured. Authentication and user account provisioning operate seamlessly without requiring email delivery. Email service credentials must be configured strictly via environment variables (`EMAIL_NOTIFICATIONS_ENABLED=false`, `RESEND_API_KEY=`, `RESEND_FROM_EMAIL=`).

---

## Repository Structure

```text
├── backend/                  # FastAPI Python backend application
│   ├── app/
│   │   ├── core/             # Configuration, security, MFA, SSO, encryption
│   │   ├── db/               # SQLAlchemy async session, migration helpers
│   │   ├── domains/          # Domain-driven architecture (33 domain modules)
│   │   │   ├── activities/   # Field activity ingestion & validation
│   │   │   ├── ai_trust_engine/ # Trust scoring & anomaly detection
│   │   │   ├── authentication/ # User auth, JWT, MFA, SSO
│   │   │   ├── biochar/      # Biochar sector calculation engine
│   │   │   ├── cookstoves/   # Cookstoves beneficiary & offset engine
│   │   │   ├── energy/       # Solar & hybrid energy telemetry
│   │   │   ├── ev/           # EV mobility fleet engine
│   │   │   ├── evidence/     # Cryptographic audit & image hashing
│   │   │   ├── methodologies/# Methodology standards & registry schemas
│   │   │   ├── organizations/# Multi-tenant management & governance
│   │   │   ├── reporting/    # Public overview & executive reporting
│   │   │   └── verification/ # Verification task queue & stage classifier
│   │   └── sdk/              # Python Client SDK (verifield_sdk.py)
│   ├── tests/                # Automated backend test suites
│   └── requirements.txt      # Python dependencies
├── dashboard/                # Next.js 16 web dashboard & admin portal
│   ├── src/
│   │   ├── app/              # App router (Landing, Dashboard, Super Admin, Auth)
│   │   ├── components/       # UI design system, Leaflet GIS maps, verification widgets
│   │   ├── context/          # Workspace & authentication context providers
│   │   └── lib/              # Type-safe API client & module registry
│   └── package.json          # Frontend dependencies
├── mobile/                   # Flutter cross-platform mobile application
│   ├── lib/                  # Offline-first field app (capture, SQLite queue, sync)
│   └── pubspec.yaml          # Flutter dependencies & assets
├── sdk/                      # TypeScript client SDK (`capture.ts`, `validate.ts`)
├── docs/                     # Comprehensive architecture blueprints & manuals
├── scripts/                  # Seed scripts & development utilities
└── examples/                 # Sample API payload specifications
```

---

## Technology Stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy (AsyncIO), Pydantic v2, PyJWT, Asyncpg.
- **Frontend**: Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS, Framer Motion, Lucide Icons, Leaflet GIS.
- **Mobile**: Flutter 3.x, Dart, SQLite (`sqflite`), Camera & Location plugins.
- **Database**: PostgreSQL 15+ (managed via Supabase in production) with SQLite fallback for local testing.
- **SDK**: Python SDK (`backend/app/sdk/verifield_sdk.py`) and TypeScript SDK (`sdk/`).

---

## Local Development & Setup

### Prerequisites
- **Node.js**: v18.x or higher
- **Python**: v3.10 or higher
- **Flutter**: 3.x (optional for mobile development)

### 1. Environment Configuration
Copy `.env.example` templates to set up local environment variables:
```bash
cp .env.example .env
cp backend/.env.example backend/.env
```

### 2. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The backend API will be available at `http://localhost:8000`. API documentation is accessible at `http://localhost:8000/docs`.

### 3. Dashboard Setup
```bash
cd dashboard
npm install
npm run dev
```
The web dashboard will be available at `http://localhost:3000`.

---

## Verification & Testing

The repository includes automated test suites to verify system integrity, governance policies, and verification pipeline logic:

### Backend Verification Suites
```bash
cd backend

# Run Verification Pipeline Production Acceptance Suite (18 Gates)
./venv/bin/python test_verification_pipeline_production_acceptance.py

# Run Super Admin Governance & Security Hardening Suite (28 Tests)
./venv/bin/python test_super_admin_governance_hardening.py
```

### Frontend Static & Build Verification
```bash
cd dashboard

# Type-check TypeScript codebase
npx tsc --noEmit

# Execute Next.js production build
npm run build
```

### Mobile App Static & Unit Verification
```bash
cd mobile

# Static analysis
flutter analyze

# Unit & widget tests
flutter test
```

---

## Security & Secrets Policy

VeriField Nexus enforces strict secret protection policies. Credentials, API keys, database passwords, and private tokens must never be committed to source control.
- Managed keys (`SUPABASE_SERVICE_ROLE_KEY`, `JWT_SECRET`) must be provided via environment variables.
- Git hooks and secret scanners run pre-commit diff checks to ensure tracked files contain zero secrets.

---

## License

Proprietary enterprise software. Refer to the [LICENSE](LICENSE) file for licensing terms.
