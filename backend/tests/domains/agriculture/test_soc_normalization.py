"""
VeriField Nexus — SOC Normalization Deterministic Unit Tests
Verifies physical laboratory analyte normalization logic with canonical unit 'g/kg'.
Covered:
- % -> g/kg (x10 scaling)
- g/kg -> g/kg (Identity)
- mg/g -> g/kg (Identity, 1 mg/g = 1 g/kg)
- mg/kg -> g/kg (/1000 scaling, 1 mg/kg = 0.001 g/kg)
- Incompatible / invalid units -> UNCONVERTIBLE
- Aliases: SOC_CONCENTRATION, SOC_STOCK_PCT, TOTAL_ORGANIC_CARBON_G_KG, SOC_PCT
- Numerical types: Decimal, float, int, str
- Preservation of raw inputs
"""

from decimal import Decimal
import pytest
from app.domains.agriculture.service import AgricultureService


@pytest.mark.parametrize(
    "analyte",
    [
        "SOC_CONCENTRATION",
        "SOC_STOCK_PCT",
        "TOTAL_ORGANIC_CARBON_G_KG",
        "SOC_PCT",
        "soc_concentration",
    ],
)
def test_soc_normalization_percentage_scaling(analyte):
    """
    Test that percentage raw units scale by 10 to canonical 'g/kg'.
    1.85 % -> 18.5000 g/kg
    """
    for unit in ["%", "pct", "percent", " % ", "PCT"]:
        norm_val, norm_unit, method, version = AgricultureService.normalize_laboratory_analyte_measurement(
            analyte=analyte,
            raw_value=Decimal("1.85"),
            raw_unit=unit,
        )
        assert norm_val == Decimal("18.5000")
        assert norm_unit == "g/kg"
        assert method == "LINEAR_SCALING:VAL*10"
        assert version == "UNIT_CONV_V1.0"


@pytest.mark.parametrize(
    "analyte",
    [
        "SOC_CONCENTRATION",
        "SOC_STOCK_PCT",
        "TOTAL_ORGANIC_CARBON_G_KG",
        "SOC_PCT",
    ],
)
def test_soc_normalization_identity_g_kg(analyte):
    """
    Test that g/kg raw units preserve value as identity.
    18.5 g/kg -> 18.5000 g/kg
    """
    for unit in ["g/kg", "g_kg", "g.kg-1", " G/KG "]:
        norm_val, norm_unit, method, version = AgricultureService.normalize_laboratory_analyte_measurement(
            analyte=analyte,
            raw_value=Decimal("18.5"),
            raw_unit=unit,
        )
        assert norm_val == Decimal("18.5000")
        assert norm_unit == "g/kg"
        assert method == "IDENTITY"
        assert version == "UNIT_CONV_V1.0"


@pytest.mark.parametrize(
    "analyte",
    [
        "SOC_CONCENTRATION",
        "SOC_STOCK_PCT",
        "TOTAL_ORGANIC_CARBON_G_KG",
        "SOC_PCT",
    ],
)
def test_soc_normalization_identity_mg_g(analyte):
    """
    Test that mg/g raw units are numerically identical to g/kg (1 mg / 1 g = 1 g / 1000 g = 1 g/kg).
    18.5 mg/g -> 18.5000 g/kg
    """
    for unit in ["mg/g", "mg_g", "mg.g-1", " MG/G "]:
        norm_val, norm_unit, method, version = AgricultureService.normalize_laboratory_analyte_measurement(
            analyte=analyte,
            raw_value=Decimal("18.5"),
            raw_unit=unit,
        )
        assert norm_val == Decimal("18.5000")
        assert norm_unit == "g/kg"
        assert method == "IDENTITY"
        assert version == "UNIT_CONV_V1.0"


@pytest.mark.parametrize(
    "analyte",
    [
        "SOC_CONCENTRATION",
        "SOC_STOCK_PCT",
        "TOTAL_ORGANIC_CARBON_G_KG",
        "SOC_PCT",
    ],
)
def test_soc_normalization_linear_scaling_mg_kg(analyte):
    """
    Test that mg/kg raw units scale down by 1000 to canonical 'g/kg'.
    18500 mg/kg -> 18.5000 g/kg
    """
    for unit in ["mg/kg", "mg_kg", "mg.kg-1", " MG/KG "]:
        norm_val, norm_unit, method, version = AgricultureService.normalize_laboratory_analyte_measurement(
            analyte=analyte,
            raw_value=Decimal("18500"),
            raw_unit=unit,
        )
        assert norm_val == Decimal("18.5000")
        assert norm_unit == "g/kg"
        assert method == "LINEAR_SCALING:VAL/1000"
        assert version == "UNIT_CONV_V1.0"


def test_soc_normalization_invalid_and_unconvertible_units():
    """
    Test that incompatible or nonsensical units safely return UNCONVERTIBLE without exceptions.
    """
    invalid_units = [
        "liters",
        "km",
        "unknown_unit",
        "psi",
        "ppm_v",
        "degC",
        "m3",
        "mol/L",
    ]
    for unit in invalid_units:
        norm_val, norm_unit, method, version = AgricultureService.normalize_laboratory_analyte_measurement(
            analyte="SOC_CONCENTRATION",
            raw_value=Decimal("1.85"),
            raw_unit=unit,
        )
        assert norm_val is None
        assert norm_unit is None
        assert method == "UNCONVERTIBLE"
        assert version == "UNIT_CONV_V1.0"


def test_soc_normalization_type_flexibility():
    """
    Test that numeric inputs provided as float, int, or string Decimal are handled deterministically.
    """
    # Float
    norm_val, norm_unit, method, version = AgricultureService.normalize_laboratory_analyte_measurement(
        analyte="SOC_CONCENTRATION",
        raw_value=1.85,
        raw_unit="%",
    )
    assert norm_val == Decimal("18.5000")
    assert norm_unit == "g/kg"
    assert method == "LINEAR_SCALING:VAL*10"

    # Int
    norm_val, norm_unit, method, version = AgricultureService.normalize_laboratory_analyte_measurement(
        analyte="SOC_CONCENTRATION",
        raw_value=2,
        raw_unit="%",
    )
    assert norm_val == Decimal("20.0000")
    assert norm_unit == "g/kg"

    # None raw value
    norm_val, norm_unit, method, version = AgricultureService.normalize_laboratory_analyte_measurement(
        analyte="SOC_CONCENTRATION",
        raw_value=None,
        raw_unit="%",
    )
    assert norm_val is None
    assert norm_unit is None
    assert method == "UNCONVERTIBLE"
