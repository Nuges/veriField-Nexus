import pytest

from app.domains.compliance_engine.validation_rules_engine import \
    ValidationRulesEngine


@pytest.fixture
def engine():
    return ValidationRulesEngine()


def test_passing_boundary_rule(engine):
    rules = [
        {
            "code": "FUEL_MAX",
            "name": "Max Fuel Consumption",
            "expression": "fuel_consumption < 500",
            "error_message": "Fuel consumption exceeds 500 kg",
            "severity": "warning",
            "action": "flag",
        }
    ]
    data = {"fuel_consumption": 200}
    result = engine.evaluate(rules, data)
    assert result["passed"] is True
    assert len(result["violations"]) == 0


def test_failing_boundary_rule(engine):
    rules = [
        {
            "code": "FUEL_MAX",
            "name": "Max Fuel Consumption",
            "expression": "fuel_consumption < 500",
            "error_message": "Fuel consumption exceeds 500 kg",
            "severity": "error",
            "action": "flag",
        }
    ]
    data = {"fuel_consumption": 600}
    result = engine.evaluate(rules, data)
    assert result["passed"] is True  # flag does not block
    assert len(result["violations"]) == 1
    assert result["violations"][0]["rule_code"] == "FUEL_MAX"


def test_blocking_violation(engine):
    rules = [
        {
            "code": "USAGE_RATE_MIN",
            "name": "Minimum Usage Rate",
            "expression": "usage_rate >= 0.1",
            "error_message": "Usage rate is below 10%",
            "severity": "critical",
            "action": "block",
        }
    ]
    data = {"usage_rate": 0.05}
    result = engine.evaluate(rules, data)
    assert result["passed"] is False
    assert len(result["blocking_violations"]) == 1


def test_string_equality(engine):
    rules = [
        {
            "code": "STATUS_CHECK",
            "name": "Status Must Be Active",
            "expression": "status == active",
            "error_message": "Status is not active",
            "severity": "warning",
            "action": "notify",
        }
    ]
    data = {"status": "active"}
    result = engine.evaluate(rules, data)
    assert result["passed"] is True
    assert result["results"][0]["passed"] is True


def test_missing_field_fails(engine):
    rules = [
        {
            "code": "TEMP_CHECK",
            "name": "Temperature Check",
            "expression": "temperature < 100",
            "error_message": "Temperature data missing",
            "severity": "error",
            "action": "flag",
        }
    ]
    data = {}  # temperature not provided
    result = engine.evaluate(rules, data)
    assert len(result["violations"]) == 1


def test_multiple_rules_mixed(engine):
    rules = [
        {
            "code": "R1",
            "name": "Rule 1",
            "expression": "value > 10",
            "error_message": "Value too low",
            "severity": "warning",
            "action": "flag",
        },
        {
            "code": "R2",
            "name": "Rule 2",
            "expression": "value < 1000",
            "error_message": "Value too high",
            "severity": "critical",
            "action": "block",
        },
    ]
    data = {"value": 50}
    result = engine.evaluate(rules, data)
    assert result["passed"] is True
    assert len(result["violations"]) == 0
    assert len(result["results"]) == 2

    # Make R2 fail
    data = {"value": 2000}
    result = engine.evaluate(rules, data)
    assert result["passed"] is False
    assert len(result["blocking_violations"]) == 1
