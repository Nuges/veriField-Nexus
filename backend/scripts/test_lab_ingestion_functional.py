#!/usr/bin/env python3
"""
VeriField Nexus — Functional Laboratory Ingestion Closure Verification
======================================================================
1. Creates disposable Agriculture test organization and project.
2. Provisions a valid LandUnit and PhysicalSample (SMP-VALID-01).
3. Tests CSV upload with header mapping detection -> STAGED.
4. Tests duplicate SHA-256 rejection (HTTP 409).
5. Tests cross-tenant upload rejection (HTTP 403).
6. Executes Batch Validation -> verifies valid and invalid rows.
7. Cleans up all disposable records completely.
"""

import asyncio
import io
import json
import os
import sys
import uuid
import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

from sqlalchemy import select, delete, func
from app.db.session import async_session_factory
from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.agriculture.models import (
    LandUnit,
    SoilSample,
    PhysicalSample,
    SamplingCampaign,
    SamplingPlanVersion,
    SamplingPoint,
    LaboratoryImportBatch,
    LaboratoryImportRow,
)
from app.domains.evidence.models import Evidence
from app.domains.authentication.service import AuthenticationService
from app.core.security import get_password_hash

BASE_URL = "http://localhost:8000"


async def run_lab_verification():
    print("============================================================")
    print("STARTING FUNCTIONAL LABORATORY INGESTION VERIFICATION")
    print("============================================================")

    tag = uuid.uuid4().hex[:8]
    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()
    proj_a_id = uuid.uuid4()
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    lu_id = uuid.uuid4()
    sample_id = uuid.uuid4()

    async with async_session_factory() as session:
        # 1. Organization A & Project A
        org_a = Organization(
            id=org_a_id,
            name=f"Disposable Agri Tenant {tag}",
            status="ACTIVE",
            licensed_sectors=["AGRICULTURE_LAND_USE"],
            licensed_methodologies=["VM0042"],
        )
        session.add(org_a)

        user_a = User(
            id=user_a_id,
            email=f"agri_lab_admin_{tag}@example.com",
            full_name="Agri Lab Admin",
            role="ORG_ADMIN",
            organization=org_a.name,
            organization_id=org_a_id,
            password_hash=get_password_hash("LabAdminPass123!"),
            status="active",
            is_active=True,
            is_deleted=False,
        )
        session.add(user_a)

        proj_a = Project(
            id=proj_a_id,
            project_code=f"AGR-LAB-{tag}",
            name=f"Disposable Lab Test Project {tag}",
            organization_id=org_a_id,
            country="Nigeria",
            baseline_source="soil_sampling",
            baseline_parameters={"is_test": True},
        )
        session.add(proj_a)

        # 2. Organization B (Foreign Tenant)
        org_b = Organization(
            id=org_b_id,
            name=f"Foreign Tenant {tag}",
            status="ACTIVE",
            licensed_sectors=["AGRICULTURE_LAND_USE"],
        )
        session.add(org_b)

        user_b = User(
            id=user_b_id,
            email=f"foreign_admin_{tag}@example.com",
            full_name="Foreign Admin",
            role="ORG_ADMIN",
            organization=org_b.name,
            organization_id=org_b_id,
            password_hash=get_password_hash("ForeignPass123!"),
            status="active",
            is_active=True,
            is_deleted=False,
        )
        session.add(user_b)

        # 3. Prerequisites: LandUnit & SoilSample
        land_unit = LandUnit(
            id=lu_id,
            organization_id=org_a_id,
            project_id=proj_a_id,
            name="Field Parcel 01",
            code=f"LU-{tag}",
            unit_type="PARCEL",
            area_ha=10.5,
            boundary_geojson={"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]},
            is_active=True,
        )
        session.add(land_unit)

        from datetime import date
        sample = SoilSample(
            id=sample_id,
            organization_id=org_a_id,
            project_id=proj_a_id,
            land_unit_id=lu_id,
            sample_code=f"SMP-VALID-01",
            sampling_date=date(2026, 10, 1),
            latitude=9.0820,
            longitude=8.6753,
            depth_upper_cm=0,
            depth_lower_cm=30,
            bulk_density_g_cm3=1.2,
            soc_stock_pct=1.8,
        )
        session.add(sample)

        camp_id = uuid.uuid4()
        camp = SamplingCampaign(
            id=camp_id,
            organization_id=org_a_id,
            project_id=proj_a_id,
            name="Test Campaign",
            campaign_code=f"CMP-{tag}",
            planned_start_date=date(2026, 10, 1),
            status="LAB_IN_PROGRESS",
        )
        session.add(camp)

        spv_id = uuid.uuid4()
        spv = SamplingPlanVersion(
            id=spv_id,
            organization_id=org_a_id,
            project_id=proj_a_id,
            campaign_id=camp_id,
            version_number=1,
            effective_as_of_date=date(2026, 10, 1),
            status="DRAFT",
        )
        session.add(spv)

        sp_id = uuid.uuid4()
        sp = SamplingPoint(
            id=sp_id,
            organization_id=org_a_id,
            project_id=proj_a_id,
            campaign_id=camp_id,
            plan_version_id=spv_id,
            land_unit_id=lu_id,
            point_code=f"P-{tag}",
            planned_lat=0.5,
            planned_lon=0.5,
            status="PLANNED",
        )
        session.add(sp)

        phys_sample = PhysicalSample(
            id=sample_id,
            organization_id=org_a_id,
            project_id=proj_a_id,
            campaign_id=camp_id,
            plan_version_id=spv_id,
            sampling_point_id=sp_id,
            land_unit_id=lu_id,
            sample_code=f"SMP-VALID-01",
            status="COLLECTED",
        )
        session.add(phys_sample)
        await session.commit()

        token_a = AuthenticationService.generate_token_static(user_a)
        token_b = AuthenticationService.generate_token_static(user_b)

    print(f"[SETUP] Created disposable Project A: {proj_a_id}")
    print(f"[SETUP] Created valid sample prerequisite: SMP-VALID-01")

    # Synthetic CSV fixture with 4 rows:
    # 2 valid rows (SOC_CONCENTRATION, BULK_DENSITY)
    # 1 row with non-existent sample code
    # 1 row with invalid analyte
    csv_content = (
        "sample_code,analyte,raw_value,raw_unit,depth_from_cm,depth_to_cm,analysis_date,method,lab_sample_id,notes\n"
        "SMP-VALID-01,SOC_CONCENTRATION,2.15,%,0,30,2026-10-10,DUMAS,LAB-001,Valid SOC analyte\n"
        "SMP-VALID-01,BULK_DENSITY,1.25,g/cm3,0,30,2026-10-10,CORE,LAB-002,Valid Bulk Density\n"
        "SMP-NONEXISTENT-99,SOC_CONCENTRATION,1.80,%,0,30,2026-10-10,DUMAS,LAB-003,Nonexistent sample code\n"
        "SMP-VALID-01,UNKNOWN_INVALID_ANALYTE,99.9,%,0,30,2026-10-10,UNKNOWN,LAB-004,Invalid analyte\n"
    ).encode("utf-8")

    batch_id = None
    results = {}

    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            # -----------------------------------------------------------------
            # TEST 1: Cross-Tenant Lab Upload Rejection
            # -----------------------------------------------------------------
            print("[TEST] Testing cross-tenant upload rejection...")
            cross_resp = await client.post(
                f"/api/v1/agriculture/projects/{proj_a_id}/laboratory-import/upload",
                headers={"Authorization": f"Bearer {token_b}"},
                files={"file": ("lab_report.csv", csv_content, "text/csv")},
            )
            print(f"[HTTP] Cross-tenant status code: {cross_resp.status_code}")
            assert cross_resp.status_code in [403, 404], f"Expected 403 or 404, got {cross_resp.status_code}"
            results["cross_tenant"] = "BLOCKED"
            print("[PASS] Cross-tenant upload blocked.")

            # -----------------------------------------------------------------
            # TEST 2: Valid Upload by Tenant A
            # -----------------------------------------------------------------
            print("[TEST] Uploading synthetic lab file as Tenant A...")
            upload_resp = await client.post(
                f"/api/v1/agriculture/projects/{proj_a_id}/laboratory-import/upload?laboratory_name=AgriTestLabs",
                headers={"Authorization": f"Bearer {token_a}"},
                files={"file": ("lab_report.csv", csv_content, "text/csv")},
            )
            print(f"[HTTP] Upload status code: {upload_resp.status_code}")
            assert upload_resp.status_code == 201, f"Failed upload: {upload_resp.text}"
            upload_data = upload_resp.json()
            batch_id = upload_data.get("id")
            rows_staged = upload_data.get("total_rows") or upload_data.get("rows_total")
            print(f"[PASS] Batch created: {batch_id}, Rows staged: {rows_staged}")
            results["upload"] = "PASS"
            results["rows_staged"] = rows_staged

            # -----------------------------------------------------------------
            # TEST 3: Duplicate SHA-256 Rejection
            # -----------------------------------------------------------------
            print("[TEST] Testing duplicate SHA-256 file upload rejection...")
            dup_resp = await client.post(
                f"/api/v1/agriculture/projects/{proj_a_id}/laboratory-import/upload?laboratory_name=AgriTestLabs",
                headers={"Authorization": f"Bearer {token_a}"},
                files={"file": ("lab_report.csv", csv_content, "text/csv")},
            )
            print(f"[HTTP] Duplicate upload status code: {dup_resp.status_code}")
            assert dup_resp.status_code == 409, f"Expected 409 Conflict, got {dup_resp.status_code}"
            results["duplicate_rejected"] = "YES"
            print("[PASS] Duplicate file correctly rejected (409 Conflict).")

            # -----------------------------------------------------------------
            # TEST 4: Batch Validation
            # -----------------------------------------------------------------
            print(f"[TEST] Triggering batch validation for batch {batch_id}...")
            val_resp = await client.post(
                f"/api/v1/agriculture/projects/{proj_a_id}/laboratory-import/batches/{batch_id}/validate",
                headers={"Authorization": f"Bearer {token_a}"},
                json={},
            )
            print(f"[HTTP] Validation status code: {val_resp.status_code}")
            assert val_resp.status_code == 200, f"Failed validation: {val_resp.text}"
            val_data = val_resp.json()
            rows_valid = val_data.get("valid_rows")
            rows_invalid = val_data.get("error_rows")
            batch_status = val_data.get("status")
            print(f"[VALIDATION] Status: {batch_status}, Valid rows: {rows_valid}, Invalid rows: {rows_invalid}")
            results["rows_valid"] = rows_valid
            results["rows_invalid"] = rows_invalid
            assert rows_valid == 2, f"Expected 2 valid rows, got {rows_valid}"
            assert rows_invalid == 2, f"Expected 2 invalid rows, got {rows_invalid}"
            print("[PASS] Validation correctly identified 2 valid and 2 invalid rows.")

    finally:
        # ---------------------------------------------------------------------
        # CLEANUP: Remove all disposable test entities
        # ---------------------------------------------------------------------
        print("[CLEANUP] Cleaning up all disposable test records...")
        async with async_session_factory() as session:
            # Delete lab import rows and batches
            if batch_id:
                await session.execute(delete(LaboratoryImportRow).filter(LaboratoryImportRow.import_batch_id == uuid.UUID(batch_id)))
                await session.execute(delete(LaboratoryImportBatch).filter(LaboratoryImportBatch.id == uuid.UUID(batch_id)))
            
            # Delete evidence, physical samples, soil samples, land units, projects, users, orgs
            await session.execute(delete(Evidence).filter(Evidence.uploaded_by.in_([user_a_id, user_b_id])))
            await session.execute(delete(PhysicalSample).filter(PhysicalSample.project_id == proj_a_id))
            await session.execute(delete(SamplingPoint).filter(SamplingPoint.project_id == proj_a_id))
            await session.execute(delete(SamplingPlanVersion).filter(SamplingPlanVersion.project_id == proj_a_id))
            await session.execute(delete(SoilSample).filter(SoilSample.project_id == proj_a_id))
            await session.execute(delete(SamplingCampaign).filter(SamplingCampaign.project_id == proj_a_id))
            await session.execute(delete(LandUnit).filter(LandUnit.project_id == proj_a_id))
            await session.execute(delete(Project).filter(Project.id == proj_a_id))
            await session.execute(delete(User).filter(User.organization_id.in_([org_a_id, org_b_id])))
            await session.execute(delete(Organization).filter(Organization.id.in_([org_a_id, org_b_id])))
            await session.commit()
            print("[CLEANUP] All disposable test records purged successfully.")
            results["cleanup"] = "PASS"

    print("============================================================")
    print("FINAL LAB INGESTION VERIFICATION RESULTS:")
    print(f"LAB FILE UPLOAD: {results.get('upload')}")
    print(f"ROWS STAGED: {results.get('rows_staged')}")
    print(f"ROWS VALID: {results.get('rows_valid')}")
    print(f"ROWS INVALID: {results.get('rows_invalid')}")
    print(f"DUPLICATE FILE REJECTED: {results.get('duplicate_rejected')}")
    print(f"CROSS-TENANT LAB UPLOAD: {results.get('cross_tenant')}")
    print(f"CLEANUP: {results.get('cleanup')}")
    print("============================================================")
    return results


if __name__ == "__main__":
    asyncio.run(run_lab_verification())
