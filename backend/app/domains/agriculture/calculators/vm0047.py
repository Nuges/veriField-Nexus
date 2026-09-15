"""
=============================================================================
VeriField Nexus — Verra VM0047 v1.1 ARR Calculator Adapter
=============================================================================
Methodology: VM0047 v1.1
Name: Afforestation, Reforestation and Revegetation (Scope 14 AFOLU)
Supports: AREA_BASED (plot sample) and CENSUS_BASED (individual tree)
Biomass Derivation: Authoritative Pantropical Allometric Equations (Chave 2014)
Production Issuance Status: NOT_CONFIGURED (Fail-closed)
=============================================================================
"""

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domains.agriculture.calculators.base import (
    AgricultureCalculator,
    CalculationResult,
    CalculationStatus,
    MethodologyMaturityTier,
    MethodologyNotConfiguredError,
)


class VM0047CalculatorV11(AgricultureCalculator):
    """
    VM0047 v1.1 ARR Calculator & Allometric Engine.
    """

    @property
    def methodology_code(self) -> str:
        return "VM0047"

    @property
    def version(self) -> str:
        return "1.1"

    @property
    def maturity_tier(self) -> MethodologyMaturityTier:
        return MethodologyMaturityTier.MRV_ENABLED

    @property
    def default_status(self) -> CalculationStatus:
        return CalculationStatus.NOT_CONFIGURED

    @classmethod
    def calculate_tree_biomass(
        cls,
        dbh_cm: float,
        height_m: Optional[float] = None,
        wood_density_g_cm3: float = 0.60,
        root_to_shoot_ratio: float = 0.235,
        carbon_fraction: float = 0.47,
    ) -> Dict[str, float]:
        """
        Derives aboveground biomass (AGB), belowground biomass (BGB),
        and carbon stock (t CO2e) for an individual tree using Chave et al. (2014).

        AGB (kg dry matter):
        If height is measured:
            AGB = 0.0673 * (wood_density * dbh^2 * height)^0.976
        If height is not measured:
            AGB = exp(-1.803 + 0.976 * ln(wood_density) + 2.673 * ln(dbh) - 0.0299 * (ln(dbh))^2)
        """
        if dbh_cm <= 0:
            return {
                "agb_kg": 0.0,
                "bgb_kg": 0.0,
                "total_biomass_kg": 0.0,
                "carbon_stock_t_co2e": 0.0,
            }

        if height_m and height_m > 0:
            compound = wood_density_g_cm3 * (dbh_cm**2) * height_m
            agb_kg = 0.0673 * (compound**0.976)
        else:
            ln_d = math.log(dbh_cm)
            ln_rho = math.log(wood_density_g_cm3)
            ln_agb = -1.803 + 0.976 * ln_rho + 2.673 * ln_d - 0.0299 * (ln_d**2)
            agb_kg = math.exp(ln_agb)

        bgb_kg = agb_kg * root_to_shoot_ratio
        total_biomass_kg = agb_kg + bgb_kg
        total_biomass_tonnes = total_biomass_kg / 1000.0

        # Carbon stock: Biomass (t) * Carbon Fraction (0.47) * (44/12)
        carbon_stock_t_co2e = total_biomass_tonnes * carbon_fraction * (44.0 / 12.0)

        return {
            "agb_kg": round(agb_kg, 2),
            "bgb_kg": round(bgb_kg, 2),
            "total_biomass_kg": round(total_biomass_kg, 2),
            "carbon_stock_t_co2e": round(carbon_stock_t_co2e, 4),
        }

    def calculate_project_credits(
        self,
        project_data: Dict[str, Any],
        monitoring_data: Dict[str, Any],
        fail_closed: bool = True,
    ) -> CalculationResult:
        """
        Fail-closed project crediting calculation for VM0047 v1.1.
        """
        msg = (
            "VM0047 v1.1 project-level net crediting requires baseline ARR stratification "
            "and dynamic performance benchmark calibration. Production crediting is blocked "
            "(status=NOT_CONFIGURED) while tree census and field measurements remain active."
        )

        provenance_payload = {
            "methodology": self.methodology_code,
            "version": self.version,
            "status": self.default_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        prov_hash = hashlib.sha256(json.dumps(provenance_payload, sort_keys=True).encode("utf-8")).hexdigest()

        if fail_closed and project_data.get("strict_validation", False):
            raise MethodologyNotConfiguredError(msg)

        return CalculationResult(
            methodology_code=self.methodology_code,
            version=self.version,
            status=CalculationStatus.NOT_CONFIGURED,
            is_issuance_eligible=False,
            total_net_removals_t_co2e=0.0,
            total_net_reductions_t_co2e=0.0,
            total_net_t_co2e=0.0,
            issuable_credits_t_co2e=0.0,
            warnings=[msg],
            compliance_notes=msg,
            provenance_hash=prov_hash,
        )
