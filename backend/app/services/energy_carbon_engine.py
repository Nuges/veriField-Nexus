"""
=============================================================================
VeriField Nexus — Energy Carbon Calculation Engine
=============================================================================
Deterministic carbon calculation service aligned with carbon registry
methodologies (AMS-I.F / VM0050). Implements the 3-layer MRV architecture:

    Project (emission factors) → Site (field data) → This Engine (calculation)

Core Calculation Logic:
    1. Baseline Emissions = fuel_rate × runtime × days × emission_factor
    2. Solar Generation = capacity_kwp × sun_hours × efficiency × 365
    3. Displaced Emissions = solar_kwh × grid_emission_factor
    4. CO2 Reduction = Baseline - Displaced (net)
    5. Apply Discounts:
       - Data source uncertainty: smart_inverter_api (5%), hybrid_inverter_manual (10%), analog_manual (20%)
       - Verification adjustments:
         * operational = false → 0% credit (system offline)
         * tamper_detected = true → 50% credit
         * usage_confirmed = false → 30% credit

Trust Score Integration:
    5-factor scoring: GPS, Image, Operational, Usage, Tamper checks.
=============================================================================
"""

from typing import Dict, Any, Optional, Tuple
from datetime import date
import logging

logger = logging.getLogger("verifield.carbon_engine")


# =============================================================================
# IPCC 2006 Default Constants
# =============================================================================

DEFAULT_DIESEL_EMISSION_FACTOR = 2.68   # kgCO2/L diesel
DEFAULT_GRID_EMISSION_FACTOR = 0.7      # kgCO2/kWh grid electricity
DEFAULT_SYSTEM_EFFICIENCY = 0.80        # Solar PV system efficiency
DEFAULT_SUN_HOURS = 5.0                 # Peak sun hours per day
DEFAULT_LEAKAGE_FACTOR = 0.05           # 5% leakage

# Uncertainty discount factors by data source tier
UNCERTAINTY_DISCOUNTS = {
    "smart_inverter_api": 0.05,         # 5% — highest confidence telemetry
    "hybrid_inverter_manual": 0.10,     # 10% — mixed data sources
    "analog_manual": 0.20,             # 20% — manual-only logging
}


# =============================================================================
# Energy Carbon Calculation Engine
# =============================================================================

class EnergyCarbonEngine:
    """
    Pure calculation engine for energy displacement carbon credits.
    
    This engine is stateless — it takes project config and site data as inputs
    and returns calculation results. No database dependency for the core math.
    """

    @staticmethod
    def calculate_energy_carbon(
        project_config: Dict[str, Any],
        site_data: Dict[str, Any],
        trust_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Full carbon calculation for an energy displacement site.

        Args:
            project_config: Project-level configuration (emission factors,
                           methodology, baseline_source). Comes from Project model.
            site_data: Site-level field data (solar capacity, runtime, fuel rate).
                      Comes from Activity.activity_data.
            trust_data: Optional trust verification data (operational status,
                       tamper detection, usage confirmation).

        Returns:
            Dict with full calculation breakdown including audit trail.
        """
        trust_data = trust_data or {}

        # --- Step 1: Calculate Baseline Emissions ---
        baseline_result = EnergyCarbonEngine._calculate_baseline_emissions(
            project_config, site_data
        )

        # --- Step 2: Estimate Solar Generation ---
        solar_result = EnergyCarbonEngine._calculate_solar_generation(
            project_config, site_data
        )

        # --- Step 3: Calculate Displaced Emissions ---
        displaced_result = EnergyCarbonEngine._calculate_displaced_emissions(
            project_config, solar_result["solar_kwh_annual"]
        )

        # --- Step 4: Calculate CO2 Reduction (net) ---
        gross_reduction_kg = max(
            0.0,
            baseline_result["baseline_emissions_kg"] - displaced_result["residual_project_emissions_kg"]
        )
        co2_reduction_kg = baseline_result["baseline_emissions_kg"] - displaced_result["residual_project_emissions_kg"]

        # --- Step 5: Apply Data Source Uncertainty Discount ---
        data_source = site_data.get("data_source", "analog_manual")
        uncertainty_discount = UNCERTAINTY_DISCOUNTS.get(
            data_source, UNCERTAINTY_DISCOUNTS["analog_manual"]
        )
        after_uncertainty_kg = gross_reduction_kg * (1.0 - uncertainty_discount)

        # --- Step 6: Apply Leakage Factor ---
        leakage_factor = float(
            project_config.get("leakage_factor", DEFAULT_LEAKAGE_FACTOR)
        )
        after_leakage_kg = after_uncertainty_kg * (1.0 - leakage_factor)

        # --- Step 7: Apply Verification Adjustments ---
        verification_result = EnergyCarbonEngine._apply_verification_adjustments(
            after_leakage_kg, trust_data
        )
        final_reduction_kg = verification_result["final_reduction_kg"]

        # --- Convert to tCO2e ---
        final_tco2e = round(final_reduction_kg / 1000.0, 4)

        # --- Build full calculation log (audit trail) ---
        calculation_log = {
            "methodology": project_config.get("methodology_id", "ENERGY_DISPLACEMENT"),
            "version": "2.0",
            "architecture": "project_site_engine",
            "data_source": data_source,
            "baseline": baseline_result,
            "solar_generation": solar_result,
            "displaced_emissions": displaced_result,
            "reductions": {
                "gross_reduction_kgCO2": round(gross_reduction_kg, 2),
                "uncertainty_discount_pct": round(uncertainty_discount * 100, 1),
                "after_uncertainty_kgCO2": round(after_uncertainty_kg, 2),
                "leakage_factor_pct": round(leakage_factor * 100, 1),
                "after_leakage_kgCO2": round(after_leakage_kg, 2),
            },
            "verification": verification_result,
            "final": {
                "net_reduction_kgCO2": round(final_reduction_kg, 2),
                "net_reduction_tCO2e": final_tco2e,
            },
            "formula_trace": (
                "Net = (Baseline - Residual) "
                "× (1 - Uncertainty%) × (1 - Leakage%) "
                "× VerificationMultiplier"
            ),
        }

        return {
            "tco2e": final_tco2e,
            "gross_reduction_kg": round(gross_reduction_kg, 2),
            "final_reduction_kg": round(final_reduction_kg, 2),
            "data_source": data_source,
            "uncertainty_discount_pct": round(uncertainty_discount * 100, 1),
            "verification_multiplier": verification_result["verification_multiplier"],
            "calculation_log": calculation_log,
        }

    # =========================================================================
    # Step 1: Baseline Emissions (Pre-Installation Fossil Fuel Use)
    # =========================================================================

    @staticmethod
    def _calculate_baseline_emissions(
        project_config: Dict[str, Any],
        site_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate annual baseline emissions from pre-installation generator usage.

        Formula:
            Baseline_kgCO2 = fuel_rate (L/hr) × runtime (hrs/day) × days/yr
                             × diesel_emission_factor (kgCO2/L)
        """
        baseline_source = project_config.get("baseline_source", "diesel_generator")

        if baseline_source == "grid":
            # Grid-based baseline
            grid_kwh_daily = float(site_data.get("grid_kwh_daily", 50.0))
            days_per_year = int(site_data.get("operating_days_per_year", 365))
            grid_ef = float(project_config.get(
                "grid_emission_factor", DEFAULT_GRID_EMISSION_FACTOR
            ))
            annual_kwh = grid_kwh_daily * days_per_year
            baseline_kg = annual_kwh * grid_ef

            return {
                "source": "grid",
                "grid_kwh_daily": grid_kwh_daily,
                "days_per_year": days_per_year,
                "annual_grid_kwh": round(annual_kwh, 2),
                "grid_emission_factor_kgCO2_per_kWh": grid_ef,
                "baseline_emissions_kg": round(baseline_kg, 2),
            }
        else:
            # Diesel generator baseline (default)
            fuel_rate_lph = float(site_data.get(
                "baseline_fuel_consumption_lph",
                project_config.get("baseline_fuel_consumption_lph", 5.0)
            ))
            daily_runtime = float(site_data.get(
                "baseline_avg_daily_runtime_hrs",
                project_config.get("baseline_avg_daily_runtime_hrs", 12.0)
            ))
            days_per_year = int(site_data.get(
                "operating_days_per_year",
                project_config.get("baseline_operating_days_per_year", 365)
            ))
            diesel_ef = float(project_config.get(
                "diesel_emission_factor", DEFAULT_DIESEL_EMISSION_FACTOR
            ))

            annual_fuel_litres = fuel_rate_lph * daily_runtime * days_per_year
            baseline_kg = annual_fuel_litres * diesel_ef

            return {
                "source": "diesel_generator",
                "fuel_rate_lph": fuel_rate_lph,
                "daily_runtime_hrs": daily_runtime,
                "days_per_year": days_per_year,
                "diesel_emission_factor_kgCO2_per_L": diesel_ef,
                "annual_fuel_litres": round(annual_fuel_litres, 2),
                "baseline_emissions_kg": round(baseline_kg, 2),
            }

    # =========================================================================
    # Step 2: Solar Generation Estimation
    # =========================================================================

    @staticmethod
    def _calculate_solar_generation(
        project_config: Dict[str, Any],
        site_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Estimate annual solar PV generation.

        Formula:
            generation_kwh = capacity_kwp × sun_hours × efficiency × 365
        """
        solar_kwp = float(site_data.get("solar_capacity_kwp", 0.0))
        sun_hours = float(site_data.get(
            "avg_sun_hours",
            project_config.get("avg_sun_hours", DEFAULT_SUN_HOURS)
        ))
        efficiency = float(site_data.get(
            "system_efficiency",
            project_config.get("system_efficiency", DEFAULT_SYSTEM_EFFICIENCY)
        ))

        annual_kwh = solar_kwp * sun_hours * efficiency * 365.0

        return {
            "solar_capacity_kwp": solar_kwp,
            "avg_sun_hours": sun_hours,
            "system_efficiency": efficiency,
            "solar_kwh_annual": round(annual_kwh, 2),
            "solar_mwh_annual": round(annual_kwh / 1000.0, 3),
        }

    # =========================================================================
    # Step 3: Displaced Emissions (Post-Installation)
    # =========================================================================

    @staticmethod
    def _calculate_displaced_emissions(
        project_config: Dict[str, Any],
        solar_kwh_annual: float,
    ) -> Dict[str, Any]:
        """
        Calculate emissions displaced by solar generation and residual
        project emissions from backup systems.

        Solar displaces grid or diesel emissions. Residual emissions
        come from any remaining backup generator usage.
        """
        baseline_source = project_config.get("baseline_source", "diesel_generator")

        if baseline_source == "grid":
            grid_ef = float(project_config.get(
                "grid_emission_factor", DEFAULT_GRID_EMISSION_FACTOR
            ))
            displaced_kg = solar_kwh_annual * grid_ef
            # Residual = whatever grid is still used (assume solar covers its portion)
            residual_kg = 0.0  # Solar fully displaces equivalent grid load

            return {
                "displaced_by_solar_kgCO2": round(displaced_kg, 2),
                "residual_project_emissions_kg": round(residual_kg, 2),
                "displacement_method": "grid_displacement",
            }
        else:
            # Diesel displacement — solar reduces diesel generator runtime
            diesel_ef = float(project_config.get(
                "diesel_emission_factor", DEFAULT_DIESEL_EMISSION_FACTOR
            ))
            # Convert solar kWh to equivalent diesel savings
            # Typical diesel generator: ~3.5 kWh per litre
            diesel_kwh_per_litre = float(project_config.get(
                "diesel_kwh_per_litre", 3.5
            ))
            litres_saved = solar_kwh_annual / diesel_kwh_per_litre
            displaced_kg = litres_saved * diesel_ef

            # Residual diesel for backup (fraction of original)
            backup_fraction = float(project_config.get(
                "diesel_backup_runtime_fraction", 0.10
            ))
            fuel_rate = float(project_config.get(
                "baseline_fuel_consumption_lph", 5.0
            ))
            daily_runtime = float(project_config.get(
                "baseline_avg_daily_runtime_hrs", 12.0
            ))
            days = int(project_config.get(
                "baseline_operating_days_per_year", 365
            ))
            residual_litres = fuel_rate * daily_runtime * backup_fraction * days
            residual_kg = residual_litres * diesel_ef

            return {
                "solar_kwh_annual": round(solar_kwh_annual, 2),
                "diesel_kwh_per_litre": diesel_kwh_per_litre,
                "litres_saved_by_solar": round(litres_saved, 2),
                "displaced_by_solar_kgCO2": round(displaced_kg, 2),
                "backup_fraction": backup_fraction,
                "residual_litres": round(residual_litres, 2),
                "residual_project_emissions_kg": round(residual_kg, 2),
                "displacement_method": "diesel_displacement",
            }

    # =========================================================================
    # Step 7: Verification Adjustments (Trust Score Integration)
    # =========================================================================

    @staticmethod
    def _apply_verification_adjustments(
        reduction_kg: float,
        trust_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Apply verification-based adjustments to emission reductions.

        Adjustment Rules (cumulative multiplier):
            - operational = false  → 0% credit (system offline, no generation)
            - tamper_detected = true → 50% credit (data integrity compromised)
            - usage_confirmed = false → 30% credit (usage not independently verified)

        These adjustments stack multiplicatively.
        """
        multiplier = 1.0
        adjustments = []

        # Check operational status
        operational = trust_data.get("operational", True)
        if not operational:
            multiplier = 0.0
            adjustments.append({
                "factor": "operational",
                "status": False,
                "action": "System offline — 0% credit",
                "multiplier_applied": 0.0,
            })
            # Return immediately — no credit if system is offline
            return {
                "verification_multiplier": 0.0,
                "adjustments": adjustments,
                "final_reduction_kg": 0.0,
            }

        # Check tamper detection
        tamper_detected = trust_data.get("tamper_detected", False)
        if tamper_detected:
            multiplier *= 0.50
            adjustments.append({
                "factor": "tamper_detected",
                "status": True,
                "action": "Data integrity compromised — 50% credit",
                "multiplier_applied": 0.50,
            })

        # Check usage confirmation
        usage_confirmed = trust_data.get("usage_confirmed", True)
        if not usage_confirmed:
            multiplier *= 0.30
            adjustments.append({
                "factor": "usage_confirmed",
                "status": False,
                "action": "Usage not verified — 30% credit",
                "multiplier_applied": 0.30,
            })

        final_kg = reduction_kg * multiplier

        return {
            "verification_multiplier": round(multiplier, 4),
            "adjustments": adjustments if adjustments else [{"factor": "all_clear", "status": True, "action": "Full credit — all checks passed"}],
            "final_reduction_kg": round(final_kg, 2),
        }

    # =========================================================================
    # Trust Score Calculation (5-Factor Engine)
    # =========================================================================

    @staticmethod
    def calculate_trust_score(
        site_data: Dict[str, Any],
        trust_checks: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate a 5-factor trust score for a site submission.

        Factors (each 0-20 points, total 100):
            1. GPS Accuracy     — GPS accuracy within acceptable range
            2. Image Integrity  — Photo hash not duplicated, EXIF present
            3. Operational      — System is generating/operational
            4. Usage Pattern    — Consistent usage patterns detected
            5. Tamper Check     — No evidence of data tampering
        """
        scores = {}
        details = {}

        # Factor 1: GPS Accuracy (0-20)
        gps_accuracy = float(trust_checks.get("gps_accuracy_m", 999))
        if gps_accuracy <= 10:
            scores["gps"] = 20
            details["gps"] = "Excellent GPS accuracy (<10m)"
        elif gps_accuracy <= 30:
            scores["gps"] = 15
            details["gps"] = "Good GPS accuracy (<30m)"
        elif gps_accuracy <= 100:
            scores["gps"] = 10
            details["gps"] = "Fair GPS accuracy (<100m)"
        else:
            scores["gps"] = 5
            details["gps"] = "Poor GPS accuracy (>100m)"

        # Factor 2: Image Integrity (0-20)
        has_image = trust_checks.get("has_image", False)
        image_duplicate = trust_checks.get("image_duplicate", False)
        if has_image and not image_duplicate:
            scores["image"] = 20
            details["image"] = "Unique image with valid hash"
        elif has_image and image_duplicate:
            scores["image"] = 5
            details["image"] = "Duplicate image detected"
        else:
            scores["image"] = 0
            details["image"] = "No image provided"

        # Factor 3: Operational Status (0-20)
        operational = trust_checks.get("operational", True)
        uptime_pct = float(trust_checks.get("system_uptime_pct", 100))
        if operational and uptime_pct >= 90:
            scores["operational"] = 20
            details["operational"] = f"System operational, {uptime_pct}% uptime"
        elif operational and uptime_pct >= 50:
            scores["operational"] = 15
            details["operational"] = f"System operational, {uptime_pct}% uptime"
        elif operational:
            scores["operational"] = 10
            details["operational"] = f"System operational but low uptime ({uptime_pct}%)"
        else:
            scores["operational"] = 0
            details["operational"] = "System offline"

        # Factor 4: Usage Pattern (0-20)
        usage_confirmed = trust_checks.get("usage_confirmed", True)
        usage_consistency = float(trust_checks.get("usage_consistency_score", 1.0))
        if usage_confirmed and usage_consistency >= 0.8:
            scores["usage"] = 20
            details["usage"] = "Usage confirmed with consistent patterns"
        elif usage_confirmed:
            scores["usage"] = 15
            details["usage"] = "Usage confirmed but inconsistent patterns"
        else:
            scores["usage"] = 5
            details["usage"] = "Usage not confirmed"

        # Factor 5: Tamper Check (0-20)
        tamper_detected = trust_checks.get("tamper_detected", False)
        if not tamper_detected:
            scores["tamper"] = 20
            details["tamper"] = "No tampering detected"
        else:
            scores["tamper"] = 0
            details["tamper"] = "Tampering evidence found"

        total_score = sum(scores.values())

        return {
            "total_score": total_score,
            "max_score": 100,
            "normalized": round(total_score / 100.0, 2),
            "factors": scores,
            "details": details,
            "grade": (
                "A" if total_score >= 80 else
                "B" if total_score >= 60 else
                "C" if total_score >= 40 else
                "F"
            ),
        }
