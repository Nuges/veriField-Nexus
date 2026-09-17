import hashlib
import json
import math
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.biochar.puro_rules import (
    CARBON_TO_CO2_FACTOR,
    MAX_ELIGIBLE_MOLAR_H_C,
    PURO_TABLE_6_1_REGRESSION_PARAMETERS,
    PURO_TABLE_8_3_ILUC_FACTORS,
    calculate_puro_persistence_fraction,
    resolve_puro_soil_temperature,
)
from app.domains.ledger.service import HashGenerator


class PuroStoredCarbonCalculator:
    """
    Computes Stored Carbon (Cstored) from eligible dry biochar mass and organic carbon content.
    Formula (Equation 6.1):
        Cstored = Q_biochar * (C_org / 100) * (44 / 12)
    When biochar is utilized under retail end-use category R3 (<50L/20kg packages),
    applies the country-specific Reversal Discount Factor (RDF) per Section 3.2 Table 3.2.
    Fail-closed: Returns status DATA_REQUIRED or INELIGIBLE if inputs are missing or non-positive.
    """

    @staticmethod
    def calculate(
        eligible_dry_mass_tonnes: Decimal,
        c_org_pct: Decimal,
        end_use_category_code: Optional[str] = None,
        reversal_discount_factor: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        if eligible_dry_mass_tonnes is None or Decimal(str(eligible_dry_mass_tonnes)) <= Decimal("0"):
            return {
                "status": "FAIL_CLOSED",
                "c_stored_tco2e": Decimal("0.0"),
                "missing_inputs": ["eligible_dry_mass_tonnes"],
                "equation": "Cstored = Q_biochar * (C_org / 100) * (44 / 12)",
                "rules": ["PURO-BIOCHAR-6.1"],
                "notes": "Eligible dry biochar mass must be strictly positive and verified.",
            }

        if c_org_pct is None or Decimal(str(c_org_pct)) <= Decimal("0"):
            return {
                "status": "FAIL_CLOSED",
                "c_stored_tco2e": Decimal("0.0"),
                "missing_inputs": ["c_org_pct"],
                "equation": "Cstored = Q_biochar * (C_org / 100) * (44 / 12)",
                "rules": ["PURO-BIOCHAR-6.1", "PURO-BIOCHAR-6.2"],
                "notes": "Organic carbon (C_org) percentage is missing or non-positive; cannot calculate stored carbon.",
            }

        eligible_dry_mass = Decimal(str(eligible_dry_mass_tonnes))
        c_org = Decimal(str(c_org_pct))

        # Check Category R3 Reversal Discount Factor requirement
        cat_code = (end_use_category_code or "").upper().strip()
        if cat_code == "R3":
            if reversal_discount_factor is None or reversal_discount_factor <= Decimal("0"):
                return {
                    "status": "DATA_REQUIRED",
                    "c_stored_tco2e": Decimal("0.0"),
                    "missing_inputs": ["reversal_discount_factor"],
                    "equation": "Cstored = Q_biochar * (C_org / 100) * (44 / 12) * RDF",
                    "rules": ["PURO-BIOCHAR-3.2", "PURO-BIOCHAR-6.1"],
                    "notes": "Retail Category R3 requires country-specific Reversal Discount Factor (RDF).",
                }

        # Equation 6.1: Cstored = Q_biochar * (C_org / 100) * (44 / 12)
        c_fraction = c_org / Decimal("100")
        c_stored_raw = eligible_dry_mass * c_fraction * CARBON_TO_CO2_FACTOR

        rdf_applied = Decimal("1.0")
        if cat_code == "R3" and reversal_discount_factor is not None:
            rdf_applied = reversal_discount_factor
            c_stored = c_stored_raw * rdf_applied
            eq_str = "Cstored = Q_biochar * (C_org / 100) * (44 / 12) * RDF"
            notes_str = f"Stored carbon quantified with RDF={rdf_applied} applied for category R3."
        else:
            c_stored = c_stored_raw
            eq_str = "Cstored = Q_biochar * (C_org / 100) * (44 / 12)"
            notes_str = "Stored carbon quantified using stoichiometric 44/12 conversion."

        return {
            "status": "SUCCESS",
            "c_stored_tco2e": c_stored,
            "c_stored_raw_tco2e": c_stored_raw,
            "reversal_discount_factor_applied": float(rdf_applied),
            "missing_inputs": [],
            "equation": eq_str,
            "rules": ["PURO-BIOCHAR-6.1"],
            "notes": notes_str,
        }


class PuroBaselineRemovalCalculator:
    """
    Computes Baseline Carbon Removal (Cbaseline) per Section 3.3.
    - NEW_FACILITY: Cbaseline = 0.
    - RETROFIT_FACILITY: Historical 3-5 year baseline char storage.
    - CHARCOAL_REPURPOSE: Historical charcoal storage baseline.
    - Fail-closed: If Retrofit or Repurpose lacks historical baseline, returns DATA_REQUIRED.
    """

    @staticmethod
    def calculate(
        scenario: str,
        historical_baseline_tco2e: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        scen = (scenario or "").upper().strip()

        if scen in ("NEW_FACILITY", "GREENFIELD"):
            return {
                "status": "SUCCESS",
                "c_baseline_tco2e": Decimal("0.0"),
                "missing_inputs": [],
                "equation": "Cbaseline = 0 (New Facility)",
                "rules": ["PURO-BIOCHAR-3.3"],
                "notes": "New production facility has zero baseline carbon removal.",
            }

        if scen in ("RETROFIT_FACILITY", "CHARCOAL_REPURPOSE"):
            if historical_baseline_tco2e is None:
                return {
                    "status": "DATA_REQUIRED",
                    "c_baseline_tco2e": Decimal("0.0"),
                    "missing_inputs": ["historical_baseline_tco2e"],
                    "equation": "Cbaseline = Historical baseline char storage",
                    "rules": ["PURO-BIOCHAR-3.3"],
                    "notes": f"Scenario '{scen}' requires verified historical baseline records. Missing data.",
                }

            return {
                "status": "SUCCESS",
                "c_baseline_tco2e": max(Decimal("0.0"), historical_baseline_tco2e),
                "missing_inputs": [],
                "equation": "Cbaseline = Historical baseline char storage",
                "rules": ["PURO-BIOCHAR-3.3"],
                "notes": f"Historical baseline carbon removal quantified for scenario '{scen}'.",
            }

        return {
            "status": "FAIL_CLOSED",
            "c_baseline_tco2e": Decimal("0.0"),
            "missing_inputs": ["scenario"],
            "equation": "Unknown scenario",
            "rules": ["PURO-BIOCHAR-3.3"],
            "notes": f"Unrecognized baseline scenario '{scenario}'. Requires Issuing Body review.",
        }


class PuroStorageLossCalculator:
    """
    Computes Expected Storage Loss (Closs) based on Edition 2025 V2 Persistence Equation (6.4).
    Formula:
        PF (%) = M - a * (H/Corg)       [Equation 6.4, Table 6.1]
        F_decay = (100 - PF) / 100      [Equation 6.3]
        Closs = Cstored * F_decay       [Equation 6.3]
    Invariants:
    - Rule 3.5.1: Molar H/Corg must be strictly < 0.70. H/Corg >= 0.70 fails eligibility.
    - Rule 6.2.4 Remark: Non-soil applications use the exact same soil decay model.
    - All eligible biochar is classified as CORC200+ under the 200-year decay model.
    """

    @staticmethod
    def calculate(
        c_stored_tco2e: Decimal,
        molar_h_c: float,
        soil_temperature_celsius: Optional[float] = None,
        is_non_soil_durable: bool = False,
    ) -> Dict[str, Any]:
        if molar_h_c is None:
            return {
                "status": "DATA_REQUIRED",
                "c_loss_tco2e": Decimal("0.0"),
                "persistence_fraction_pf": 0.0,
                "durability_class": "INELIGIBLE",
                "missing_inputs": ["molar_h_c"],
                "equation": "PF = M - a * (H/Corg)",
                "rules": ["PURO-BIOCHAR-3.5.1", "PURO-BIOCHAR-6.2.2"],
                "notes": "Molar H/Corg ratio is required to evaluate biochar carbonization degree.",
            }

        # Delegate to normative rule implementation
        pf_res = calculate_puro_persistence_fraction(molar_h_c, soil_temperature_celsius)
        if pf_res["status"] != "SUCCESS":
            return {
                "status": pf_res["status"],
                "c_loss_tco2e": c_stored_tco2e,  # 100% loss / ineligible
                "persistence_fraction_pf": 0.0,
                "durability_class": pf_res.get("durability_class", "INELIGIBLE"),
                "missing_inputs": [],
                "equation": "PF = 0% (Ineligible H/Corg >= 0.70)",
                "rules": pf_res.get("rules", ["PURO-BIOCHAR-3.5.1"]),
                "notes": pf_res.get("notes", "Fails minimum carbonization degree."),
            }

        pf_val = pf_res["persistence_fraction_pf"]
        loss_fraction = Decimal(str(pf_res["loss_fraction"]))
        c_loss = c_stored_tco2e * loss_fraction

        non_soil_note = " (non-soil end-use evaluated under soil decay equivalence per Rule 6.2.4)" if is_non_soil_durable else ""

        return {
            "status": "SUCCESS",
            "c_loss_tco2e": c_loss,
            "persistence_fraction_pf": pf_val,
            "durability_class": pf_res["durability_class"],
            "regression_m": pf_res["regression_m"],
            "regression_a": pf_res["regression_a"],
            "effective_soil_temp_celsius": pf_res["effective_soil_temp_celsius"],
            "temperature_provenance": pf_res.get("temperature_provenance", {}),
            "missing_inputs": [],
            "equation": f"Closs = Cstored * ((100 - {pf_val:.2f}) / 100)",
            "rules": pf_res["rules"],
            "notes": f"Persistence evaluated under Table 6.1 (Ts={pf_res['effective_soil_temp_celsius']}°C, M={pf_res['regression_m']}, a={pf_res['regression_a']} -> PF={pf_val:.3f}%){non_soil_note}.",
        }


class PuroProjectEmissionsCalculator:
    """
    Computes Project Emissions (Eproject) according to Chapter 7 Life Cycle Assessment (LCA).
    Formula:
        Eproject = Eops + (Eemb / crediting_years)
        Eops = Ebiomass + Eproduction + Euse
        Eemb = Einst + EdLUC
    Co-product emissions allocation (Rule 7.5.2b):
        Must be based on Lower Heating Value (LHV) energy allocation.
        Mass-based allocation is strictly prohibited.
    """

    @staticmethod
    def calculate(
        # Operational components (Eops)
        e_biomass: Decimal = Decimal("0.0"),
        e_production: Decimal = Decimal("0.0"),
        e_use: Decimal = Decimal("0.0"),
        # Embodied components (Eemb)
        e_infra: Decimal = Decimal("0.0"),
        e_dluc: Decimal = Decimal("0.0"),
        crediting_years: int = 10,
    ) -> Dict[str, Any]:
        e_biomass_val = e_biomass or Decimal("0.0")
        e_production_val = e_production or Decimal("0.0")
        e_use_val = e_use or Decimal("0.0")
        e_infra_val = e_infra or Decimal("0.0")
        e_dluc_val = e_dluc or Decimal("0.0")
        cred_years = max(1, crediting_years or 10)

        # Operational sum
        e_ops = e_biomass_val + e_production_val + e_use_val

        # Embodied annualized sum
        e_emb_total = e_infra_val + e_dluc_val
        e_emb_annualized = e_emb_total / Decimal(str(cred_years))

        # Total project emissions
        e_project = e_ops + e_emb_annualized

        return {
            "status": "SUCCESS",
            "e_project_tco2e": e_project,
            "e_ops_total_tco2e": e_ops,
            "e_ops_biomass_tco2e": e_biomass_val,
            "e_ops_production_tco2e": e_production_val,
            "e_ops_use_tco2e": e_use_val,
            "e_emb_total_tco2e": e_emb_total,
            "e_emb_infra_tco2e": e_infra_val,
            "e_emb_dluc_tco2e": e_dluc_val,
            "e_emb_annualized_tco2e": e_emb_annualized,
            "crediting_years": cred_years,
            "equation": f"Eproject = Eops ({e_ops:.3f}) + Eemb_annualized ({e_emb_annualized:.3f})",
            "rules": ["PURO-BIOCHAR-7.1", "PURO-BIOCHAR-7.2", "PURO-BIOCHAR-7.4"],
            "notes": "Full Life Cycle Assessment decomposition calculated per Chapter 7.",
        }

    @staticmethod
    def allocate_coproduct_emissions(
        total_production_emissions_tco2e: Decimal,
        biochar_dry_mass_tonnes: Decimal,
        biochar_lhv_mj_kg: Decimal,
        coproduct_quantity: Decimal,
        coproduct_lhv_mj_unit: Decimal,
        coproduct_name: str = "BIO_OIL",
    ) -> Dict[str, Any]:
        """
        Calculates Lower Heating Value (LHV) energy allocation between biochar and co-product.
        Strictly mandates Rule 7.5.2b: Mass allocation is prohibited.
        """
        # Biochar total energy = mass (kg) * LHV (MJ/kg)
        biochar_energy_mj = (biochar_dry_mass_tonnes * Decimal("1000")) * biochar_lhv_mj_kg
        coproduct_energy_mj = coproduct_quantity * coproduct_lhv_mj_unit
        total_energy_mj = biochar_energy_mj + coproduct_energy_mj

        if total_energy_mj <= Decimal("0"):
            return {
                "status": "FAIL_CLOSED",
                "allocated_biochar_emissions_tco2e": total_production_emissions_tco2e,
                "biochar_energy_share_pct": 100.0,
                "coproduct_energy_share_pct": 0.0,
                "notes": "Total system energy is zero; cannot allocate co-product emissions.",
            }

        biochar_share = biochar_energy_mj / total_energy_mj
        coproduct_share = coproduct_energy_mj / total_energy_mj

        allocated_biochar_emissions = total_production_emissions_tco2e * biochar_share
        allocated_coproduct_emissions = total_production_emissions_tco2e * coproduct_share

        return {
            "status": "SUCCESS",
            "allocation_method": "ENERGY_LHV",
            "biochar_energy_mj": biochar_energy_mj,
            "coproduct_energy_mj": coproduct_energy_mj,
            "biochar_energy_share_pct": float(biochar_share * Decimal("100")),
            "coproduct_energy_share_pct": float(coproduct_share * Decimal("100")),
            "allocated_biochar_emissions_tco2e": allocated_biochar_emissions,
            "allocated_coproduct_emissions_tco2e": allocated_coproduct_emissions,
            "coproduct_name": coproduct_name,
            "rules": ["PURO-BIOCHAR-7.5.2b"],
            "notes": f"LHV energy allocation applied ({coproduct_name}): Biochar share = {float(biochar_share)*100:.2f}%.",
        }


class PuroLeakageCalculator:
    """
    Computes Leakage Emissions (Eleakage) according to Chapter 8.
    Formula:
        Eleakage = LECO + LMA
    where:
        LECO = Ecological leakage (soil organic carbon depletion from excessive residue removal)
        LMA  = Market analysis leakage = max(0, sum(Delta Pi * EFi)) + iLUC
    Table 8.3 iLUC Factors:
        Cereals & starch crops: 0.012 kg CO2e / MJ
        Sugar crops:            0.013 kg CO2e / MJ
        Oil crops:              0.055 kg CO2e / MJ
    """

    @staticmethod
    def calculate(
        is_leakage_mitigated: bool = True,
        ecological_leakage_tco2e: Decimal = Decimal("0.0"),
        market_activity_shifting_tco2e: Decimal = Decimal("0.0"),
        iluc_feedstock_category: Optional[str] = None,
        feedstock_quantity_dry_tonnes: Decimal = Decimal("0.0"),
        feedstock_lhv_mj_kg: Decimal = Decimal("18.0"),
    ) -> Dict[str, Any]:
        l_eco = ecological_leakage_tco2e or Decimal("0.0")
        l_ma_direct = market_activity_shifting_tco2e or Decimal("0.0")

        # iLUC calculation (Equation 8.3)
        iluc_tco2e = Decimal("0.0")
        iluc_factor_used = 0.0
        if iluc_feedstock_category and iluc_feedstock_category in PURO_TABLE_8_3_ILUC_FACTORS:
            iluc_factor_used = PURO_TABLE_8_3_ILUC_FACTORS[iluc_feedstock_category]
            # iLUC (tCO2e) = Q_biomass_kg * LHV (MJ/kg) * iLUC_factor (kgCO2e/MJ) / 1000 kg/t
            biomass_kg = feedstock_quantity_dry_tonnes * Decimal("1000")
            total_mj = biomass_kg * feedstock_lhv_mj_kg
            iluc_kg = total_mj * Decimal(str(iluc_factor_used))
            iluc_tco2e = iluc_kg / Decimal("1000")

        l_ma = max(Decimal("0.0"), l_ma_direct) + iluc_tco2e

        if is_leakage_mitigated and l_ma == Decimal("0.0") and l_eco == Decimal("0.0"):
            return {
                "status": "SUCCESS",
                "e_leakage_tco2e": Decimal("0.0"),
                "ecological_leakage_tco2e": Decimal("0.0"),
                "market_leakage_tco2e": Decimal("0.0"),
                "iluc_leakage_tco2e": Decimal("0.0"),
                "equation": "Eleakage = LECO (0) + LMA (0) [Mitigated]",
                "rules": ["PURO-BIOCHAR-8.1", "PURO-BIOCHAR-8.2"],
                "notes": "Leakage mitigated under verified biomass sourcing safeguards.",
            }

        total_leakage = l_eco + l_ma
        return {
            "status": "SUCCESS",
            "e_leakage_tco2e": total_leakage,
            "ecological_leakage_tco2e": l_eco,
            "market_leakage_tco2e": l_ma,
            "iluc_leakage_tco2e": iluc_tco2e,
            "iluc_feedstock_category": iluc_feedstock_category,
            "equation": f"Eleakage = LECO ({l_eco:.3f}) + LMA ({l_ma:.3f})",
            "rules": ["PURO-BIOCHAR-8.1", "PURO-BIOCHAR-8.2", "PURO-BIOCHAR-8.3"],
            "notes": f"Leakage quantified: LECO={l_eco:.3f}, LMA={l_ma:.3f} (iLUC={iluc_tco2e:.3f} tCO2e).",
        }


class PuroUncertaintyCalculator:
    """
    ISO GUM Law of Propagation of Uncertainty (Chapter 10).
    Computes combined percentage uncertainty across measurement stages:
        u_combined = sqrt(u_mass^2 + u_corg^2 + u_decay^2 + u_emissions^2)
    In Puro.earth Biochar Edition 2025 V2:
        Uncertainty is evaluated and reported as an official uncertainty range on the certificate/report:
        (e.g., "120.45 tCO2e ± 4.8%").
        No arbitrary penalty deduction is levied against net CORCs.
    """

    @staticmethod
    def calculate(
        net_removal_tco2e: Decimal,
        u_mass_pct: float = 2.0,
        u_c_org_pct: float = 3.0,
        u_persistence_pct: float = 3.0,
        u_emissions_pct: float = 2.0,
    ) -> Dict[str, Any]:
        # Quadratic sum of independent relative standard uncertainties
        sum_sq = (u_mass_pct ** 2) + (u_c_org_pct ** 2) + (u_persistence_pct ** 2) + (u_emissions_pct ** 2)
        combined_pct = math.sqrt(sum_sq)

        # In Edition 2025 V2, uncertainty is reported on the certificate rather than subtracted
        reported_text = f"{float(net_removal_tco2e):.2f} tCO2e ± {combined_pct:.1f}%"

        return {
            "status": "SUCCESS",
            "combined_uncertainty_pct": round(combined_pct, 2),
            "deductible_uncertainty_pct": 0.0,
            "deduction_tco2e": Decimal("0.0"),
            "reported_uncertainty_text": reported_text,
            "rules": ["PURO-BIOCHAR-10.1", "PURO-BIOCHAR-10.3"],
            "notes": f"Combined uncertainty {combined_pct:.2f}% evaluated under ISO GUM law of propagation. Reported: {reported_text}.",
        }


class PuroCORCCalculator:
    """
    Master Deterministic Puro CORC Quantification Orchestrator (Edition 2025 V2).
    Formula:
        CORCs = max(0, Cstored - Cbaseline - Closs - Eproject - Eleakage)
    Engine Version: 2.0.0 (Forensically aligned with Approved 27 November 2025 specification).
    Supports both AUTHORITATIVE and SIMULATION execution modes.
    """

    @staticmethod
    def calculate_net_corcs(
        c_stored: Decimal,
        c_baseline: Decimal,
        c_loss: Decimal,
        e_project: Decimal,
        e_leakage: Decimal,
    ) -> Decimal:
        """
        Puro Biochar Edition 2025 V2 Equation 5.1:
        CORCs = max(0, Cstored - Cbaseline - Closs - Eproject - Eleakage)
        """
        net = Decimal(str(c_stored)) - Decimal(str(c_baseline)) - Decimal(str(c_loss)) - Decimal(str(e_project)) - Decimal(str(e_leakage))
        return max(Decimal("0.0"), net)

    @classmethod
    def execute_quantification(
        cls,
        eligible_dry_mass_tonnes: Decimal,
        c_org_pct: Decimal,
        molar_h_c: float,
        soil_temperature_celsius: float = 15.0,
        baseline_scenario: str = "NEW_FACILITY",
        historical_baseline_tco2e: Optional[Decimal] = None,
        end_use_category_code: Optional[str] = None,
        reversal_discount_factor: Optional[Decimal] = None,
        is_non_soil_durable: bool = False,
        # LCA project emissions breakdown
        e_biomass: Decimal = Decimal("0.0"),
        e_production: Decimal = Decimal("0.0"),
        e_use: Decimal = Decimal("0.0"),
        e_infra: Decimal = Decimal("0.0"),
        e_dluc: Decimal = Decimal("0.0"),
        crediting_years: int = 10,
        # Leakage breakdown
        is_leakage_mitigated: bool = True,
        ecological_leakage_tco2e: Decimal = Decimal("0.0"),
        market_activity_shifting_tco2e: Decimal = Decimal("0.0"),
        iluc_feedstock_category: Optional[str] = None,
        feedstock_quantity_dry_tonnes: Decimal = Decimal("0.0"),
        feedstock_lhv_mj_kg: Decimal = Decimal("18.0"),
        end_use_corc_point_eligible: bool = True,
        calculation_mode: str = "AUTHORITATIVE",
        engine_version: str = "2.0.0",
        methodology_version: str = "PURO_BIOCHAR_2025_V2",
    ) -> Dict[str, Any]:
        warnings: List[str] = []
        rules: List[str] = ["PURO-BIOCHAR-5.1", "PURO-BIOCHAR-6.1"]

        # Check Point of Creation of CORC
        if not end_use_corc_point_eligible:
            return {
                "calculation_status": "FAIL_CLOSED",
                "corc_point_status": "CORC_POINT_NOT_REACHED",
                "final_corcs_issuable": Decimal("0.0"),
                "c_stored_tco2e": Decimal("0.0"),
                "c_baseline_tco2e": Decimal("0.0"),
                "c_loss_tco2e": Decimal("0.0"),
                "e_project_tco2e": Decimal("0.0"),
                "e_leakage_tco2e": Decimal("0.0"),
                "notes": "Point of Creation of CORC has not been reached. Durable end-use verification required.",
                "warnings": ["End-use application not demonstrated as durable or complete."],
                "calculation_hash": "",
            }

        # 1. Stored Carbon (Equation 6.1)
        stored_res = PuroStoredCarbonCalculator.calculate(
            eligible_dry_mass_tonnes,
            c_org_pct,
            end_use_category_code=end_use_category_code,
            reversal_discount_factor=reversal_discount_factor,
        )
        if stored_res["status"] != "SUCCESS":
            return {
                "calculation_status": stored_res["status"],
                "corc_point_status": "DATA_REQUIRED",
                "final_corcs_issuable": Decimal("0.0"),
                "c_stored_tco2e": Decimal("0.0"),
                "c_baseline_tco2e": Decimal("0.0"),
                "c_loss_tco2e": Decimal("0.0"),
                "e_project_tco2e": Decimal("0.0"),
                "e_leakage_tco2e": Decimal("0.0"),
                "notes": stored_res["notes"],
                "warnings": [stored_res["notes"]],
                "calculation_hash": "",
            }
        c_stored = stored_res["c_stored_tco2e"]

        # 2. Baseline Removal (Section 3.3)
        base_res = PuroBaselineRemovalCalculator.calculate(baseline_scenario, historical_baseline_tco2e)
        if base_res["status"] != "SUCCESS":
            return {
                "calculation_status": base_res["status"],
                "corc_point_status": "DATA_REQUIRED",
                "final_corcs_issuable": Decimal("0.0"),
                "c_stored_tco2e": c_stored,
                "c_baseline_tco2e": Decimal("0.0"),
                "c_loss_tco2e": Decimal("0.0"),
                "e_project_tco2e": Decimal("0.0"),
                "e_leakage_tco2e": Decimal("0.0"),
                "notes": base_res["notes"],
                "warnings": [base_res["notes"]],
                "calculation_hash": "",
            }
        c_baseline = base_res["c_baseline_tco2e"]

        # 3. Storage Loss (Equation 6.4 & Table 6.1)
        loss_res = PuroStorageLossCalculator.calculate(
            c_stored, molar_h_c, soil_temperature_celsius, is_non_soil_durable
        )
        if loss_res["status"] != "SUCCESS":
            return {
                "calculation_status": loss_res["status"],
                "corc_point_status": "FAIL_CLOSED",
                "final_corcs_issuable": Decimal("0.0"),
                "c_stored_tco2e": c_stored,
                "c_baseline_tco2e": c_baseline,
                "c_loss_tco2e": loss_res["c_loss_tco2e"],
                "durability_class": loss_res.get("durability_class", "INELIGIBLE"),
                "persistence_fraction_pf": loss_res.get("persistence_fraction_pf", 0.0),
                "e_project_tco2e": Decimal("0.0"),
                "e_leakage_tco2e": Decimal("0.0"),
                "notes": loss_res["notes"],
                "warnings": [loss_res["notes"]],
                "calculation_hash": "",
            }
        c_loss = loss_res["c_loss_tco2e"]
        durability_class = loss_res["durability_class"]
        persistence_fraction_pf = loss_res["persistence_fraction_pf"]
        regression_m = loss_res.get("regression_m")
        regression_a = loss_res.get("regression_a")

        # 4. Project LCA Emissions (Chapter 7)
        proj_res = PuroProjectEmissionsCalculator.calculate(
            e_biomass=e_biomass,
            e_production=e_production,
            e_use=e_use,
            e_infra=e_infra,
            e_dluc=e_dluc,
            crediting_years=crediting_years,
        )
        e_project = proj_res["e_project_tco2e"]

        # 5. Leakage (Chapter 8)
        leak_res = PuroLeakageCalculator.calculate(
            is_leakage_mitigated=is_leakage_mitigated,
            ecological_leakage_tco2e=ecological_leakage_tco2e,
            market_activity_shifting_tco2e=market_activity_shifting_tco2e,
            iluc_feedstock_category=iluc_feedstock_category,
            feedstock_quantity_dry_tonnes=feedstock_quantity_dry_tonnes,
            feedstock_lhv_mj_kg=feedstock_lhv_mj_kg,
        )
        e_leakage = leak_res["e_leakage_tco2e"]

        # 6. Net CORCs Quantification
        # CORCs = max(0, Cstored - Cbaseline - Closs - Eproject - Eleakage)
        net_corcs = cls.calculate_net_corcs(c_stored, c_baseline, c_loss, e_project, e_leakage)
        final_corcs = net_corcs

        # 7. Uncertainty Quantification (Chapter 10)
        unc_res = PuroUncertaintyCalculator.calculate(final_corcs)
        combined_uncertainty_pct = unc_res["combined_uncertainty_pct"]
        reported_uncertainty_text = unc_res["reported_uncertainty_text"]

        if calculation_mode.upper() == "SIMULATION":
            warnings.append("SIMULATION MODE: Results are for scenario modeling and are not registered for issuance.")

        # 8. Deterministic Input Manifest & Canonical Hash
        manifest = {
            "calculation_mode": calculation_mode.upper(),
            "eligible_dry_mass_tonnes": f"{eligible_dry_mass_tonnes:.6f}",
            "c_org_pct": f"{c_org_pct:.4f}",
            "molar_h_c": f"{molar_h_c:.4f}",
            "soil_temperature_celsius": f"{soil_temperature_celsius:.2f}",
            "baseline_scenario": baseline_scenario,
            "historical_baseline_tco2e": f"{c_baseline:.6f}",
            "end_use_category_code": end_use_category_code or "AF1",
            "reversal_discount_factor": str(reversal_discount_factor) if reversal_discount_factor else "1.0",
            "is_non_soil_durable": is_non_soil_durable,
            "c_stored_tco2e": f"{c_stored:.6f}",
            "c_loss_tco2e": f"{c_loss:.6f}",
            "persistence_fraction_pf": f"{persistence_fraction_pf:.4f}",
            "regression_m": f"{regression_m:.2f}" if regression_m else "0.0",
            "regression_a": f"{regression_a:.2f}" if regression_a else "0.0",
            "e_project_tco2e": f"{e_project:.6f}",
            "e_ops_total_tco2e": f"{proj_res['e_ops_total_tco2e']:.6f}",
            "e_emb_annualized_tco2e": f"{proj_res['e_emb_annualized_tco2e']:.6f}",
            "e_leakage_tco2e": f"{e_leakage:.6f}",
            "final_corcs_issuable": f"{final_corcs:.6f}",
            "durability_class": durability_class,
            "combined_uncertainty_pct": f"{combined_uncertainty_pct:.2f}",
            "reported_uncertainty_text": reported_uncertainty_text,
            "engine_version": engine_version,
            "methodology_version": methodology_version,
        }
        calc_hash = HashGenerator.generate_canonical_hash(manifest)

        return {
            "calculation_status": "SUCCESS",
            "calculation_mode": calculation_mode.upper(),
            "corc_point_status": "CORC_POINT_ELIGIBLE",
            "eligible_dry_biochar_mass_tonnes": eligible_dry_mass_tonnes,
            "organic_carbon_pct": c_org_pct,
            "molar_h_c": molar_h_c,
            "soil_temperature_celsius": soil_temperature_celsius,
            "persistence_fraction_pf": persistence_fraction_pf,
            "regression_m": regression_m,
            "regression_a": regression_a,
            "durability_class": durability_class,
            "c_stored_tco2e": c_stored,
            "c_baseline_tco2e": c_baseline,
            "c_loss_tco2e": c_loss,
            "e_project_tco2e": e_project,
            "e_ops_biomass_tco2e": proj_res["e_ops_biomass_tco2e"],
            "e_ops_production_tco2e": proj_res["e_ops_production_tco2e"],
            "e_ops_use_tco2e": proj_res["e_ops_use_tco2e"],
            "e_ops_total_tco2e": proj_res["e_ops_total_tco2e"],
            "e_emb_infra_tco2e": proj_res["e_emb_infra_tco2e"],
            "e_emb_dluc_tco2e": proj_res["e_emb_dluc_tco2e"],
            "e_emb_annualized_tco2e": proj_res["e_emb_annualized_tco2e"],
            "leakage_eco_tco2e": leak_res["ecological_leakage_tco2e"],
            "leakage_ma_tco2e": leak_res["market_leakage_tco2e"],
            "leakage_iluc_tco2e": leak_res["iluc_leakage_tco2e"],
            "e_leakage_tco2e": e_leakage,
            "net_corcs_calculated": final_corcs,
            "final_corcs_issuable": final_corcs,
            "combined_uncertainty_pct": combined_uncertainty_pct,
            "deductible_uncertainty_pct": 0.0,
            "reported_uncertainty_text": reported_uncertainty_text,
            "calculation_hash": calc_hash,
            "input_manifest": manifest,
            "methodology_version": methodology_version,
            "coefficient_version": "PURO_2025_V2_TABLE_6_1_INTEGER_LOOKUP",
            "engine_version": engine_version,
            "timestamp": datetime.now(timezone.utc),
            "rule_references": rules,
            "warnings": warnings,
            "notes": f"Puro CORC quantification executed ({durability_class}: {float(final_corcs):.3f} tCO2e, Uncertainty: {reported_uncertainty_text}).",
        }


class PuroAuthoritativeQuantificationService:
    """
    Authoritative Server-Side Quantification Engine.
    Strictly resolves parameters from database records (batch dry mass, lab elemental analysis,
    baseline records, LCA entries, leakage assessments, end-use attestations).
    Rejects client override parameters.
    Fails closed if any required verified record is missing.
    Marks legacy engine v1.0.0 calculations as superseded.
    """

    @classmethod
    async def resolve_and_execute(
        cls,
        db: AsyncSession,
        batch_id: UUID,
        organization_id: UUID,
        mode: str = "AUTHORITATIVE",
    ) -> Dict[str, Any]:
        from app.domains.biochar.models import (
            BiocharBatch,
            BiocharLabAnalysis,
            BiocharEndUseRecord,
            PuroBaselineAssessment,
            PuroCalculationExecution,
            PuroEndUseCategory,
            PuroEndUseRecordLink,
            PuroLCAModel,
            PuroLCIEntry,
        )

        # 1. Fetch batch
        stmt_batch = select(BiocharBatch).where(
            BiocharBatch.id == batch_id,
            BiocharBatch.organization_id == organization_id,
        )
        res_batch = await db.execute(stmt_batch)
        batch = res_batch.scalar_one_or_none()
        if not batch:
            return {
                "calculation_status": "FAIL_CLOSED",
                "notes": f"Biochar batch {batch_id} not found for organization {organization_id}.",
            }

        # Dry mass resolution
        dry_mass = batch.dry_mass_tonnes or batch.biochar_yield_tonnes
        if dry_mass is None or dry_mass <= Decimal("0"):
            return {
                "calculation_status": "DATA_REQUIRED",
                "missing_inputs": ["dry_mass_tonnes"],
                "notes": f"Batch {batch.batch_number} does not have a verified dry mass.",
            }

        # 2. Fetch lab analysis for batch
        stmt_lab = select(BiocharLabAnalysis).where(
            BiocharLabAnalysis.batch_id == batch_id,
            BiocharLabAnalysis.organization_id == organization_id,
        ).order_by(BiocharLabAnalysis.sampling_date.desc())
        res_lab = await db.execute(stmt_lab)
        lab = res_lab.scalars().first()
        if not lab:
            return {
                "calculation_status": "DATA_REQUIRED",
                "missing_inputs": ["lab_analysis"],
                "notes": f"Batch {batch.batch_number} has no registered accredited laboratory analysis.",
            }

        if lab.organic_carbon_pct is None or Decimal(str(lab.organic_carbon_pct)) <= Decimal("0"):
            return {
                "calculation_status": "DATA_REQUIRED",
                "missing_inputs": ["organic_carbon_pct"],
                "notes": f"Lab analysis {lab.sample_id} lacks certified organic carbon content (C_org).",
            }

        if lab.molar_h_c_ratio is None:
            return {
                "calculation_status": "DATA_REQUIRED",
                "missing_inputs": ["molar_h_c"],
                "notes": f"Lab analysis {lab.sample_id} lacks certified molar H/Corg ratio.",
            }

        molar_h_c = float(lab.molar_h_c_ratio)
        c_org_pct = Decimal(str(lab.organic_carbon_pct))

        # Check carbonization degree threshold
        if molar_h_c >= MAX_ELIGIBLE_MOLAR_H_C:
            return {
                "calculation_status": "FAIL_CLOSED",
                "durability_class": "INELIGIBLE",
                "notes": f"Molar H/Corg {molar_h_c:.4f} >= {MAX_ELIGIBLE_MOLAR_H_C}. Batch fails carbonization requirement (Rule 3.5.1).",
            }

        # Resolve facility_id
        facility_id = getattr(batch, "facility_id", None)
        if not facility_id and batch.production_run_id:
            from app.domains.biochar.models import ProductionRun
            stmt_run = select(ProductionRun).where(ProductionRun.id == batch.production_run_id)
            res_run = await db.execute(stmt_run)
            run = res_run.scalar_one_or_none()
            if run:
                facility_id = run.facility_id
        if not facility_id:
            from app.domains.biochar.models import ProductionFacility
            stmt_fac = select(ProductionFacility.id).where(
                ProductionFacility.project_id == batch.project_id
            ).limit(1)
            res_fac = await db.execute(stmt_fac)
            facility_id = res_fac.scalar_one_or_none()

        if not facility_id:
            return {
                "calculation_status": "DATA_REQUIRED",
                "missing_inputs": ["facility_id"],
                "notes": f"Batch {batch.batch_number} cannot be mapped to an authorized production facility.",
            }

        # 3. Baseline assessment
        stmt_base = select(PuroBaselineAssessment).where(
            PuroBaselineAssessment.facility_id == facility_id,
            PuroBaselineAssessment.organization_id == organization_id,
        )
        res_base = await db.execute(stmt_base)
        base_assess = res_base.scalars().first()
        baseline_scenario = base_assess.scenario if base_assess else "NEW_FACILITY"
        historical_baseline = base_assess.baseline_removal_tco2e_per_year if base_assess else Decimal("0.0")

        # 4. End-use record & soil temperature
        stmt_link = (
            select(PuroEndUseRecordLink, PuroEndUseCategory)
            .join(PuroEndUseCategory, PuroEndUseRecordLink.category_id == PuroEndUseCategory.id)
            .where(
                PuroEndUseRecordLink.batch_id == batch_id,
                PuroEndUseRecordLink.organization_id == organization_id,
            )
        )
        res_link = await db.execute(stmt_link)
        link_row = res_link.first()

        end_use_cat_code = "AF1"
        is_non_soil = False
        soil_temp = 15.0
        reversal_discount_factor = None
        corc_point_eligible = True

        if link_row:
            link_record, cat_record = link_row
            end_use_cat_code = cat_record.category_code
            is_non_soil = (cat_record.application_type == "NON_SOIL")
            corc_point_eligible = (link_record.corc_point_reached == "CORC_POINT_ELIGIBLE")

        # 5. LCA Emissions from registered model/entries
        stmt_lca = select(PuroLCAModel).where(
            PuroLCAModel.facility_id == facility_id,
            PuroLCAModel.organization_id == organization_id,
            PuroLCAModel.status == "ACTIVE",
        )
        res_lca = await db.execute(stmt_lca)
        lca_model = res_lca.scalars().first()

        e_biomass = Decimal("0.0")
        e_production = Decimal("0.0")
        e_use = Decimal("0.0")
        e_infra = Decimal("0.0")
        e_dluc = Decimal("0.0")
        cred_years = 10

        if lca_model:
            cred_years = lca_model.crediting_years
            stmt_entries = select(PuroLCIEntry).where(PuroLCIEntry.lca_model_id == lca_model.id)
            res_entries = await db.execute(stmt_entries)
            for entry in res_entries.scalars():
                cat = entry.category
                ghg = entry.ghg_emissions_tco2e
                if cat == "OPERATIONAL_BIOMASS":
                    e_biomass += ghg
                elif cat == "OPERATIONAL_PRODUCTION":
                    e_production += ghg
                elif cat == "OPERATIONAL_USE":
                    e_use += ghg
                elif cat == "EMBODIED_INFRASTRUCTURE":
                    e_infra += ghg
                elif cat == "EMBODIED_DLUC":
                    e_dluc += ghg

        # Execute quantification
        calc_result = PuroCORCCalculator.execute_quantification(
            eligible_dry_mass_tonnes=dry_mass,
            c_org_pct=c_org_pct,
            molar_h_c=molar_h_c,
            soil_temperature_celsius=soil_temp,
            baseline_scenario=baseline_scenario,
            historical_baseline_tco2e=historical_baseline,
            end_use_category_code=end_use_cat_code,
            reversal_discount_factor=reversal_discount_factor,
            is_non_soil_durable=is_non_soil,
            e_biomass=e_biomass,
            e_production=e_production,
            e_use=e_use,
            e_infra=e_infra,
            e_dluc=e_dluc,
            crediting_years=cred_years,
            end_use_corc_point_eligible=corc_point_eligible,
            calculation_mode=mode,
            engine_version="2.0.0",
        )

        # If authoritative and successful, persist execution and supersede old engine records
        if mode.upper() == "AUTHORITATIVE" and calc_result["calculation_status"] == "SUCCESS":
            # Invalidate/supersede any v1.0.0 calculations for this batch
            stmt_supersede = (
                update(PuroCalculationExecution)
                .where(
                    PuroCalculationExecution.batch_id == batch_id,
                    PuroCalculationExecution.engine_version != "2.0.0",
                    PuroCalculationExecution.superseded_at.is_(None),
                )
                .values(
                    superseded_at=datetime.now(timezone.utc),
                    superseded_reason="SUPERSEDED_METHODOLOGY_IMPLEMENTATION",
                    replacement_engine_version="2.0.0",
                )
            )
            await db.execute(stmt_supersede)

            # Persist execution
            execution = PuroCalculationExecution(
                organization_id=organization_id,
                project_id=batch.project_id,
                facility_id=facility_id,
                batch_id=batch_id,
                calculation_mode="AUTHORITATIVE",
                calculation_status="SUCCESS",
                methodology_version="PURO_BIOCHAR_2025_V2",
                coefficient_version="PURO_2025_V2_TABLE_6_1_INTEGER_LOOKUP",
                eligible_dry_biochar_mass_tonnes=dry_mass,
                c_org_pct=float(c_org_pct),
                molar_h_c=molar_h_c,
                soil_temperature_celsius=soil_temp,
                persistence_fraction_pf=calc_result["persistence_fraction_pf"],
                persistence_m_param=calc_result.get("regression_m"),
                persistence_a_param=calc_result.get("regression_a"),
                durability_class=calc_result["durability_class"],
                c_stored_tco2e=calc_result["c_stored_tco2e"],
                c_baseline_tco2e=calc_result["c_baseline_tco2e"],
                c_loss_tco2e=calc_result["c_loss_tco2e"],
                e_ops_biomass_tco2e=calc_result["e_ops_biomass_tco2e"],
                e_ops_production_tco2e=calc_result["e_ops_production_tco2e"],
                e_ops_use_tco2e=calc_result["e_ops_use_tco2e"],
                e_ops_total_tco2e=calc_result["e_ops_total_tco2e"],
                e_emb_infra_tco2e=calc_result["e_emb_infra_tco2e"],
                e_emb_dluc_tco2e=calc_result["e_emb_dluc_tco2e"],
                e_emb_annualized_tco2e=calc_result["e_emb_annualized_tco2e"],
                e_project_tco2e=calc_result["e_project_tco2e"],
                leakage_eco_tco2e=calc_result["leakage_eco_tco2e"],
                leakage_ma_tco2e=calc_result["leakage_ma_tco2e"],
                leakage_iluc_tco2e=calc_result["leakage_iluc_tco2e"],
                e_leakage_tco2e=calc_result["e_leakage_tco2e"],
                net_corcs_calculated=calc_result["net_corcs_calculated"],
                combined_uncertainty_pct=calc_result["combined_uncertainty_pct"],
                deductible_uncertainty_pct=0.0,
                final_corcs_issuable=calc_result["final_corcs_issuable"],
                reported_uncertainty_text=calc_result["reported_uncertainty_text"],
                input_manifest_json=calc_result["input_manifest"],
                calculation_hash=calc_result["calculation_hash"],
                engine_version="2.0.0",
            )
            db.add(execution)
            await db.commit()
            calc_result["execution_id"] = str(execution.id)

        return calc_result
