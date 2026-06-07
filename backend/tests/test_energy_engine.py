"""
=============================================================================
VeriField Nexus — Energy Displacement Calculation Engine Tests
=============================================================================
Validates:
  1. Baseline emissions calculation for diesel, petrol, and other fuels.
  2. Project emissions (post-installation backup generator / gas) calculations.
  3. Solar PV generation estimates.
  4. Full quantification pipeline with different data source uncertainty tiers.
  5. Integration with property sustainability metrics.
=============================================================================
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Import stubs and paths
# ---------------------------------------------------------------------------
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.energy_displacement_engine import EnergyDisplacementEngine, FUEL_EMISSION_FACTORS, UNCERTAINTY_DISCOUNTS
from app.models.activity import Activity
from app.models.project import Project
from app.models.carbon_calculation import CarbonCalculation
from app.models.property import Property


class FakeActivity:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid.uuid4())
        self.user_id = kwargs.get("user_id", uuid.uuid4())
        self.property_id = kwargs.get("property_id", uuid.uuid4())
        self.activity_type = kwargs.get("activity_type", "HYBRID_ENERGY")
        self.activity_data = kwargs.get("activity_data", {})
        self.status = kwargs.get("status", "verified")
        self.latitude = kwargs.get("latitude", 6.5244)
        self.longitude = kwargs.get("longitude", 3.3792)
        self.captured_at = kwargs.get("captured_at", datetime.now(timezone.utc))
        self.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
        self.image_url = kwargs.get("image_url", "https://example.com/solar.jpg")


class FakeProject:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid.uuid4())
        self.methodology_id = kwargs.get("methodology_id", "ENERGY_DISPLACEMENT")
        self.baseline_parameters = kwargs.get("baseline_parameters", {})


class TestEnergyDisplacementEnginePure:
    """Pure unit tests for calculation helper methods (no DB dependency)."""

    def test_baseline_emissions_diesel(self):
        engine = EnergyDisplacementEngine(db=MagicMock())
        data = {
            "baseline_generator_type": "diesel",
            "baseline_fuel_consumption_lph": 5.0,
            "baseline_avg_daily_runtime_hrs": 10.0,
            "baseline_operating_days_per_year": 300,
        }
        params = {}
        # 5.0 * 10.0 * 300 * 2.68 = 15000 * 2.68 = 40,200 kgCO2
        co2, log = engine._calculate_baseline_emissions(data, params)
        assert co2 == 40200.0
        assert log["fuel_type"] == "diesel"
        assert log["annual_fuel_litres"] == 15000.0
        assert log["baseline_kgCO2"] == 40200.0

    def test_baseline_emissions_petrol(self):
        engine = EnergyDisplacementEngine(db=MagicMock())
        data = {
            "baseline_generator_type": "petrol",
            "baseline_fuel_consumption_lph": 4.0,
            "baseline_avg_daily_runtime_hrs": 8.0,
            "baseline_operating_days_per_year": 365,
        }
        params = {}
        # 4.0 * 8.0 * 365 * 2.31 = 11,680 * 2.31 = 26,980.8 kgCO2
        co2, log = engine._calculate_baseline_emissions(data, params)
        assert abs(co2 - 26980.8) < 0.1
        assert log["fuel_type"] == "petrol"

    def test_project_emissions_no_backup(self):
        engine = EnergyDisplacementEngine(db=MagicMock())
        data = {
            "diesel_backup_capacity_kva": 0.0,
            "gas_generator_capacity_kva": 0.0,
        }
        co2, log = engine._calculate_project_emissions(data, {})
        assert co2 == 0.0
        assert len(log["components"]) == 0

    def test_project_emissions_with_diesel_backup(self):
        engine = EnergyDisplacementEngine(db=MagicMock())
        data = {
            "diesel_backup_capacity_kva": 10.0,
            "baseline_avg_daily_runtime_hrs": 10.0,
            "baseline_fuel_consumption_lph": 5.0,
            "baseline_operating_days_per_year": 300,
        }
        # default diesel_backup_runtime_fraction = 0.10 -> backup_runtime = 1.0 hr/day
        # default diesel_backup_fuel_rate_lph = 2.5 (0.5 * 5.0)
        # 2.5 * 1.0 * 300 * 2.68 = 2010 kgCO2
        co2, log = engine._calculate_project_emissions(data, {})
        assert abs(co2 - 2010.0) < 0.1
        assert len(log["components"]) == 1
        assert log["components"][0]["source"] == "diesel_backup"
        assert log["components"][0]["runtime_hrs_day"] == 1.0

    def test_project_emissions_with_gas_generator(self):
        engine = EnergyDisplacementEngine(db=MagicMock())
        data = {
            "diesel_backup_capacity_kva": 0.0,
            "gas_generator_capacity_kva": 20.0,
            "baseline_operating_days_per_year": 365,
        }
        # default gas_runtime_hrs_day = 4.0
        # default gas_fuel_m3_per_hr = 20 * 0.25 = 5.0 m3/hr
        # 5.0 * 4.0 * 365 * 1.89 = 13,797 kgCO2
        co2, log = engine._calculate_project_emissions(data, {})
        assert abs(co2 - 13797.0) < 0.1
        assert len(log["components"]) == 1
        assert log["components"][0]["source"] == "gas_generator"

    def test_solar_generation_estimate(self):
        engine = EnergyDisplacementEngine(db=MagicMock())
        data = {
            "solar_capacity_kwp": 15.0,
            "avg_sun_hours": 5.5,
            "system_efficiency": 0.82,
        }
        # 15.0 * 5.5 * 0.82 * 365 = 24692.25 kWh
        kwh, log = engine._estimate_solar_generation(data, {})
        assert abs(kwh - 24692.25) < 0.1
        assert log["estimated_annual_mwh"] == 24.692


@pytest.mark.anyio
class TestEnergyDisplacementEngineAsync:
    """Asynchronous tests for full activity quantification pipeline."""

    async def test_quantify_activity_success_smart_inverter(self):
        # Setup mocks
        db = AsyncMock()
        db.add = MagicMock()
        engine = EnergyDisplacementEngine(db)

        activity_id = uuid.uuid4()
        project_id = uuid.uuid4()
        property_id = uuid.uuid4()

        fake_act = FakeActivity(
            id=activity_id,
            property_id=property_id,
            status="verified",
            activity_data={
                "site_id": "SITE-001",
                "data_source": "smart_inverter_api",
                "baseline_generator_type": "diesel",
                "baseline_fuel_consumption_lph": 6.0,
                "baseline_avg_daily_runtime_hrs": 12.0,
                "baseline_operating_days_per_year": 365,
                "solar_capacity_kwp": 20.0,
                "avg_sun_hours": 5.0,
                "system_efficiency": 0.80,
                "is_monthly_check": False, # Treat as annual to avoid division by 12 in the main assertion
            }
        )

        fake_proj = FakeProject(
            id=project_id,
            baseline_parameters={"leakage_factor": 0.05}
        )

        # Baseline: 6.0 * 12.0 * 365 * 2.68 = 70430.4 kgCO2
        # Project: 0.0 kgCO2 (no backup, no gas generator)
        # Gross reductions = 70430.4 kgCO2
        # Smart Inverter Discount = 5% -> after_uncertainty = 70430.4 * 0.95 = 66908.88
        # Leakage = 5% -> net_reductions = 66908.88 * 0.95 = 63563.436
        # net_tco2e = 63.5634 tCO2e

        # Mock database queries
        db.execute.side_return = [
            MagicMock(scalar_one_or_none=lambda: fake_act),
            MagicMock(scalar_one_or_none=lambda: fake_proj)
        ]

        # Intercept database queries
        async def mock_execute(query):
            # Try to determine if it's querying Activity, Project, or Property
            query_str = str(query)
            mock_result = MagicMock()
            if "activity" in query_str:
                mock_result.scalar_one_or_none.return_value = fake_act
            elif "project" in query_str:
                mock_result.scalar_one_or_none.return_value = fake_proj
            elif "property" in query_str:
                # Mock property sustainability metrics update
                fake_prop = Property(id=property_id, sustainability_metrics={})
                mock_result.scalar_one_or_none.return_value = fake_prop
            return mock_result

        db.execute.side_effect = mock_execute

        # Run quantification
        calc = await engine.quantify_activity(activity_id, project_id)

        # Assertions
        assert calc is not None
        assert calc.methodology_used == "ENERGY_DISPLACEMENT"
        assert calc.status == "calculated"
        assert abs(calc.tco2e_generated - 63.5634) < 0.1
        assert calc.calculation_log["mrv_data_source"] == "smart_inverter_api"
        assert calc.calculation_log["reductions"]["uncertainty_discount_pct"] == 5.0
        assert calc.calculation_log["reductions"]["leakage_factor_pct"] == 5.0

        # Verify db.add was called
        assert db.add.call_count >= 1

    async def test_quantify_activity_not_verified_throws_error(self):
        db = AsyncMock()
        db.add = MagicMock()
        engine = EnergyDisplacementEngine(db)
        activity_id = uuid.uuid4()

        # Non-verified activity
        fake_act = FakeActivity(id=activity_id, status="pending")
        db.execute.return_value = MagicMock(scalar_one_or_none=lambda: fake_act)

        with pytest.raises(ValueError, match="Cannot quantify non-verified activity"):
            await engine.quantify_activity(activity_id)


@pytest.mark.anyio
class TestGPSValidator:
    """Validates the GPSValidator adapts correctly to new activity types."""

    async def test_gps_validator_hybrid_energy(self):
        from app.services.gps_validator import GPSValidator
        db = AsyncMock()
        # Mock _detect_environment return value
        validator = GPSValidator(db)
        
        # Test HYBRID_ENERGY type resolutions
        with patch.object(validator, "_detect_environment", return_value="URBAN"):
            with patch.object(validator, "_find_nearby", return_value=[]):
                res = await validator.check_duplicate(6.5244, 3.3792, "HYBRID_ENERGY")
                assert res["environment_type"] == "URBAN"
                assert res["radius_used_m"] == 50
                assert res["duplicate_flag"] is False

        with patch.object(validator, "_detect_environment", return_value="RURAL"):
            with patch.object(validator, "_find_nearby", return_value=[]):
                res = await validator.check_duplicate(6.5244, 3.3792, "HYBRID_ENERGY")
                assert res["environment_type"] == "RURAL"
                assert res["radius_used_m"] == 100

    async def test_gps_validator_fallback_other(self):
        from app.services.gps_validator import GPSValidator
        db = AsyncMock()
        validator = GPSValidator(db)
        
        # Test unknown/other type resolutions (fallback OTHER)
        with patch.object(validator, "_detect_environment", return_value="URBAN"):
            with patch.object(validator, "_find_nearby", return_value=[]):
                res = await validator.check_duplicate(6.5244, 3.3792, "SOME_UNKNOWN_TYPE")
                assert res["environment_type"] == "URBAN"
                assert res["radius_used_m"] == 20

        with patch.object(validator, "_detect_environment", return_value="RURAL"):
            with patch.object(validator, "_find_nearby", return_value=[]):
                res = await validator.check_duplicate(6.5244, 3.3792, "SOME_UNKNOWN_TYPE")
                assert res["environment_type"] == "RURAL"
                assert res["radius_used_m"] == 50

