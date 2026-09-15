"""
=============================================================================
VeriField Nexus — Verra VM0042 v2.2 Calculator Adapter
=============================================================================
Methodology: VM0042 v2.2
Name: Improved Agricultural Land Management (Scope 15 Agriculture)
Corrections & Clarifications: Effective 11 June 2026 applied.
Maturity Tier: MRV_ENABLED
Calculation Status: NOT_CONFIGURED (Strict fail-closed policy)
=============================================================================
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.domains.agriculture.calculators.base import (
    AgricultureCalculator,
    CalculationResult,
    CalculationStatus,
    MethodologyMaturityTier,
    MethodologyNotConfiguredError,
)


class VM0042CalculatorV22(AgricultureCalculator):
    """
    Verra VM0042 v2.2 Quantification Adapter.
    Strictly fail-closed: blocks credit issuance while supporting full MRV ingestion.
    """

    @property
    def methodology_code(self) -> str:
        return "VM0042"

    @property
    def version(self) -> str:
        return "2.2"

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
        """
        Executes fail-closed calculation policy.
        """
        msg = (
            "VM0042 v2.2 official quantification formulas require registry-verified "
            "worked-example calibration. Production credit issuance is strictly blocked "
            "(status=NOT_CONFIGURED) while MRV monitoring, soil sampling, and boundary "
            "management remain fully operational."
        )

        provenance_payload = {
            "methodology": self.methodology_code,
            "version": self.version,
            "status": self.default_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": msg,
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
