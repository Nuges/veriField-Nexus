"""
=============================================================================
VeriField Nexus — Authoritative Agriculture Methodology Catalogue Tests
=============================================================================
Verifies exact official names, document types, sectoral scopes, statuses,
C&C dependencies, and maturity tiers across Verra, India CCTS (BEE), and Gold Standard.

Mandatory Verification Rules:
1. Registries:
   - INDIA_CCTS: "India Carbon Credit Trading Scheme — Offset Mechanism"
     (Authority: Bureau of Energy Efficiency / Government of India)
   - VERRA: "Verra (VCS)"
   - GOLD_STANDARD: "Gold Standard (GS)"

2. Official Verra Records:
   - VM0042: "Improved Agricultural Land Management" (v2.2 active with C&C 11 June 2026,
     v2.1 active, v3.0 draft / under development).
   - VT0014: "Estimating Organic Carbon Stocks Using Digital Soil Mapping" (TOOL,
     active, C&C 16 Oct 2025, NOT standalone).
   - VMD0053: "Model Calibration, Validation, and Uncertainty Guidance for Biogeochemical Modeling for Agricultural Land Management Projects" (MODULE).
   - VM0047: "Afforestation, Reforestation, and Revegetation" (ARR, Scope 14 AFOLU, Removals, Area & Census based, VMD0054).
   - VM0032: "Methodology for the Adoption of Sustainable Grasslands through Adjustment of Fire and Grazing" (Scope 14 AFOLU, Pending Update, C&C 16 Oct 2025, v2.0 watchlist draft).
   - VM0051: "Improved Management in Rice Production Systems" (Scope 15 Agriculture, Reductions, broader practices beyond AWD).
   - VM0041: "Methodology for the Reduction of Enteric Methane Emissions from Ruminants through the Use of Feed Ingredients" (Scope 15 Livestock, crop-gated).
   - VM0044: "Biochar Utilization in Soil and Non-Soil Applications" (Scope 13 Waste, Removals, cross-linked to Biochar family).

3. Official India CCTS (BEE / MoP) Records:
   - BM AG04.001: "Methane recovery from livestock and manure management at households and small farms"
   - BM AG04.002: "Emission reduction through improved management practices in rice cultivation"
   - BM FR05.002: "Afforestation and reforestation of lands except wetlands"
   - BM-T-001: "Combined tool to identify the baseline scenario and demonstrate additionality" (METHODOLOGICAL_TOOL)

4. Official Gold Standard Record:
   - GS_AGRI_ACT_REQ: "Agriculture Activity Requirements" (ACTIVITY_REQUIREMENT, Paris Agreement Alignment mandatory for post-2026 vintages).
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
async def test_agriculture_sector_and_registries_integrity(db_session: AsyncSession):
    """Verifies official registries and sector family metadata."""
    await seed_agriculture_methodologies(db_session)

    # 1. Check INDIA_CCTS Registry
    ccts_res = await db_session.execute(
        select(MethodologyRegistry).where(MethodologyRegistry.code == "INDIA_CCTS")
    )
    ccts = ccts_res.scalars().first()
    assert ccts is not None
    assert ccts.name == "India Carbon Credit Trading Scheme — Offset Mechanism"
    assert "Bureau of Energy Efficiency" in ccts.description
    assert "Ministry of Power" in ccts.description
    assert ccts.is_active is True

    # 2. Check VERRA Registry
    verra_res = await db_session.execute(
        select(MethodologyRegistry).where(MethodologyRegistry.code == "VERRA")
    )
    verra = verra_res.scalars().first()
    assert verra is not None
    assert verra.name == "Verra (VCS)"

    # 3. Check GOLD_STANDARD Registry
    gs_res = await db_session.execute(
        select(MethodologyRegistry).where(MethodologyRegistry.code == "GOLD_STANDARD")
    )
    gs = gs_res.scalars().first()
    assert gs is not None
    assert gs.name == "Gold Standard (GS)"

    # 4. Check AGRICULTURE_LAND_USE Family
    fam_res = await db_session.execute(
        select(MethodologyFamily).where(MethodologyFamily.code == "AGRICULTURE_LAND_USE")
    )
    fam = fam_res.scalars().first()
    assert fam is not None
    assert fam.name == "Agriculture & Land Use"
    assert fam.is_active is True

    project_type_ids = [pt["id"] for pt in fam.project_types]
    assert "ALM_CROPLAND" in project_type_ids
    assert "ALM_RICE" in project_type_ids
    assert "ARR_REFORESTATION" in project_type_ids
    assert "ALM_GRASSLAND" in project_type_ids
    assert "AGROFORESTRY" in project_type_ids


@pytest.mark.asyncio
async def test_verra_methodology_catalogue_official_names_and_metadata(db_session: AsyncSession):
    """Verifies exact official names, versions, scopes, and C&Cs for all Verra records."""
    await seed_agriculture_methodologies(db_session)

    # A. VM0042
    m42_res = await db_session.execute(select(Methodology).where(Methodology.code == "VM0042"))
    m42 = m42_res.scalars().first()
    assert m42 is not None
    assert m42.name == "Improved Agricultural Land Management"
    assert m42.ui_config["document_type"] == "METHODOLOGY"
    assert m42.ui_config["sectoral_scope"] == "15 — Agriculture"
    assert m42.ui_config["outcome"] == "Reductions and Removals"
    assert m42.ui_config["depth_requirement_cm"] == 30.0
    assert m42.ui_config["maturity_state"] == "MRV_ENABLED"
    assert m42.ui_config["quantification_status"] == "NOT_CONFIGURED"
    assert any("11 June 2026" in c for c in m42.ui_config["corrections_clarifications"])

    v42_res = await db_session.execute(
        select(MethodologyVersion).where(MethodologyVersion.methodology_id == m42.id)
    )
    v42_map = {v.version: v for v in v42_res.scalars().all()}
    assert v42_map["2.2"].status == "active"
    assert v42_map["2.1"].status == "active"  # v2.1 NOT retired!
    assert v42_map["3.0"].status == "draft"   # v3.0 under development / watchlist

    # B. VT0014 (Tool, NOT standalone)
    vt14_res = await db_session.execute(select(Methodology).where(Methodology.code == "VT0014"))
    vt14 = vt14_res.scalars().first()
    assert vt14 is not None
    assert vt14.name == "Estimating Organic Carbon Stocks Using Digital Soil Mapping"
    assert vt14.ui_config["document_type"] == "TOOL"
    assert vt14.ui_config["sectoral_scope"] == "AFOLU"
    assert vt14.ui_config["is_standalone_project_methodology"] is False
    assert any("16 October 2025" in c for c in vt14.ui_config["corrections_clarifications"])

    # C. VMD0053 (Guidance Module)
    vmd53_res = await db_session.execute(select(Methodology).where(Methodology.code == "VMD0053"))
    vmd53 = vmd53_res.scalars().first()
    assert vmd53 is not None
    assert vmd53.name == "Model Calibration, Validation, and Uncertainty Guidance for Biogeochemical Modeling for Agricultural Land Management Projects"
    assert vmd53.ui_config["document_type"] == "MODULE"
    assert vmd53.ui_config["is_standalone_project_methodology"] is False

    # D. VM0047 (ARR)
    m47_res = await db_session.execute(select(Methodology).where(Methodology.code == "VM0047"))
    m47 = m47_res.scalars().first()
    assert m47 is not None
    assert m47.name == "Afforestation, Reforestation, and Revegetation"
    assert m47.ui_config["document_type"] == "METHODOLOGY"
    assert m47.ui_config["sectoral_scope"] == "14 — AFOLU"
    assert m47.ui_config["outcome"] == "Removals"
    assert "AREA_BASED" in m47.ui_config["approaches"]
    assert "CENSUS_BASED" in m47.ui_config["approaches"]
    assert "VMD0054" in m47.ui_config["applicable_modules"]
    assert m47.ui_config["all_trees_eligible"] is False

    # E. VM0032 (Adoption of Sustainable Grasslands)
    m32_res = await db_session.execute(select(Methodology).where(Methodology.code == "VM0032"))
    m32 = m32_res.scalars().first()
    assert m32 is not None
    assert m32.name == "Methodology for the Adoption of Sustainable Grasslands through Adjustment of Fire and Grazing"
    assert m32.ui_config["document_type"] == "METHODOLOGY"
    assert m32.ui_config["sectoral_scope"] == "14 — AFOLU"
    assert m32.ui_config["mitigation_outcome_label_eligibility"] == "PENDING_METHODOLOGY_UPDATE"
    assert any("16 October 2025" in c for c in m32.ui_config["corrections_clarifications"])
    v32_res = await db_session.execute(
        select(MethodologyVersion).where(MethodologyVersion.methodology_id == m32.id)
    )
    v32_map = {v.version: v for v in v32_res.scalars().all()}
    assert v32_map["1.0"].status == "active"
    assert v32_map["2.0"].status == "draft"  # Watchlist revision

    # F. VM0051 (Rice Production Systems)
    m51_res = await db_session.execute(select(Methodology).where(Methodology.code == "VM0051"))
    m51 = m51_res.scalars().first()
    assert m51 is not None
    assert m51.name == "Improved Management in Rice Production Systems"
    assert m51.ui_config["document_type"] == "METHODOLOGY"
    assert m51.ui_config["sectoral_scope"] == "15 — Agriculture"
    assert m51.ui_config["outcome"] == "Reductions"
    assert "AWD" in m51.ui_config["practices"]
    assert "MULTIPLE_DRAINAGE" in m51.ui_config["practices"]
    assert "SHORTENED_FLOODING" in m51.ui_config["practices"]

    # G. VM0041 (Enteric Methane)
    m41_res = await db_session.execute(select(Methodology).where(Methodology.code == "VM0041"))
    m41 = m41_res.scalars().first()
    assert m41 is not None
    assert m41.name == "Methodology for the Reduction of Enteric Methane Emissions from Ruminants through the Use of Feed Ingredients"
    assert m41.ui_config["document_type"] == "METHODOLOGY"
    assert m41.ui_config["sectoral_scope"] == "15 — Livestock and manure management"
    assert m41.ui_config["outcome"] == "Reductions"
    assert m41.ui_config["crop_gated"] is True

    # H. VM0044 (Biochar - Scope 13 Waste)
    m44_res = await db_session.execute(select(Methodology).where(Methodology.code == "VM0044"))
    m44 = m44_res.scalars().first()
    assert m44 is not None
    assert m44.name == "Biochar Utilization in Soil and Non-Soil Applications"
    assert m44.ui_config["document_type"] == "METHODOLOGY"
    assert m44.ui_config["sectoral_scope"] == "13 — Waste handling and disposal"
    assert m44.ui_config["outcome"] == "Removals"


@pytest.mark.asyncio
async def test_india_ccts_official_names_and_document_types(db_session: AsyncSession):
    """Verifies India CCTS (BEE / MoP) official names and document types."""
    await seed_agriculture_methodologies(db_session)

    # BM AG04.001
    res1 = await db_session.execute(select(Methodology).where(Methodology.code == "BM_AG04_001"))
    m1 = res1.scalars().first()
    assert m1 is not None
    assert m1.name == "Methane recovery from livestock and manure management at households and small farms"
    assert m1.ui_config["official_code"] == "BM AG04.001"
    assert m1.ui_config["document_type"] == "METHODOLOGY"
    assert m1.ui_config["sectoral_scope"] == "Agriculture"
    assert m1.ui_config["authority"] == "Bureau of Energy Efficiency / Government of India"

    # BM AG04.002
    res2 = await db_session.execute(select(Methodology).where(Methodology.code == "BM_AG04_002"))
    m2 = res2.scalars().first()
    assert m2 is not None
    assert m2.name == "Emission reduction through improved management practices in rice cultivation"
    assert m2.ui_config["official_code"] == "BM AG04.002"
    assert m2.ui_config["document_type"] == "METHODOLOGY"
    assert m2.ui_config["sectoral_scope"] == "Agriculture"
    assert "AWD" in m2.ui_config["practices"]
    assert "DIRECT_SEEDING_DSR" in m2.ui_config["practices"]

    # BM FR05.002
    res3 = await db_session.execute(select(Methodology).where(Methodology.code == "BM_FR05_002"))
    m3 = res3.scalars().first()
    assert m3 is not None
    assert m3.name == "Afforestation and reforestation of lands except wetlands"
    assert m3.ui_config["official_code"] == "BM FR05.002"
    assert m3.ui_config["document_type"] == "METHODOLOGY"
    assert m3.ui_config["sectoral_scope"] == "Forestry"

    # BM-T-001 (Methodological Tool)
    res_tool = await db_session.execute(select(Methodology).where(Methodology.code == "BM_T_001"))
    tool = res_tool.scalars().first()
    assert tool is not None
    assert tool.name == "Combined tool to identify the baseline scenario and demonstrate additionality"
    assert tool.ui_config["official_code"] == "BM-T-001"
    assert tool.ui_config["document_type"] == "METHODOLOGICAL_TOOL"
    assert tool.ui_config["is_standalone_project_methodology"] is False


@pytest.mark.asyncio
async def test_gold_standard_activity_requirements_and_paa(db_session: AsyncSession):
    """Verifies Gold Standard Agriculture Activity Requirements and Paris Agreement Alignment."""
    await seed_agriculture_methodologies(db_session)

    gs_res = await db_session.execute(select(Methodology).where(Methodology.code == "GS_AGRI_ACT_REQ"))
    gs = gs_res.scalars().first()
    assert gs is not None
    assert gs.name == "Agriculture Activity Requirements"
    assert gs.ui_config["official_code"] == "GS-AGR-ACT"
    assert gs.ui_config["document_type"] == "ACTIVITY_REQUIREMENT"
    assert gs.ui_config["is_standalone_project_methodology"] is False
    assert gs.ui_config["paris_agreement_alignment_required"] is True
    assert gs.ui_config["vintages_starting_from"] == "2026-01-01"
    assert "ACTIVE_PAA" in gs.ui_config["allowed_paa_states"]
    assert "PAA_REVIEW_REQUIRED" in gs.ui_config["allowed_paa_states"]


@pytest.mark.asyncio
async def test_methodology_catalogue_source_of_truth_frozen_constants(db_session: AsyncSession):
    """
    Asserts frozen official registry source-of-truth metadata, preventing
    accidental future renaming of official methodology codes, names, and scopes.
    """
    await seed_agriculture_methodologies(db_session)

    EXPECTED_REGISTRY = {
        "VM0042": {
            "name": "Improved Agricultural Land Management",
            "type": "METHODOLOGY",
            "scope": "15 — Agriculture",
        },
        "VT0014": {
            "name": "Estimating Organic Carbon Stocks Using Digital Soil Mapping",
            "type": "TOOL",
            "scope": "AFOLU",
        },
        "VMD0053": {
            "name": "Model Calibration, Validation, and Uncertainty Guidance for Biogeochemical Modeling for Agricultural Land Management Projects",
            "type": "MODULE",
            "scope": "Quantification Approach 1 Guidance",
        },
        "VM0047": {
            "name": "Afforestation, Reforestation, and Revegetation",
            "type": "METHODOLOGY",
            "scope": "14 — AFOLU",
        },
        "VM0032": {
            "name": "Methodology for the Adoption of Sustainable Grasslands through Adjustment of Fire and Grazing",
            "type": "METHODOLOGY",
            "scope": "14 — AFOLU",
        },
        "VM0051": {
            "name": "Improved Management in Rice Production Systems",
            "type": "METHODOLOGY",
            "scope": "15 — Agriculture",
        },
        "VM0041": {
            "name": "Methodology for the Reduction of Enteric Methane Emissions from Ruminants through the Use of Feed Ingredients",
            "type": "METHODOLOGY",
            "scope": "15 — Livestock and manure management",
        },
        "VM0044": {
            "name": "Biochar Utilization in Soil and Non-Soil Applications",
            "type": "METHODOLOGY",
            "scope": "13 — Waste handling and disposal",
        },
        "BM_AG04_001": {
            "name": "Methane recovery from livestock and manure management at households and small farms",
            "type": "METHODOLOGY",
            "scope": "Agriculture",
        },
        "BM_AG04_002": {
            "name": "Emission reduction through improved management practices in rice cultivation",
            "type": "METHODOLOGY",
            "scope": "Agriculture",
        },
        "BM_FR05_002": {
            "name": "Afforestation and reforestation of lands except wetlands",
            "type": "METHODOLOGY",
            "scope": "Forestry",
        },
        "BM_T_001": {
            "name": "Combined tool to identify the baseline scenario and demonstrate additionality",
            "type": "METHODOLOGICAL_TOOL",
            "scope": "Cross-sectoral Tool",
        },
        "GS_AGRI_ACT_REQ": {
            "name": "Agriculture Activity Requirements",
            "type": "ACTIVITY_REQUIREMENT",
            "scope": "Agriculture Activity Standards",
        },
    }

    for code, expected in EXPECTED_REGISTRY.items():
        stmt = select(Methodology).where(Methodology.code == code)
        res = await db_session.execute(stmt)
        record = res.scalars().first()
        assert record is not None, f"Methodology '{code}' missing from catalogue."
        assert record.name == expected["name"], f"Name mismatch for '{code}': expected '{expected['name']}', got '{record.name}'"
        assert record.ui_config["document_type"] == expected["type"], f"Type mismatch for '{code}': expected '{expected['type']}'"
        assert record.ui_config["sectoral_scope"] == expected["scope"], f"Scope mismatch for '{code}': expected '{expected['scope']}'"
