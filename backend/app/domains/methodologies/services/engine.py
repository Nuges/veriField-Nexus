import math
import random
import uuid
from typing import Any, Dict, List, Optional

import asteval
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domains.methodologies.models.components import (
    CalculationRule, VersionCalculationRule)


class UncertaintyPropagationEngine:
    """
    Handles Monte Carlo simulations for calculating uncertainty
    across complex, chained methodology calculations.
    """

    def __init__(self, rule_pipeline: List[CalculationRule], iterations: int = 1000):
        self.rule_pipeline = rule_pipeline
        self.iterations = iterations

    def _sample_normal(self, mean: float, std_dev: float) -> float:
        return random.gauss(mean, std_dev)

    def _sample_uniform(self, min_val: float, max_val: float) -> float:
        return random.uniform(min_val, max_val)

    def run_simulation(
        self,
        base_inputs: Dict[str, Any],
        input_uncertainties: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Runs Monte Carlo iterations by sampling input distributions and
        re-evaluating the AST pipeline.
        input_uncertainties format: {"fuel_consumed": {"type": "normal", "std_dev": 0.5}}
        """
        results_dist = {rule.code: [] for rule in self.rule_pipeline}

        for _ in range(self.iterations):
            # 1. Sample inputs
            sampled_inputs = base_inputs.copy()
            for key, dist in input_uncertainties.items():
                if key in sampled_inputs and isinstance(
                    sampled_inputs[key], (int, float)
                ):
                    if dist["type"] == "normal":
                        sampled_inputs[key] = self._sample_normal(
                            sampled_inputs[key], dist.get("std_dev", 0)
                        )
                    elif dist["type"] == "uniform":
                        sampled_inputs[key] = self._sample_uniform(
                            dist.get("min", sampled_inputs[key]),
                            dist.get("max", sampled_inputs[key]),
                        )

            # 2. Evaluate pipeline
            aeval = asteval.Interpreter(use_numpy=False)
            for k, v in sampled_inputs.items():
                aeval.symtable[k] = v

            for rule in self.rule_pipeline:
                res = aeval(rule.formula)
                if len(aeval.error) == 0:
                    results_dist[rule.code].append(res)
                    aeval.symtable[rule.code] = res

        # 3. Calculate statistics
        final_stats = {}
        for code, dist in results_dist.items():
            if dist and all(isinstance(x, (int, float)) for x in dist):
                n = len(dist)
                mean = sum(dist) / n
                variance = sum((x - mean) ** 2 for x in dist) / n
                std_dev = math.sqrt(variance)

                # Calculate 90% confidence interval
                sorted_dist = sorted(dist)
                lower_bound = sorted_dist[int(n * 0.05)]
                upper_bound = sorted_dist[int(n * 0.95)]

                final_stats[code] = {
                    "mean": mean,
                    "std_dev": std_dev,
                    "confidence_interval_90": [lower_bound, upper_bound],
                    "relative_uncertainty": (std_dev / mean) if mean != 0 else 0,
                }

        return final_stats


class MethodologyEngine:
    """
    Universal Methodology Engine.
    Executes AST-based calculation rules using safe dynamic evaluation.
    Supports deterministic execution and Monte Carlo uncertainty propagation.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        # Safe math evaluator
        self.aeval = asteval.Interpreter(use_numpy=False)

    async def execute_calculation(
        self,
        version_id: uuid.UUID,
        inputs: Dict[str, Any],
        run_monte_carlo: bool = False,
        input_uncertainties: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Executes all calculation rules for a specific methodology version in sequence.
        """
        rules_res = await self.db.execute(
            select(CalculationRule, VersionCalculationRule.execution_order)
            .join(
                VersionCalculationRule,
                VersionCalculationRule.rule_id == CalculationRule.id,
            )
            .filter(VersionCalculationRule.version_id == version_id)
            .order_by(VersionCalculationRule.execution_order.asc())
        )

        rules_pipeline = [rule for rule, _ in rules_res.all()]

        # Deterministic Pass
        # Merge inputs into the symbol table
        for key, val in inputs.items():
            self.aeval.symtable[key] = val

        results = {"deterministic": {}, "uncertainty": None}

        for rule in rules_pipeline:
            try:
                res = self.aeval(rule.formula)
                if len(self.aeval.error) > 0:
                    raise ValueError(
                        f"AST Evaluation Error in rule {rule.code}: {self.aeval.error}"
                    )

                results["deterministic"][rule.code] = res
                self.aeval.symtable[rule.code] = res

            except Exception as e:
                raise RuntimeError(
                    f"Failed to execute calculation rule {rule.code}: {str(e)}"
                )

        # Stochastic Pass (Monte Carlo)
        if run_monte_carlo and input_uncertainties:
            mc_engine = UncertaintyPropagationEngine(rules_pipeline, iterations=1000)
            results["uncertainty"] = mc_engine.run_simulation(
                inputs, input_uncertainties
            )

        return results
