import logging
from typing import Any, Dict, List
import asteval

logger = logging.getLogger("verifield.methodology.validator")


class ValidationResult:
    def __init__(self, is_valid: bool, errors: List[str]):
        self.is_valid = is_valid
        self.errors = errors


class BaseValidationEngine:
    """
    Evaluates dynamic ValidationRules associated with a MethodologyVersion.
    """

    def validate(
        self, activity_data: Dict[str, Any], validation_rules: list
    ) -> ValidationResult:
        """
        Evaluate all validation rules against incoming activity data.
        Returns a ValidationResult indicating success or failure with errors.
        """
        errors = []

        # Create an evaluation context
        context = dict(activity_data)

        aeval = asteval.Interpreter(use_numpy=False)
        for k, v in context.items():
            aeval.symtable[k] = v

        for rule in validation_rules:
            expression = rule.expression
            try:
                # Expression should evaluate to True if valid, False if invalid
                # E.g. "fuel_consumption > 0 and fuel_consumption < 1000"
                result = aeval.eval(expression)
                if not result:
                    errors.append(
                        rule.error_message or f"Validation failed for rule {rule.code}"
                    )
            except Exception as e:
                logger.error(
                    f"Error evaluating validation rule {rule.code} expression '{expression}': {e}"
                )
                # Treat evaluation failure as a validation failure
                errors.append(f"Validation error evaluating rule {rule.code}: {e}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)


validation_engine = BaseValidationEngine()
