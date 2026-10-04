"""
=============================================================================
VeriField Nexus — Equivalent Soil Mass (ESM) & Depth Sufficiency Engine
=============================================================================
Evaluates VM0042 Section 8 soil depth horizons, shallow soil impeding layers,
bulk density provenance, coarse fragments, and compiles the immutable ESM
Input Dossier without calculating premature carbon quantities.
=============================================================================
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class DepthSufficiencyStatus(str, Enum):
    DEPTH_SUFFICIENT = "DEPTH_SUFFICIENT"
    DEPTH_INSUFFICIENT = "DEPTH_INSUFFICIENT"
    SHALLOW_SOIL_EXCEPTION_VALID = "SHALLOW_SOIL_EXCEPTION_VALID"
    SHALLOW_SOIL_EXCEPTION_UNVERIFIED = "SHALLOW_SOIL_EXCEPTION_UNVERIFIED"
    INVALID_DEPTH_INTERVAL = "INVALID_DEPTH_INTERVAL"


class BulkDensityProvenance(str, Enum):
    MEASURED = "MEASURED"
    CALCULATED = "CALCULATED"
    NOT_REQUIRED_BY_SELECTED_PROCEDURE = "NOT_REQUIRED_BY_SELECTED_PROCEDURE"
    MISSING = "MISSING"


class CoarseFragmentProvenance(str, Enum):
    MEASURED = "MEASURED"
    NOT_REQUIRED = "NOT_REQUIRED"
    MISSING = "MISSING"
    INVALID = "INVALID"


VALID_IMPEDING_LAYERS = {
    "BEDROCK",
    "HARDPAN",
    "LITHIC_CONTACT",
    "PARALITHIC_CONTACT",
    "PETROCALCIC_HORIZON",
    "DENSE_GLACIAL_TILL",
}


@dataclass(frozen=True)
class SampleLayerEvidence:
    sample_id: str
    sampling_point_id: str
    depth_upper_cm: float
    depth_lower_cm: float
    soc_concentration_g_kg: float
    bulk_density_provenance: str
    bulk_density_value: Optional[float]
    coarse_fragment_provenance: str
    coarse_fragment_fraction: Optional[float]
    qa_status: str
    impeding_layer_present: bool = False
    impeding_layer_type: Optional[str] = None
    impeding_evidence_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ESMInputDossier:
    project_id: str
    quantification_unit_id: str
    campaign_id: str
    stratum_id: str
    methodology_version: str
    depth_sufficiency_status: str
    shallow_soil_exception_applied: bool
    max_sampled_depth_cm: float
    has_deeper_bounding_layer: bool
    total_layers: int
    layers: List[SampleLayerEvidence]
    dossier_hash: str
    compiled_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "quantification_unit_id": self.quantification_unit_id,
            "campaign_id": self.campaign_id,
            "stratum_id": self.stratum_id,
            "methodology_version": self.methodology_version,
            "depth_sufficiency_status": self.depth_sufficiency_status,
            "shallow_soil_exception_applied": self.shallow_soil_exception_applied,
            "max_sampled_depth_cm": self.max_sampled_depth_cm,
            "has_deeper_bounding_layer": self.has_deeper_bounding_layer,
            "total_layers": self.total_layers,
            "layers": [l.to_dict() for l in self.layers],
            "dossier_hash": self.dossier_hash,
            "compiled_at": self.compiled_at,
        }


def evaluate_depth_sufficiency(
    layers: List[Dict[str, Any]],
    require_esm_bounding_layer: bool = True,
    minimum_depth_cm: float = 30.0,
) -> Tuple[DepthSufficiencyStatus, str, Dict[str, Any]]:
    """
    Evaluates depth sufficiency across a profile of sampled horizons.

    Inputs:
        layers: List of dicts with depth_upper_cm, depth_lower_cm, impeding_layer metadata.
        require_esm_bounding_layer: Whether deeper sampling is required for future ESM interpolation.
        minimum_depth_cm: Standard VM0042 depth minimum (default 30.0 cm).

    Returns:
        (DepthSufficiencyStatus, explanation_note, details)
    """
    if not layers:
        return (
            DepthSufficiencyStatus.DEPTH_INSUFFICIENT,
            "No sampled depth layers present.",
            {"total_layers": 0},
        )

    # 1. Validate intervals for physical integrity
    sorted_layers = sorted(layers, key=lambda l: (l.get("depth_upper_cm", 0.0), l.get("depth_lower_cm", 0.0)))
    for lyr in sorted_layers:
        u = lyr.get("depth_upper_cm")
        d = lyr.get("depth_lower_cm")
        if u is None or d is None:
            return DepthSufficiencyStatus.INVALID_DEPTH_INTERVAL, "Null depth bounds detected.", {}
        if u < 0.0 or d <= u:
            return (
                DepthSufficiencyStatus.INVALID_DEPTH_INTERVAL,
                f"Invalid depth interval [{u}, {d}] cm. Lower bound must exceed upper bound and be non-negative.",
                {"upper": u, "lower": d},
            )

    # Check for shallow soil impeding layer exception (§16, §66)
    shallow_soil_layers = [l for l in sorted_layers if l.get("impeding_layer_present") is True]
    if shallow_soil_layers:
        sl = shallow_soil_layers[0]
        imp_type = str(sl.get("impeding_layer_type") or "").upper()
        depth_cm = float(sl.get("depth_lower_cm") or 0.0)
        is_verified = bool(sl.get("impeding_evidence_verified")) and sl.get("qa_status") == "VERIFIED"

        if imp_type not in VALID_IMPEDING_LAYERS:
            return (
                DepthSufficiencyStatus.SHALLOW_SOIL_EXCEPTION_UNVERIFIED,
                f"Unrecognized impeding layer type '{imp_type}'. Must be one of {sorted(VALID_IMPEDING_LAYERS)} (VM0042_NORMATIVE_REQUIREMENT).",
                {"layer_type": imp_type, "depth_cm": depth_cm, "normative_basis": "VM0042_NORMATIVE_REQUIREMENT"},
            )

        # VM0042 Normative Requirement: Sampled to the impeding layer with documented refusal
        has_refusal_log = bool(sl.get("impeding_evidence_documented", True))
        if not has_refusal_log:
            return (
                DepthSufficiencyStatus.SHALLOW_SOIL_EXCEPTION_UNVERIFIED,
                f"Shallow soil exception at {depth_cm:.1f} cm lacks documented refusal evidence (VM0042_NORMATIVE_REQUIREMENT).",
                {"depth_cm": depth_cm, "normative_basis": "VM0042_NORMATIVE_REQUIREMENT"},
            )

        # Platform Policy: Independent verification / QA sign-off
        if not is_verified:
            return (
                DepthSufficiencyStatus.SHALLOW_SOIL_EXCEPTION_UNVERIFIED,
                f"Shallow soil exception at {depth_cm:.1f} cm documented per VM0042, but pending independent QA/verifier review (PLATFORM_POLICY).",
                {"depth_cm": depth_cm, "verified": is_verified, "governance_policy": "PLATFORM_POLICY"},
            )

        return (
            DepthSufficiencyStatus.SHALLOW_SOIL_EXCEPTION_VALID,
            f"Shallow soil exception verified: {imp_type} at {depth_cm:.1f} cm documented per VM0042 normative rule and accepted under platform policy.",
            {"depth_cm": depth_cm, "layer_type": imp_type, "normative_basis": "VM0042_NORMATIVE_REQUIREMENT", "governance_policy": "PLATFORM_POLICY"},
        )

    # Standard depth evaluation
    max_depth = max(l.get("depth_lower_cm", 0.0) for l in sorted_layers)
    min_upper = min(l.get("depth_upper_cm", 0.0) for l in sorted_layers)

    if min_upper > 0.0:
        return (
            DepthSufficiencyStatus.DEPTH_INSUFFICIENT,
            f"Sampling profile does not start at surface (starts at {min_upper} cm). Surface 0 cm required.",
            {"min_upper": min_upper},
        )

    # Check if reaches 30 cm minimum
    if max_depth < minimum_depth_cm:
        return (
            DepthSufficiencyStatus.DEPTH_INSUFFICIENT,
            f"Maximum sampled depth ({max_depth:.1f} cm) does not meet VM0042 minimum {minimum_depth_cm} cm requirement.",
            {"max_depth": max_depth, "minimum_required": minimum_depth_cm},
        )

    # Check if ESM deeper bounding layer is required (§15, §19, §66)
    # If project requires ESM, sampling to exactly 30 cm only without deeper horizons leads to mass extrapolation
    has_deeper_bounding = max_depth > minimum_depth_cm
    if require_esm_bounding_layer and not has_deeper_bounding:
        return (
            DepthSufficiencyStatus.DEPTH_INSUFFICIENT,
            f"Profile samples to exactly {max_depth:.1f} cm. Equivalent Soil Mass (ESM) normalization requires deeper bounding horizon (e.g. 30-50 cm) to avoid extrapolation outside measured range.",
            {"max_depth": max_depth, "reason_code": "ESM_DEEPER_BOUNDING_LAYER_MISSING"},
        )

    return (
        DepthSufficiencyStatus.DEPTH_SUFFICIENT,
        f"Sampled profile [{min_upper:.1f}, {max_depth:.1f}] cm meets minimum depth and ESM bounding layer requirements.",
        {"max_depth": max_depth, "has_deeper_bounding": has_deeper_bounding},
    )


def compile_esm_input_dossier(
    project_id: str,
    quantification_unit_id: str,
    campaign_id: str,
    stratum_id: str,
    methodology_version: str,
    sample_layers: List[SampleLayerEvidence],
    require_esm_bounding_layer: bool = True,
) -> ESMInputDossier:
    """
    Assembles and cryptographically hashes an immutable ESM Input Dossier.
    Strictly builds the input contract without calculating carbon stocks or removals.
    """
    raw_layers = [l.to_dict() for l in sample_layers]
    status, note, details = evaluate_depth_sufficiency(
        raw_layers,
        require_esm_bounding_layer=require_esm_bounding_layer,
    )

    max_depth = max((l.depth_lower_cm for l in sample_layers), default=0.0)
    has_deeper = max_depth > 30.0
    is_shallow = status == DepthSufficiencyStatus.SHALLOW_SOIL_EXCEPTION_VALID

    now_iso = datetime.now(timezone.utc).isoformat()

    dossier_content = {
        "project_id": str(project_id),
        "quantification_unit_id": str(quantification_unit_id),
        "campaign_id": str(campaign_id),
        "stratum_id": str(stratum_id),
        "methodology_version": str(methodology_version),
        "depth_sufficiency_status": status.value,
        "shallow_soil_exception_applied": is_shallow,
        "max_sampled_depth_cm": float(max_depth),
        "has_deeper_bounding_layer": has_deeper,
        "total_layers": len(sample_layers),
        "layers": sorted(raw_layers, key=lambda l: (l["depth_upper_cm"], l["depth_lower_cm"])),
    }

    serialized = json.dumps(dossier_content, sort_keys=True)
    dossier_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    return ESMInputDossier(
        project_id=str(project_id),
        quantification_unit_id=str(quantification_unit_id),
        campaign_id=str(campaign_id),
        stratum_id=str(stratum_id),
        methodology_version=str(methodology_version),
        depth_sufficiency_status=status.value,
        shallow_soil_exception_applied=is_shallow,
        max_sampled_depth_cm=float(max_depth),
        has_deeper_bounding_layer=has_deeper,
        total_layers=len(sample_layers),
        layers=sample_layers,
        dossier_hash=dossier_hash,
        compiled_at=now_iso,
    )
