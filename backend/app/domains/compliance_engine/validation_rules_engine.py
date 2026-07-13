"""
Universal Validation Rules Engine

Evaluates metadata-defined validation/QA/QC rules against entity data.
Zero hardcoded sector logic — all rules come from methodology metadata.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List


class RuleSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RuleAction(Enum):
    FLAG = "flag"  # Create an anomaly flag
    BLOCK = "block"  # Block the workflow transition
    NOTIFY = "notify"  # Send a notification
    LOG = "log"  # Log to audit trail only


@dataclass
class ValidationRuleDefinition:
    """A single validation rule from methodology metadata."""

    code: str
    name: str
    expression: str  # e.g., "fuel_consumption < 500"
    error_message: str
    severity: RuleSeverity = RuleSeverity.WARNING
    action: RuleAction = RuleAction.FLAG
    rule_type: str = "boundary"  # boundary, completeness, anomaly, consistency


@dataclass
class RuleEvaluationResult:
    """Result of evaluating a single rule."""

    rule_code: str
    rule_name: str
    passed: bool
    severity: str
    action: str
    message: str


class ValidationRulesEngine:
    """
    Evaluates a set of validation rules against data.
    All rules are metadata-driven.
    """

    # Safe operators for expression evaluation
    SAFE_OPERATORS = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
    }

    def evaluate(
        self, rules: List[Dict[str, Any]], data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate all rules against the provided data.

        Args:
            rules: List of rule definition dicts from methodology metadata.
            data: The data dict to evaluate against (e.g., activity_data).

        Returns:
            {
                "passed": bool,
                "results": List[RuleEvaluationResult],
                "violations": List[RuleEvaluationResult],
                "blocking_violations": List[RuleEvaluationResult]
            }
        """
        parsed_rules = [self._parse_rule(r) for r in rules]
        results: List[RuleEvaluationResult] = []
        violations: List[RuleEvaluationResult] = []
        blocking: List[RuleEvaluationResult] = []

        for rule in parsed_rules:
            passed = self._evaluate_expression(rule.expression, data)
            result = RuleEvaluationResult(
                rule_code=rule.code,
                rule_name=rule.name,
                passed=passed,
                severity=rule.severity.value,
                action=rule.action.value,
                message="" if passed else rule.error_message,
            )
            results.append(result)

            if not passed:
                violations.append(result)
                if rule.action == RuleAction.BLOCK:
                    blocking.append(result)

        overall_passed = len(blocking) == 0

        return {
            "passed": overall_passed,
            "results": [self._result_to_dict(r) for r in results],
            "violations": [self._result_to_dict(r) for r in violations],
            "blocking_violations": [self._result_to_dict(r) for r in blocking],
        }

    def _parse_rule(self, raw: Dict[str, Any]) -> ValidationRuleDefinition:
        """Parse a raw rule dict into a ValidationRuleDefinition."""
        return ValidationRuleDefinition(
            code=raw.get("code", "UNKNOWN"),
            name=raw.get("name", "Unnamed Rule"),
            expression=raw.get("expression", "true"),
            error_message=raw.get("error_message", "Validation failed"),
            severity=RuleSeverity(raw.get("severity", "warning")),
            action=RuleAction(raw.get("action", "flag")),
            rule_type=raw.get("rule_type", "boundary"),
        )

    def _evaluate_expression(self, expression: str, data: Dict[str, Any]) -> bool:
        """
        Safely evaluate a simple comparison expression.
        Supports: "field op value" format.
        Examples:
            "fuel_consumption < 500"
            "usage_rate >= 0.1"
            "status == active"
        """
        expression = expression.strip()

        # Handle boolean literals
        if expression.lower() == "true":
            return True
        if expression.lower() == "false":
            return False

        # Try each operator (longest first to avoid partial matches)
        for op_str in sorted(self.SAFE_OPERATORS.keys(), key=len, reverse=True):
            if op_str in expression:
                parts = expression.split(op_str, 1)
                if len(parts) == 2:
                    left_key = parts[0].strip()
                    right_raw = parts[1].strip()

                    left_value = data.get(left_key)
                    if left_value is None:
                        # Missing data — rule fails
                        return False

                    right_value = self._coerce_value(right_raw)
                    left_value = (
                        self._coerce_value(str(left_value))
                        if not isinstance(left_value, (int, float))
                        else left_value
                    )

                    try:
                        return self.SAFE_OPERATORS[op_str](left_value, right_value)
                    except (TypeError, ValueError):
                        return False

        # Truthiness fallback
        return bool(data.get(expression))

    def _coerce_value(self, raw: str) -> Any:
        """Attempt to coerce a string value to a number, then fall back to string."""
        raw = raw.strip().strip('"').strip("'")
        try:
            if "." in raw:
                return float(raw)
            return int(raw)
        except ValueError:
            return raw

    def _result_to_dict(self, result: RuleEvaluationResult) -> Dict[str, Any]:
        return {
            "rule_code": result.rule_code,
            "rule_name": result.rule_name,
            "passed": result.passed,
            "severity": result.severity,
            "action": result.action,
            "message": result.message,
        }
