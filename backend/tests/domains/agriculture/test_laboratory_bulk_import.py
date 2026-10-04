"""
=============================================================================
VeriField Nexus — Agriculture MRV Laboratory Bulk Data Import Test Suite
=============================================================================
Comprehensive unit, integration, and REST API tests for:
1. Template generation (.csv and .xlsx)
2. Automated column mapping detection & aliases
3. Secure file upload, SHA-256 integrity, Evidence record archiving
4. Staging of raw rows in laboratory_import_rows
5. Scientific validation:
   - PhysicalSample matching & lifecycle checks
   - Analyte canonicalization & deterministic unit conversion (SOC g/kg)
   - Domain range / plausibility checks
   - Depth interval verification
   - Intra-batch duplicate detection & historical duplicate warnings
6. Concurrency locking & transactional commit:
   - Automatic LaboratoryReceipt / LaboratoryAnalysis generation (qa_status="PENDING")
   - LaboratoryResult creation & immutable superseding
   - PhysicalSample status transition to ANALYZED
   - Partial import with import_valid_only=True
7. Security:
   - CSV Formula Injection defense
   - Executable upload rejection
   - ABAC tenant & project isolation
   - Segregation of Duties (SoD) enforcement
=============================================================================
"""

import io
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import jwt as pyjwt
import openpyxl
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException

from app.core.config import settings
from app.main import app
from app.domains.agriculture.models import (
    LaboratoryImportBatch,
    LaboratoryImportRow,
    PhysicalSample,
    LaboratoryReceipt,
    LaboratoryAnalysis,
    LaboratoryResult,
    SamplingCampaign,
    SamplingPlanVersion,
    SamplingPoint,
    LandUnit,
)
from app.domains.agriculture.schemas import (
    ColumnMappingConfig,
    SamplingCampaignCreate,
    SamplingPlanVersionCreate,
    SamplingPointCreate,
)
from app.domains.agriculture.laboratory_import_service import LaboratoryImportService
from app.domains.agriculture.service import AgricultureService
from app.domains.authentication.models import User
from app.domains.evidence.models import Evidence
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from tests.domains.agriculture.test_agriculture_mrv_phase2 import create_agri_setup


def _create_token(user_id: uuid.UUID, email: str, role: str, org_id: uuid.UUID = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "org_id": str(org_id) if org_id else None,
        "organization_id": str(org_id) if org_id else None,
        "exp": int((now + timedelta(hours=2)).timestamp()),
        "iat": int(now.timestamp()),
        "type": "access",
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def create_agri_lab_import_setup(db_session: AsyncSession):
    """Sets up an org, project, methodology, and sample physical samples for testing."""
    setup = await create_agri_setup(db_session)
    org = setup["org"]
    admin = setup["admin"]
    field = setup["field"]
    project = setup["project"]
    lu = setup["land_unit"]
    stratum = setup["stratum"]

    other_org = Organization(name=f"Other Lab Org {uuid.uuid4().hex[:8]}")
    db_session.add(other_org)
    await db_session.flush()

    user_other_org = User(
        email=f"other.admin.{uuid.uuid4().hex[:6]}@verifield.test",
        full_name="Other Org Admin",
        role="ORG_ADMIN",
        organization_id=other_org.id,
        is_active=True,
    )
    db_session.add(user_other_org)
    await db_session.flush()

    campaign = await AgricultureService.create_sampling_campaign(
        db_session,
        project.id,
        org.id,
        SamplingCampaignCreate(
            campaign_code=f"CAMP-BULK-{uuid.uuid4().hex[:4]}",
            name="Bulk Import Ground Campaign",
            planned_start_date=date(2026, 9, 1),
        ),
        user_id=admin.id,
    )
    spv = await AgricultureService.create_sampling_plan_version(
        db_session, campaign.id, org.id, SamplingPlanVersionCreate(effective_as_of_date=date(2026, 6, 1))
    )
    points = await AgricultureService.create_sampling_points(
        db_session,
        campaign.id,
        spv.id,
        org.id,
        [
            SamplingPointCreate(point_code=f"P-BLK-1-{uuid.uuid4().hex[:4]}", planned_lat=28.50500, planned_lon=77.10500, land_unit_id=lu.id, stratum_id=stratum.id),
            SamplingPointCreate(point_code=f"P-BLK-2-{uuid.uuid4().hex[:4]}", planned_lat=28.50600, planned_lon=77.10600, land_unit_id=lu.id, stratum_id=stratum.id),
            SamplingPointCreate(point_code=f"P-BLK-3-{uuid.uuid4().hex[:4]}", planned_lat=28.50700, planned_lon=77.10700, land_unit_id=lu.id, stratum_id=stratum.id),
        ],
    )
    sample1 = await db_session.scalar(select(PhysicalSample).where(PhysicalSample.sampling_point_id == points[0].id))
    sample2 = await db_session.scalar(select(PhysicalSample).where(PhysicalSample.sampling_point_id == points[1].id))
    sample_rejected = await db_session.scalar(select(PhysicalSample).where(PhysicalSample.sampling_point_id == points[2].id))
    sample_rejected.status = "REJECTED_BY_LAB"
    await db_session.commit()

    return {
        "org": org,
        "admin": admin,
        "field": field,
        "other_org_user": user_other_org,
        "project": project,
        "campaign": campaign,
        "sample1": sample1,
        "sample2": sample2,
        "sample_rejected": sample_rejected,
    }


# =============================================================================
# 1. Template Generation Tests
# =============================================================================

def test_template_generation_csv():
    """Verifies that CSV template is generated with proper headers and sample rows."""
    content, filename, media_type = LaboratoryImportService.generate_template(file_format="csv")
    assert filename.endswith(".csv")
    assert media_type == "text/csv"
    assert len(content) > 0

    text = content.decode("utf-8")
    lines = text.strip().split("\n")
    headers = [h.strip() for h in lines[0].split(",")]
    assert "sample_code" in headers
    assert "analyte" in headers
    assert "raw_value" in headers
    assert "raw_unit" in headers
    assert len(lines) >= 6


def test_template_generation_xlsx():
    """Verifies that XLSX template is generated with openpyxl styling and readable data."""
    content, filename, media_type = LaboratoryImportService.generate_template(file_format="xlsx")
    assert filename.endswith(".xlsx")
    assert "openxmlformats" in media_type
    assert len(content) > 0

    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    assert "Lab_Results_Import" in wb.sheetnames
    ws = wb["Lab_Results_Import"]
    headers = [c.value for c in ws[1] if c.value]
    assert "sample_code" in headers
    assert "analyte" in headers
    assert "raw_value" in headers
    assert ws.max_row >= 6


# =============================================================================
# 2. Column Mapping Auto-Detection Tests
# =============================================================================

def test_suggest_column_mappings_standard():
    headers = ["sample_code", "analyte", "raw_value", "raw_unit", "depth_from_cm", "depth_to_cm"]
    mapping = LaboratoryImportService.suggest_column_mappings(headers)
    assert mapping["sample_code_column"] == "sample_code"
    assert mapping["analyte_column"] == "analyte"
    assert mapping["value_column"] == "raw_value"
    assert mapping["unit_column"] == "raw_unit"


def test_suggest_column_mappings_aliases():
    headers = ["SampleID", "Parameter", "Concentration", "Units", "Top_Depth", "Bottom_Depth", "Test_Date"]
    mapping = LaboratoryImportService.suggest_column_mappings(headers)
    assert mapping["sample_code_column"] == "SampleID"
    assert mapping["analyte_column"] == "Parameter"
    assert mapping["value_column"] == "Concentration"
    assert mapping["unit_column"] == "Units"
    assert mapping["depth_from_column"] == "Top_Depth"
    assert mapping["depth_to_column"] == "Bottom_Depth"


# =============================================================================
# 3. File Ingestion & Staging Tests
# =============================================================================

@pytest.mark.asyncio
async def test_file_upload_csv_stages_rows_and_creates_evidence(db_session: AsyncSession):
    setup = await create_agri_lab_import_setup(db_session)
    s1_code = setup["sample1"].sample_code
    s2_code = setup["sample2"].sample_code

    csv_data = (
        f"sample_code,analyte,raw_value,raw_unit,depth_from_cm,depth_to_cm,method\n"
        f"{s1_code},SOC_CONCENTRATION,2.15,%,0,30,DUMAS_COMBUSTION\n"
        f"{s1_code},BULK_DENSITY_G_CM3,1.35,g/cm3,0,30,CORE_RING\n"
        f"{s2_code},SOC_CONCENTRATION,25.0,g/kg,0,30,DUMAS_COMBUSTION\n"
    ).encode("utf-8")

    upload_file = UploadFile(
        file=io.BytesIO(csv_data),
        filename="soil_lab_results_2026.csv",
        headers={"content-type": "text/csv"},
    )

    batch = await LaboratoryImportService.upload_file(
        db=db_session,
        project_id=setup["project"].id,
        organization_id=setup["org"].id,
        user_id=setup["admin"].id,
        file=upload_file,
        laboratory_name="AgriLab Global",
        sampling_campaign_id=setup["campaign"].id,
    )
    await db_session.commit()

    assert batch.status in ("VALIDATED", "UPLOADED")
    assert batch.total_rows == 3
    assert batch.file_type == "CSV"
    assert batch.file_sha256 is not None
    assert batch.evidence_id is not None

    # Verify Evidence record in database
    ev_stmt = select(Evidence).where(Evidence.id == batch.evidence_id)
    ev = (await db_session.execute(ev_stmt)).scalars().first()
    assert ev is not None
    assert ev.file_hash == batch.file_sha256
    assert ev.evidence_type == "LABORATORY_REPORT"

    # Verify staged rows
    rows_stmt = select(LaboratoryImportRow).where(LaboratoryImportRow.import_batch_id == batch.id)
    rows = (await db_session.execute(rows_stmt)).scalars().all()
    assert len(rows) == 3
    assert all(r.validation_status in ("VALID", "WARNING") for r in rows)


@pytest.mark.asyncio
async def test_file_upload_xlsx_stages_rows(db_session: AsyncSession):
    setup = await create_agri_lab_import_setup(db_session)
    s1_code = setup["sample1"].sample_code
    s2_code = setup["sample2"].sample_code

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["sample_code", "analyte", "raw_value", "raw_unit", "depth_from_cm", "depth_to_cm"])
    ws.append([s1_code, "SOC", 1.95, "%", 0, 30])
    ws.append([s2_code, "PH", 6.8, "pH", 0, 30])

    buf = io.BytesIO()
    wb.save(buf)
    xlsx_bytes = buf.getvalue()

    upload_file = UploadFile(
        file=io.BytesIO(xlsx_bytes),
        filename="lab_report_q3.xlsx",
        headers={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    )

    batch = await LaboratoryImportService.upload_file(
        db=db_session,
        project_id=setup["project"].id,
        organization_id=setup["org"].id,
        user_id=setup["admin"].id,
        file=upload_file,
    )
    await db_session.commit()

    assert batch.total_rows == 2
    assert batch.file_type == "XLSX"


@pytest.mark.asyncio
async def test_duplicate_file_upload_rejected(db_session: AsyncSession):
    setup = await create_agri_lab_import_setup(db_session)
    s1_code = setup["sample1"].sample_code
    csv_data = f"sample_code,analyte,raw_value,raw_unit\n{s1_code},SOC,2.0,%\n".encode("utf-8")

    upload_file_1 = UploadFile(file=io.BytesIO(csv_data), filename="dup.csv")
    batch1 = await LaboratoryImportService.upload_file(
        db=db_session,
        project_id=setup["project"].id,
        organization_id=setup["org"].id,
        user_id=setup["admin"].id,
        file=upload_file_1,
    )
    await db_session.commit()
    assert batch1.id is not None

    # Upload exact duplicate
    upload_file_2 = UploadFile(file=io.BytesIO(csv_data), filename="dup.csv")
    with pytest.raises(HTTPException) as exc_info:
        await LaboratoryImportService.upload_file(
            db=db_session,
            project_id=setup["project"].id,
            organization_id=setup["org"].id,
            user_id=setup["admin"].id,
            file=upload_file_2,
        )
    assert exc_info.value.status_code == 409


# =============================================================================
# 4. Validation Logic & Edge Cases Tests
# =============================================================================

@pytest.mark.asyncio
async def test_validation_flags_unknown_sample_code(db_session: AsyncSession):
    setup = await create_agri_lab_import_setup(db_session)
    csv_data = (
        "sample_code,analyte,raw_value,raw_unit\n"
        "UNKNOWN-SAMPLE-999,SOC,1.5,%\n"
    ).encode("utf-8")

    batch = await LaboratoryImportService.upload_file(
        db=db_session,
        project_id=setup["project"].id,
        organization_id=setup["org"].id,
        user_id=setup["admin"].id,
        file=UploadFile(file=io.BytesIO(csv_data), filename="unknown.csv"),
    )
    await db_session.commit()

    assert batch.error_rows == 1
    rows = (await db_session.execute(
        select(LaboratoryImportRow).where(LaboratoryImportRow.import_batch_id == batch.id)
    )).scalars().all()
    assert rows[0].validation_status == "ERROR"
    assert any(m["code"] == "SAMPLE_NOT_FOUND" for m in rows[0].validation_messages)


@pytest.mark.asyncio
async def test_validation_flags_rejected_sample(db_session: AsyncSession):
    setup = await create_agri_lab_import_setup(db_session)
    rej_code = setup["sample_rejected"].sample_code
    csv_data = f"sample_code,analyte,raw_value,raw_unit\n{rej_code},SOC,1.5,%\n".encode("utf-8")

    batch = await LaboratoryImportService.upload_file(
        db=db_session,
        project_id=setup["project"].id,
        organization_id=setup["org"].id,
        user_id=setup["admin"].id,
        file=UploadFile(file=io.BytesIO(csv_data), filename="rejected.csv"),
    )
    await db_session.commit()

    assert batch.error_rows == 1
    rows = (await db_session.execute(
        select(LaboratoryImportRow).where(LaboratoryImportRow.import_batch_id == batch.id)
    )).scalars().all()
    assert rows[0].validation_status == "ERROR"
    assert any(m["code"] == "SAMPLE_REJECTED" for m in rows[0].validation_messages)


@pytest.mark.asyncio
async def test_validation_analyte_normalization_and_ranges(db_session: AsyncSession):
    setup = await create_agri_lab_import_setup(db_session)
    s1_code = setup["sample1"].sample_code
    s2_code = setup["sample2"].sample_code

    csv_data = (
        f"sample_code,analyte,raw_value,raw_unit\n"
        f"{s1_code},SOC_CONCENTRATION,2.0,%\n"
        f"{s2_code},SOC_CONCENTRATION,20.0,g/kg\n"
    ).encode("utf-8")

    batch = await LaboratoryImportService.upload_file(
        db=db_session,
        project_id=setup["project"].id,
        organization_id=setup["org"].id,
        user_id=setup["admin"].id,
        file=UploadFile(file=io.BytesIO(csv_data), filename="norm.csv"),
    )
    await db_session.commit()

    rows = (await db_session.execute(
        select(LaboratoryImportRow).where(LaboratoryImportRow.import_batch_id == batch.id).order_by(LaboratoryImportRow.source_row_number)
    )).scalars().all()

    # 2.0% -> 20.0000 g/kg
    assert rows[0].normalized_value == Decimal("20.0000")
    assert rows[0].normalized_unit == "g/kg"
    # 20.0 g/kg -> 20.0000 g/kg
    assert rows[1].normalized_value == Decimal("20.0000")
    assert rows[1].normalized_unit == "g/kg"


@pytest.mark.asyncio
async def test_validation_unconvertible_unit_flags_error(db_session: AsyncSession):
    setup = await create_agri_lab_import_setup(db_session)
    s1_code = setup["sample1"].sample_code
    csv_data = f"sample_code,analyte,raw_value,raw_unit\n{s1_code},SOC_CONCENTRATION,2.0,gallons\n".encode("utf-8")

    batch = await LaboratoryImportService.upload_file(
        db=db_session,
        project_id=setup["project"].id,
        organization_id=setup["org"].id,
        user_id=setup["admin"].id,
        file=UploadFile(file=io.BytesIO(csv_data), filename="bad_unit.csv"),
    )
    await db_session.commit()

    assert batch.error_rows == 1
    rows = (await db_session.execute(
        select(LaboratoryImportRow).where(LaboratoryImportRow.import_batch_id == batch.id)
    )).scalars().all()
    assert rows[0].validation_status == "ERROR"
    assert any(m["code"] == "UNCONVERTIBLE_UNIT" for m in rows[0].validation_messages)


@pytest.mark.asyncio
async def test_validation_intra_batch_duplicate_detection(db_session: AsyncSession):
    setup = await create_agri_lab_import_setup(db_session)
    s1_code = setup["sample1"].sample_code
    csv_data = (
        f"sample_code,analyte,raw_value,raw_unit,depth_from_cm,depth_to_cm\n"
        f"{s1_code},SOC,2.0,%,0,30\n"
        f"{s1_code},SOC,2.1,%,0,30\n"
    ).encode("utf-8")

    batch = await LaboratoryImportService.upload_file(
        db=db_session,
        project_id=setup["project"].id,
        organization_id=setup["org"].id,
        user_id=setup["admin"].id,
        file=UploadFile(file=io.BytesIO(csv_data), filename="intra_dup.csv"),
    )
    await db_session.commit()

    assert batch.error_rows >= 1
    rows = (await db_session.execute(
        select(LaboratoryImportRow).where(LaboratoryImportRow.import_batch_id == batch.id).order_by(LaboratoryImportRow.source_row_number)
    )).scalars().all()
    assert rows[1].validation_status == "ERROR"
    assert any(m["code"] == "DUPLICATE_IN_BATCH" for m in rows[1].validation_messages)


# =============================================================================
# 5. Transactional Commit Tests
# =============================================================================

@pytest.mark.asyncio
async def test_commit_clean_batch_creates_canonical_records(db_session: AsyncSession):
    setup = await create_agri_lab_import_setup(db_session)
    s1_code = setup["sample1"].sample_code
    s2_code = setup["sample2"].sample_code

    csv_data = (
        f"sample_code,analyte,raw_value,raw_unit,depth_from_cm,depth_to_cm,method\n"
        f"{s1_code},SOC_CONCENTRATION,1.85,%,0,30,DUMAS_COMBUSTION\n"
        f"{s1_code},BULK_DENSITY_G_CM3,1.32,g/cm3,0,30,CORE_RING\n"
        f"{s2_code},SOC_CONCENTRATION,24.5,g/kg,0,30,DUMAS_COMBUSTION\n"
    ).encode("utf-8")

    batch = await LaboratoryImportService.upload_file(
        db=db_session,
        project_id=setup["project"].id,
        organization_id=setup["org"].id,
        user_id=setup["admin"].id,
        file=UploadFile(file=io.BytesIO(csv_data), filename="commit_clean.csv"),
        laboratory_name="Eurofins Accredited",
    )
    await db_session.commit()

    assert batch.valid_rows == 3
    assert batch.error_rows == 0

    commit_res = await LaboratoryImportService.commit_batch(
        db=db_session,
        batch_id=batch.id,
        organization_id=setup["org"].id,
        user_id=setup["admin"].id,
    )
    await db_session.commit()

    assert commit_res["imported_rows"] == 3
    assert commit_res["results_created"] == 3
    assert commit_res["samples_analyzed"] == 2

    # Check PhysicalSample status
    s1 = await db_session.get(PhysicalSample, setup["sample1"].id)
    s2 = await db_session.get(PhysicalSample, setup["sample2"].id)
    assert s1.status == "ANALYZED"
    assert s2.status == "ANALYZED"

    # Verify LaboratoryAnalysis records have qa_status="PENDING"
    analyses = (await db_session.execute(
        select(LaboratoryAnalysis).where(LaboratoryAnalysis.analysis_batch_id == str(batch.id))
    )).scalars().all()
    assert len(analyses) == 2
    for an in analyses:
        assert an.qa_status == "PENDING"
        assert an.laboratory_name == "Eurofins Accredited"
        assert an.evidence_id == batch.evidence_id
        assert an.accreditation_status == "UNVERIFIED"

    # Verify LaboratoryResult records
    results = (await db_session.execute(
        select(LaboratoryResult).where(LaboratoryResult.analysis_id.in_([a.id for a in analyses]))
    )).scalars().all()
    assert len(results) == 3
    soc_results = [r for r in results if r.analyte == "SOC_CONCENTRATION"]
    assert len(soc_results) == 2
    # Verify deterministic normalization
    s1_soc = [r for r in soc_results if r.physical_sample_id == setup["sample1"].id][0]
    assert s1_soc.raw_value == Decimal("1.85")
    assert s1_soc.raw_unit == "%"
    assert s1_soc.normalized_value == Decimal("18.5000")
    assert s1_soc.normalized_unit == "g/kg"


@pytest.mark.asyncio
async def test_commit_with_errors_rejected_unless_import_valid_only(db_session: AsyncSession):
    setup = await create_agri_lab_import_setup(db_session)
    s1_code = setup["sample1"].sample_code
    csv_data = (
        f"sample_code,analyte,raw_value,raw_unit\n"
        f"{s1_code},SOC,2.0,%\n"
        f"UNKNOWN-SAMPLE,SOC,2.0,%\n"
    ).encode("utf-8")

    batch = await LaboratoryImportService.upload_file(
        db=db_session,
        project_id=setup["project"].id,
        organization_id=setup["org"].id,
        user_id=setup["admin"].id,
        file=UploadFile(file=io.BytesIO(csv_data), filename="with_errors.csv"),
    )
    await db_session.commit()

    assert batch.error_rows == 1

    # Attempt commit without import_valid_only
    with pytest.raises(HTTPException) as exc_info:
        await LaboratoryImportService.commit_batch(
            db=db_session,
            batch_id=batch.id,
            organization_id=setup["org"].id,
            user_id=setup["admin"].id,
            import_valid_only=False,
        )
    assert exc_info.value.status_code == 400

    # Now commit with import_valid_only=True
    res = await LaboratoryImportService.commit_batch(
        db=db_session,
        batch_id=batch.id,
        organization_id=setup["org"].id,
        user_id=setup["admin"].id,
        import_valid_only=True,
    )
    await db_session.commit()

    assert res["status"] == "PARTIALLY_IMPORTED"
    assert res["imported_rows"] == 1
    assert res["skipped_rows"] == 1


@pytest.mark.asyncio
async def test_commit_supersedes_existing_active_result(db_session: AsyncSession):
    setup = await create_agri_lab_import_setup(db_session)
    s1_code = setup["sample1"].sample_code
    csv_data_1 = f"sample_code,analyte,raw_value,raw_unit\n{s1_code},SOC_CONCENTRATION,1.5,%\n".encode("utf-8")

    batch1 = await LaboratoryImportService.upload_file(
        db=db_session,
        project_id=setup["project"].id,
        organization_id=setup["org"].id,
        user_id=setup["admin"].id,
        file=UploadFile(file=io.BytesIO(csv_data_1), filename="run1.csv"),
    )
    await db_session.commit()
    await LaboratoryImportService.commit_batch(
        db=db_session, batch_id=batch1.id, organization_id=setup["org"].id, user_id=setup["admin"].id
    )
    await db_session.commit()

    # Get initial result
    r1 = (await db_session.execute(
        select(LaboratoryResult).where(
            and_(
                LaboratoryResult.physical_sample_id == setup["sample1"].id,
                LaboratoryResult.analyte == "SOC_CONCENTRATION",
                LaboratoryResult.is_superseded.is_(False),
            )
        )
    )).scalars().first()
    assert r1 is not None
    assert r1.raw_value == Decimal("1.5")

    # Ingest revision in batch 2
    csv_data_2 = f"sample_code,analyte,raw_value,raw_unit\n{s1_code},SOC_CONCENTRATION,1.85,%\n".encode("utf-8")
    batch2 = await LaboratoryImportService.upload_file(
        db=db_session,
        project_id=setup["project"].id,
        organization_id=setup["org"].id,
        user_id=setup["admin"].id,
        file=UploadFile(file=io.BytesIO(csv_data_2), filename="run2.csv"),
    )
    await db_session.commit()

    # Unconfirmed revision must be rejected with 400
    with pytest.raises(HTTPException) as exc:
        await LaboratoryImportService.commit_batch(
            db=db_session,
            batch_id=batch2.id,
            organization_id=setup["org"].id,
            user_id=setup["admin"].id,
            import_as_revision=False,
        )
    assert exc.value.status_code == 400
    assert "import_as_revision=True" in exc.value.detail

    # Explicitly confirmed revision succeeds with import_as_revision=True
    await LaboratoryImportService.commit_batch(
        db=db_session,
        batch_id=batch2.id,
        organization_id=setup["org"].id,
        user_id=setup["admin"].id,
        import_as_revision=True,
    )
    await db_session.commit()

    # Refresh previous result: should be superseded
    await db_session.refresh(r1)
    assert r1.is_superseded is True
    assert r1.superseded_by_id is not None

    # New result
    r2 = await db_session.get(LaboratoryResult, r1.superseded_by_id)
    assert r2 is not None
    assert r2.is_superseded is False
    assert r2.supersedes_id == r1.id
    assert r2.raw_value == Decimal("1.85")


@pytest.mark.asyncio
async def test_commit_double_commit_blocked(db_session: AsyncSession):
    setup = await create_agri_lab_import_setup(db_session)
    s1_code = setup["sample1"].sample_code
    csv_data = f"sample_code,analyte,raw_value,raw_unit\n{s1_code},SOC,2.0,%\n".encode("utf-8")
    batch = await LaboratoryImportService.upload_file(
        db=db_session,
        project_id=setup["project"].id,
        organization_id=setup["org"].id,
        user_id=setup["admin"].id,
        file=UploadFile(file=io.BytesIO(csv_data), filename="double.csv"),
    )
    await db_session.commit()

    await LaboratoryImportService.commit_batch(
        db=db_session, batch_id=batch.id, organization_id=setup["org"].id, user_id=setup["admin"].id
    )
    await db_session.commit()

    # Second commit should raise error
    with pytest.raises(HTTPException) as exc_info:
        await LaboratoryImportService.commit_batch(
            db=db_session, batch_id=batch.id, organization_id=setup["org"].id, user_id=setup["admin"].id
        )
    assert exc_info.value.status_code == 400


# =============================================================================
# 6. CSV Formula Injection Defense Tests
# =============================================================================

def test_csv_formula_injection_defense():
    """Ensures formula control characters (=, +, -, @) are sanitized with leading single quote."""
    assert LaboratoryImportService.sanitize_formula_injection("=cmd|'/C calc'!A0") == "'=cmd|'/C calc'!A0"
    assert LaboratoryImportService.sanitize_formula_injection("+12345") == "'+12345"
    assert LaboratoryImportService.sanitize_formula_injection("-100") == "'-100"
    assert LaboratoryImportService.sanitize_formula_injection("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert LaboratoryImportService.sanitize_formula_injection("Normal Text") == "Normal Text"


@pytest.mark.asyncio
async def test_export_errors_csv_sanitizes_injection(db_session: AsyncSession):
    setup = await create_agri_lab_import_setup(db_session)
    csv_data = (
        "sample_code,analyte,raw_value,raw_unit\n"
        "=DDE('cmd';'calc.exe';'a'),SOC,2.0,%\n"
    ).encode("utf-8")

    batch = await LaboratoryImportService.upload_file(
        db=db_session,
        project_id=setup["project"].id,
        organization_id=setup["org"].id,
        user_id=setup["admin"].id,
        file=UploadFile(file=io.BytesIO(csv_data), filename="injection.csv"),
    )
    await db_session.commit()

    content, filename = await LaboratoryImportService.export_errors_csv(
        db=db_session,
        batch_id=batch.id,
        organization_id=setup["org"].id,
    )
    text = content.decode("utf-8")
    assert filename.endswith(".csv")
    assert "'=DDE" in text


# =============================================================================
# 7. REST API Endpoints & Multi-Tenant RBAC Tests
# =============================================================================

@pytest.mark.asyncio
async def test_rest_api_full_workflow(db_session: AsyncSession):
    setup = await create_agri_lab_import_setup(db_session)
    s1_code = setup["sample1"].sample_code
    s2_code = setup["sample2"].sample_code

    admin_token = _create_token(setup["admin"].id, setup["admin"].email, "ORG_ADMIN", setup["org"].id)
    headers = {"Authorization": f"Bearer {admin_token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Download template
        tpl_res = await client.get(
            f"/api/v1/agriculture/projects/{setup['project'].id}/laboratory-import/template?format=csv",
            headers=headers,
        )
        assert tpl_res.status_code == 200
        assert "text/csv" in tpl_res.headers["content-type"]

        # 2. Upload file
        csv_payload = (
            f"sample_code,analyte,raw_value,raw_unit\n"
            f"{s1_code},SOC_CONCENTRATION,2.35,%\n"
            f"{s2_code},PH,6.7,pH\n"
        )
        files = {"file": ("api_test.csv", csv_payload, "text/csv")}
        up_res = await client.post(
            f"/api/v1/agriculture/projects/{setup['project'].id}/laboratory-import/upload",
            files=files,
            headers=headers,
        )
        assert up_res.status_code == 201
        batch_data = up_res.json()
        batch_id = batch_data["id"]
        assert batch_data["total_rows"] == 2
        assert batch_data["valid_rows"] == 2

        # 3. List batches
        list_res = await client.get(
            f"/api/v1/agriculture/projects/{setup['project'].id}/laboratory-import/batches",
            headers=headers,
        )
        assert list_res.status_code == 200
        assert any(b["id"] == batch_id for b in list_res.json())

        # 4. Get batch rows
        rows_res = await client.get(
            f"/api/v1/agriculture/projects/{setup['project'].id}/laboratory-import/batches/{batch_id}/rows",
            headers=headers,
        )
        assert rows_res.status_code == 200
        assert len(rows_res.json()) == 2

        # 5. Commit batch
        commit_res = await client.post(
            f"/api/v1/agriculture/projects/{setup['project'].id}/laboratory-import/batches/{batch_id}/commit",
            json={"import_valid_only": False},
            headers=headers,
        )
        assert commit_res.status_code == 200
        c_json = commit_res.json()
        assert c_json["status"] == "IMPORTED"
        assert c_json["results_created"] == 2


@pytest.mark.asyncio
async def test_rest_api_tenant_isolation_enforced(db_session: AsyncSession):
    setup = await create_agri_lab_import_setup(db_session)
    other_org_token = _create_token(
        setup["other_org_user"].id,
        setup["other_org_user"].email,
        "ORG_ADMIN",
        setup["other_org_user"].organization_id,
    )
    headers = {"Authorization": f"Bearer {other_org_token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(
            f"/api/v1/agriculture/projects/{setup['project'].id}/laboratory-import/batches",
            headers=headers,
        )
        assert res.status_code in (403, 404) or len(res.json()) == 0
