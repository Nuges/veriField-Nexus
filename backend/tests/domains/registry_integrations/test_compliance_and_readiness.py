"""
=============================================================================
VeriField Nexus — Registry Documentation & Compliance Verification Suite
=============================================================================
Tests:
1. Nigeria NCCC / NCMAP Regulatory Compliance Dossier
2. UNFCCC Article 6.2 ITMO Structured Summary
3. UNFCCC Article 6.4 Mechanism Dossier & A6.4ER Accounting
4. Verra VCS Version 5.0 Project Description & Monitoring Dossier
5. Gold Standard for the Global Goals (GS4GG) 3-SDG Matrix & Safeguards
6. Data Lineage & Provenance Traceability Engine
7. Deterministic 9-Pillar Registry Readiness & Completeness Scoring
8. Multi-Directory Standardized ZIP Package Generation & SHA-256 Manifest Integrity
9. Realistic Synthetic Cross-Sector Pipeline (Cookstoves, Biochar, EV, Solar)
=============================================================================
"""

import io
import json
import uuid
import zipfile
from datetime import date, datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user
from app.db.session import _get_fallback_session_factory, _init_fallback_db, get_db
from app.domains.activities.models import Activity
from app.domains.assets.models import Asset
from app.domains.authentication.models import User
from app.domains.documents.models import ProjectDocument
from app.domains.evidence.models import Evidence
from app.domains.methodologies.models.base_registry import Methodology, MethodologyFamily, MethodologyRegistry
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.registry_integrations.services.compliance_dossier import RegistryComplianceDossierService
from app.domains.registry_integrations.services.package_builder import ComprehensivePackageBuilder
from app.domains.registry_integrations.services.readiness_engine import RegistryReadinessEngine
from app.domains.reporting.services.lineage import DataLineageEngine
from app.main import app


@pytest.mark.asyncio
async def test_nccc_nigeria_dossier_generation():
    """Verify Nigeria NCCC / NCMAP regulatory compliance dossier generation."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    reg_id = uuid.uuid4()
    sec_id = uuid.uuid4()
    meth_id = uuid.uuid4()
    asset_id = uuid.uuid4()

    async with factory() as session:
        org = Organization(id=org_id, name=f"West Africa Clean Energy Ltd {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
        user = User(id=user_id, organization_id=org_id, email=f"agent_{uuid.uuid4().hex[:6]}@orga.com", full_name="Agent", role="FIELD_AGENT")
        reg = MethodologyRegistry(id=reg_id, code=f"NCCC_{uuid.uuid4().hex[:4]}", name="National Council on Climate Change")
        sector = MethodologyFamily(id=sec_id, code=f"COOKING_{uuid.uuid4().hex[:4]}", name="Clean Cooking & Household Energy")
        meth = Methodology(id=meth_id, code=f"VMR0006_{uuid.uuid4().hex[:4]}", name="Clean Cookstove Methodology", registry_id=reg_id, family_id=sec_id)
        proj = Project(
            id=proj_id,
            name=f"Kano State Clean Cooking Programme {uuid.uuid4().hex[:6]}",
            organization_id=org_id,
            sector_id=sec_id,
            methodology_id=meth_id,
            country="Nigeria",
            crediting_start=date(2026, 1, 1),
            crediting_end=date(2035, 12, 31),
        )
        asset = Asset(id=asset_id, project_id=proj_id, organization_id=org_id, name="Cookstove Batch 1", status="active")
        session.add_all([org, user, reg, sector, meth, proj, asset])

        for i in range(5):
            act = Activity(
                id=uuid.uuid4(),
                organization_id=org_id,
                user_id=user_id,
                asset_id=asset_id,
                activity_type="stove_monitoring",
                trust_score=92.0,
                activity_data={"emission_reduction_kg": 450.0},
                captured_at=datetime.now(timezone.utc),
                submitted_at=datetime.now(timezone.utc),
            )
            session.add(act)
        await session.commit()

        dossier_service = RegistryComplianceDossierService(session)
        dossier = await dossier_service.generate_dossier(standard="NCCC", project_id=proj_id)

        assert dossier["standard_profile"] == "NIGERIA_NCCC_NCMAP"
        assert dossier["project_metadata"]["host_country"] == "Federal Republic of Nigeria"
        assert dossier["mitigation_quantification"]["verified_activity_records"] == 5
        assert dossier["mitigation_quantification"]["cumulative_mitigation_tco2e"] == 2.25
        assert dossier["regulatory_compliance_sections"]["section_1_no_objection_certificate_status"]["noc_status"] == "APPLICATION_DOSSIER_COMPILED"
        assert dossier["regulatory_compliance_sections"]["section_3_benefit_sharing_and_social_impact"]["community_benefit_allocation_pct"] == 15.0
        assert "dossier_sha256" in dossier


@pytest.mark.asyncio
async def test_article_6_dossiers_and_accounting():
    """Verify Article 6.2 and 6.4 dossier structures and deduction math."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    proj_id = uuid.uuid4()
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    asset_id = uuid.uuid4()

    async with factory() as session:
        org = Organization(id=org_id, name=f"Solar Dev Corp {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
        user = User(id=user_id, organization_id=org_id, email=f"solar_{uuid.uuid4().hex[:6]}@orga.com", full_name="Solar Agent", role="FIELD_AGENT")
        proj = Project(
            id=proj_id,
            name=f"Solar Hybrid Mini-Grid Article 6 Programme {uuid.uuid4().hex[:6]}",
            organization_id=org_id,
            country="Nigeria",
            crediting_start=date(2026, 1, 1),
            crediting_end=date(2035, 12, 31),
        )
        asset = Asset(id=asset_id, project_id=proj_id, organization_id=org_id, name="MiniGrid #1", status="active")
        session.add_all([org, user, proj, asset])

        for i in range(10):
            session.add(Activity(
                id=uuid.uuid4(),
                organization_id=org_id,
                user_id=user_id,
                asset_id=asset_id,
                activity_type="solar_generation",
                trust_score=95.0,
                activity_data={"emission_reduction_kg": 1000.0},
                captured_at=datetime.now(timezone.utc),
                submitted_at=datetime.now(timezone.utc),
            ))
        await session.commit()

        dossier_service = RegistryComplianceDossierService(session)

        # 1. Article 6.2 ITMO
        a62 = await dossier_service.generate_dossier(standard="ARTICLE6_2", project_id=proj_id)
        assert a62["standard_profile"] == "UNFCCC_ARTICLE_6_2"
        assert a62["itmo_accounting_ledger"]["cumulative_itmos_generated_tco2e"] == 10.0
        assert a62["itmo_accounting_ledger"]["corresponding_adjustment_status"] == "PENDING_FIRST_TRANSFER"

        # 2. Article 6.4 Mechanism
        a64 = await dossier_service.generate_dossier(standard="ARTICLE6_4", project_id=proj_id)
        assert a64["standard_profile"] == "UNFCCC_ARTICLE_6_4"
        assert a64["a64er_unit_accounting"]["verified_a64ers_total"] == 10.0
        assert a64["a64er_unit_accounting"]["adaptation_share_of_proceeds_deduction_pct"] == 5.0
        assert a64["a64er_unit_accounting"]["mitigation_overall_omge_cancellation_pct"] == 2.0
        assert a64["a64er_unit_accounting"]["net_tradeable_a64ers"] == 9.3


@pytest.mark.asyncio
async def test_verra_v5_and_gold_standard_profiles():
    """Verify Verra VCS v5.0 and Gold Standard GS4GG 3-SDG compliance profiles."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    proj_id = uuid.uuid4()
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    asset_id = uuid.uuid4()

    async with factory() as session:
        org = Organization(id=org_id, name=f"Biochar Hub Ltd {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
        user = User(id=user_id, organization_id=org_id, email=f"bio_{uuid.uuid4().hex[:6]}@orga.com", full_name="Biochar Tech", role="FIELD_AGENT")
        proj = Project(
            id=proj_id,
            name=f"Biochar Carbon Sequestration Hub {uuid.uuid4().hex[:6]}",
            organization_id=org_id,
            country="Nigeria",
            crediting_start=date(2026, 1, 1),
            crediting_end=date(2035, 12, 31),
        )
        asset = Asset(id=asset_id, project_id=proj_id, organization_id=org_id, name="Kiln #1", status="active")
        act = Activity(
            id=uuid.uuid4(),
            organization_id=org_id,
            user_id=user_id,
            asset_id=asset_id,
            activity_type="biochar_pyrolysis",
            trust_score=98.0,
            activity_data={"emission_reduction_kg": 25000.0},
            captured_at=datetime.now(timezone.utc),
            submitted_at=datetime.now(timezone.utc),
        )
        session.add_all([org, user, proj, asset, act])
        await session.commit()

        dossier_service = RegistryComplianceDossierService(session)

        # 1. Verra v5
        verra = await dossier_service.generate_dossier(standard="VERRA", project_id=proj_id, version="v5.0")
        assert verra["standard_profile"] == "VERRA_VCS"
        assert verra["standard_version"] == "v5.0"
        assert verra["project_description_sections"]["section_4_quantification_of_ghg_emission_reductions"]["net_estimated_emission_reductions_vcus"] == 25.0
        assert verra["project_description_sections"]["section_2_safeguards_and_esg"]["esg_risk_assessment_required"] is True

        # 2. Gold Standard GS4GG
        gs = await dossier_service.generate_dossier(standard="GOLD_STANDARD", project_id=proj_id)
        assert gs["standard_profile"] == "GOLD_STANDARD_GS4GG"
        assert gs["sdg_impact_matrix"]["mandatory_minimum_sdgs"] == 3
        assert "sdg_13_climate_action" in gs["sdg_impact_matrix"]
        assert len(gs["sdg_impact_matrix"]) >= 3


@pytest.mark.asyncio
async def test_data_lineage_and_provenance_engine():
    """Verify data lineage engine provenance graph linking sensor readings to credits."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    proj_id = uuid.uuid4()
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    act_id = uuid.uuid4()

    async with factory() as session:
        org = Organization(id=org_id, name=f"EV Mobility Ltd {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
        user = User(id=user_id, organization_id=org_id, email=f"ev_{uuid.uuid4().hex[:6]}@orga.com", full_name="EV Agent", role="FIELD_AGENT")
        proj = Project(id=proj_id, name=f"EV Fleet E-Mobility Project {uuid.uuid4().hex[:6]}", organization_id=org_id, country="Nigeria")
        asset = Asset(id=asset_id, project_id=proj_id, organization_id=org_id, name="EV Bus #12", status="active")
        act = Activity(
            id=act_id,
            organization_id=org_id,
            user_id=user_id,
            asset_id=asset_id,
            activity_type="ev_telemetry",
            trust_score=88.0,
            activity_data={"emission_reduction_kg": 500.0},
            captured_at=datetime.now(timezone.utc),
            submitted_at=datetime.now(timezone.utc),
        )
        ev = Evidence(
            id=uuid.uuid4(),
            activity_id=act_id,
            file_uri="s3://evidence/meter_01.bin",
            file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            evidence_type="METER_READING",
        )
        session.add_all([org, user, proj, asset, act, ev])
        await session.commit()

        lineage_engine = DataLineageEngine(session)
        lineage = await lineage_engine.get_project_data_lineage(project_id=proj_id)

        assert lineage["project_name"].startswith("EV Fleet E-Mobility Project")
        assert lineage["summary_metrics"]["total_activities_processed"] == 1
        assert lineage["summary_metrics"]["total_emission_reductions_tco2e"] == 0.5
        assert len(lineage["lineage_records"]) == 1
        assert lineage["lineage_records"][0]["evidence_attachments"][0]["evidence_type"] == "METER_READING"
        assert "lineage_digest" in lineage


@pytest.mark.asyncio
async def test_readiness_scoring_and_missing_requirements():
    """Verify deterministic 9-pillar readiness scoring and missing item detection."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    incomplete_proj_id = uuid.uuid4()

    async with factory() as session:
        # Incomplete project: No methodology, no assets, no activities
        proj = Project(id=incomplete_proj_id, name=f"Incomplete Concept {uuid.uuid4().hex[:6]}", country="Nigeria")
        session.add(proj)
        await session.commit()

        readiness_engine = RegistryReadinessEngine(session)
        readiness = await readiness_engine.evaluate_readiness(project_id=incomplete_proj_id)

        assert readiness["readiness_status"] == "BLOCKED"
        assert readiness["missing_requirements_count"] > 0
        assert any("methodology" in r.lower() for r in readiness["missing_requirements"])
        assert any("assets" in r.lower() for r in readiness["missing_requirements"])


@pytest.mark.asyncio
async def test_comprehensive_package_builder_zip():
    """Verify full multi-directory ZIP package generation with valid manifest and CSV files."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    proj_id = uuid.uuid4()
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    reg_id = uuid.uuid4()
    sec_id = uuid.uuid4()
    meth_id = uuid.uuid4()
    asset_id = uuid.uuid4()

    async with factory() as session:
        org = Organization(id=org_id, name=f"Clean Tech Org {uuid.uuid4().hex[:6]}", org_type="DEVELOPER")
        user = User(id=user_id, organization_id=org_id, email=f"solar_{uuid.uuid4().hex[:6]}@orga.com", full_name="Solar Engineer", role="FIELD_AGENT")
        reg = MethodologyRegistry(id=reg_id, code=f"VERRA_{uuid.uuid4().hex[:4]}", name="Verra Registry")
        sector = MethodologyFamily(id=sec_id, code=f"SOLAR_{uuid.uuid4().hex[:4]}", name="Solar Renewable Energy")
        meth = Methodology(id=meth_id, code=f"AMS_{uuid.uuid4().hex[:4]}", name="Grid Connected Solar", registry_id=reg_id, family_id=sec_id)
        proj = Project(
            id=proj_id,
            name=f"Kaduna Solar Plant {uuid.uuid4().hex[:6]}",
            organization_id=org_id,
            sector_id=sec_id,
            methodology_id=meth_id,
            country="Nigeria",
            crediting_start=date(2026, 1, 1),
            crediting_end=date(2035, 12, 31),
        )
        asset = Asset(id=asset_id, project_id=proj_id, organization_id=org_id, name="Solar Array 1", status="active")
        act = Activity(
            id=uuid.uuid4(),
            organization_id=org_id,
            user_id=user_id,
            asset_id=asset_id,
            activity_type="generation_kwh",
            trust_score=95.0,
            activity_data={"emission_reduction_kg": 12000.0},
            captured_at=datetime.now(timezone.utc),
            submitted_at=datetime.now(timezone.utc),
        )
        session.add_all([org, user, reg, sector, meth, proj, asset, act])
        await session.commit()

        builder = ComprehensivePackageBuilder(session)
        zip_bytes, filename, manifest = await builder.build_package_zip(project_id=proj_id, standard="VERRA", version="v5.0")

        assert filename.startswith("REGISTRY_PACKAGE_VERRA_")
        assert filename.endswith(".zip")
        assert manifest["package_standard"] == "VERRA"
        assert manifest["file_count"] >= 12

        # Validate ZIP structure in memory
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            namelist = zf.namelist()
            assert "00_manifest/manifest.json" in namelist
            assert "01_project/project_metadata.json" in namelist
            assert "04_monitoring/parameter_timeseries.csv" in namelist
            assert "05_calculations/data_lineage_provenance.json" in namelist
            assert "14_cryptographic_integrity/sha256_package_checksum.json" in namelist

            # Verify CSV content
            csv_content = zf.read("04_monitoring/parameter_timeseries.csv").decode("utf-8")
            assert "emission_reduction_kg" in csv_content
            assert "12000.0" in csv_content


@pytest.mark.asyncio
async def test_api_registry_dossier_and_readiness_endpoints():
    """Verify HTTP API endpoints for compliance dossiers, readiness, and package download."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    user = User(
        id=user_id,
        email=f"compliance_{uuid.uuid4().hex[:6]}@orga.com",
        full_name="Compliance Officer",
        role="COMPLIANCE_ADMIN",
        organization_id=org_id,
        status="active",
        is_active=True,
    )
    proj = Project(id=proj_id, name=f"Enugu Biomass Project {uuid.uuid4().hex[:6]}", organization_id=org_id, country="Nigeria")

    async with factory() as session:
        session.add(user)
        session.add(proj)
        await session.commit()

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test /dossier/NCCC/{proj_id}
        res_dossier = await client.get(f"/api/v1/registry/dossier/NCCC/{proj_id}")
        assert res_dossier.status_code == 200
        assert res_dossier.json()["standard_profile"] == "NIGERIA_NCCC_NCMAP"

        # 2. Test /readiness/{proj_id}
        res_readiness = await client.get(f"/api/v1/registry/readiness/{proj_id}")
        assert res_readiness.status_code == 200
        assert "overall_readiness_score" in res_readiness.json()

        # 3. Test /lineage/{proj_id}
        res_lineage = await client.get(f"/api/v1/registry/lineage/{proj_id}")
        assert res_lineage.status_code == 200
        assert "summary_metrics" in res_lineage.json()

        # 4. Test /package-download/VERRA/{proj_id}
        res_pkg = await client.get(f"/api/v1/registry/package-download/VERRA/{proj_id}")
        assert res_pkg.status_code == 200
        assert res_pkg.headers["content-type"] == "application/zip"
        assert len(res_pkg.content) > 1000

    app.dependency_overrides.clear()
