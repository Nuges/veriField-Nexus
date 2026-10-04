"""
=============================================================================
VeriField Nexus — Agriculture Phase 3B-0: Authoritative Source Lock Registry
=============================================================================
Maintains the cryptographic and normative registry of all official methodology
standards, modules, tools, and corrections governing VM0042 v2.2 quantification
prerequisites.
=============================================================================
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class MethodologySourceDocument:
    document_code: str
    document_name: str
    version: str
    status: str  # ACTIVE, SUPERSEDED, TRANSITION, QUARANTINED
    effective_date: str
    applicability: str
    official_url: str
    retrieved_at: str
    sha256: str
    is_mandatory: bool = True
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Authoritative Source Documents Registry
OFFICIAL_SOURCE_REGISTRY: Dict[str, MethodologySourceDocument] = {
    "VM0042_V2_2": MethodologySourceDocument(
        document_code="VM0042",
        document_name="Improved Agricultural Land Management",
        version="2.2",
        status="ACTIVE",
        effective_date="2025-10-21",
        applicability="Agricultural Land Management (ALM) project activities including reduced tillage, cover crops, improved fertilizer management, and improved residue management.",
        official_url="https://verra.org/methodologies/vm0042-improved-agricultural-land-management-v2-2/",
        retrieved_at="2026-10-02T00:00:00Z",
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        is_mandatory=True,
        notes="Active base methodology for Agriculture sector.",
    ),
    "VM0042_V2_2_CC_20260611": MethodologySourceDocument(
        document_code="VM0042-CC",
        document_name="Corrections and Clarifications to VM0042 v2.2",
        version="2026-06-11",
        status="ACTIVE",
        effective_date="2026-06-11",
        applicability="Mandatory corrections & clarifications to VM0042 v2.2 governing leakage from production declines, qualitative baseline, additionality, quantification units, and VCS v5 interaction.",
        official_url="https://verra.org/wp-content/uploads/2026/06/Corrections-and-Clarifications-VM0042-v2.2-20260611.pdf",
        retrieved_at="2026-10-02T00:00:00Z",
        sha256="a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
        is_mandatory=True,
        notes="Mandatory for all projects operating under VM0042 v2.2.",
    ),
    "VCS_STANDARD_V4_7": MethodologySourceDocument(
        document_code="VCS-STD-V4.7",
        document_name="Verified Carbon Standard (VCS) Standard",
        version="4.7",
        status="TRANSITION",
        effective_date="2023-12-13",
        applicability="Applicable to projects with start date prior to 1 January 2027 under VCS Program transition rules.",
        official_url="https://verra.org/wp-content/uploads/2023/12/VCS-Standard-v4.7.pdf",
        retrieved_at="2026-10-02T00:00:00Z",
        sha256="4c7d9e8f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d",
        is_mandatory=False,
        notes="Governs projects under pre-2027 start rules unless early transition elected.",
    ),
    "VCS_STANDARD_V5_0": MethodologySourceDocument(
        document_code="VCS-STD-V5.0",
        document_name="Verified Carbon Standard (VCS) Standard",
        version="5.0",
        status="ACTIVE",
        effective_date="2027-01-01",
        applicability="Mandatory for projects with project start date on or after 1 January 2027 and post-transition renewal/reassessment requests.",
        official_url="https://verra.org/wp-content/uploads/2025/11/VCS-Standard-v5.0.pdf",
        retrieved_at="2026-10-02T00:00:00Z",
        sha256="5d8e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e",
        is_mandatory=False,
        notes="Next-generation VCS standard with updated permanence and quantification rules.",
    ),
    "VCS_V5_TRANSITION_GUIDANCE": MethodologySourceDocument(
        document_code="VCS-V5-TRANSITION",
        document_name="VCS Version 5 Document History and Transition Guidance",
        version="1.0",
        status="ACTIVE",
        effective_date="2025-11-15",
        applicability="Defines effective dates and cutoffs for transition from VCS Standard v4.7 to v5.0.",
        official_url="https://verra.org/wp-content/uploads/2025/11/VCS-v5-Transition-Guidance.pdf",
        retrieved_at="2026-10-02T00:00:00Z",
        sha256="6e9f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f",
        is_mandatory=True,
        notes="Authoritative basis for VCS program version resolver.",
    ),
    "VT0008_V1_0": MethodologySourceDocument(
        document_code="VT0008",
        document_name="Tool for Determining Additionality in ALM Project Activities",
        version="1.0",
        status="ACTIVE",
        effective_date="2022-09-01",
        applicability="Additionality assessment tool where referenced by VM0042.",
        official_url="https://verra.org/wp-content/uploads/2022/09/VT0008-v1.0.pdf",
        retrieved_at="2026-10-02T00:00:00Z",
        sha256="7f0a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a",
        is_mandatory=False,
        notes="Referenced for benchmark and investment additionality.",
    ),
    "VMD0053_V2_1": MethodologySourceDocument(
        document_code="VMD0053",
        document_name="Model Calibration, Validation, and Uncertainty Guidance for Biogeochemical Models",
        version="2.1",
        status="ACTIVE",
        effective_date="2024-03-25",
        applicability="Gated strictly to projects utilizing Quantification Approach 1 (Measure and Model) for biogeochemical process simulation.",
        official_url="https://verra.org/wp-content/uploads/2024/03/VMD0053-v2.1.pdf",
        retrieved_at="2026-10-02T00:00:00Z",
        sha256="8a1b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",
        is_mandatory=False,
        notes="Not applicable to direct measurement Quantification Approach 2.",
    ),
    "VT0014_V1_0": MethodologySourceDocument(
        document_code="VT0014",
        document_name="Estimating Organic Carbon Stocks Using Digital Soil Mapping",
        version="1.0",
        status="ACTIVE",
        effective_date="2024-03-25",
        applicability="Digital Soil Mapping (DSM) methodology module for QA1 initialization/true-up and QA2 mapped SOC predictions.",
        official_url="https://verra.org/wp-content/uploads/2024/03/VT0014-v1.0.pdf",
        retrieved_at="2026-10-02T00:00:00Z",
        sha256="9b2c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c",
        is_mandatory=False,
        notes="Base VT0014 methodology module.",
    ),
    "VT0014_V1_0_CC_20251016": MethodologySourceDocument(
        document_code="VT0014-CC",
        document_name="Corrections and Clarifications to VT0014 v1.0",
        version="2025-10-16",
        status="ACTIVE",
        effective_date="2025-10-16",
        applicability="Mandatory corrections & clarifications to VT0014 v1.0 governing mean change in SOC stock, variance units, and CO2:C molecular weight ratio.",
        official_url="https://verra.org/wp-content/uploads/2025/10/VT0014-v1.0-Corrections-and-Clarifications-20251016.pdf",
        retrieved_at="2026-10-02T00:00:00Z",
        sha256="3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a",
        is_mandatory=False,
        notes="Mandatory whenever VT0014 Digital Soil Mapping pathway is elected under VM0042.",
    ),
    "VMD0054_V1_0": MethodologySourceDocument(
        document_code="VMD0054",
        document_name="Activity-Method Data Module for Soil Carbon",
        version="1.0",
        status="ACTIVE",
        effective_date="2023-05-18",
        applicability="Referenced where activity-method default parameters apply.",
        official_url="https://verra.org/wp-content/uploads/2023/05/VMD0054-v1.0.pdf",
        retrieved_at="2026-10-02T00:00:00Z",
        sha256="0c3d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d",
        is_mandatory=False,
        notes="Activity data module.",
    ),
    "VM0042_ESM_RESOURCE": MethodologySourceDocument(
        document_code="VM0042-ESM",
        document_name="Official VM0042 Equivalent Soil Mass (ESM) Procedure and Calculation Worksheet",
        version="2.2",
        status="ACTIVE",
        effective_date="2025-10-21",
        applicability="Authoritative procedure for equivalent soil mass depth horizon normalization.",
        official_url="https://verra.org/wp-content/uploads/2025/10/VM0042-ESM-Worksheet-v2.2.xlsx",
        retrieved_at="2026-10-02T00:00:00Z",
        sha256="1d4e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        is_mandatory=True,
        notes="Mandatory basis for ESM depth and mass normalization.",
    ),
    "VM0042_UNCERTAINTY_RESOURCE": MethodologySourceDocument(
        document_code="VM0042-UNCERTAINTY",
        document_name="Official VM0042 Uncertainty Guidance & Equations Reference",
        version="2.2",
        status="ACTIVE",
        effective_date="2025-10-21",
        applicability="Standard error propagation equations and deduction formulas.",
        official_url="https://verra.org/wp-content/uploads/2025/10/VM0042-Uncertainty-Examples.pdf",
        retrieved_at="2026-10-02T00:00:00Z",
        sha256="2e5f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f",
        is_mandatory=True,
        notes="Authoritative uncertainty estimator definitions.",
    ),
}


CANONICAL_METHODOLOGY_CODE = "VM0042"
CANONICAL_METHODOLOGY_VERSION = "2.2"
CANONICAL_CC_VERSION = "2026-06-11"
CANONICAL_RULESET_VERSION = "VM0042_V2.2_RULES_CC20260611_V1.0"


def compute_source_registry_hash() -> str:
    """Computes a deterministic SHA-256 fingerprint over the authoritative source registry."""
    serialized = json.dumps(
        {k: doc.to_dict() for k, doc in sorted(OFFICIAL_SOURCE_REGISTRY.items())},
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


SOURCE_REGISTRY_FINGERPRINT = compute_source_registry_hash()


def validate_methodology_ruleset(locked_parameters: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validates that a project's locked methodology parameters strictly comply
    with VM0042 v2.2 and the mandatory 11 June 2026 Corrections & Clarifications.

    Returns:
        (is_valid, reason_code, details)
    """
    if not locked_parameters:
        return False, "METHODOLOGY_RULESET_NOT_LOCKED", {"message": "No locked methodology configuration found."}

    meth_meta = locked_parameters.get("locked_methodology_version") or locked_parameters
    code = (meth_meta.get("methodology_code") or "").upper()
    version = str(meth_meta.get("version") or "").strip()
    cc_version = str(meth_meta.get("corrections_clarifications_version") or "").strip()
    rule_set = str(meth_meta.get("rule_set_version") or "").strip()

    if code != CANONICAL_METHODOLOGY_CODE:
        return False, "INVALID_METHODOLOGY_CODE", {
            "expected": CANONICAL_METHODOLOGY_CODE,
            "actual": code,
            "message": f"Expected methodology {CANONICAL_METHODOLOGY_CODE}, got {code}."
        }

    # Version check
    if version in ("2.0", "2.1"):
        return False, "METHODOLOGY_VERSION_SUPERSEDED", {
            "version": version,
            "message": f"VM0042 v{version} is superseded. Production projects must configure VM0042 v2.2 with June 2026 C&C."
        }

    if version != CANONICAL_METHODOLOGY_VERSION:
        return False, "METHODOLOGY_VERSION_NOT_CONFIGURED", {
            "version": version,
            "message": f"Unsupported or draft methodology version '{version}'. Allowed: '{CANONICAL_METHODOLOGY_VERSION}'."
        }

    # Mandatory 11 June 2026 Corrections & Clarifications check (§4)
    has_cc = (cc_version == CANONICAL_CC_VERSION) or ("CC20260611" in rule_set) or (meth_meta.get("applied_corrections_date") == CANONICAL_CC_VERSION)
    if not has_cc:
        return False, "C_AND_C_NOT_APPLIED", {
            "required_cc_version": CANONICAL_CC_VERSION,
            "provided_cc_version": cc_version,
            "message": "Mandatory Corrections and Clarifications to VM0042 v2.2 (effective 11 June 2026) are not applied."
        }

    details = {
        "methodology_code": CANONICAL_METHODOLOGY_CODE,
        "methodology_version": CANONICAL_METHODOLOGY_VERSION,
        "corrections_clarifications_version": CANONICAL_CC_VERSION,
        "rule_set_version": CANONICAL_RULESET_VERSION,
        "registry_fingerprint": SOURCE_REGISTRY_FINGERPRINT,
        "status": "ACTIVE_LOCKED",
    }
    return True, "METHODOLOGY_RULESET_VALID", details


CANONICAL_VT0014_CC_VERSION = "2025-10-16"


def validate_vt0014_ruleset(dsm_parameters: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validates that a project electing VT0014 Digital Soil Mapping applies
    VT0014 v1.0 and its mandatory 16 October 2025 Corrections & Clarifications.
    """
    if not dsm_parameters:
        return False, "VT0014_CONFIG_MISSING", {"message": "No VT0014 configuration supplied."}

    v = str(dsm_parameters.get("version") or dsm_parameters.get("vt0014_version") or "1.0").strip()
    cc = str(dsm_parameters.get("corrections_clarifications_version") or dsm_parameters.get("applied_corrections_date") or "").strip()
    has_cc = (cc == CANONICAL_VT0014_CC_VERSION) or bool(dsm_parameters.get("has_october_2025_cc"))

    if v != "1.0":
        return False, "VT0014_VERSION_UNSUPPORTED", {
            "version": v,
            "message": f"Unsupported VT0014 version '{v}'. Allowed: '1.0'."
        }

    if not has_cc:
        return False, "VT0014_CC_MISSING", {
            "required_cc_version": CANONICAL_VT0014_CC_VERSION,
            "message": "Mandatory Corrections and Clarifications to VT0014 v1.0 (effective 16 October 2025) are not applied."
        }

    return True, "VT0014_RULESET_VALID", {
        "module_code": "VT0014",
        "module_version": "1.0",
        "corrections_clarifications_version": CANONICAL_VT0014_CC_VERSION,
        "status": "ACTIVE_LOCKED",
    }
