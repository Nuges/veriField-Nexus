import pytest

from app.domains.methodologies.calculation_engine import (
    CycleDetectedError, DeterministicEvaluator, EvaluationError,
    ExecutionEngine, extract_dependencies)


def test_evaluator_basic_math():
    evaluator = DeterministicEvaluator({"A": 10, "B": 5})
    assert evaluator.evaluate("A + B") == 15.0
    assert evaluator.evaluate("A - B") == 5.0
    assert evaluator.evaluate("A * B") == 50.0
    assert evaluator.evaluate("A / B") == 2.0
    assert evaluator.evaluate("A ** 2") == 100.0


def test_evaluator_functions():
    evaluator = DeterministicEvaluator({"A": 100})
    assert evaluator.evaluate("log10(A)") == 2.0
    assert evaluator.evaluate("sqrt(A)") == 10.0
    assert evaluator.evaluate("max(A, 200)") == 200.0


def test_evaluator_security():
    evaluator = DeterministicEvaluator({"A": 10})
    # Disallowed function
    with pytest.raises(EvaluationError):
        evaluator.evaluate("print(A)")

    # OS execution attempt
    with pytest.raises(EvaluationError):
        evaluator.evaluate("__import__('os').system('ls')")

    # Syntax error
    with pytest.raises(EvaluationError):
        evaluator.evaluate("A + * B")


def test_extract_dependencies():
    deps = extract_dependencies("log10(A) + B * C - D")
    assert deps == {"A", "B", "C", "D"}


def test_execution_engine():
    engine = ExecutionEngine()
    rules = [
        {"output_parameter": "ER", "formula": "BE - PE - LE"},
        {"output_parameter": "BE", "formula": "fuel_consumed * emission_factor"},
        {"output_parameter": "PE", "formula": "project_emissions"},
        {"output_parameter": "LE", "formula": "0.05 * BE"},
    ]
    initial = {"fuel_consumed": 100, "emission_factor": 2.5, "project_emissions": 10}

    result = engine.execute(rules, initial)
    state = result["final_state"]

    # BE = 100 * 2.5 = 250
    assert state["BE"] == 250.0
    # PE = 10
    assert state["PE"] == 10.0
    # LE = 0.05 * 250 = 12.5
    assert state["LE"] == 12.5
    # ER = 250 - 10 - 12.5 = 227.5
    assert state["ER"] == 227.5


def test_execution_engine_circular_dependency():
    engine = ExecutionEngine()
    rules = [
        {"output_parameter": "A", "formula": "B + 1"},
        {"output_parameter": "B", "formula": "A + 1"},
    ]
    with pytest.raises(CycleDetectedError):
        engine.execute(rules, {})
