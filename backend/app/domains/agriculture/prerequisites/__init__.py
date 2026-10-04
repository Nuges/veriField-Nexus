"""
=============================================================================
VeriField Nexus — Agriculture Phase 3B-0 Prerequisites Package
=============================================================================
"""

from app.domains.agriculture.prerequisites.sources import (
    CANONICAL_METHODOLOGY_CODE,
    CANONICAL_METHODOLOGY_VERSION,
    CANONICAL_CC_VERSION,
    CANONICAL_RULESET_VERSION,
    SOURCE_REGISTRY_FINGERPRINT,
    OFFICIAL_SOURCE_REGISTRY,
    validate_methodology_ruleset,
)
from app.domains.agriculture.prerequisites.vcs_resolver import (
    resolve_vcs_program_version,
    resolve_baseline_reassessment_rule,
    GoverningVCSStandard,
    V5TemplateVariant,
    ProjectDescriptionTemplate,
    EarlyAdoptionMode,
    BaselineReassessmentRuleResult,
    VCSResolutionResult,
    OFFICIAL_V5_DELAYED_UPDATES_5_0A,
    CANONICAL_5_0A_DELAYED_UPDATE_IDS,
)
from app.domains.agriculture.prerequisites.route_resolver import (
    resolve_quantification_routes,
    QuantificationApproach,
    RouteMapResolution,
    CANONICAL_VM0042_TABLE_5_COMPONENTS,
    VM0042Table5Component,
)
from app.domains.agriculture.prerequisites.esm_engine import (
    evaluate_depth_sufficiency,
    compile_esm_input_dossier,
    DepthSufficiencyStatus,
    ESMInputDossier,
    SampleLayerEvidence,
    BulkDensityProvenance,
    CoarseFragmentProvenance,
)
from app.domains.agriculture.prerequisites.sampling_design_engine import (
    evaluate_sampling_design,
    calculate_vm0042_power_analysis,
    PowerAnalysisResult,
    PowerAnalysisStatus,
    DesignSufficiencyStatus,
    SamplingDesignAssessment,
)
from app.domains.agriculture.prerequisites.baseline_engine import (
    evaluate_management_history_coverage,
    evaluate_baseline_control_sites,
    ManagementHistoryCoverage,
    BaselineControlSiteStatus,
)
from app.domains.agriculture.prerequisites.quantification_unit_governance import (
    validate_quantification_unit_mapping,
    resolve_temporal_stratum,
)
from app.domains.agriculture.prerequisites.pairing_engine import (
    evaluate_baseline_monitoring_pairing,
    evaluate_method_consistency,
    MethodConsistencyStatus,
    BaselineMonitoringPair,
)
from app.domains.agriculture.prerequisites.uncertainty_engine import (
    evaluate_uncertainty_input_readiness,
    UncertaintyInputReadiness,
    UncertaintyEstimatorType,
)
from app.domains.agriculture.prerequisites.assessment_service import (
    AgriculturePrerequisiteAssessmentService,
    PrerequisiteDimensionKey,
)

__all__ = [
    "CANONICAL_METHODOLOGY_CODE",
    "CANONICAL_METHODOLOGY_VERSION",
    "CANONICAL_CC_VERSION",
    "CANONICAL_RULESET_VERSION",
    "SOURCE_REGISTRY_FINGERPRINT",
    "OFFICIAL_SOURCE_REGISTRY",
    "validate_methodology_ruleset",
    "resolve_vcs_program_version",
    "resolve_baseline_reassessment_rule",
    "GoverningVCSStandard",
    "V5TemplateVariant",
    "ProjectDescriptionTemplate",
    "EarlyAdoptionMode",
    "BaselineReassessmentRuleResult",
    "VCSResolutionResult",
    "OFFICIAL_V5_DELAYED_UPDATES_5_0A",
    "CANONICAL_5_0A_DELAYED_UPDATE_IDS",
    "resolve_quantification_routes",
    "QuantificationApproach",
    "RouteMapResolution",
    "CANONICAL_VM0042_TABLE_5_COMPONENTS",
    "VM0042Table5Component",
    "evaluate_depth_sufficiency",
    "compile_esm_input_dossier",
    "DepthSufficiencyStatus",
    "ESMInputDossier",
    "SampleLayerEvidence",
    "BulkDensityProvenance",
    "CoarseFragmentProvenance",
    "evaluate_sampling_design",
    "calculate_vm0042_power_analysis",
    "PowerAnalysisResult",
    "PowerAnalysisStatus",
    "DesignSufficiencyStatus",
    "SamplingDesignAssessment",
    "evaluate_management_history_coverage",
    "evaluate_baseline_control_sites",
    "ManagementHistoryCoverage",
    "BaselineControlSiteStatus",
    "validate_quantification_unit_mapping",
    "resolve_temporal_stratum",
    "evaluate_baseline_monitoring_pairing",
    "evaluate_method_consistency",
    "MethodConsistencyStatus",
    "BaselineMonitoringPair",
    "evaluate_uncertainty_input_readiness",
    "UncertaintyInputReadiness",
    "UncertaintyEstimatorType",
    "AgriculturePrerequisiteAssessmentService",
    "PrerequisiteDimensionKey",
]
