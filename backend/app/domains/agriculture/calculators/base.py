"""
=============================================================================
VeriField Nexus — Agriculture Methodology Calculator Base
=============================================================================
Defines standard interfaces, calculation results, and fail-closed policies:
- Strict fail-closed policy: If a methodology lacks authoritative, verified
  worked examples, it MUST declare status="NOT_CONFIGURED" and block credit issuance.
- Pre-quantification MRV ingestion and monitoring remain operational.
=============================================================================
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MethodologyMaturityTier(str, Enum):
    CATALOGUED = "CATALOGUED"
    MRV_ENABLED = "MRV_ENABLED"
    QUANTIFICATION_ENABLED = "QUANTIFICATION_ENABLED"


class CalculationStatus(str, Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    BLOCKED_METHODOLOGY_CALIBRATION = "BLOCKED_METHODOLOGY_CALIBRATION"
    EX_ANTE_ESTIMATE = "EX_ANTE_ESTIMATE"
    QUANTIFIED = "QUANTIFIED"
    VERIFIED = "VERIFIED"


class MethodologyNotConfiguredError(Exception):
    """Raised when attempting production carbon quantification on a NOT_CONFIGURED calculator."""
    pass


@dataclass
class CalculationResult:
    methodology_code: str
    version: str
    status: CalculationStatus
    is_issuance_eligible: bool
    total_net_removals_t_co2e: float = 0.0
    total_net_reductions_t_co2e: float = 0.0
    total_net_t_co2e: float = 0.0
    uncertainty_deduction_pct: float = 0.0
    buffer_pool_contribution_t_co2e: float = 0.0
    issuable_credits_t_co2e: float = 0.0
    breakdown_by_management_unit: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    compliance_notes: str = ""
    provenance_hash: str = ""


class AgricultureCalculator(ABC):
    """
    Abstract base class for all agricultural sector methodology calculators.
    """

    @property
    @abstractmethod
    def methodology_code(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @property
    @abstractmethod
    def maturity_tier(self) -> MethodologyMaturityTier:
        pass

    @property
    @abstractmethod
    def default_status(self) -> CalculationStatus:
        pass

    @abstractmethod
    def calculate_project_credits(
        self,
        project_data: Dict[str, Any],
        monitoring_data: Dict[str, Any],
    ) -> CalculationResult:
        """
        Executes quantification. If calculator is NOT_CONFIGURED, strictly returns
        fail-closed result with is_issuance_eligible=False.
        """
        pass
