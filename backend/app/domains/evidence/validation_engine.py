"""
Universal Evidence Validation Engine

Validates evidence submissions against methodology-defined evidence requirements.
All rules are metadata-driven — no sector-specific logic lives here.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class EvidenceRuleType(Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    CONDITIONAL = "conditional"


@dataclass
class EvidenceRequirement:
    """A single evidence requirement from methodology metadata."""

    evidence_type: str  # e.g., "gps", "photo", "document", "sensor_data"
    rule_type: EvidenceRuleType = EvidenceRuleType.REQUIRED
    min_count: int = 1
    max_age_hours: Optional[float] = None  # Max age of evidence in hours
    min_resolution: Optional[int] = None  # Min image resolution (pixels)
    gps_required: bool = False
    gps_bounding_box: Optional[Dict[str, float]] = (
        None  # {"min_lat", "max_lat", "min_lon", "max_lon"}
    )
    file_types: List[str] = field(default_factory=list)  # e.g., ["jpg", "png"]
    condition_expression: Optional[str] = None  # For conditional rules


@dataclass
class EvidenceValidationResult:
    """Result of validating a single evidence submission."""

    is_valid: bool
    requirement: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class EvidenceValidationEngine:
    """
    Validates submitted evidence against methodology-defined requirements.
    All rules come from metadata — zero hardcoded sector logic.
    """

    def validate_submission(
        self,
        requirements: List[Dict[str, Any]],
        submitted_evidence: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Validates a collection of evidence submissions against requirements.

        Args:
            requirements: List of evidence requirement dicts from methodology metadata.
            submitted_evidence: List of evidence dicts with keys like
                {"evidence_type", "file_uri", "file_hash", "metadata_json", "created_at"}.
            context: Optional context for evaluating conditional rules.

        Returns:
            {"is_complete": bool, "results": List[EvidenceValidationResult], "missing": List[str]}
        """
        parsed_requirements = [self._parse_requirement(r) for r in requirements]
        results: List[EvidenceValidationResult] = []
        missing: List[str] = []

        for req in parsed_requirements:
            # Skip conditional requirements if condition is not met
            if req.rule_type == EvidenceRuleType.CONDITIONAL:
                if not self._evaluate_condition(
                    req.condition_expression, context or {}
                ):
                    continue

            # Find matching evidence
            matching = [
                e
                for e in submitted_evidence
                if e.get("evidence_type", "").lower() == req.evidence_type.lower()
            ]

            result = self._validate_requirement(req, matching)
            results.append(result)

            if not result.is_valid and req.rule_type in (
                EvidenceRuleType.REQUIRED,
                EvidenceRuleType.CONDITIONAL,
            ):
                missing.append(req.evidence_type)

        is_complete = len(missing) == 0

        return {
            "is_complete": is_complete,
            "results": [
                {
                    "requirement": r.requirement,
                    "is_valid": r.is_valid,
                    "errors": r.errors,
                    "warnings": r.warnings,
                }
                for r in results
            ],
            "missing": missing,
        }

    def _parse_requirement(self, raw: Dict[str, Any]) -> EvidenceRequirement:
        """Parse a raw requirement dict into an EvidenceRequirement."""
        return EvidenceRequirement(
            evidence_type=raw.get("evidence_type", "unknown"),
            rule_type=EvidenceRuleType(raw.get("rule_type", "required")),
            min_count=raw.get("min_count", 1),
            max_age_hours=raw.get("max_age_hours"),
            min_resolution=raw.get("min_resolution"),
            gps_required=raw.get("gps_required", False),
            gps_bounding_box=raw.get("gps_bounding_box"),
            file_types=raw.get("file_types", []),
            condition_expression=raw.get("condition_expression"),
        )

    def _validate_requirement(
        self, req: EvidenceRequirement, matching_evidence: List[Dict[str, Any]]
    ) -> EvidenceValidationResult:
        """Validate matching evidence against a single requirement."""
        errors: List[str] = []
        warnings: List[str] = []

        # Check minimum count
        if len(matching_evidence) < req.min_count:
            errors.append(
                f"Expected at least {req.min_count} '{req.evidence_type}' evidence, "
                f"got {len(matching_evidence)}"
            )

        for evidence in matching_evidence:
            meta = evidence.get("metadata_json", {})

            # Check max age
            if req.max_age_hours is not None:
                created_str = evidence.get("created_at")
                if created_str:
                    if isinstance(created_str, str):
                        try:
                            created = datetime.fromisoformat(created_str)
                        except ValueError:
                            warnings.append(
                                f"Could not parse created_at: {created_str}"
                            )
                            continue
                    elif isinstance(created_str, datetime):
                        created = created_str
                    else:
                        continue

                    now = datetime.now(timezone.utc)
                    if created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)
                    age_hours = (now - created).total_seconds() / 3600
                    if age_hours > req.max_age_hours:
                        errors.append(
                            f"Evidence '{req.evidence_type}' is {age_hours:.1f}h old, "
                            f"max allowed is {req.max_age_hours}h"
                        )

            # Check GPS requirement
            if req.gps_required:
                lat = meta.get("latitude")
                lon = meta.get("longitude")
                if lat is None or lon is None:
                    errors.append(
                        f"Evidence '{req.evidence_type}' is missing GPS coordinates"
                    )
                elif req.gps_bounding_box:
                    bb = req.gps_bounding_box
                    if not (bb.get("min_lat", -90) <= lat <= bb.get("max_lat", 90)):
                        errors.append(f"Latitude {lat} is outside bounding box")
                    if not (bb.get("min_lon", -180) <= lon <= bb.get("max_lon", 180)):
                        errors.append(f"Longitude {lon} is outside bounding box")

            # Check file type
            if req.file_types:
                file_uri = evidence.get("file_uri", "")
                ext = file_uri.rsplit(".", 1)[-1].lower() if "." in file_uri else ""
                if ext not in [ft.lower() for ft in req.file_types]:
                    errors.append(
                        f"Evidence '{req.evidence_type}' file type '.{ext}' not in allowed types: {req.file_types}"
                    )

            # Check resolution
            if req.min_resolution is not None:
                width = meta.get("width", 0)
                height = meta.get("height", 0)
                if width < req.min_resolution or height < req.min_resolution:
                    warnings.append(
                        f"Evidence '{req.evidence_type}' resolution {width}x{height} "
                        f"below minimum {req.min_resolution}px"
                    )

        is_valid = len(errors) == 0
        return EvidenceValidationResult(
            is_valid=is_valid,
            requirement=req.evidence_type,
            errors=errors,
            warnings=warnings,
        )

    def _evaluate_condition(
        self, expression: Optional[str], context: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a simple conditional expression against context.
        Only supports basic key lookups for safety — no eval().
        """
        if not expression:
            return True

        # Simple format: "key == value" or "key != value" or "key"
        expression = expression.strip()

        if "==" in expression:
            key, value = [
                s.strip().strip('"').strip("'") for s in expression.split("==", 1)
            ]
            return str(context.get(key, "")) == value
        elif "!=" in expression:
            key, value = [
                s.strip().strip('"').strip("'") for s in expression.split("!=", 1)
            ]
            return str(context.get(key, "")) != value
        else:
            # Truthiness check
            return bool(context.get(expression))
