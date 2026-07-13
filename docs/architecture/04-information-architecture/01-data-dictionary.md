# Enterprise Data Dictionary & Information Architecture

This document defines the core data entities, their attributes, constraints, and audit behavior across the CIOS platform.

## Principles of Information Architecture
1. **UUIDv4 Primary Keys:** All entities use UUIDs, preventing enumeration attacks and allowing distributed offline generation (e.g., offline mobile apps).
2. **Audit Trails:** Every mutation (INSERT/UPDATE/DELETE) is tracked. `created_at`, `updated_at`, `created_by`, and `updated_by` are mandatory on all tables.
3. **Tenant Isolation:** Every table containing business data must have an `organization_id` column.
4. **Soft Deletion:** Records are hidden via `is_deleted = TRUE` or `status = 'ARCHIVED'`, never hard-deleted.

## Core Entities

### 1. `Organization`
The tenant entity bounding all data.
- **`id`** (UUID, PK)
- **`name`** (String, Unique)
- **`type`** (Enum: `DEVELOPER`, `REGULATOR`, `VVB`, `BUYER`)
- **`status`** (Enum: `ACTIVE`, `SUSPENDED`, `ARCHIVED`)
- **`parent_id`** (UUID, FK -> Organization, Nullable) - For subsidiary inheritance.
- **`config`** (JSONB) - Whitelabel settings and feature flags.

### 2. `User`
The actor interacting with the platform.
- **`id`** (UUID, PK) - Matches Supabase Auth ID.
- **`organization_id`** (UUID, FK -> Organization)
- **`email`** (String, Unique)
- **`role`** (Enum: `ORG_ADMIN`, `FIELD_AGENT`, `VERIFIER`, `AUDITOR`)
- **`is_active`** (Boolean)

### 3. `Jurisdiction`
The legal boundary governing climate policies.
- **`id`** (UUID, PK)
- **`name`** (String)
- **`owner_id`** (UUID, FK -> Organization) - The Regulator owning this.
- **`spatial_boundary_id`** (UUID, FK -> SpatialBoundary)
- **`policies`** (JSONB) - e.g., acceptable methodologies, permanence requirements.

### 4. `Project`
The core climate initiative.
- **`id`** (UUID, PK)
- **`organization_id`** (UUID, FK -> Organization)
- **`jurisdiction_id`** (UUID, FK -> Jurisdiction)
- **`methodology_id`** (UUID, FK -> Methodology)
- **`status`** (Enum: `DRAFT`, `REGISTERED`, `MONITORING`, etc.)
- **`metadata`** (JSONB) - Schema-less data conforming to the Methodology template.

### 5. `Asset`
Physical installations (e.g., a specific cookstove).
- **`id`** (UUID, PK)
- **`project_id`** (UUID, FK -> Project)
- **`serial_number`** (String, Indexed)
- **`gps_coordinates`** (Point / PostGIS Geometry)
- **`installation_date`** (Timestamp)

### 6. `Evidence`
Proof of operation or impact.
- **`id`** (UUID, PK)
- **`asset_id`** (UUID, FK -> Asset)
- **`type`** (Enum: `PHOTO`, `DOCUMENT`, `TELEMETRY`)
- **`blob_uri`** (String) - Pointer to Object Storage.
- **`hash`** (String) - Cryptographic hash of the file payload for immutability proof.
- **`status`** (Enum: `RAW`, `VERIFIED`, `AUDITED`, `REJECTED`)

### 7. `LedgerTransaction`
The immutable financial record.
- **`id`** (UUID, PK)
- **`credit_id`** (UUID, FK -> CarbonCredit)
- **`type`** (Enum: `ISSUANCE`, `TRANSFER`, `RETIREMENT`)
- **`from_org_id`** (UUID, FK -> Organization, Nullable)
- **`to_org_id`** (UUID, FK -> Organization, Nullable)
- **`timestamp`** (Timestamp, Indexed)
