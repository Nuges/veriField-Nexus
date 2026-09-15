"""
=============================================================================
VeriField Nexus — Agriculture & Land Use Methodology Catalogue Seed
=============================================================================
Seeds the complete authoritative methodology catalogue:
1. Registries:
   - INDIA_CCTS (India Carbon Credit Trading Scheme — Bureau of Energy Efficiency)
   - Verra (VCS)
   - Gold Standard (GS)
2. Families:
   - AGRICULTURE_LAND_USE (Scope 14 AFOLU & Scope 15 Agriculture)
3. Verra Catalogue:
   - VM0042 v2.2 (Active, C&C 11 June 2026), v2.1 (Active), v3.0 (Watchlist / Draft)
   - VT0014 v1.0 (Tool, Active, C&C 16 Oct 2025)
   - VMD0053 v2.1 (Guidance Module, Active)
   - VM0047 v1.1 (ARR, Active, Area-based & Census-based)
   - VM0032 v1.0 (Grasslands, Active, Pending Update), v2.0 (Watchlist / Draft)
   - VM0051 v1.1 (Rice Systems, Active, AWD & Water Regimes)
   - VM0041 v2.0 (Enteric Methane, Active, Crop-gated)
4. India CCTS (BEE) Catalogue:
   - BM AG04.001 v1.0 (Livestock Methane Recovery)
   - BM AG04.002 v1.0 (Rice Cultivation Emission Reduction)
   - BM FR05.002 v1.0 (Afforestation & Reforestation)
   - BM-T-001 v1.0 (Tool: Baseline & Additionality)
5. Gold Standard Catalogue:
   - Agriculture Activity Requirements v1.1 (Active, Paris Agreement Alignment)

Idempotent: safe to run multiple times without duplicating records.
=============================================================================
"""

import asyncio
from datetime import date
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.methodologies.models.base_registry import (
    Methodology,
    MethodologyFamily,
    MethodologyRegistry,
    MethodologyVersion,
)


async def seed_agriculture_methodologies(db: AsyncSession) -> Dict[str, int]:
    """
    Seeds the Agriculture & Land Use sector and complete methodology catalogue.
    Returns counts of seeded entities.
    """
    counts = {"registries": 0, "families": 0, "methodologies": 0, "versions": 0}

    # ─── 1. Registries ───
    async def get_or_create_registry(code: str, name: str, description: str, website: Optional[str] = None):
        stmt = select(MethodologyRegistry).where(MethodologyRegistry.code == code)
        res = await db.execute(stmt)
        reg = res.scalars().first()
        if not reg:
            reg = MethodologyRegistry(
                code=code,
                name=name,
                description=description,
                website=website,
                is_active=True,
            )
            db.add(reg)
            await db.flush()
            counts["registries"] += 1
        return reg

    verra = await get_or_create_registry("VERRA", "Verra (VCS)", "Verified Carbon Standard", "https://verra.org")
    gs = await get_or_create_registry("GOLD_STANDARD", "Gold Standard (GS)", "Gold Standard for the Global Goals", "https://goldstandard.org")
    india_ccts = await get_or_create_registry(
        "INDIA_CCTS",
        "India Carbon Credit Trading Scheme (BEE)",
        "Bureau of Energy Efficiency (BEE) — Ministry of Power, Government of India Offset Mechanism",
        "https://beeindia.gov.in",
    )

    # ─── 2. Family ───
    fam_stmt = select(MethodologyFamily).where(MethodologyFamily.code == "AGRICULTURE_LAND_USE")
    fam_res = await db.execute(fam_stmt)
    agri_fam = fam_res.scalars().first()
    if not agri_fam:
        agri_fam = MethodologyFamily(
            code="AGRICULTURE_LAND_USE",
            name="Agriculture & Land Use",
            description=(
                "Climate methodologies covering improved agricultural land management, "
                "afforestation/reforestation, digital soil mapping, rice water management, "
                "and sustainable grazing systems."
            ),
            is_active=True,
            project_types=[
                {
                    "id": "ALM_CROPLAND",
                    "name": "Agricultural Land Management - Cropland",
                    "description": "Improved soil carbon, reduced fertilizer, cover cropping, reduced tillage.",
                },
                {
                    "id": "ALM_RICE",
                    "name": "Rice Cultivation Water Management",
                    "description": "Alternate Wetting and Drying (AWD) and intermittent flooding.",
                },
                {
                    "id": "ARR_REFORESTATION",
                    "name": "Afforestation, Reforestation & Revegetation",
                    "description": "Tree planting and assisted natural regeneration across eligible lands.",
                },
                {
                    "id": "ALM_GRASSLAND",
                    "name": "Sustainable Grassland Management",
                    "description": "Grazing management and fire regime adjustments on grasslands.",
                },
                {
                    "id": "AGROFORESTRY",
                    "name": "Agroforestry Systems",
                    "description": "Integration of woody perennials into croplands and pastures.",
                },
            ],
        )
        db.add(agri_fam)
        await db.flush()
        counts["families"] += 1

    # ─── 3. Helper for Methodologies & Versions ───
    async def upsert_methodology(
        code: str,
        name: str,
        description: str,
        registry_id,
        ui_config: dict,
        versions_data: list,
    ):
        stmt = select(Methodology).where(Methodology.code == code)
        res = await db.execute(stmt)
        meth = res.scalars().first()
        if not meth:
            meth = Methodology(
                code=code,
                name=name,
                description=description,
                registry_id=registry_id,
                family_id=agri_fam.id,
                is_active=True,
                ui_config=ui_config,
                form_schema={},
                recommendation_rules={},
            )
            db.add(meth)
            await db.flush()
            counts["methodologies"] += 1
        else:
            # Update ui_config to ensure latest metadata
            meth.ui_config = ui_config
            meth.name = name
            meth.description = description
            await db.flush()

        for v in versions_data:
            v_stmt = select(MethodologyVersion).where(
                MethodologyVersion.methodology_id == meth.id,
                MethodologyVersion.version == v["version"],
            )
            v_res = await db.execute(v_stmt)
            ver = v_res.scalars().first()
            if not ver:
                ver = MethodologyVersion(
                    methodology_id=meth.id,
                    version=v["version"],
                    status=v["status"],
                    release_date=v["release_date"],
                    migration_notes=v.get("migration_notes"),
                )
                db.add(ver)
                await db.flush()
                counts["versions"] += 1
            else:
                ver.status = v["status"]
                ver.release_date = v["release_date"]
                ver.migration_notes = v.get("migration_notes")
                await db.flush()

    # ─── 4. Verra Methodologies ───

    # VM0042 (v2.2 active, v2.1 active, v3.0 watchlist)
    await upsert_methodology(
        code="VM0042",
        name="Improved Agricultural Land Management",
        description=(
            "Quantifies greenhouse gas emission reductions and carbon removals resulting "
            "from adoption of improved agricultural land management practices (reduced tillage, "
            "cover crops, improved nutrient management, organic amendments)."
        ),
        registry_id=verra.id,
        ui_config={
            "document_type": "METHODOLOGY",
            "scope": "Scope 15 Agriculture",
            "credit_type": "REDUCTIONS_AND_REMOVALS",
            "maturity_tier": "MRV_ENABLED",
            "quantification_status": "NOT_CONFIGURED",
            "fail_closed": True,
            "corrections_clarifications": ["Mandatory C&C effective 11 June 2026 applied"],
            "depth_requirement_cm": 30.0,
        },
        versions_data=[
            {
                "version": "2.2",
                "status": "active",
                "release_date": date(2025, 10, 21),
                "migration_notes": "Active version with mandatory C&C effective 11 June 2026.",
            },
            {
                "version": "2.1",
                "status": "active",
                "release_date": date(2023, 11, 15),
                "migration_notes": "Active previous version.",
            },
            {
                "version": "3.0",
                "status": "draft",
                "release_date": date(2027, 1, 1),
                "migration_notes": "Under development / Watchlist revision. Strictly not selectable for production issuance.",
            },
        ],
    )

    # VT0014 v1.0 (Tool)
    await upsert_methodology(
        code="VT0014",
        name="Estimating Organic Carbon Stocks Using Digital Soil Mapping",
        description=(
            "Methodological tool specifying procedures for estimating soil organic carbon (SOC) "
            "stocks using digital soil mapping techniques, combining point soil samples, environmental "
            "covariates, spatial regression modeling, and explicit spatial uncertainty mapping."
        ),
        registry_id=verra.id,
        ui_config={
            "document_type": "TOOL",
            "scope": "AFOLU Tool",
            "maturity_tier": "MRV_ENABLED",
            "corrections_clarifications": ["C&C 16 Oct 2025 applied"],
            "requires_spatial_uncertainty": True,
        },
        versions_data=[
            {
                "version": "1.0",
                "status": "active",
                "release_date": date(2025, 8, 26),
                "migration_notes": "Tool for Digital Soil Mapping with explicit spatial uncertainty quantification.",
            },
        ],
    )

    # VMD0053 v2.1 (Guidance Module)
    await upsert_methodology(
        code="VMD0053",
        name="Model Calibration, Validation, and Uncertainty Guidance for Biogeochemical Modeling",
        description=(
            "Guidance module for calibrating and validating biogeochemical models (e.g. DayCent, DNDC, RothC) "
            "under VM0042 Quantification Approach 1, including parameter sensitivity and uncertainty propagation."
        ),
        registry_id=verra.id,
        ui_config={
            "document_type": "MODULE",
            "scope": "Quantification Approach 1 Guidance",
            "maturity_tier": "MRV_ENABLED",
        },
        versions_data=[
            {
                "version": "2.1",
                "status": "active",
                "release_date": date(2025, 3, 25),
                "migration_notes": "Biogeochemical model calibration and validation module.",
            },
        ],
    )

    # VM0047 v1.1 (ARR)
    await upsert_methodology(
        code="VM0047",
        name="Afforestation, Reforestation and Revegetation",
        description=(
            "Methodology for carbon removal through establishment and restoration of forest ecosystems. "
            "Supports area-based sampling and census-based individual tree tracking."
        ),
        registry_id=verra.id,
        ui_config={
            "document_type": "METHODOLOGY",
            "scope": "Scope 14 AFOLU",
            "credit_type": "REMOVALS",
            "maturity_tier": "MRV_ENABLED",
            "quantification_status": "NOT_CONFIGURED",
            "approaches": ["AREA_BASED", "CENSUS_BASED"],
        },
        versions_data=[
            {
                "version": "1.1",
                "status": "active",
                "release_date": date(2025, 5, 14),
                "migration_notes": "Active ARR methodology version.",
            },
        ],
    )

    # VM0032 v1.0 (Grasslands)
    await upsert_methodology(
        code="VM0032",
        name="Adoption of Sustainable Grasslands through Adjustment of Fire and Grazing",
        description=(
            "Applies to grassland management activities that alter fire and grazing regimes to increase "
            "soil carbon stocks and reduce non-CO2 emissions from burning."
        ),
        registry_id=verra.id,
        ui_config={
            "document_type": "METHODOLOGY",
            "scope": "Scope 14 AFOLU Grasslands",
            "outcome_state": "PENDING_METHODOLOGY_UPDATE",
            "corrections_clarifications": ["C&C 16 Oct 2025 applied"],
            "maturity_tier": "CATALOGUED",
        },
        versions_data=[
            {
                "version": "1.0",
                "status": "active",
                "release_date": date(2015, 7, 16),
                "migration_notes": "Active; pending methodology update.",
            },
            {
                "version": "2.0",
                "status": "draft",
                "release_date": date(2026, 12, 31),
                "migration_notes": "Under revision / Watchlist. Not available for production issuance.",
            },
        ],
    )

    # VM0051 v1.1 (Rice Systems)
    await upsert_methodology(
        code="VM0051",
        name="Improved Management in Rice Production Systems",
        description=(
            "Emission reductions in paddy rice cultivation via improved water regimes "
            "(alternate wetting and drying, shortened flooding, drainage) and soil management."
        ),
        registry_id=verra.id,
        ui_config={
            "document_type": "METHODOLOGY",
            "scope": "Scope 15 Agriculture Rice",
            "credit_type": "REDUCTIONS",
            "practices": ["AWD", "INTERMITTENT_FLOODING", "DRAINAGE"],
            "maturity_tier": "MRV_ENABLED",
            "quantification_status": "NOT_CONFIGURED",
        },
        versions_data=[
            {
                "version": "1.1",
                "status": "active",
                "release_date": date(2026, 7, 14),
                "migration_notes": "Active version covering AWD and water regime improvements.",
            },
        ],
    )

    # VM0041 v2.0 (Enteric Methane)
    await upsert_methodology(
        code="VM0041",
        name="Reduction of Enteric Methane Emissions from Ruminants through Use of Feed Ingredients",
        description="Reduces enteric fermentation emissions from dairy and beef cattle through feed additives.",
        registry_id=verra.id,
        ui_config={
            "document_type": "METHODOLOGY",
            "scope": "Livestock",
            "credit_type": "REDUCTIONS",
            "crop_gated": True,
            "maturity_tier": "CATALOGUED",
            "notes": "Gated: not displayed for crop-only agricultural projects.",
        },
        versions_data=[
            {
                "version": "2.0",
                "status": "active",
                "release_date": date(2024, 6, 1),
                "migration_notes": "Active livestock feed methodology.",
            },
        ],
    )

    # ─── 5. India CCTS Methodologies ───

    # BM AG04.001 v1.0
    await upsert_methodology(
        code="BM_AG04_001",
        name="Methane recovery from livestock and manure management at households and small farms",
        description=(
            "Bureau of Energy Efficiency CCTS baseline and monitoring methodology for household "
            "and small-farm biodigesters and methane recovery."
        ),
        registry_id=india_ccts.id,
        ui_config={
            "document_type": "METHODOLOGY",
            "authority": "Bureau of Energy Efficiency",
            "sector": "Agriculture",
            "maturity_tier": "MRV_ENABLED",
        },
        versions_data=[
            {
                "version": "1.0",
                "status": "active",
                "release_date": date(2025, 3, 27),
                "migration_notes": "Published 27 Mar 2025 by Bureau of Energy Efficiency.",
            },
        ],
    )

    # BM AG04.002 v1.0
    await upsert_methodology(
        code="BM_AG04_002",
        name="Emission reduction through improved management practices in rice cultivation",
        description=(
            "BEE CCTS methodology for methane emission reductions in rice cultivation using "
            "direct seeded rice (DSR) and alternate wetting and drying (AWD)."
        ),
        registry_id=india_ccts.id,
        ui_config={
            "document_type": "METHODOLOGY",
            "authority": "Bureau of Energy Efficiency",
            "sector": "Agriculture",
            "practices": ["AWD", "DIRECT_SEEDING_DSR"],
            "maturity_tier": "MRV_ENABLED",
        },
        versions_data=[
            {
                "version": "1.0",
                "status": "active",
                "release_date": date(2026, 6, 30),
                "migration_notes": "Published 30 June 2026 by Bureau of Energy Efficiency.",
            },
        ],
    )

    # BM FR05.002 v1.0
    await upsert_methodology(
        code="BM_FR05_002",
        name="Afforestation and reforestation of lands except wetlands",
        description=(
            "BEE CCTS methodology for afforestation and reforestation on degraded lands, "
            "wastelands, and agricultural boundaries."
        ),
        registry_id=india_ccts.id,
        ui_config={
            "document_type": "METHODOLOGY",
            "authority": "Bureau of Energy Efficiency",
            "sector": "Forestry",
            "maturity_tier": "MRV_ENABLED",
        },
        versions_data=[
            {
                "version": "1.0",
                "status": "active",
                "release_date": date(2025, 9, 8),
                "migration_notes": "Published 8 Sep 2025 by Bureau of Energy Efficiency.",
            },
        ],
    )

    # BM-T-001 v1.0 (Tool)
    await upsert_methodology(
        code="BM_T_001",
        name="Combined tool to identify baseline scenario and demonstrate additionality",
        description="BEE CCTS methodological tool for establishing baseline scenarios and regulatory additionality.",
        registry_id=india_ccts.id,
        ui_config={
            "document_type": "TOOL",
            "authority": "Bureau of Energy Efficiency",
            "maturity_tier": "MRV_ENABLED",
        },
        versions_data=[
            {
                "version": "1.0",
                "status": "active",
                "release_date": date(2025, 3, 27),
                "migration_notes": "Additionality tool published by BEE.",
            },
        ],
    )

    # ─── 6. Gold Standard Catalogue ───

    await upsert_methodology(
        code="GS_AGRI_ACT_REQ",
        name="Agriculture Activity Requirements",
        description=(
            "Gold Standard for the Global Goals requirements for agricultural land interventions. "
            "For crediting vintages starting 1 Jan 2026, strict Paris Agreement Alignment (PAA) is enforced."
        ),
        registry_id=gs.id,
        ui_config={
            "document_type": "ACTIVITY_REQUIREMENT",
            "paris_agreement_alignment_required": True,
            "vintages_starting_from": "2026-01-01",
            "maturity_tier": "MRV_ENABLED",
            "legacy_modules_status": "PAA_REVIEW_REQUIRED",
        },
        versions_data=[
            {
                "version": "1.1",
                "status": "active",
                "release_date": date(2026, 7, 9),
                "migration_notes": "Published 9 July 2026. Mandates Paris Agreement Alignment for post-2026 vintages.",
            },
        ],
    )

    await db.commit()
    return counts
