"""
=============================================================================
VeriField Nexus — Adversarial Registry Compliance & Production Gate Suite
=============================================================================
Adversarial Verification:
1. Multi-Tenant IDOR Attack: Tenant A attacking Tenant B registry endpoints (403 Forbidden)
2. Anti-Fabrication Invariants: Zero fake registry identifiers or synthesized employment counts
3. Incomplete Project Hard-Gating Attack: Gating blocks false "SUBMISSION_READY" status
4. Article 6.4 Supervisory Body Deduction & Unit Accounting Math (5% SOP + 2% OMGE)
5. Gold Standard Dynamic Multi-Sector SDG Matrix (Clean Cooking, EV Mobility, Biochar)
6. Configurable Sovereign Levies & Non-Permanence Buffer Overrides
7. Multi-Directory Package Determinism & SHA-256 Manifest Reproducibility
8. High-Volume Precision & Unit Conversion Forensics (kgCO2e to tCO2e)
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
async def test_multi_tenant_idor_attack_all_registry_endpoints():
    """Adversarial Test: Tenant A attempts to access Tenant B's compliance artifacts."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()
    user_a_id = uuid.uuid4()
    super_admin_id = uuid.uuid4()
    proj_b_id = uuid.uuid4()

    user_a = User(
        id=user_a_id,
        email=f"attacker_{uuid.uuid4().hex[:6]}@orga.com",
        full_name="Attacker A",
        role="COMPLIANCE_ADMIN",
        organization_id=org_a_id,
        status="active",
        is_active=True,
    )
    super_admin = User(
        id=super_admin_id,
        email=f"sa_{uuid.uuid4().hex[:6]}@admin.com",
        full_name="Super Admin",
        role="SUPER_ADMIN",
        status="active",
        is_active=True,
    )
    proj_b = Project(
        id=proj_b_id,
        name=f"Victim Project {uuid.uuid4().hex[:6]}",
        organization_id=org_b_id,
        country="Nigeria",
    )

    async with factory() as session:
        session.add_all([
            Organization(id=org_a_id, name=f"Org A {uuid.uuid4().hex[:6]}", org_type="DEVELOPER"),
            Organization(id=org_b_id, name=f"Org B {uuid.uuid4().hex[:6]}", org_type="DEVELOPER"),
            user_a,
            proj_b,
        ])
        await session.commit()

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    # 1. Attacker A attempts IDOR access to Tenant B project
    app.dependency_overrides[get_current_user] = lambda: user_a
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # A. Dossier attack
        res1 = await client.get(f"/api/v1/registry/dossier/VERRA/{proj_b_id}")
        assert res1.status_code == 403, f"Expected 403 Forbidden on dossier, got {res1.status_code}"

        # B. Readiness attack
        res2 = await client.get(f"/api/v1/registry/readiness/{proj_b_id}")
        assert res2.status_code == 403, f"Expected 403 Forbidden on readiness, got {res2.status_code}"

        # C. Lineage attack
        res3 = await client.get(f"/api/v1/registry/lineage/{proj_b_id}")
        assert res3.status_code == 403, f"Expected 403 Forbidden on lineage, got {res3.status_code}"

        # D. Package download attack
        res4 = await client.get(f"/api/v1/registry/package-download/VERRA/{proj_b_id}")
        assert res4.status_code == 403, f"Expected 403 Forbidden on package download, got {res4.status_code}"

    # 2. Super Admin access succeeds
    app.dependency_overrides[get_current_user] = lambda: super_admin
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_sa = await client.get(f"/api/v1/registry/dossier/VERRA/{proj_b_id}")
        assert res_sa.status_code == 200

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_anti_fabrication_zero_invented_identifiers():
    """Verify that unverified projects do not contain fabricated official registration codes."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    proj_id = uuid.uuid4()
    org_id = uuid.uuid4()

    async with factory() as session:
        proj = Project(
            id=proj_id,
            name=f"Clean Test Project {uuid.uuid4().hex[:6]}",
            organization_id=org_id,
            country="Nigeria",
            registry_id=None,  # No official registration yet
        )
        session.add(proj)
        await session.commit()

        service = RegistryComplianceDossierService(session)

        # 1. NCCC dossier check
        nccc = await service.generate_dossier(standard="NCCC", project_id=proj_id)
        assert nccc["regulatory_compliance_sections"]["section_1_no_objection_certificate_status"]["application_reference"] == "PENDING_OFFICIAL_FILING"
        assert nccc["regulatory_compliance_sections"]["section_3_benefit_sharing_and_social_impact"]["local_employment_count"] == "UNVERIFIED_PENDING_AUDIT"

        # 2. Verra dossier check
        verra = await service.generate_dossier(standard="VERRA", project_id=proj_id)
        assert verra["project_description_sections"]["section_1_project_details"]["vcs_project_id"] is None
        assert "NEXUS/VCS/" in verra["project_description_sections"]["section_1_project_details"]["internal_nexus_reference"]

        # 3. Gold Standard check
        gs = await service.generate_dossier(standard="GOLD_STANDARD", project_id=proj_id)
        assert gs["project_details"]["gs_project_id"] is None


@pytest.mark.asyncio
async def test_incomplete_project_hard_gating_attack():
    """Verify that incomplete projects are strictly BLOCKED and never marked SUBMISSION_READY."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    incomplete_proj_id = uuid.uuid4()

    async with factory() as session:
        proj = Project(id=incomplete_proj_id, name="Incomplete Stub", country="Nigeria")
        session.add(proj)
        await session.commit()

        engine = RegistryReadinessEngine(session)
        readiness = await engine.evaluate_readiness(project_id=incomplete_proj_id)

        assert readiness["readiness_status"] == "BLOCKED"
        assert readiness["blocking_items_count"] > 0
        assert "METHODOLOGY_UNLINKED" in readiness["blocking_items"]
        assert "ZERO_ASSETS_ENROLLED" in readiness["blocking_items"]
        assert readiness["readiness_status"] != "SUBMISSION_READY"


@pytest.mark.asyncio
async def test_article_6_4_supervisory_body_math():
    """Verify Article 6.4 deduction math: 5% SOP Adaptation + 2% OMGE = 7% total deduction."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    proj_id = uuid.uuid4()
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    asset_id = uuid.uuid4()

    async with factory() as session:
        proj = Project(id=proj_id, name=f"A64 Plant {uuid.uuid4().hex[:6]}", organization_id=org_id, country="Nigeria")
        asset = Asset(id=asset_id, project_id=proj_id, organization_id=org_id, name="Asset 1")
        act = Activity(
            id=uuid.uuid4(),
            organization_id=org_id,
            user_id=user_id,
            asset_id=asset_id,
            activity_type="solar_generation",
            activity_data={"emission_reduction_kg": 10000.0},  # Exactly 10.0 tCO2e
            captured_at=datetime.now(timezone.utc),
            submitted_at=datetime.now(timezone.utc),
        )
        session.add_all([proj, asset, act])
        await session.commit()

        service = RegistryComplianceDossierService(session)
        a64 = await service.generate_dossier(standard="ARTICLE6_4", project_id=proj_id)

        ledger = a64["a64er_unit_accounting"]
        assert ledger["verified_a64ers_total"] == 10.0
        assert ledger["adaptation_share_of_proceeds_tco2e"] == 0.5   # 5%
        assert ledger["mitigation_overall_omge_cancellation_tco2e"] == 0.2  # 2%
        assert ledger["net_tradeable_a64ers"] == 9.3  # 10.0 - 0.5 - 0.2


@pytest.mark.asyncio
async def test_gold_standard_dynamic_sectoral_sdgs():
    """Verify that Gold Standard secondary SDGs adapt dynamically to project sector."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()

    async with factory() as session:
        reg_id = uuid.uuid4()
        reg = MethodologyRegistry(id=reg_id, code=f"GS_{uuid.uuid4().hex[:4]}", name="Gold Standard Registry")
        session.add(reg)

        # 1. Clean Cooking Sector
        sec_cook_id = uuid.uuid4()
        meth_cook_id = uuid.uuid4()
        proj_cook_id = uuid.uuid4()
        sec_cook = MethodologyFamily(id=sec_cook_id, code=f"COOK_{uuid.uuid4().hex[:4]}", name="Clean Cooking")
        meth_cook = Methodology(id=meth_cook_id, code=f"VMR0006_{uuid.uuid4().hex[:4]}", name="Cookstoves", registry_id=reg_id, family_id=sec_cook_id)
        proj_cook = Project(id=proj_cook_id, name="Cook Project", sector_id=sec_cook_id, methodology_id=meth_cook_id, country="Nigeria")
        session.add_all([sec_cook, meth_cook, proj_cook])

        # 2. EV Mobility Sector
        sec_ev_id = uuid.uuid4()
        meth_ev_id = uuid.uuid4()
        proj_ev_id = uuid.uuid4()
        sec_ev = MethodologyFamily(id=sec_ev_id, code=f"EV_{uuid.uuid4().hex[:4]}", name="Electric Mobility")
        meth_ev = Methodology(id=meth_ev_id, code=f"AMSEV_{uuid.uuid4().hex[:4]}", name="EV Methodology", registry_id=reg_id, family_id=sec_ev_id)
        proj_ev = Project(id=proj_ev_id, name="EV Project", sector_id=sec_ev_id, methodology_id=meth_ev_id, country="Nigeria")
        session.add_all([sec_ev, meth_ev, proj_ev])

        # 3. Biochar Sector
        sec_bio_id = uuid.uuid4()
        meth_bio_id = uuid.uuid4()
        proj_bio_id = uuid.uuid4()
        sec_bio = MethodologyFamily(id=sec_bio_id, code=f"BIOCHAR_{uuid.uuid4().hex[:4]}", name="Biochar Sequestration")
        meth_bio = Methodology(id=meth_bio_id, code=f"VM0044_{uuid.uuid4().hex[:4]}", name="Biochar Method", registry_id=reg_id, family_id=sec_bio_id)
        proj_bio = Project(id=proj_bio_id, name="Biochar Project", sector_id=sec_bio_id, methodology_id=meth_bio_id, country="Nigeria")
        session.add_all([sec_bio, meth_bio, proj_bio])

        await session.commit()

        service = RegistryComplianceDossierService(session)

        # Verify Cookstove SDGs: SDG 13 + SDG 3 (Health) + SDG 7 (Clean Energy)
        gs_cook = await service.generate_dossier(standard="GOLD_STANDARD", project_id=proj_cook_id)
        assert "sdg_13_climate_action" in gs_cook["sdg_impact_matrix"]
        assert "sdg_3_good_health" in gs_cook["sdg_impact_matrix"]
        assert "sdg_7_affordable_clean_energy" in gs_cook["sdg_impact_matrix"]

        # Verify EV SDGs: SDG 13 + SDG 11 (Sustainable Cities) + SDG 7 (Clean Energy)
        gs_ev = await service.generate_dossier(standard="GOLD_STANDARD", project_id=proj_ev_id)
        assert "sdg_13_climate_action" in gs_ev["sdg_impact_matrix"]
        assert "sdg_11_sustainable_cities" in gs_ev["sdg_impact_matrix"]

        # Verify Biochar SDGs: SDG 13 + SDG 15 (Life on Land) + SDG 2 (Zero Hunger)
        gs_bio = await service.generate_dossier(standard="GOLD_STANDARD", project_id=proj_bio_id)
        assert "sdg_13_climate_action" in gs_bio["sdg_impact_matrix"]
        assert "sdg_15_life_on_land" in gs_bio["sdg_impact_matrix"]
        assert "sdg_2_zero_hunger" in gs_bio["sdg_impact_matrix"]


@pytest.mark.asyncio
async def test_configurable_buffer_and_benefit_sharing():
    """Verify that custom baseline parameters override defaults for risk buffers and community revenue share."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    proj_id = uuid.uuid4()

    async with factory() as session:
        proj = Project(
            id=proj_id,
            name=f"Configurable Project {uuid.uuid4().hex[:6]}",
            country="Nigeria",
            baseline_parameters={
                "community_benefit_pct": 25.0,  # Custom 25% community share
                "buffer_pct": 18.5,             # Custom 18.5% risk buffer
                "local_employment_count": 42,
            },
        )
        session.add(proj)
        await session.commit()

        service = RegistryComplianceDossierService(session)

        nccc = await service.generate_dossier(standard="NCCC", project_id=proj_id)
        assert nccc["regulatory_compliance_sections"]["section_3_benefit_sharing_and_social_impact"]["community_benefit_allocation_pct"] == 25.0
        assert nccc["regulatory_compliance_sections"]["section_3_benefit_sharing_and_social_impact"]["local_employment_count"] == 42

        verra = await service.generate_dossier(standard="VERRA", project_id=proj_id)
        assert verra["project_description_sections"]["section_2_safeguards_and_esg"]["non_permanence_risk_buffer_pct"] == 18.5


@pytest.mark.asyncio
async def test_package_builder_determinism_and_hash_reproducibility():
    """Verify that generating a package for an identical project state produces identical manifest digests."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    proj_id = uuid.uuid4()
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    asset_id = uuid.uuid4()

    async with factory() as session:
        proj = Project(id=proj_id, name=f"Repro Project {uuid.uuid4().hex[:6]}", organization_id=org_id, country="Nigeria")
        asset = Asset(id=asset_id, project_id=proj_id, organization_id=org_id, name="Solar 1")
        act = Activity(
            id=uuid.uuid4(),
            organization_id=org_id,
            user_id=user_id,
            asset_id=asset_id,
            activity_type="solar_generation",
            activity_data={"emission_reduction_kg": 5000.0},
            captured_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            submitted_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        session.add_all([proj, asset, act])
        await session.commit()

        builder = ComprehensivePackageBuilder(session)
        fixed_time = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Run 1
        zip_bytes_1, filename_1, manifest_1 = await builder.build_package_zip(project_id=proj_id, standard="VERRA", timestamp=fixed_time)
        # Run 2
        zip_bytes_2, filename_2, manifest_2 = await builder.build_package_zip(project_id=proj_id, standard="VERRA", timestamp=fixed_time)

        # Verify all deterministic internal data, lineage, and metadata files have identical SHA-256
        files1_map = {f["path"]: f["sha256"] for f in manifest_1["files"] if not f["path"].endswith(".docx") and not f["path"].endswith("sha256_package_checksum.json")}
        files2_map = {f["path"]: f["sha256"] for f in manifest_2["files"] if not f["path"].endswith(".docx") and not f["path"].endswith("sha256_package_checksum.json")}
        assert len(files1_map) >= 15
        assert files1_map == files2_map



@pytest.mark.asyncio
async def test_article_6_2_invalid_state_transition_blocked():
    """Adversarial Test: Verify CA cannot precede Authorization and First Transfer."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    proj_id = uuid.uuid4()

    async with factory() as session:
        # Invalid state: corresponding_adjustment_applied is True, but first_transferred is False
        proj = Project(
            id=proj_id,
            name=f"Illegal Transition Project {uuid.uuid4().hex[:6]}",
            country="Nigeria",
            baseline_parameters={
                "article_6_authorized": False,
                "first_transferred": False,
                "corresponding_adjustment_applied": True,  # Impossible state!
            },
        )
        session.add(proj)
        await session.commit()

        service = RegistryComplianceDossierService(session)
        dossier = await service.generate_dossier(standard="ARTICLE6_2", project_id=proj_id)

        ca_status = dossier["itmo_accounting_ledger"]["corresponding_adjustment_status"]
        assert ca_status == "INVALID_STATE_CA_CANNOT_PRECEDE_FIRST_TRANSFER"
        assert dossier["itmo_accounting_ledger"]["authorization_status"] == "PENDING_AUTHORIZATION"


@pytest.mark.asyncio
async def test_itmo_authorization_endpoint_workflow():
    """Verify ITMO authorization endpoint updates baseline params, sync log, and returns sealed A6.2 dossier."""
    await _init_fallback_db()
    factory = _get_fallback_session_factory()
    proj_id = uuid.uuid4()
    org_id = uuid.uuid4()

    async with factory() as session:
        proj = Project(
            id=proj_id,
            name="ITMO Authorization Test Project",
            organization_id=org_id,
            country="Nigeria",
            baseline_parameters={"article_6_authorized": False},
        )
        session.add(proj)
        await session.commit()

        # Import endpoint directly and execute
        from app.domains.registry_integrations.api import submit_itmo_authorization, ITMOAuthorizationRequest
        from app.domains.authentication.models import User

        user = User(
            id=uuid.uuid4(),
            email="auth_officer@verifield.io",
            role="ORG_ADMIN",
            organization_id=org_id,
            is_active=True,
        )

        req = ITMOAuthorizationRequest(
            project_id=proj_id,
            acquiring_party="Swiss Federal Office for the Environment (FOEN)",
            authorized_use_scope="NDC Achievement",
        )

        res = await submit_itmo_authorization(data=req, db=session, current_user=user)

        assert res["status"] == "AUTHORIZED"
        assert res["acquiring_party"] == "Swiss Federal Office for the Environment (FOEN)"
        assert "ITMO-NGA" in res["serial_number"]
        assert res["dossier"]["itmo_accounting_ledger"]["authorization_status"] == "AUTHORIZED"
        assert res["dossier"]["dossier_sha256"] is not None
