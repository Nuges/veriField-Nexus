import logging
from typing import Any, Dict

logger = logging.getLogger("verifield.rules")


class RuleEngine:
    """
    Evaluates dynamic compliance rules against a given context.
    Provides metadata-driven logic evaluation without hardcoding.
    """

    @staticmethod
    def evaluate(rule_definition: Dict[str, Any], target_data: Dict[str, Any]) -> bool:
        """
        Evaluate a simple JSON rule against the target's data.
        Example rule: {"field": "status", "operator": "equals", "value": "ACTIVE"}
        """
        try:
            field = rule_definition.get("field")
            operator = rule_definition.get("operator")
            expected_value = rule_definition.get("value")

            if not field or not operator:
                return True  # Malformed rules pass by default or we could fail them

            actual_value = target_data.get(field)

            if operator == "equals":
                return str(actual_value) == str(expected_value)
            elif operator == "not_equals":
                return str(actual_value) != str(expected_value)
            elif operator == "exists":
                return actual_value is not None
            elif operator == "contains":
                if isinstance(actual_value, list):
                    return expected_value in actual_value
                elif isinstance(actual_value, str):
                    return str(expected_value) in actual_value
                return False

            logger.warning(f"Unsupported operator in rule: {operator}")
            return False

        except Exception as e:
            logger.error(f"Rule evaluation failed: {e}")
            return False

    @staticmethod
    def execute_rule_pack(rules: list, target_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a collection of rules and returns a detailed compliance report.
        """
        passed = 0
        failed = 0
        details = []

        for rule in rules:
            result = RuleEngine.evaluate(rule, target_data)
            if result:
                passed += 1
            else:
                failed += 1
            details.append({"rule": rule, "passed": result})

        return {
            "total": len(rules),
            "passed": passed,
            "failed": failed,
            "is_compliant": failed == 0,
            "details": details,
        }
