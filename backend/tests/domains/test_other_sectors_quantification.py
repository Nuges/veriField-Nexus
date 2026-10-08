"""
=============================================================================
VeriField Nexus — Runtime Verification for Implemented Sector Methodologies
=============================================================================
Validates mathematical calculations, boundary parameters, and anomaly/fraud
detection for implemented methodologies:
1. Clean Cookstoves (AMS_II_G) -> CookstoveQuantificationEngine
2. Hybrid Energy & Mini-grids (AMS_I_F) -> EnergyQuantificationEngine
3. EV Mobility (AMS_III_C) -> EVQuantificationEngine
=============================================================================
"""

import datetime
import uuid
import pytest

from app.domains.cookstoves.service import CookstoveQuantificationEngine
from app.domains.cookstoves.schemas import UsageSurveyCreate
from app.domains.cookstoves.models import HouseholdBeneficiary, CookstoveDevice

from app.domains.energy.service import EnergyQuantificationEngine
from app.domains.energy.schemas import EnergyTelemetryCreate

from app.domains.ev.service import EVQuantificationEngine
from app.domains.ev.schemas import EVChargingSessionCreate
from app.domains.ev.models import EVChargingStation


def test_cookstove_ams_ii_g_quantification_and_fraud_rules():
    """
    Verifies AMS_II_G Cookstove Quantification Engine.
    Formula: Annual Reduction (tCO2e) = Annual Saved Tonnes * f_nrb (0.85) * ef_biomass (1.68)
    """
    hh = HouseholdBeneficiary(
        id=uuid.uuid4(),
        baseline_fuel_kg_per_day=5.0
    )
    stove = CookstoveDevice(id=uuid.uuid4())

    # Case 1: Standard valid survey (5.0 baseline - 2.0 consumed = 3.0 kg/day saved)
    # Annual saved = 3.0 * 365 / 1000 = 1.095 tonnes
    # Reduction = 1.095 * 0.85 * 1.68 = 1.56366 -> 1.564 tCO2e
    valid_survey = UsageSurveyCreate(
        stove_id=stove.id,
        surveyor_user_id=uuid.uuid4(),
        survey_date=datetime.date.today(),
        is_stove_in_use=True,
        reported_daily_usage_hours=4.0,
        fuel_consumed_kg_per_day=2.0,
        is_primary_cooking_method=True,
        thermal_tampering_detected=False
    )
    reduction, has_fraud, reason = CookstoveQuantificationEngine.calculate_emissions_reduction(
        valid_survey, hh, stove
    )
    assert reduction == 1.564
    assert has_fraud is False
    assert reason is None

    # Case 2: Stove not in use returns 0.0
    unused_survey = UsageSurveyCreate(
        stove_id=stove.id,
        surveyor_user_id=uuid.uuid4(),
        survey_date=datetime.date.today(),
        is_stove_in_use=False,
        reported_daily_usage_hours=0.0,
        fuel_consumed_kg_per_day=0.0,
        is_primary_cooking_method=False,
        thermal_tampering_detected=False
    )
    reduction_0, has_fraud_0, reason_0 = CookstoveQuantificationEngine.calculate_emissions_reduction(
        unused_survey, hh, stove
    )
    assert reduction_0 == 0.0
    assert has_fraud_0 is False

    # Case 3: Fraud detection - unrealistic hours (> 14 hrs/day)
    excess_hours_survey = UsageSurveyCreate(
        stove_id=stove.id,
        surveyor_user_id=uuid.uuid4(),
        survey_date=datetime.date.today(),
        is_stove_in_use=True,
        reported_daily_usage_hours=16.0,
        fuel_consumed_kg_per_day=2.0,
        is_primary_cooking_method=True,
        thermal_tampering_detected=False
    )
    _, has_fraud_hours, reason_hours = CookstoveQuantificationEngine.calculate_emissions_reduction(
        excess_hours_survey, hh, stove
    )
    assert has_fraud_hours is True
    assert "Unrealistic daily usage duration" in reason_hours

    # Case 4: Fraud detection - zero fuel reported despite active cooking
    zero_fuel_survey = UsageSurveyCreate(
        stove_id=stove.id,
        surveyor_user_id=uuid.uuid4(),
        survey_date=datetime.date.today(),
        is_stove_in_use=True,
        reported_daily_usage_hours=3.0,
        fuel_consumed_kg_per_day=0.0,
        is_primary_cooking_method=True,
        thermal_tampering_detected=False
    )
    _, has_fraud_zero, reason_zero = CookstoveQuantificationEngine.calculate_emissions_reduction(
        zero_fuel_survey, hh, stove
    )
    assert has_fraud_zero is True
    assert "Zero fuel consumption reported despite active cooking" in reason_zero


def test_energy_ams_i_f_quantification_and_anomalies():
    """
    Verifies AMS_I_F Hybrid Energy Quantification Engine.
    Formula: Net Avoided CO2e (t) = ((Solar kWh + Battery kWh) * Baseline Diesel EF) / 1000
    """
    asset_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.timezone.utc)

    # Case 1: Standard valid generation
    # Clean kWh = 100 + 20 = 120 kWh
    # Net CO2e = (120 * 0.8) / 1000 = 0.096 tCO2e
    valid_reading = EnergyTelemetryCreate(
        solar_asset_id=asset_id,
        timestamp=now,
        solar_generation_kwh=100.0,
        battery_discharge_kwh=20.0,
        diesel_generation_kwh=50.0,
        diesel_fuel_consumed_liters=15.0,
        grid_displaced_kwh=120.0
    )
    clean_kwh, net_co2e, has_ano, reason = EnergyQuantificationEngine.calculate_co2_avoidance(
        data=valid_reading,
        baseline_diesel_ef_kg_kwh=0.8,
        capacity_kwp=15.0
    )
    assert clean_kwh == 120.0
    assert net_co2e == 0.096
    assert has_ano is False
    assert reason is None

    # Case 2: Anomaly - Generation exceeds physical capacity (capacity_kwp * 24)
    # 15 kWp * 24h = 360 kWh theoretical max. Reading has 400 kWh.
    over_capacity_reading = EnergyTelemetryCreate(
        solar_asset_id=asset_id,
        timestamp=now,
        solar_generation_kwh=400.0,
        battery_discharge_kwh=0.0,
        diesel_generation_kwh=0.0,
        diesel_fuel_consumed_liters=0.0,
        grid_displaced_kwh=400.0
    )
    _, _, has_ano_cap, reason_cap = EnergyQuantificationEngine.calculate_co2_avoidance(
        data=over_capacity_reading,
        baseline_diesel_ef_kg_kwh=0.8,
        capacity_kwp=15.0
    )
    assert has_ano_cap is True
    assert "Solar generation exceeds physical theoretical maximum array capacity" in reason_cap

    # Case 3: Anomaly - Diesel consumed without electrical generation
    fuel_inconsistent_reading = EnergyTelemetryCreate(
        solar_asset_id=asset_id,
        timestamp=now,
        solar_generation_kwh=50.0,
        battery_discharge_kwh=0.0,
        diesel_generation_kwh=0.0,
        diesel_fuel_consumed_liters=25.0,
        grid_displaced_kwh=50.0
    )
    _, _, has_ano_fuel, reason_fuel = EnergyQuantificationEngine.calculate_co2_avoidance(
        data=fuel_inconsistent_reading,
        baseline_diesel_ef_kg_kwh=0.8,
        capacity_kwp=15.0
    )
    assert has_ano_fuel is True
    assert "Diesel fuel consumed without registered electrical generation" in reason_fuel


def test_ev_ams_iii_c_quantification_and_anomalies():
    """
    Verifies AMS_III_C EV Mobility Quantification Engine.
    Formula: Net Avoided Emissions (kg CO2e) = Baseline ICE - EV Grid Emissions
    """
    station = EVChargingStation(
        id=uuid.uuid4(),
        grid_emission_factor_kg_kwh=0.5,
        renewable_source_pct=20.0,
        max_output_kw=50.0
    )
    now = datetime.datetime.now(datetime.timezone.utc)

    # Case 1: Standard valid charging session
    # Distance: 100 km, ICE_GASOLINE: 190 g/km -> Baseline: (100 * 190) / 1000 = 19.0 kg CO2e
    # Effective Grid EF: 0.5 * (1 - 0.20) = 0.40 kg CO2e/kWh
    # EV Grid Emissions: 20 kWh * 0.40 = 8.0 kg CO2e
    # Net Avoided: 19.0 - 8.0 = 11.0 kg CO2e
    valid_session = EVChargingSessionCreate(
        station_id=station.id,
        vehicle_vin="1HGCR2F83HA000000",
        vehicle_identifier="EV-FLEET-01",
        baseline_vehicle_type="ICE_GASOLINE",
        distance_displaced_km=100.0,
        start_time=now - datetime.timedelta(hours=2),
        end_time=now,
        energy_consumed_kwh=20.0,
        battery_state_of_health_pct=95.0
    )
    avoided_kg, has_ano, reason = EVQuantificationEngine.calculate_avoided_emissions(
        valid_session, station
    )
    assert avoided_kg == 11.0
    assert has_ano is False
    assert reason is None

    # Case 2: Anomaly - Abnormally high consumption (> 0.8 kWh/km)
    high_eff_session = EVChargingSessionCreate(
        station_id=station.id,
        vehicle_vin="1HGCR2F83HA000000",
        vehicle_identifier="EV-FLEET-02",
        baseline_vehicle_type="ICE_GASOLINE",
        distance_displaced_km=20.0,
        start_time=now - datetime.timedelta(hours=1),
        end_time=now,
        energy_consumed_kwh=25.0,  # 1.25 kWh/km > 0.8
        battery_state_of_health_pct=95.0
    )
    _, has_ano_high, reason_high = EVQuantificationEngine.calculate_avoided_emissions(
        high_eff_session, station
    )
    assert has_ano_high is True
    assert "Abnormally high energy consumption" in reason_high

    # Case 3: Anomaly - Critical battery degradation (< 60% SoH)
    degraded_battery_session = EVChargingSessionCreate(
        station_id=station.id,
        vehicle_vin="1HGCR2F83HA000000",
        vehicle_identifier="EV-FLEET-03",
        baseline_vehicle_type="ICE_GASOLINE",
        distance_displaced_km=100.0,
        start_time=now - datetime.timedelta(hours=2),
        end_time=now,
        energy_consumed_kwh=20.0,
        battery_state_of_health_pct=55.0  # < 60%
    )
    _, has_ano_soh, reason_soh = EVQuantificationEngine.calculate_avoided_emissions(
        degraded_battery_session, station
    )
    assert has_ano_soh is True
    assert "Critical battery degradation flag" in reason_soh
