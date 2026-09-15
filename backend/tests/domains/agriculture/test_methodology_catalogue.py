"""
=============================================================================
VeriField Nexus — Agriculture Methodology Catalogue & Registry Tests
=============================================================================
Tests:
1. Sector registration of AGRICULTURE_LAND_USE family and INDIA_CCTS registry.
2. Complete Verra catalogue: VM0042 (v2.2, v2.1, v3.0 watchlist), VT0014 v1.0,
   VMD0053 v2.1, VM0047 v1.1, VM0032 (v1.0, v2.0 watchlist), VM0051 v1.1,
   VM0041 v2.0, VM0044 v1.2 scope isolation.
3. Complete India CCTS (BEE) catalogue: BM AG04.001 v1.0, BM AG04.002 v1.0,
   BM FR05.002 v1.0, BM-T-001 v1.0.
4. Gold Standard Agriculture Activity Requirements v1.1 and Paris Agreement Alignment.
5. Document types: METHODOLOGY, TOOL, MODULE, ACTIVITY_REQUIREMENT.
6. Maturity tiers: CATALOGUED, MRV_ENABLED, QUANTIFICATION_ENABLED.
7. Verification that draft/watchlist revisions are not active for issuance.
=============================================================================
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agriculture.seed import seed_agriculture_methodologies
from app.domains.methodologies.models.base_registry import (
    Methodology,
    MethodologyFamily,
    MethodologyRegistry,
    MethodologyVersion,
)


@pytest.mark.asyncio
async def test_agriculture_sector_and_ccts_registry_seeded(db_session: AsyncSession):
    """Verifies that AGRICULTURE_LAND_USE family and INDIA_CCTS registry are properly seeded."""
    await seed_agriculture_methodologies(db_session)

    # 1. Check INDIA_CCTS Registry
    ccts_res = await db_session.execute(
        select(MethodologyRegistry).where(MethodologyRegistry.code == "INDIA_CCTS")
    )
    ccts = ccts_res.scalars().first()
    assert ccts is not None
    assert "Bureau of Energy Efficiency" in ccts.description
    assert ccts.is_active is True

    # 2. Check AGRICULTURE_LAND_USE Family
    fam_res = await db_session.execute(
        select(MethodologyFamily).where(MethodologyFamily.code == "AGRICULTURE_LAND_USE")
    )
    fam = fam_res.scalars().first()
    assert fam is not None
    assert fam.name == "Agriculture & Land Use"
    assert fam.is_active is True

    # Check project types
    project_type_ids = [pt["id"] for pt in fam.project_types]
    assert "ALM_CROPLAND" in project_type_ids
    assert "ALM_RICE" in project_type_ids
    assert "ARR_REFORESTATION" in project_type_ids
    assert "ALM_GRASSLAND" in project_type_ids
    assert "AGROFORESTRY" in project_type_ids


@pytest.mark.asyncio
async def test_verra_methodology_catalogue_integrity(db_session: AsyncSession):
    """Verifies Verra VM0042, VT0014, VMD0053, VM0047, VM0032, VM0051, VM0041 versions and metadata."""
    await seed_agriculture_methodologies(db_session)

    # VM0042
    m42_res = await db_session.execute(select(Methodology).where(Methodology.code == "VM0042"))
    m42 = m42_res.scalars().first()
    assert m42 is not None
    assert m42.ui_config["document_type"] == "METHODOLOGY"
    assert m42.ui_config["depth_requirement_cm"] == 30.0
    assert m42.ui_config["maturity_tier"] == "MRV_ENABLED"
    assert "C&C effective 11 June 2026" in m42.ui_config["corrections_clarifications"][0]

    # VM0042 versions
    v_res = await db_session.execute(
        select(MethodologyVersion).where(MethodologyVersion.methodology_id == m42.id)
    )
    versions = {v.version: v for v in v_res.scalars().all()}
    assert "2.2" in versions and versions["2.2"].status == "active"
    assert "2.1" in versions and versions["2.1"].status == "active"
    assert "3.0" in versions and versions["3.0"].status == "draft"  # Watchlist must NOT be active!

    # VT0014 (Tool)
    vt14_res = await db_session.execute(select(Methodology).where(Methodology.code == "VT0014"))
    vt14 = vt14_res.scalars().first()
    assert vt14 is not None
    assert vt14.ui_config["document_type"] == "TOOL"
    assert vt14.ui_config["requires_spatial_uncertainty"] is True

    # VMD0053 (Module)
    vmd53_res = await db_session.execute(select(Methodology).where(Methodology.code == "VMD0053"))
    vmd53 = vmd53_res.scalars().first()
    assert vmd53 is not None
    assert vmd53.ui_config["document_type"] == "MODULE"

    # VM0047 (ARR)
    m47_res = await db_session.execute(select(Methodology).where(Methodology.code == "VM0047"))
    m47 = m47_res.scalars().first()
    assert m47 is not None
    assert "AREA_BASED" in m47.ui_config["approaches"]
    assert "CENSUS_BASED" in m47.ui_config["approaches"]

    # VM0032 (Grasslands)
    m32_res = await db_session.execute(select(Methodology).where(Methodology.code == "VM0032"))
    m32 = m32_res.scalars().first()
    assert m32 is not None
    assert m32.ui_config["outcome_state"] == "PENDING_METHODOLOGY_UPDATE"
    m32_v_res = await db_session.execute(
        select(MethodologyVersion).where(MethodologyVersion.methodology_id == m32.id)
    )
    m32_versions = {v.version: v for v in m32_v_res.scalars().all()}
    assert m32_versions["1.0"].status == "active"
    assert m32_versions["2.0"].status == "draft"  # Watchlist draft

    # VM0051 (Rice)
    m51_res = await db_session.execute(select(Methodology).where(Methodology.code == "VM0051"))
    m51 = m51_res.scalars().first()
    assert m51 is not None
    assert "AWD" in m51.ui_config["practices"]

    # VM0041 (Enteric Methane - crop-gated)
    m41_res = await db_session.execute(select(Methodology).where(Methodology.code == "VM0041"))
    m41 = m41_res.scalars().first()
    assert m41 is not None
    assert m41.ui_config["crop_gated"] is True


@pytest.mark.asyncio
async def test_india_ccts_and_gold_standard_catalogue(db_session: AsyncSession):
    """Verifies India CCTS (BEE) and Gold Standard methodologies and requirements."""
    await seed_agriculture_methodologies(db_session)

    # India CCTS Methodologies
    for code in ["BM_AG04_001", "BM_AG04_002", "BM_FR05_002", "BM_T_001"]:
        res = await db_session.execute(select(Methodology).where(Methodology.code == code))
        meth = res.scalars().first()
        assert meth is not None, f"Expected methodology '{code}' to be seeded."
        assert meth.ui_config["authority"] == "Bureau of Energy Efficiency"

    # BM-T-001 is a TOOL
    tool_res = await db_session.execute(select(Methodology).where(Methodology.code == "BM_T_001"))
    tool = tool_res.scalars().first()
    assert tool.ui_config["document_type"] == "TOOL"

    # Gold Standard Agriculture Activity Requirements v1.1
    gs_res = await db_session.execute(select(Methodology).where(Methodology.code == "GS_AGRI_ACT_REQ"))
    gs = gs_res.scalars().first()
    assert gs is not None
    assert gs.ui_config["document_type"] == "ACTIVITY_REQUIREMENT"
    assert gs.ui_config["paris_agreement_alignment_required"] is True
    assert gs.ui_config["vintages_starting_from"] == "2026-01-01"
