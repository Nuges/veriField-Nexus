import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.domains.biochar.vm0044_models import (
        VM0044MethodologyVersion,
        VM0044RuleDefinition,
        VM0044NormativeDependency,
    )

# ---------------------------------------------------------------------------
# Verra VM0044 v1.2 — Authoritative Constants & Stoichiometric Parameters
# Active since: 27 June 2025 | Sectoral Scope 13 Waste Handling & Disposal
# ---------------------------------------------------------------------------

VM0044_OFFICIAL_CODE = "VM0044"
VM0044_OFFICIAL_NAME = "Biochar Utilization in Soil and Non-Soil Applications"
VM0044_OFFICIAL_VERSION = "1.2"
VM0044_ACTIVE_DATE = date(2025, 6, 27)
VM0044_SECTORAL_SCOPE = "13 — Waste handling and disposal"

# VM0044 v2.0 Quarantine
VM0044_V2_QUARANTINE_NOTE = (
    "VM0044 v2.0 is UNDER DEVELOPMENT / VVB ASSESSMENT / INDEPENDENT REVIEW, "
    "NOT NORMATIVE, and NOT PRODUCTION CONFIGURED"
)

# Stoichiometric conversion: Organic Carbon (C) -> Carbon Dioxide (CO2)
# MW_CO2 / MW_C = 44 / 12 = 3.666666666666666666666666667 tCO2e / tC
# VM0044 Equation (1) strictly multiplies carbon by 44/12 to convert tonnes of C to tonnes of CO2e.
CARBON_TO_CO2_FACTOR = Decimal("44") / Decimal("12")

# Global Warming Potential of Methane (IPCC AR5 without climate-carbon feedback per VCS Standard v4.5/v4.7 Section 3.15)
GWP_CH4 = Decimal("28")

# Low Technology Process Methane Emission Factor Fe (Cornelissen et al. 2016 Table 3 default for traditional/unknown kiln)
DEFAULT_FE_LOW_TECH_CH4 = Decimal("0.049")  # tCH4 per tonne dry biochar

# Transport exemption threshold per Section 4 Condition 6 & CDM TOOL16 (distances <= 200 km are exempt)
TRANSPORT_EXEMPTION_DISTANCE_KM = 200.0

# Biochar quality & carbonization threshold (Section 4 Condition 10b for soil applications)
MAX_ELIGIBLE_MOLAR_H_C = 0.70

# Minimum soil incorporation depth for sub-surface application (Section 4 Condition 10 & Section 8.4.1)
MIN_SOIL_INCORPORATION_DEPTH_CM = 10.0

# Maximum permitted carbon loss during non-soil processing/manufacturing (Section 4 Condition 15)
MAX_NON_SOIL_CARBON_LOSS_PCT = 50.0

# Minimum biochar carbon content on a dry weight basis for non-soil applications (Section 3)
MIN_NON_SOIL_CARBON_CONTENT_PCT = 50.0

# High-technology facility minimum waste heat utilization percentage (Section 3)
MIN_WASTE_HEAT_UTILIZATION_PCT = 70.0

# Biochar utilization timeline limit (Section 4 Condition 9: utilized within one year of production)
MAX_UTILIZATION_TIMELINE_DAYS = 365

# Eligible and excluded thermochemical technologies (Section 4 Condition 1 & Footnote 7)
# Footnote 7: "the terms pyrolysis, gasification, and biomass boilers are used interchangeably."
VM0044_ELIGIBLE_THERMOCHEMICAL_TECHNOLOGIES = {
    "PYROLYSIS",
    "GASIFICATION",
    "BIOMASS_BOILER",
    "BIOMASS_BOILERS",
    "KILN",
    "RETORT",
}

VM0044_EXCLUDED_THERMOCHEMICAL_TECHNOLOGIES = {
    "TORREFACTION",
    "HYDROTHERMAL_CARBONIZATION",
    "CHARCOAL_KILN",
}

# Standardized default emission factors (CDM TOOL03, TOOL05, TOOL12)
DEFAULT_GRID_ELECTRICITY_EF_TCO2E_PER_KWH = Decimal("0.00045")  # tCO2e/kWh (0.45 kg CO2e/kWh conservative default)
DEFAULT_DIESEL_FUEL_EF_TCO2E_PER_LITRE = Decimal("0.00268")    # tCO2e/Litre (IPCC 2006 / TOOL03)
DEFAULT_ROAD_FREIGHT_EF_TCO2E_PER_TKM = Decimal("0.00012")     # tCO2e / tonne-km (TOOL12 default for heavy diesel truck)

# ---------------------------------------------------------------------------
# Table 3: Default 100-Year Permanence Adjustment Factors (PR_de,k)
# Source: VM0044 v1.2 Table 3 (Table 4AP.2 of IPCC 2019 & Woolf et al. 2021)
# Exactly 3 temperature tiers per authoritative Table 3
# ---------------------------------------------------------------------------
TABLE_3_PERMANENCE_FACTORS = {
    "HIGH_TEMP_PYROLYSIS": Decimal("0.89"),    # High temperature pyrolysis and gasification (> 600 °C)
    "MEDIUM_TEMP_PYROLYSIS": Decimal("0.80"),  # Medium temperature pyrolysis (450 - 600 °C)
    "LOW_TEMP_PYROLYSIS": Decimal("0.65"),     # Low temperature (350 - 450 °C)
}

# Separate conservative default when pyrolysis temperature is unmonitored / unknown (Section 8.2.2.2 & Footnote 21)
DEFAULT_PR_DE_LOW_TECH_UNKNOWN_TEMP = Decimal("0.56")

# ---------------------------------------------------------------------------
# Table 4: Default Values for Organic Carbon Content (FC_p,t,p)
# Source: VM0044 v1.2 Table 4 (Table 4AP.1 of IPCC 2019)
# Complete set of all 6 feedstocks across Pyrolysis and Gasification
# ---------------------------------------------------------------------------
TABLE_4_DEFAULT_FC_P = {
    "WOOD": {
        "PYROLYSIS": Decimal("0.77"),
        "GASIFICATION": Decimal("0.52"),
    },
    "HERBACEOUS": {
        "PYROLYSIS": Decimal("0.65"),
        "GASIFICATION": Decimal("0.28"),
    },
    "RICE_HUSK_STRAW": {
        "PYROLYSIS": Decimal("0.49"),
        "GASIFICATION": Decimal("0.13"),
    },
    "NUT_SHELLS_PITS": {
        "PYROLYSIS": Decimal("0.74"),
        "GASIFICATION": Decimal("0.40"),
    },
    "ANIMAL_MANURE": {
        "PYROLYSIS": Decimal("0.38"),
        "GASIFICATION": Decimal("0.09"),
    },
    "BIOSOLIDS_PAPER_SLUDGE": {
        "PYROLYSIS": Decimal("0.35"),
        "GASIFICATION": Decimal("0.07"),
    },
}

# Table 4 Feedstock Alias Normalizer
TABLE_4_FEEDSTOCK_ALIASES = {
    "WOOD": "WOOD",
    "WOOD_WASTE": "WOOD",
    "FORESTRY_RESIDUE": "WOOD",
    "HERBACEOUS": "HERBACEOUS",
    "HERBACEOUS_WASTE": "HERBACEOUS",
    "AGRICULTURAL_RESIDUE": "HERBACEOUS",
    "RICE_HUSK_STRAW": "RICE_HUSK_STRAW",
    "RICE_HUSKS_AND_RICE_STRAW": "RICE_HUSK_STRAW",
    "RICE_HUSK": "RICE_HUSK_STRAW",
    "RICE_STRAW": "RICE_HUSK_STRAW",
    "NUT_SHELLS_PITS": "NUT_SHELLS_PITS",
    "NUT_SHELLS_PITS_AND_STONES": "NUT_SHELLS_PITS",
    "NUT_SHELLS": "NUT_SHELLS_PITS",
    "COFFEE_HUSK": "HERBACEOUS",
    "ANIMAL_MANURE": "ANIMAL_MANURE",
    "MANURE": "ANIMAL_MANURE",
    "BIOSOLIDS_PAPER_SLUDGE": "BIOSOLIDS_PAPER_SLUDGE",
    "BIOSOLIDS": "BIOSOLIDS_PAPER_SLUDGE",
    "PAPER_SLUDGE": "BIOSOLIDS_PAPER_SLUDGE",
}

# ---------------------------------------------------------------------------
# Prohibited Feedstock and Application Taxonomies (Immediate Fail-Closed)
# ---------------------------------------------------------------------------
VM0044_PROHIBITED_FEEDSTOCKS = {
    "PURPOSE_GROWN_BIOMASS",
    "PURPOSE_GROWN_CROP",
    "IMPORTED_BIOMASS_CROSS_BORDER",
    "HAZARDOUS_WASTE",
    "MUNICIPAL_SOLID_WASTE_FOSSIL_MIXED",
    "TREATED_WOOD_CONTAMINATED",
}

VM0044_PROHIBITED_END_USES = {
    "COMBUSTION_FUEL",
    "ENERGY_PRODUCTION",
    "CHARCOAL_SUBSTITUTE",
    "METALLURGY_REDUCTION_AGENT",
    "ACTIVATED_CARBON_EXCESS_LOSS",
    "WETLAND_APPLICATION",
}

# ---------------------------------------------------------------------------
# Normative Rule Definitions for Verra VM0044 v1.2
# ---------------------------------------------------------------------------
VM0044_NORMATIVE_RULES: List[Dict[str, Any]] = [
    {
        "rule_id": "VM0044-AP-01",
        "section_number": "4",
        "rule_title": "Technological Scope & Excluded Processes",
        "requirement_type": "APPLICABILITY",
        "equation_reference": None,
        "is_blocking": True,
        "metadata_json": {
            "description": "Applicable to thermochemical conversion (pyrolysis, gasification, biomass boilers). Torrefaction and hydrothermal carbonization strictly excluded.",
            "sources": ["VM0044 v1.2 Section 4 Condition 1"],
        },
    },
    {
        "rule_id": "VM0044-AP-02",
        "section_number": "4",
        "rule_title": "Greenfield Facility Additionality Requirement",
        "requirement_type": "APPLICABILITY",
        "equation_reference": None,
        "is_blocking": True,
        "metadata_json": {
            "description": "Project activity must install and operate a new (greenfield) biochar production facility. Start date is first biochar production in new facility.",
            "sources": ["VM0044 v1.2 Section 4 Preamble", "FAQ Question 2"],
        },
    },
    {
        "rule_id": "VM0044-AP-03",
        "section_number": "4",
        "rule_title": "Feedstock Waste Biomass & Origin Criteria",
        "requirement_type": "APPLICABILITY",
        "equation_reference": None,
        "is_blocking": True,
        "metadata_json": {
            "description": "Purely biogenic waste biomass; purpose-grown biomass prohibited; cross-border imported biomass prohibited; baseline fate decay or burning without energy.",
            "sources": ["VM0044 v1.2 Section 4 Condition 4", "Table 1"],
        },
    },
    {
        "rule_id": "VM0044-AP-04",
        "section_number": "4",
        "rule_title": "Soil Application Restrictions & Molar H:Corg Threshold",
        "requirement_type": "APPLICABILITY",
        "equation_reference": None,
        "is_blocking": True,
        "metadata_json": {
            "description": "Soil application on land other than wetlands; subsurface incorporation to min 10cm depth or mixed with amendments if surface; H:Corg <= 0.70; IBI/EBC contaminants pass.",
            "sources": ["VM0044 v1.2 Section 4 Condition 10"],
        },
    },
    {
        "rule_id": "VM0044-AP-05",
        "section_number": "4",
        "rule_title": "Non-Soil Application Durability & High-Tech Requirement",
        "requirement_type": "APPLICABILITY",
        "equation_reference": None,
        "is_blocking": True,
        "metadata_json": {
            "description": "Eligible in durable matrices (cement, asphalt, building panels). ONLY biochar from high-technology facilities is eligible. Product lifetime evidence required; <= 50% carbon loss.",
            "sources": ["VM0044 v1.2 Section 4 Condition 11, 12, 15"],
        },
    },
    {
        "rule_id": "VM0044-AP-06",
        "section_number": "4",
        "rule_title": "Excluded End-Use Applications",
        "requirement_type": "APPLICABILITY",
        "equation_reference": None,
        "is_blocking": True,
        "metadata_json": {
            "description": "Biochar used for energy purposes, burned as fuel, or metallurgical reduction agent is strictly excluded.",
            "sources": ["VM0044 v1.2 Section 4 Condition 13, 14"],
        },
    },
    {
        "rule_id": "VM0044-AD-01",
        "section_number": "7",
        "rule_title": "Additionality Step 1 — Regulatory Surplus",
        "requirement_type": "ADDITIONALITY",
        "equation_reference": None,
        "is_blocking": True,
        "metadata_json": {
            "description": "Demonstrate regulatory surplus in accordance with VCS Standard and VCS Methodology Requirements.",
            "sources": ["VM0044 v1.2 Section 7 Step 1"],
        },
    },
    {
        "rule_id": "VM0044-AD-02",
        "section_number": "7",
        "rule_title": "Additionality Step 2 — Positive List Compliance",
        "requirement_type": "ADDITIONALITY",
        "equation_reference": None,
        "is_blocking": True,
        "metadata_json": {
            "description": "Demonstrate compliance with all Section 4 applicability conditions under the standardized activity penetration rate method (<= 5%).",
            "sources": ["VM0044 v1.2 Section 7 Step 2", "Appendix 1"],
        },
    },
    {
        "rule_id": "VM0044-AD-03",
        "section_number": "7",
        "rule_title": "Additionality Step 3 — VT0008 Investment Analysis",
        "requirement_type": "ADDITIONALITY",
        "equation_reference": None,
        "is_blocking": True,
        "metadata_json": {
            "description": "Conduct investment analysis per VT0008 Step 3 via either Option 1 (investment comparison) or Option 2 (benchmark analysis).",
            "sources": ["VM0044 v1.2 Section 7 Step 3", "VT0008 v1.0"],
        },
    },
    {
        "rule_id": "VM0044-EQ-14",
        "section_number": "8.5",
        "rule_title": "Equation (14) — Sourcing Stage Net Emission Reductions",
        "requirement_type": "QUANTIFICATION",
        "equation_reference": "Equation (14)",
        "is_blocking": True,
        "metadata_json": {
            "description": "ER_SS,y = BE_SS,y - PE_SS,y. Conservatively set to 0.0 to prevent double counting.",
            "sources": ["VM0044 v1.2 Section 8.1.1", "Section 8.2.1", "Equation 14"],
        },
    },
    {
        "rule_id": "VM0044-EQ-01",
        "section_number": "8.2.2",
        "rule_title": "Equation (1) — Production Stage Carbon Balance",
        "requirement_type": "QUANTIFICATION",
        "equation_reference": "Equation (1)",
        "is_blocking": True,
        "metadata_json": {
            "description": "ER_PS,y = sum_t [ (sum_k CC_t,k,y * 44/12) - (sum_p PE_PS,t,p,y) ].",
            "sources": ["VM0044 v1.2 Section 8.2.2 Equation 1"],
        },
    },
    {
        "rule_id": "VM0044-EQ-02",
        "section_number": "8.2.2.1",
        "rule_title": "Equation (2) — Organic Carbon Content for High-Tech Facilities",
        "requirement_type": "QUANTIFICATION",
        "equation_reference": "Equation (2)",
        "is_blocking": True,
        "metadata_json": {
            "description": "CC_t,k,y = sum_p (M_t,k,p,y * FC_p,t,p * PR_de,k). Lab analysis required for FC; Table 3 for PR_de.",
            "sources": ["VM0044 v1.2 Section 8.2.2.1 Equation 2", "Table 3"],
        },
    },
    {
        "rule_id": "VM0044-EQ-03",
        "section_number": "8.2.2.1",
        "rule_title": "Equation (3) — Production Project Emissions for High-Tech Facilities",
        "requirement_type": "QUANTIFICATION",
        "equation_reference": "Equation (3)",
        "is_blocking": True,
        "metadata_json": {
            "description": "PE_PS,p,y = (PE_D,p,y + PE_P,p,y + PE_C,p,y) * (M_allocated / M_total). PE_P = 0 for high tech.",
            "sources": ["VM0044 v1.2 Section 8.2.2.1 Equation 3"],
        },
    },
    {
        "rule_id": "VM0044-EQ-04",
        "section_number": "8.2.2.1",
        "rule_title": "Equation (4) — Feedstock Pre-treatment Emissions",
        "requirement_type": "QUANTIFICATION",
        "equation_reference": "Equation (4)",
        "is_blocking": True,
        "metadata_json": {
            "description": "PE_D,p,y = PE_DE,p,y + PE_DF,p,y. Grid electricity per TOOL05, fossil fuel per TOOL03.",
            "sources": ["VM0044 v1.2 Section 8.2.2.1 Equation 4"],
        },
    },
    {
        "rule_id": "VM0044-EQ-05",
        "section_number": "8.2.2.1",
        "rule_title": "Equation (5) — Pyrolysis Auxiliary Energy Emissions",
        "requirement_type": "QUANTIFICATION",
        "equation_reference": "Equation (5)",
        "is_blocking": True,
        "metadata_json": {
            "description": "PE_C,p,y = PE_CE,p,y + PE_CF,p,y. Grid electricity per TOOL05, fossil fuel per TOOL03.",
            "sources": ["VM0044 v1.2 Section 8.2.2.1 Equation 5"],
        },
    },
    {
        "rule_id": "VM0044-EQ-06",
        "section_number": "8.2.2.2",
        "rule_title": "Equation (6) — Organic Carbon Content for Low-Tech Facilities",
        "requirement_type": "QUANTIFICATION",
        "equation_reference": "Equation (6)",
        "is_blocking": True,
        "metadata_json": {
            "description": "CC_t,k,y = sum_p (M_t,k,p,y * FC_p,t,p * PR_de,k). Table 4 defaults for FC; 0.56 default for PR_de if unmonitored.",
            "sources": ["VM0044 v1.2 Section 8.2.2.2 Equation 6", "Table 4"],
        },
    },
    {
        "rule_id": "VM0044-EQ-09",
        "section_number": "8.2.2.2",
        "rule_title": "Equation (9) — Conversion Process Methane Emissions for Low-Tech Facilities",
        "requirement_type": "QUANTIFICATION",
        "equation_reference": "Equation (9)",
        "is_blocking": True,
        "metadata_json": {
            "description": "PE_P,p,y = sum_t sum_k (Fe * GWP_CH4 * M_t,k,p,y). Fe = 0.049 tCH4/t biochar, GWP_CH4 = 28.",
            "sources": ["VM0044 v1.2 Section 8.2.2.2 Equation 9"],
        },
    },
    {
        "rule_id": "VM0044-EQ-11",
        "section_number": "8.2.3",
        "rule_title": "Equation (11) — Application Stage Emissions",
        "requirement_type": "QUANTIFICATION",
        "equation_reference": "Equation (11)",
        "is_blocking": True,
        "metadata_json": {
            "description": "PE_AS,y = sum_t sum_k (E_P,t,k,y + E_ap,t,k,y). Field utilization E_ap = 0.0.",
            "sources": ["VM0044 v1.2 Section 8.2.3 Equation 11"],
        },
    },
    {
        "rule_id": "VM0044-EQ-12",
        "section_number": "8.2.3",
        "rule_title": "Equation (12) — Biochar Mechanical Processing Emissions",
        "requirement_type": "QUANTIFICATION",
        "equation_reference": "Equation (12)",
        "is_blocking": True,
        "metadata_json": {
            "description": "E_P,k,y = PE_PE,k,y + PE_PF,k,y. Electricity per TOOL05, fossil fuel per TOOL03.",
            "sources": ["VM0044 v1.2 Section 8.2.3 Equation 12"],
        },
    },
    {
        "rule_id": "VM0044-EQ-13",
        "section_number": "8.3",
        "rule_title": "Equation (13) — Total Leakage Emissions",
        "requirement_type": "LEAKAGE",
        "equation_reference": "Equation (13)",
        "is_blocking": True,
        "metadata_json": {
            "description": "LE_y = LE_as,y + LE_bd,y + LE_ts,y + LE_tap,y. Transport > 200 km calculated per TOOL12; <= 200 km is 0.0.",
            "sources": ["VM0044 v1.2 Section 8.3 Equation 13", "TOOL12", "TOOL16"],
        },
    },
    {
        "rule_id": "VM0044-AP-07",
        "section_number": "4",
        "rule_title": "One-Year Biochar Utilization Rule",
        "requirement_type": "APPLICABILITY",
        "equation_reference": None,
        "is_blocking": True,
        "metadata_json": {
            "description": "Biochar must be utilized in soil or non-soil applications within one calendar year of its production to prevent pre-application decay.",
            "sources": ["VM0044 v1.2 Section 4 Condition 9"],
        },
    },
    {
        "rule_id": "VM0044-EQ-15",
        "section_number": "8.5",
        "rule_title": "Equation (15) — Master Net GHG Emission Reductions and Removals",
        "requirement_type": "QUANTIFICATION",
        "equation_reference": "Equation (15)",
        "is_blocking": True,
        "metadata_json": {
            "description": "ER_y = ER_SS,y + ER_PS,y - PE_AS,y - LE_y. Calculates net GHG emission reductions and removals per VM0044 Equation 15. No methodology uncertainty deduction in VM0044.",
            "sources": ["VM0044 v1.2 Section 8.5 Equation 15"],
        },
    },
]

# ---------------------------------------------------------------------------
# External Normative Dependencies
# ---------------------------------------------------------------------------
VM0044_NORMATIVE_DEPENDENCIES: List[Dict[str, Any]] = [
    {
        "code": "VCS_STANDARD_V4_7",
        "title": "Verified Carbon Standard (VCS) Program Standard v4.7",
        "version": "4.7",
        "document_type": "STANDARD",
        "effective_date": date(2024, 1, 17),
        "source_reference": "https://verra.org/programs/verified-carbon-standard/",
        "checksum_hash": None,
    },
    {
        "code": "VCS_STANDARD_V4_5",
        "title": "Verified Carbon Standard (VCS) Program Standard v4.5",
        "version": "4.5",
        "document_type": "STANDARD",
        "effective_date": date(2023, 8, 29),
        "source_reference": "https://verra.org/programs/verified-carbon-standard/",
        "checksum_hash": None,
    },
    {
        "code": "VT0008_V1_0",
        "title": "VT0008 Additionality Assessment v1.0",
        "version": "1.0",
        "document_type": "TOOL",
        "effective_date": date(2024, 10, 14),
        "source_reference": "https://verra.org/methodologies/vt0008-additionality-assessment/",
        "checksum_hash": None,
    },
    {
        "code": "CDM_TOOL03_V3_0",
        "title": "CDM TOOL03: Tool to calculate project or leakage CO2 emissions from fossil fuel combustion v3.0",
        "version": "3.0",
        "document_type": "TOOL",
        "effective_date": date(2015, 11, 27),
        "source_reference": "https://cdm.unfccc.int/methodologies/PAmethodologies/tools/am-tool-03-v3.pdf",
        "checksum_hash": None,
    },
    {
        "code": "CDM_TOOL05_V3_0",
        "title": "CDM TOOL05: Baseline, project and/or leakage emissions from electricity consumption v3.0",
        "version": "3.0",
        "document_type": "TOOL",
        "effective_date": date(2018, 12, 14),
        "source_reference": "https://cdm.unfccc.int/methodologies/PAmethodologies/tools/am-tool-05-v3.0.pdf",
        "checksum_hash": None,
    },
    {
        "code": "CDM_TOOL12_V1_1",
        "title": "CDM TOOL12: Project and leakage emissions from transportation of freight v1.1.0",
        "version": "1.1.0",
        "document_type": "TOOL",
        "effective_date": date(2012, 7, 20),
        "source_reference": "https://cdm.unfccc.int/methodologies/PAmethodologies/tools/am-tool-12-v1.1.0.pdf",
        "checksum_hash": None,
    },
    {
        "code": "CDM_TOOL16_V4_0",
        "title": "CDM TOOL16: Project and leakage emissions from biomass v4.0",
        "version": "4.0",
        "document_type": "TOOL",
        "effective_date": date(2019, 9, 13),
        "source_reference": "https://cdm.unfccc.int/methodologies/PAmethodologies/tools/am-tool-16-v4.pdf",
        "checksum_hash": None,
    },
    {
        "code": "IPCC_2019_REFINEMENT_BIOCHAR",
        "title": "2019 Refinement to the 2006 IPCC Guidelines (Volume 4, Chapter 2, Appendix 4)",
        "version": "2019",
        "document_type": "GUIDELINE",
        "effective_date": date(2019, 5, 12),
        "source_reference": "https://www.ipcc-nggip.iges.or.jp/public/2019rf/pdf/4_Volume4/19R_V4_Ch02_Ap4_Biochar.pdf",
        "checksum_hash": None,
    },
]


async def seed_vm0044_normative_metadata(db: AsyncSession) -> Dict[str, Any]:
    """
    Idempotent seeder for Verra VM0044 v1.2 normative metadata, rules, and dependencies.
    """
    from app.domains.biochar.vm0044_models import (
        VM0044MethodologyVersion,
        VM0044RuleDefinition,
        VM0044NormativeDependency,
    )

    # 1. Methodology Version
    stmt = select(VM0044MethodologyVersion).where(
        VM0044MethodologyVersion.code == VM0044_OFFICIAL_CODE,
        VM0044MethodologyVersion.version == VM0044_OFFICIAL_VERSION,
    )
    res = await db.execute(stmt)
    version_row = res.scalar_one_or_none()

    if not version_row:
        version_row = VM0044MethodologyVersion(
            id=uuid.uuid4(),
            code=VM0044_OFFICIAL_CODE,
            name=VM0044_OFFICIAL_NAME,
            version=VM0044_OFFICIAL_VERSION,
            sectoral_scope="13",
            release_date=VM0044_ACTIVE_DATE,
            status="ACTIVE",
            mitigation_outcome="REMOVALS",
            ccp_approved=True,
            source_url="https://verra.org/methodologies/vm0044-biochar-utilization-in-soil-and-non-soil-applications-v1-2/",
            metadata_json={
                "icvcm_ccp_decision": "Approved August 2025",
                "quarantine_v2": VM0044_V2_QUARANTINE_NOTE,
            },
        )
        db.add(version_row)
        await db.flush()

    # 2. Rule Definitions
    rules_added = 0
    for r in VM0044_NORMATIVE_RULES:
        stmt_r = select(VM0044RuleDefinition).where(
            VM0044RuleDefinition.methodology_version_id == version_row.id,
            VM0044RuleDefinition.rule_id == r["rule_id"],
        )
        res_r = await db.execute(stmt_r)
        rule_row = res_r.scalar_one_or_none()
        if not rule_row:
            rule_row = VM0044RuleDefinition(
                id=uuid.uuid4(),
                methodology_version_id=version_row.id,
                rule_id=r["rule_id"],
                section_number=r["section_number"],
                rule_title=r["rule_title"],
                requirement_type=r["requirement_type"],
                equation_reference=r.get("equation_reference"),
                is_blocking=r.get("is_blocking", True),
                metadata_json=r.get("metadata_json", {}),
            )
            db.add(rule_row)
            rules_added += 1

    # 3. Normative Dependencies
    deps_added = 0
    for d in VM0044_NORMATIVE_DEPENDENCIES:
        stmt_d = select(VM0044NormativeDependency).where(
            VM0044NormativeDependency.methodology_version_id == version_row.id,
            VM0044NormativeDependency.code == d["code"],
        )
        res_d = await db.execute(stmt_d)
        dep_row = res_d.scalar_one_or_none()
        if not dep_row:
            dep_row = VM0044NormativeDependency(
                id=uuid.uuid4(),
                methodology_version_id=version_row.id,
                code=d["code"],
                title=d["title"],
                version=d["version"],
                document_type=d["document_type"],
                effective_date=d["effective_date"],
                source_reference=d.get("source_reference"),
                checksum_hash=d.get("checksum_hash"),
            )
            db.add(dep_row)
            deps_added += 1

    await db.flush()
    return {
        "methodology_version_id": str(version_row.id),
        "code": version_row.code,
        "version": version_row.version,
        "rules_added": rules_added,
        "dependencies_added": deps_added,
    }


def add_one_calendar_year(d: date) -> date:
    """
    Computes the exact one calendar-year anniversary of date d.
    Handles leap-year boundaries: 2028-02-29 -> 2029-02-28.
    """
    try:
        return d.replace(year=d.year + 1)
    except ValueError:
        # Handles Feb 29 on leap year transitioning to Feb 28 on following non-leap year
        return d.replace(year=d.year + 1, day=28)


class VCSProgramResolution(NamedTuple):
    vcs_version: str
    gwp_ch4: Decimal
    source_document: str
    source_version: str
    gwp_source: str
    resolution_reason: str


def resolve_vcs_program_version(
    requested_vcs_version: Optional[str] = None,
    project_date: Optional[date] = None,
    execution_date: Optional[date] = None,
) -> VCSProgramResolution:
    """
    Resolves the normative VCS Program version and corresponding GWP_CH4.
    - VCS Program Standard v4.7 is active under transition provisions until 1 January 2027.
      GWP_CH4 = 28 per IPCC AR5 (100-year without climate-carbon feedbacks).
    - VCS Program Standard v5.0 is effective for projects requiring v5.0 or post-2026.
    """
    if requested_vcs_version:
        req = requested_vcs_version.strip().lower()
        if "5" in req:
            return VCSProgramResolution(
                vcs_version="v5.0",
                gwp_ch4=Decimal("28"),
                source_document="VCS Program Standard",
                source_version="v5.0",
                gwp_source="IPCC AR5 (100-year without climate-carbon feedbacks)",
                resolution_reason="VCS v5.0 explicitly requested by project configuration.",
            )
        elif "4" in req:
            return VCSProgramResolution(
                vcs_version="v4.7",
                gwp_ch4=Decimal("28"),
                source_document="VCS Program Standard",
                source_version="v4.7",
                gwp_source="IPCC AR5 (100-year without climate-carbon feedbacks)",
                resolution_reason="VCS v4.7 requested under official transition provisions.",
            )

    target = execution_date or (project_date or date.today())
    if target >= date(2027, 1, 1):
        return VCSProgramResolution(
            vcs_version="v5.0",
            gwp_ch4=Decimal("28"),
            source_document="VCS Program Standard",
            source_version="v5.0",
            gwp_source="IPCC AR5 (100-year without climate-carbon feedbacks)",
            resolution_reason="Mandatory VCS v5.0 regime (effective 1 January 2027).",
        )
    return VCSProgramResolution(
        vcs_version="v4.7",
        gwp_ch4=Decimal("28"),
        source_document="VCS Program Standard",
        source_version="v4.7",
        gwp_source="IPCC AR5 (100-year without climate-carbon feedbacks)",
        resolution_reason="VCS v4.7 active under official transition provisions until 1 January 2027.",
    )


def get_default_fc_p(feedstock_name: str, process_type: str = "PYROLYSIS") -> Decimal:
    """
    Look up authoritative organic carbon content FC_p,t,p from VM0044 v1.2 Table 4.
    """
    cleaned = (
        feedstock_name.upper()
        .strip()
        .replace(" ", "_")
        .replace("-", "_")
        .replace(",", "")
    )
    norm_feed = TABLE_4_FEEDSTOCK_ALIASES.get(cleaned, "HERBACEOUS")
    norm_proc = "GASIFICATION" if "GAS" in process_type.upper() else "PYROLYSIS"
    return TABLE_4_DEFAULT_FC_P.get(norm_feed, {}).get(norm_proc, Decimal("0.65"))
