"""
=============================================================================
VeriField Nexus — Verra VM0047 v1.1 ARR Calculator Adapter
=============================================================================
Methodology: VM0047 v1.1
Name: Afforestation, Reforestation, and Revegetation (Scope 14 AFOLU)
Supports: AREA_BASED (plot sample) and CENSUS_BASED (individual tree)
Biomass Derivation: Allometric Model Registry (Supports Chave 2014, IPCC 2006, etc.)
Strict Separation: Aboveground Biomass (AGB) and Belowground Biomass (BGB) are NOT conflated.
Production Issuance Status: NOT_CONFIGURED (Fail-closed)
=============================================================================
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domains.agriculture.allometrics import (
    AllometricModelRegistry,
    estimate_tree_biomass_pools,
)
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
        agb_model_id: str = "CHAVE_2014_PANTROPICAL_AGB",
        bgb_model_id: Optional[str] = None,
        carbon_fraction: float = 0.47,
    ) -> Dict[str, Any]:
        """
        Derives aboveground biomass (AGB), belowground biomass (BGB, if requested),
        and carbon stock (t CO2e) for an individual tree using the Allometric Model Registry.
        Adheres to VM0047: does NOT automatically infer BGB unless an approved belowground
        or root-shoot model is explicitly configured.
        """
        if dbh_cm <= 0:
            return {
                "agb_kg": 0.0,
                "bgb_kg": None,
                "total_biomass_kg": 0.0,
                "carbon_stock_t_co2e": 0.0,
                "provenance": None,
            }

        return estimate_tree_biomass_pools(
            dbh_cm=dbh_cm,
            height_m=height_m,
            wood_density_g_cm3=wood_density_g_cm3,
            agb_model_id=agb_model_id,
            bgb_model_id=bgb_model_id,
            carbon_fraction=carbon_fraction,
        )

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
            "VM0047 v1.1 project-level net crediting requires baseline ARR stratification, "
            "leakage assessment, and dynamic performance benchmark calibration. Production crediting "
            "is blocked (status=NOT_CONFIGURED) while tree census and field measurements remain active."
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
