"""
=============================================================================
VeriField Nexus — Verra VM0051 v1.1 Rice Cultivation Calculator Adapter
=============================================================================
Methodology: VM0051 v1.1
Name: Improved Management in Rice Production Systems (Scope 15 Agriculture)
Practices: Alternate Wetting and Drying (AWD), Intermittent Flooding, Drainage
Status: NOT_CONFIGURED (Strict fail-closed policy)
=============================================================================
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict

from app.domains.agriculture.calculators.base import (
    AgricultureCalculator,
    CalculationResult,
    CalculationStatus,
    MethodologyMaturityTier,
    MethodologyNotConfiguredError,
)


class VM0051CalculatorV11(AgricultureCalculator):
    """
    VM0051 v1.1 Rice Cultivation Methane Reduction Adapter.
    """

    @property
    def methodology_code(self) -> str:
        return "VM0051"

    @property
    def version(self) -> str:
        return "1.1"

    @property
    def maturity_tier(self) -> MethodologyMaturityTier:
        return MethodologyMaturityTier.MRV_ENABLED

    @property
    def default_status(self) -> CalculationStatus:
        return CalculationStatus.NOT_CONFIGURED

    def calculate_project_credits(
        self,
        project_data: Dict[str, Any],
        monitoring_data: Dict[str, Any],
        fail_closed: bool = True,
    ) -> CalculationResult:
        msg = (
            "VM0051 v1.1 methane reduction quantification requires baseline scaling factor "
            "and water regime verification. Production credit issuance is blocked "
            "(status=NOT_CONFIGURED) while water-level loggers and field drainage activities remain operational."
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
