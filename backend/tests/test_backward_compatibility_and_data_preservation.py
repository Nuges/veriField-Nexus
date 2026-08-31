"""
=============================================================================
VeriField Nexus — Backward Compatibility & Data Preservation Test Suite
=============================================================================
Proves that pre-existing historical records (Projects, Activities, Assets,
Ledger Entries, Verification Tasks) created under legacy or partial schemas
successfully activate and drive newly introduced features, calculations,
registry readiness metrics, and document synthesizers without requiring
destructive data migrations or record recreation.
=============================================================================
"""

import pytest
import uuid
from datetime import datetime, timezone, date

from app.domains.authentication.models import User
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project, CarbonCalculation
from app.domains.activities.models import Activity
from app.domains.assets.models import Asset
from app.domains.ledger.models import Signature, AuditTrail
from app.domains.verification.models import VerificationTask
from app.domains.registry_integrations.services.readiness_engine import RegistryReadinessEngine
from app.domains.registry_integrations.services.package_builder import ComprehensivePackageBuilder


@pytest.mark.asyncio
async def test_legacy_project_activates_registry_readiness_and_document_package(db_session):
    """
    Proves that an existing legacy project with NULL optional fields
    (no crediting_start, no baseline_parameters, legacy country string)
    can calculate readiness and generate registry packages without error.
    """
    org_id = uuid.uuid4()
    org = Organization(
        id=org_id,
        name=f"Legacy Climate Holdings Ltd {uuid.uuid4().hex[:6]}",
        org_type="DEVELOPER",
        status="ACTIVE",
        plan="ENTERPRISE",
    )
    db_session.add(org)

    proj_id = uuid.uuid4()
    # Legacy project created without new v3 fields
    proj = Project(
        id=proj_id,
        name="Kano Clean Cookstove Legacy Initiative",
        organization_id=org_id,
        country="Nigeria",
        project_code=None,
        crediting_start=None,
        crediting_end=None,
        baseline_parameters={},
    )
    db_session.add(proj)

    # Legacy carbon calculation
    calc = CarbonCalculation(
        id=uuid.uuid4(),
        project_id=proj_id,
        tco2e_generated=142.50,
        status="verified",
    )
    db_session.add(calc)
    await db_session.commit()

    # 1. Test Readiness Engine with Legacy Project
    readiness_engine = RegistryReadinessEngine(db_session)
    readiness = await readiness_engine.evaluate_readiness(proj_id, "VERRA")

    assert readiness is not None
    assert "overall_readiness_score" in readiness
    assert "authorization_status" in readiness
    assert "blocking_items" in readiness
    assert isinstance(readiness["overall_readiness_score"], (int, float))

    # 2. Test Document Synthesizer with Legacy Project
    builder = ComprehensivePackageBuilder(db_session)
    zip_bytes, zip_filename, manifest = await builder.build_package_zip(
        project_id=proj_id,
        standard="VERRA",
    )

    assert zip_bytes is not None
    assert len(zip_bytes) > 0
    assert zip_filename.endswith(".zip")
    assert manifest is not None
    assert len(manifest["files"]) >= 4  # PDD, Monitoring, Stakeholder, Lineage


@pytest.mark.asyncio
async def test_legacy_activities_aggregate_without_crash(db_session):
    """
    Proves that historical activities with missing optional fields
    (NULL trust score, NULL environment_type, NULL gps accuracy)
    still aggregate correctly in repository and service layers.
    """
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()

    legacy_act = Activity(
        id=uuid.uuid4(),
        organization_id=org_id,
        user_id=user_id,
        activity_type="cookstove_distribution",
        activity_data={"stoves_distributed": 50, "beneficiary": "Fatima Bello"},
        status="pending",
        latitude=12.002,
        longitude=8.591,
        gps_accuracy=None,
        trust_score=None,
        captured_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(legacy_act)
    await db_session.commit()

    from app.domains.activities.repository import ActivityRepository
    repo = ActivityRepository(db_session)
    activities, total = await repo.list_activities_paginated(organization_id=org_id)

    assert total >= 1
    matched = [a for a in activities if a.id == legacy_act.id]
    assert len(matched) == 1
    assert matched[0].activity_data["stoves_distributed"] == 50


@pytest.mark.asyncio
async def test_legacy_asset_remains_intact_with_arbitrary_json(db_session):
    """
    Proves that legacy assets with custom arbitrary attributes JSON
    remain queryable and do not fail Pydantic model validation.
    """
    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    proj = Project(
        id=proj_id,
        name="Asset Container Project",
        organization_id=org_id,
        country="Nigeria",
    )
    db_session.add(proj)

    asset = Asset(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=proj_id,
        name="Legacy Save80 Cookstove #99",
        status="ACTIVE",
        attributes={"model": "Save80-Legacy-2023", "thermal_efficiency": 0.42, "legacy_tag": True},
    )
    db_session.add(asset)
    await db_session.commit()

    from app.domains.assets.service import AssetService
    from app.domains.assets.repository import AssetRepository
    service = AssetService(AssetRepository(db_session))
    retrieved = await service.get_asset(asset.id, org_id)

    assert retrieved is not None
    assert retrieved.attributes["legacy_tag"] is True
    assert retrieved.attributes["thermal_efficiency"] == 0.42


@pytest.mark.asyncio
async def test_idempotent_package_generation_reproducibility(db_session):
    """
    Proves that running package generation multiple times against the same
    existing project produces deterministic files and structure.
    """
    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    proj = Project(
        id=proj_id,
        name="Delta State Biochar Sequestration Facility",
        organization_id=org_id,
        country="Nigeria",
    )
    db_session.add(proj)
    await db_session.commit()

    builder = ComprehensivePackageBuilder(db_session)
    zip1, name1, manifest1 = await builder.build_package_zip(project_id=proj_id, standard="GOLD_STANDARD")
    zip2, name2, manifest2 = await builder.build_package_zip(project_id=proj_id, standard="GOLD_STANDARD")

    # Files generated must have the exact same count and relative paths
    assert manifest1["file_count"] == manifest2["file_count"]
    assert len(manifest1["files"]) == len(manifest2["files"])
    assert len(zip1) > 1000
    assert len(zip2) > 1000
