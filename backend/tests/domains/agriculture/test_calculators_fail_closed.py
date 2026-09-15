"""
=============================================================================
VeriField Nexus — Methodology Calculators Fail-Closed Policy Tests
=============================================================================
Tests:
1. Strict fail-closed policy:
   - VM0042CalculatorV22 default status is NOT_CONFIGURED.
   - VM0047CalculatorV11 default status is NOT_CONFIGURED.
   - VM0051CalculatorV11 default status is NOT_CONFIGURED.
2. CalculationResult:
   - is_issuance_eligible is False.
   - issuable_credits_t_co2e is 0.0.
   - warnings and compliance_notes contain clear explanation.
3. Strict validation flag raises MethodologyNotConfiguredError.
=============================================================================
"""

import pytest

from app.domains.agriculture.calculators import (
    CalculationStatus,
    MethodologyMaturityTier,
    MethodologyNotConfiguredError,
    VM0042CalculatorV22,
    VM0047CalculatorV11,
    VM0051CalculatorV11,
)


def test_vm0042_calculator_fail_closed():
    calc = VM0042CalculatorV22()
    assert calc.methodology_code == "VM0042"
    assert calc.version == "2.2"
    assert calc.maturity_tier == MethodologyMaturityTier.MRV_ENABLED
    assert calc.default_status == CalculationStatus.NOT_CONFIGURED

    res = calc.calculate_project_credits(
        project_data={"id": "test-project-1"},
        monitoring_data={"units": 5},
    )
    assert res.status == CalculationStatus.NOT_CONFIGURED
    assert res.is_issuance_eligible is False
    assert res.issuable_credits_t_co2e == 0.0
    assert "VM0042 v2.2 official quantification formulas require registry-verified" in res.compliance_notes

    # With strict validation
    with pytest.raises(MethodologyNotConfiguredError):
        calc.calculate_project_credits(
            project_data={"id": "test-project-1", "strict_validation": True},
            monitoring_data={},
            fail_closed=True,
        )


def test_vm0047_calculator_fail_closed():
    calc = VM0047CalculatorV11()
    assert calc.methodology_code == "VM0047"
    assert calc.version == "1.1"
    assert calc.default_status == CalculationStatus.NOT_CONFIGURED

    res = calc.calculate_project_credits(
        project_data={"id": "test-project-arr"},
        monitoring_data={},
    )
    assert res.status == CalculationStatus.NOT_CONFIGURED
    assert res.is_issuance_eligible is False
    assert res.issuable_credits_t_co2e == 0.0


def test_vm0051_calculator_fail_closed():
    calc = VM0051CalculatorV11()
    assert calc.methodology_code == "VM0051"
    assert calc.version == "1.1"
    assert calc.default_status == CalculationStatus.NOT_CONFIGURED

    res = calc.calculate_project_credits(
        project_data={"id": "test-project-rice"},
        monitoring_data={},
    )
    assert res.status == CalculationStatus.NOT_CONFIGURED
    assert res.is_issuance_eligible is False
    assert res.issuable_credits_t_co2e == 0.0
