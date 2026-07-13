from typing import Any, Dict, List

from .evaluator import DeterministicEvaluator, EvaluationError
from .planner import ExecutionPlanner


class ExecutionEngine:
    def __init__(self):
        self.planner = ExecutionPlanner()

    def execute(
        self, rules: List[Dict[str, str]], initial_parameters: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Executes a set of calculation rules against an initial parameter state.
        Returns a dictionary with the final state and an audit trail.
        """
        # Plan execution order
        sorted_rules = self.planner.plan(rules)

        # Initialize state with input parameters
        state = initial_parameters.copy()
        audit_trail = []

        for rule in sorted_rules:
            output = rule["output_parameter"]
            formula = rule["formula"]

            evaluator = DeterministicEvaluator(state)
            try:
                result = evaluator.evaluate(formula)
                state[output] = result

                # Append to full audit trail
                audit_trail.append(
                    {
                        "rule": output,
                        "formula": formula,
                        "result": result,
                        "evaluation_steps": evaluator.audit_trail,
                    }
                )

            except EvaluationError as e:
                audit_trail.append(
                    {"rule": output, "formula": formula, "error": str(e)}
                )
                raise RuntimeError(
                    f"Failed to evaluate {output} = {formula}: {str(e)}"
                ) from e

        return {"final_state": state, "audit_trail": audit_trail}
