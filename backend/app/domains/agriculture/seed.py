"""
=============================================================================
VeriField Nexus — Agriculture & Land Use Methodology Catalogue Seed
=============================================================================
Authoritative methodology catalogue seed implementing exact official records:

1. Registries:
   - INDIA_CCTS: India Carbon Credit Trading Scheme — Offset Mechanism
     (Authority: Bureau of Energy Efficiency / Government of India)
   - VERRA: Verra (VCS)
   - GOLD_STANDARD: Gold Standard (GS)

2. Families:
   - AGRICULTURE_LAND_USE (Scope 14 AFOLU & Scope 15 Agriculture)

3. Verra Official Catalogue:
   - VM0042 v2.2: "Improved Agricultural Land Management" (Active, C&C 11 June 2026)
     v2.1 (Active, not retired), v3.0 (Under Development / Independent Expert Review)
   - VT0014 v1.0: "Estimating Organic Carbon Stocks Using Digital Soil Mapping" (Tool, Active, C&C 16 Oct 2025)
   - VMD0053 v2.1: "Model Calibration, Validation, and Uncertainty Guidance for Biogeochemical Modeling for Agricultural Land Management Projects" (Module, Active)
   - VM0047 v1.1: "Afforestation, Reforestation, and Revegetation" (Active, Area-based & Census-based)
   - VM0032 v1.0: "Methodology for the Adoption of Sustainable Grasslands through Adjustment of Fire and Grazing" (Active, Pending Update, C&C 16 Oct 2025), v2.0 (Under Revision / Watchlist)
   - VM0051 v1.1: "Improved Management in Rice Production Systems" (Active, broad water and crop management practices)
   - VM0041 v2.0: "Methodology for the Reduction of Enteric Methane Emissions from Ruminants through the Use of Feed Ingredients" (Active, Scope 15 Livestock, crop-gated)
   - VM0044 v1.2: "Biochar Utilization in Soil and Non-Soil Applications" (Active, Scope 13 Waste, cross-linked to Biochar family)

4. India CCTS (BEE) Catalogue:
   - BM AG04.001 v1.0: "Methane recovery from livestock and manure management at households and small farms"
   - BM AG04.002 v1.0: "Emission reduction through improved management practices in rice cultivation"
   - BM FR05.002 v1.0: "Afforestation and reforestation of lands except wetlands"
   - BM-T-001 v1.0: "Combined tool to identify the baseline scenario and demonstrate additionality" (Methodological Tool)

5. Gold Standard Catalogue:
   - Agriculture Activity Requirements v1.1 (Activity Requirement, Paris Agreement Alignment)

Idempotent: safe to run multiple times without duplicating or corrupting records.
=============================================================================
"""

import asyncio
from datetime import date, datetime, timezone
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
    Seeds or updates the Agriculture & Land Use sector and complete methodology catalogue.
    Returns counts of seeded/updated entities.
    """
    counts = {"registries": 0, "families": 0, "methodologies": 0, "versions": 0}
    now_iso = datetime.now(timezone.utc).isoformat()

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
        else:
            reg.name = name
            reg.description = description
            reg.website = website
            reg.is_active = True
            await db.flush()
        return reg

    verra = await get_or_create_registry(
        "VERRA",
        "Verra (VCS)",
        "Verified Carbon Standard",
        "https://verra.org",
    )
    gs = await get_or_create_registry(
        "GOLD_STANDARD",
        "Gold Standard (GS)",
        "Gold Standard for the Global Goals",
        "https://goldstandard.org",
    )
    india_ccts = await get_or_create_registry(
        "INDIA_CCTS",
        "India Carbon Credit Trading Scheme — Offset Mechanism",
        "Bureau of Energy Efficiency / Government of India Carbon Credit Trading Scheme (CCTS) Offset Mechanism under Ministry of Power",
        "https://beeindia.gov.in",
    )
    puro = await get_or_create_registry(
        "PURO_STANDARD",
        "Puro.earth Standard",
        "Puro.earth Standard for Engineered Carbon Removals",
        "https://puro.earth",
    )

    # ─── 2. Sector Family ───
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
                    "description": "Improved water management practices in rice cultivation including alternate wetting and drying.",
                },
                {
                    "id": "ARR_REFORESTATION",
                    "name": "Afforestation, Reforestation & Revegetation",
                    "description": "Tree planting and assisted natural regeneration across eligible non-wetland lands.",
                },
                {
                    "id": "ALM_GRASSLAND",
                    "name": "Sustainable Grassland Management",
                    "description": "Adjustment of fire and grazing regimes on grasslands.",
                },
                {
                    "id": "AGROFORESTRY",
                    "name": "Agroforestry Systems",
                    "description": "Integration of woody perennials into croplands and pastures subject to methodology screening.",
                },
            ],
        )
        db.add(agri_fam)
        await db.flush()
        counts["families"] += 1

    # Also resolve BIOCHAR family for VM0044 cross-linking
    bio_stmt = select(MethodologyFamily).where(MethodologyFamily.code == "BIOCHAR")
    bio_res = await db.execute(bio_stmt)
    biochar_fam = bio_res.scalars().first()
    biochar_fam_id = biochar_fam.id if biochar_fam else agri_fam.id

    # ─── 3. Helper for Upserting Methodologies & Versions ───
    async def upsert_methodology(
        code: str,
        name: str,
        description: str,
        registry_id,
        family_id,
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
                family_id=family_id,
                is_active=True,
                ui_config=ui_config,
                form_schema={},
                recommendation_rules={},
            )
            db.add(meth)
            await db.flush()
            counts["methodologies"] += 1
        else:
            meth.name = name
            meth.description = description
            meth.family_id = family_id
            meth.ui_config = ui_config
            meth.is_active = True
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

        return meth

    # ─── 4. Verra Official Methodology Catalogue ───

    # A. VM0042 (v2.2 active, v2.1 active, v3.0 under development)
    await upsert_methodology(
        code="VM0042",
        name="Improved Agricultural Land Management",
        description=(
            "Quantifies greenhouse gas emission reductions and carbon dioxide removals "
            "resulting from the adoption of improved agricultural land management practices "
            "(e.g., reduced tillage, cover crops, improved nutrient management, organic amendments)."
        ),
        registry_id=verra.id,
        family_id=agri_fam.id,
        ui_config={
            "official_code": "VM0042",
            "official_name": "Improved Agricultural Land Management",
            "document_type": "METHODOLOGY",
            "status": "ACTIVE",
            "sectoral_scope": "15 — Agriculture",
            "outcome": "Reductions and Removals",
            "active_since": "2025-10-21",
            "depth_requirement_cm": 30.0,
            "maturity_state": "MRV_ENABLED",
            "quantification_status": "NOT_CONFIGURED",
            "fail_closed": True,
            "corrections_clarifications": [
                "Mandatory Corrections and Clarifications effective 11 June 2026 applied"
            ],
            "official_source_url": "https://verra.org/methodologies/vm0042-improved-agricultural-land-management/",
            "last_verified_at": now_iso,
        },
        versions_data=[
            {
                "version": "2.2",
                "status": "active",
                "release_date": date(2025, 10, 21),
                "migration_notes": "Active version with mandatory Corrections and Clarifications effective 11 June 2026.",
            },
            {
                "version": "2.1",
                "status": "active",
                "release_date": date(2023, 11, 15),
                "migration_notes": "Active previous version. Not retired.",
            },
            {
                "version": "3.0",
                "status": "draft",
                "release_date": date(2027, 1, 1),
                "migration_notes": "UNDER_DEVELOPMENT / INDEPENDENT_EXPERT_REVIEW. Strictly not selectable as an active methodology.",
            },
        ],
    )

    # B. VT0014 v1.0 (Tool - NOT a standalone project methodology)
    await upsert_methodology(
        code="VT0014",
        name="Estimating Organic Carbon Stocks Using Digital Soil Mapping",
        description=(
            "Methodological tool specifying procedures for estimating soil organic carbon (SOC) "
            "stocks using digital soil mapping techniques, combining point soil samples, environmental "
            "covariates, spatial regression modeling, and explicit spatial uncertainty mapping. "
            "Must be applied in conjunction with an applicable AFOLU methodology."
        ),
        registry_id=verra.id,
        family_id=agri_fam.id,
        ui_config={
            "official_code": "VT0014",
            "official_name": "Estimating Organic Carbon Stocks Using Digital Soil Mapping",
            "document_type": "TOOL",
            "status": "ACTIVE",
            "sectoral_scope": "14 — Agriculture, forestry, and other land use (AFOLU)",
            "active_since": "2025-08-26",
            "is_standalone_project_methodology": False,
            "maturity_state": "MRV_ENABLED",
            "corrections_clarifications": [
                "Mandatory Corrections and Clarifications effective 16 October 2025 applied"
            ],
            "requires_spatial_uncertainty": True,
            "official_source_url": "https://verra.org/methodologies/vt0014-estimating-organic-carbon-stocks-using-digital-soil-mapping/",
            "last_verified_at": now_iso,
        },
        versions_data=[
            {
                "version": "1.0",
                "status": "active",
                "release_date": date(2025, 8, 26),
                "migration_notes": "Active tool with mandatory Corrections and Clarifications effective 16 October 2025.",
            },
        ],
    )

    # C. VMD0053 v2.1 (Guidance Module)
    await upsert_methodology(
        code="VMD0053",
        name="Model Calibration, Validation, and Uncertainty Guidance for Biogeochemical Modeling for Agricultural Land Management Projects",
        description=(
            "Guidance module for calibrating and validating biogeochemical models (e.g. DayCent, DNDC, RothC) "
            "under VM0042 Quantification Approach 1, including parameter sensitivity, shallow-depth extrapolation rules, "
            "and uncertainty propagation."
        ),
        registry_id=verra.id,
        family_id=agri_fam.id,
        ui_config={
            "official_code": "VMD0053",
            "official_name": "Model Calibration, Validation, and Uncertainty Guidance for Biogeochemical Modeling for Agricultural Land Management Projects",
            "document_type": "MODULE",
            "status": "ACTIVE",
            "sectoral_scope": "14 — AFOLU",
            "active_since": "2025-03-25",
            "is_standalone_project_methodology": False,
            "maturity_state": "MRV_ENABLED",
            "official_source_url": "https://verra.org/methodologies/vmd0053-guidance-for-biogeochemical-modeling/",
            "last_verified_at": now_iso,
        },
        versions_data=[
            {
                "version": "2.1",
                "status": "active",
                "release_date": date(2025, 3, 25),
                "migration_notes": "Active guidance module for Quantification Approach 1 biogeochemical modeling.",
            },
        ],
    )

    # D. VM0047 v1.1 (ARR)
    await upsert_methodology(
        code="VM0047",
        name="Afforestation, Reforestation, and Revegetation",
        description=(
            "Methodology for carbon dioxide removals through establishment, restoration and assisted "
            "regeneration of forest ecosystems. Supports area-based sampling and census-based individual tree tracking. "
            "VMD0054 is applicable to area-based projects where required. Eligibility requires methodology screening."
        ),
        registry_id=verra.id,
        family_id=agri_fam.id,
        ui_config={
            "official_code": "VM0047",
            "official_name": "Afforestation, Reforestation, and Revegetation",
            "document_type": "METHODOLOGY",
            "status": "ACTIVE",
            "sectoral_scope": "14 — AFOLU",
            "outcome": "Removals",
            "active_since": "2025-05-14",
            "maturity_state": "MRV_ENABLED",
            "quantification_status": "NOT_CONFIGURED",
            "approaches": ["AREA_BASED", "CENSUS_BASED"],
            "applicable_modules": ["VMD0054"],
            "all_trees_eligible": False,
            "fail_closed": True,
            "official_source_url": "https://verra.org/methodologies/vm0047-afforestation-reforestation-and-revegetation/",
            "last_verified_at": now_iso,
        },
        versions_data=[
            {
                "version": "1.1",
                "status": "active",
                "release_date": date(2025, 5, 14),
                "migration_notes": "Active ARR methodology version supporting area-based and census-based accounting.",
            },
        ],
    )

    # E. VM0032 v1.0 & v2.0 (Sustainable Grasslands)
    await upsert_methodology(
        code="VM0032",
        name="Methodology for the Adoption of Sustainable Grasslands through Adjustment of Fire and Grazing",
        description=(
            "Methodology for the adoption of sustainable grassland management through the adjustment of fire "
            "and grazing regimes to increase soil carbon stocks and reduce non-CO2 emissions."
        ),
        registry_id=verra.id,
        family_id=agri_fam.id,
        ui_config={
            "official_code": "VM0032",
            "official_name": "Methodology for the Adoption of Sustainable Grasslands through Adjustment of Fire and Grazing",
            "document_type": "METHODOLOGY",
            "status": "ACTIVE",
            "sectoral_scope": "14 — AFOLU",
            "active_since": "2015-07-16",
            "mitigation_outcome_label_eligibility": "PENDING_METHODOLOGY_UPDATE",
            "corrections_clarifications": [
                "Mandatory Corrections and Clarifications effective 16 October 2025 applied"
            ],
            "maturity_state": "CATALOGUED",
            "official_source_url": "https://verra.org/methodologies/vm0032-adoption-of-sustainable-grasslands/",
            "last_verified_at": now_iso,
        },
        versions_data=[
            {
                "version": "1.0",
                "status": "active",
                "release_date": date(2015, 7, 16),
                "migration_notes": "Active; mitigation outcome label eligibility is PENDING_METHODOLOGY_UPDATE.",
            },
            {
                "version": "2.0",
                "status": "draft",
                "release_date": date(2026, 12, 31),
                "migration_notes": "UNDER_REVISION / WATCHLIST. Strictly NOT selectable as active.",
            },
        ],
    )

    # F. VM0051 v1.1 (Rice Production Systems)
    await upsert_methodology(
        code="VM0051",
        name="Improved Management in Rice Production Systems",
        description=(
            "Greenhouse gas emission reductions in rice cultivation systems through improved water regimes "
            "(alternate wetting and drying, shortened flooding periods, single or multiple aerations) "
            "and integrated residue and nutrient management practices. Not limited to AWD."
        ),
        registry_id=verra.id,
        family_id=agri_fam.id,
        ui_config={
            "official_code": "VM0051",
            "official_name": "Improved Management in Rice Production Systems",
            "document_type": "METHODOLOGY",
            "status": "ACTIVE",
            "sectoral_scope": "15 — Agriculture",
            "outcome": "Reductions",
            "active_since": "2026-07-14",
            "practices": [
                "AWD",
                "MULTIPLE_DRAINAGE",
                "SHORTENED_FLOODING",
                "RESIDUE_MANAGEMENT",
                "WATER_REGIME_OPTIMIZATION",
            ],
            "maturity_state": "MRV_ENABLED",
            "quantification_status": "NOT_CONFIGURED",
            "fail_closed": True,
            "official_source_url": "https://verra.org/methodologies/vm0051-improved-management-in-rice-production-systems/",
            "last_verified_at": now_iso,
        },
        versions_data=[
            {
                "version": "1.1",
                "status": "active",
                "release_date": date(2026, 7, 14),
                "migration_notes": "Active version supporting comprehensive rice water regimes and management practices.",
            },
        ],
    )

    # G. VM0041 v2.0 (Enteric Methane)
    await upsert_methodology(
        code="VM0041",
        name="Methodology for the Reduction of Enteric Methane Emissions from Ruminants through the Use of Feed Ingredients",
        description=(
            "Quantifies greenhouse gas emission reductions from enteric fermentation in dairy and beef cattle "
            "through the utilization of approved feed additives and dietary ingredients."
        ),
        registry_id=verra.id,
        family_id=agri_fam.id,
        ui_config={
            "official_code": "VM0041",
            "official_name": "Methodology for the Reduction of Enteric Methane Emissions from Ruminants through the Use of Feed Ingredients",
            "document_type": "METHODOLOGY",
            "status": "ACTIVE",
            "sectoral_scope": "15 — Livestock and manure management",
            "outcome": "Reductions",
            "active_since": "2021-12-21",
            "crop_gated": True,
            "applicable_activities": ["LIVESTOCK_RUMINANT_FEED"],
            "maturity_state": "CATALOGUED",
            "notes": "Gated: not exposed to crop-only agricultural projects unless livestock activity is configured.",
            "official_source_url": "https://verra.org/methodologies/vm0041-reduction-of-enteric-methane-emissions/",
            "last_verified_at": now_iso,
        },
        versions_data=[
            {
                "version": "2.0",
                "status": "active",
                "release_date": date(2021, 12, 21),
                "migration_notes": "Active livestock feed methodology.",
            },
        ],
    )

    # H. VM0044 v1.2 (Biochar Utilization - Scope 13 Waste)
    await upsert_methodology(
        code="VM0044",
        name="Biochar Utilization in Soil and Non-Soil Applications",
        description=(
            "Quantifies greenhouse gas emission reductions and carbon dioxide removals from the production "
            "and utilization of biochar. Governed under Scope 13 Waste handling and disposal; cross-linked "
            "to agricultural projects as an approved soil amendment."
        ),
        registry_id=verra.id,
        family_id=biochar_fam_id,
        ui_config={
            "official_code": "VM0044",
            "official_name": "Biochar Utilization in Soil and Non-Soil Applications",
            "document_type": "METHODOLOGY",
            "status": "ACTIVE",
            "sectoral_scope": "13 — Waste handling and disposal",
            "outcome": "Removals",
            "active_since": "2025-06-27",
            "maturity_state": "MRV_ENABLED",
            "quantification_status": "NOT_CONFIGURED",
            "notes": "Retained under Biochar family; cross-linked to agriculture as a soil amendment activity.",
            "official_source_url": "https://verra.org/methodologies/vm0044-biochar-utilization/",
            "last_verified_at": now_iso,
        },
        versions_data=[
            {
                "version": "1.2",
                "status": "active",
                "release_date": date(2025, 6, 27),
                "migration_notes": "Active version covering biochar utilization in soil and non-soil applications.",
            },
            {
                "version": "2.0",
                "status": "draft",
                "release_date": date(2027, 1, 1),
                "migration_notes": "UNDER_DEVELOPMENT / WATCHLIST. VM0044 v2.0 is currently in public consultation / under review by Verra and cannot be selected for crediting.",
            },
        ],
    )

    # I. Puro Standard Biochar Edition 2025 v2
    await upsert_methodology(
        code="PURO_BIOCHAR_2025",
        name="Puro Standard Biochar Methodology",
        description=(
            "Puro Standard Biochar Methodology Edition 2025 Version 2. "
            "Quantifies net CO2 removal and long-term durability of biochar produced from sustainable biomass sources "
            "and utilized in terrestrial soil or durable non-soil materials. Issues CORC and CORC200+."
        ),
        registry_id=puro.id,
        family_id=biochar_fam_id,
        ui_config={
            "official_code": "PURO-BIOCHAR-2025-V2",
            "official_name": "Puro Standard Biochar Methodology Edition 2025 Version 2",
            "document_type": "METHODOLOGY",
            "status": "ACTIVE",
            "credit_unit": "CORC",
            "sectoral_scope": "Engineered Carbon Removals",
            "outcome": "Removals",
            "active_since": "2025-01-01",
            "maturity_state": "MRV_ENABLED",
            "quantification_status": "NOT_CONFIGURED",
            "notes": "Accepts existing operational facilities and new facilities; verified via independent ISO 17025 lab testing.",
            "official_source_url": "https://puro.earth/biochar/",
            "last_verified_at": now_iso,
        },
        versions_data=[
            {
                "version": "Edition 2025 v2",
                "status": "active",
                "release_date": date(2025, 1, 1),
                "migration_notes": "Current active edition of Puro Standard biochar methodology.",
            }
        ],
    )

    # J. Gold Standard PARC (Under Development)
    await upsert_methodology(
        code="GS_PARC",
        name="Gold Standard Biochar Methodology (PARC / NMC 110)",
        description=(
            "Gold Standard Platform for Agriculture & Removals from Carbon (PARC / NMC 110) biochar methodology. "
            "Currently under development by Gold Standard Technical Advisory Committee."
        ),
        registry_id=gs.id,
        family_id=biochar_fam_id,
        ui_config={
            "official_code": "GS-PARC-NMC110",
            "official_name": "Gold Standard PARC Biochar Methodology",
            "document_type": "METHODOLOGY",
            "status": "UNDER_DEVELOPMENT",
            "selectable": False,
            "credit_unit": "GS-VER",
            "maturity_state": "NOT_SELECTABLE",
            "quantification_status": "NOT_CONFIGURED",
            "notes": "Under development / TAC review; not selectable for project crediting.",
            "official_source_url": "https://www.goldstandard.org/",
            "last_verified_at": now_iso,
        },
        versions_data=[
            {
                "version": "1.0_DRAFT",
                "status": "draft",
                "release_date": date(2027, 1, 1),
                "migration_notes": "UNDER_DEVELOPMENT. Draft methodology under TAC review.",
            }
        ],
    )

    # ─── 5. India CCTS (BEE / MoP) Catalogue ───

    # BM AG04.001 v1.0
    await upsert_methodology(
        code="BM_AG04_001",
        name="Methane recovery from livestock and manure management at households and small farms",
        description=(
            "Bureau of Energy Efficiency (BEE) / Government of India CCTS baseline and monitoring methodology "
            "for methane recovery from livestock and manure management at households and small farms."
        ),
        registry_id=india_ccts.id,
        family_id=agri_fam.id,
        ui_config={
            "official_code": "BM AG04.001",
            "official_name": "Methane recovery from livestock and manure management at households and small farms",
            "authority": "Bureau of Energy Efficiency / Government of India",
            "document_type": "METHODOLOGY",
            "sectoral_scope": "Agriculture",
            "publication_date": "2025-03-27",
            "maturity_state": "MRV_ENABLED",
            "official_source_url": "https://beeindia.gov.in/en/carbon-credit-trading-scheme/methodologies/bm-ag04-001",
            "last_verified_at": now_iso,
        },
        versions_data=[
            {
                "version": "1.0",
                "status": "active",
                "release_date": date(2025, 3, 27),
                "migration_notes": "Published 27 March 2025 by Bureau of Energy Efficiency / Ministry of Power.",
            },
        ],
    )

    # BM AG04.002 v1.0
    await upsert_methodology(
        code="BM_AG04_002",
        name="Emission reduction through improved management practices in rice cultivation",
        description=(
            "Bureau of Energy Efficiency (BEE) / Government of India CCTS methodology for greenhouse gas "
            "emission reductions through improved management practices in rice cultivation, including "
            "direct seeded rice (DSR) and alternate wetting and drying (AWD)."
        ),
        registry_id=india_ccts.id,
        family_id=agri_fam.id,
        ui_config={
            "official_code": "BM AG04.002",
            "official_name": "Emission reduction through improved management practices in rice cultivation",
            "authority": "Bureau of Energy Efficiency / Government of India",
            "document_type": "METHODOLOGY",
            "sectoral_scope": "Agriculture",
            "publication_date": "2026-06-30",
            "practices": ["AWD", "DIRECT_SEEDING_DSR", "WATER_MANAGEMENT"],
            "maturity_state": "MRV_ENABLED",
            "official_source_url": "https://beeindia.gov.in/en/carbon-credit-trading-scheme/methodologies/bm-ag04-002",
            "last_verified_at": now_iso,
        },
        versions_data=[
            {
                "version": "1.0",
                "status": "active",
                "release_date": date(2026, 6, 30),
                "migration_notes": "Published 30 June 2026 by Bureau of Energy Efficiency / Ministry of Power.",
            },
        ],
    )

    # BM FR05.002 v1.0
    await upsert_methodology(
        code="BM_FR05_002",
        name="Afforestation and reforestation of lands except wetlands",
        description=(
            "Bureau of Energy Efficiency (BEE) / Government of India CCTS methodology for afforestation "
            "and reforestation of lands except wetlands. Applicability to a farm or agricultural parcel "
            "must be determined through rigorous methodology screening."
        ),
        registry_id=india_ccts.id,
        family_id=agri_fam.id,
        ui_config={
            "official_code": "BM FR05.002",
            "official_name": "Afforestation and reforestation of lands except wetlands",
            "authority": "Bureau of Energy Efficiency / Government of India",
            "document_type": "METHODOLOGY",
            "sectoral_scope": "Forestry",
            "publication_date": "2025-09-08",
            "maturity_state": "MRV_ENABLED",
            "official_source_url": "https://beeindia.gov.in/en/carbon-credit-trading-scheme/methodologies/bm-fr05-002",
            "last_verified_at": now_iso,
        },
        versions_data=[
            {
                "version": "1.0",
                "status": "active",
                "release_date": date(2025, 9, 8),
                "migration_notes": "Published 8 September 2025 by Bureau of Energy Efficiency / Ministry of Power.",
            },
        ],
    )

    # BM-T-001 v1.0 (Methodological Tool)
    await upsert_methodology(
        code="BM_T_001",
        name="Combined tool to identify the baseline scenario and demonstrate additionality",
        description=(
            "Bureau of Energy Efficiency (BEE) / Government of India CCTS methodological tool to identify "
            "the baseline scenario and demonstrate additionality across project activities."
        ),
        registry_id=india_ccts.id,
        family_id=agri_fam.id,
        ui_config={
            "official_code": "BM-T-001",
            "official_name": "Combined tool to identify the baseline scenario and demonstrate additionality",
            "authority": "Bureau of Energy Efficiency / Government of India",
            "document_type": "METHODOLOGICAL_TOOL",
            "sectoral_scope": "Cross-sectoral Tool",
            "publication_date": "2025-03-27",
            "is_standalone_project_methodology": False,
            "maturity_state": "MRV_ENABLED",
            "official_source_url": "https://beeindia.gov.in/en/carbon-credit-trading-scheme/tools/bm-t-001",
            "last_verified_at": now_iso,
        },
        versions_data=[
            {
                "version": "1.0",
                "status": "active",
                "release_date": date(2025, 3, 27),
                "migration_notes": "Published 27 March 2025 by Bureau of Energy Efficiency / Ministry of Power.",
            },
        ],
    )

    # ─── 6. Gold Standard Catalogue ───

    # Gold Standard Agriculture Activity Requirements v1.1
    await upsert_methodology(
        code="GS_AGRI_ACT_REQ",
        name="Agriculture Activity Requirements",
        description=(
            "Gold Standard for the Global Goals requirements for agricultural land interventions. "
            "Defines eligibility, boundary setting, and safeguard requirements for agriculture projects. "
            "Does NOT represent a standalone carbon quantification methodology."
        ),
        registry_id=gs.id,
        family_id=agri_fam.id,
        ui_config={
            "official_code": "GS-AGR-ACT",
            "official_name": "Agriculture Activity Requirements",
            "document_type": "ACTIVITY_REQUIREMENT",
            "status": "ACTIVE",
            "sectoral_scope": "Agriculture Activity Standards",
            "release_date": "2026-07-09",
            "is_standalone_project_methodology": False,
            "maturity_state": "MRV_ENABLED",
            "paris_agreement_alignment_required": True,
            "vintages_starting_from": "2026-01-01",
            "allowed_paa_states": ["ACTIVE_PAA", "TRANSITION", "LEGACY", "PAA_REVIEW_REQUIRED"],
            "official_source_url": "https://globalgoals.goldstandard.org/activity-requirements/agriculture/",
            "notes": (
                "For GSVER vintages from 1 January 2026 onward, Paris Agreement Alignment (PAA) is mandatory. "
                "Selecting this requirement does NOT automatically confer Article 6 host-country authorization, "
                "corresponding adjustment, or automatic issuance eligibility. Fail-closed if eligibility is not established."
            ),
            "last_verified_at": now_iso,
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
