import logging
import math
import asteval
from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple

logger = logging.getLogger("verifield.methodology.calculator")


class BaseMethodologyCalculator(ABC):
    """
    Abstract base class for all methodology calculators.
    Every custom calculator MUST inherit from this.
    """

    @abstractmethod
    def quantify(
        self,
        activity_data: Dict[str, Any],
        baseline_parameters: Dict[str, Any],
        calculation_rules: list,
        emission_factors: Dict[str, float],
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Execute credit calculations.
        Returns:
            Tuple[float, Dict[str, Any]]: (calculated tCO2e, detailed calculation log trace)
        """
        pass


class DynamicMetadataCalculator(BaseMethodologyCalculator):
    """
    Default dynamic calculator that evaluates mathematical expressions
    from the database (`MethodologyCalculationRule.formula`).
    """

    def quantify(
        self,
        activity_data: Dict[str, Any],
        baseline_parameters: Dict[str, Any],
        calculation_rules: list,
        emission_factors: Dict[str, float],
    ) -> Tuple[float, Dict[str, Any]]:

        # Merge all inputs into a single evaluation context
        context = {}
        context.update(baseline_parameters)
        context.update(activity_data)
        context.update(emission_factors)

        # Use asteval for sandboxed evaluation of mathematical expressions
        aeval = asteval.Interpreter(use_numpy=False)
        for k, v in context.items():
            aeval.symtable[k] = v

        total_tco2e = 0.0
        logs = []

        for rule in calculation_rules:
            formula = rule.formula
            try:
                # E.g. formula might be "(baseline_fuel - project_fuel) * ef_tco2_tj"
                result = aeval.eval(formula)

                # Assume the last rule evaluated is the final tCO2e
                total_tco2e = float(result)

                # Update context with this rule's output so subsequent rules can use it
                # For simplicity, we just store it as 'result_{rule.code}'
                context[f"result_{rule.code}"] = result

                logs.append(
                    {"rule_code": rule.code, "formula": formula, "result": result}
                )
            except Exception as e:
                logger.error(
                    f"Error evaluating rule {rule.code} formula '{formula}': {e}"
                )
                logs.append(
                    {"rule_code": rule.code, "formula": formula, "error": str(e)}
                )
                # We could raise an error here, but for now we'll just fail gracefully
                return 0.0, {
                    "error": f"Failed evaluating {rule.code}: {e}",
                    "logs": logs,
                }

        return total_tco2e, {
            "inputs": {k: v for k, v in context.items() if not k.startswith("result_")},
            "steps": logs,
            "final_tco2e": total_tco2e,
        }
