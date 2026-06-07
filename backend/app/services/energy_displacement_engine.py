"""
=============================================================================
VeriField Nexus — Energy Displacement Calculation Engine
=============================================================================
Deterministic MRV calculation engine for hybrid energy displacement projects
(Solar, Gas, Diesel conversion). Produces audit-ready carbon credit data
aligned with Verra AMS-I.F and Gold Standard Renewable Energy methodologies.

COMPLETELY INDEPENDENT from the cookstove quantification engine.
No shared logic, no shared constants, no shared parameters.

Supported calculation modes:
  - Smart Inverter API Telemetry (highest integrity, 5% uncertainty discount)
  - Hybrid Inverter + Manual Logs (moderate integrity, 10% discount)
  - Analog Manual Logging (lowest integrity, 20% discount)

All calculations are 100% reproducible, logged, and auditor-traceable.
=============================================================================
"""

import uuid
from typing import Tuple, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.activity import Activity
from app.models.project import Project
from app.models.carbon_calculation import CarbonCalculation


# =============================================================================
# IPCC 2006 Default Emission Factors for Fuel Combustion
# =============================================================================
FUEL_EMISSION_FACTORS = {
    # kgCO2 per litre of fuel consumed
    "diesel": 2.68,        # IPCC default for diesel/gas oil
    "petrol": 2.31,        # IPCC default for motor gasoline
    "heavy_fuel_oil": 3.11, # IPCC default for residual fuel oil
    "natural_gas": 1.89,    # kgCO2 per m³ of natural gas (for gas generators)
}

# Grid emission factor fallback (kgCO2/kWh) for the Nigerian grid
GRID_EMISSION_FACTOR_KG_PER_KWH = 0.43

# Uncertainty discount factors by data source tier
UNCERTAINTY_DISCOUNTS = {
    "smart_inverter_api": 0.05,      # 5% — highest confidence telemetry
    "hybrid_inverter_manual": 0.10,  # 10% — mixed data sources
    "analog_manual": 0.20,           # 20% — manual-only logging
}

# Default leakage factor (proportion of reductions lost to leakage effects)
DEFAULT_LEAKAGE_FACTOR = 0.05  # 5%

# Default system efficiency for solar PV estimation when not provided
DEFAULT_SYSTEM_EFFICIENCY = 0.80


class EnergyDisplacementEngine:
    """
    Calculates emission reductions from hybrid energy displacement projects.

    Core Formula:
        Net Reduction = (Baseline Emissions - Project Emissions)
                        × (1 - Uncertainty Discount)
                        × (1 - Leakage Factor)

    Baseline Emissions:
        fuel_rate (L/hr) × runtime (hrs/day) × days/yr × emission_factor (kgCO2/L)

    Project Emissions:
        Remaining diesel backup + gas generator emissions

    Solar Generation Estimation (analog fallback):
        generation_kwh = capacity_kwp × sun_hours × efficiency × days
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Public API — Quantify a single energy displacement activity
    # =========================================================================

    async def quantify_activity(
        self, activity_id: uuid.UUID, project_id: uuid.UUID = None
    ) -> CarbonCalculation:
        """
        Calculate emission reductions for a verified hybrid energy activity.

        Args:
            activity_id: UUID of the activity to quantify.
            project_id: UUID of the associated project (optional, auto-detects
                        ENERGY_DISPLACEMENT methodology if not provided).

        Returns:
            CarbonCalculation ORM instance with immutable audit log.
        """
        # --- Fetch and validate the activity ---
        result = await self.db.execute(
            select(Activity).where(Activity.id == activity_id)
        )
        activity = result.scalar_one_or_none()
        if not activity:
            raise ValueError("Activity not found")
        if activity.status != "verified":
            raise ValueError("Cannot quantify non-verified activity")

        # --- Resolve the project ---
        project = await self._resolve_project(project_id)

        # --- Extract activity data ---
        data = activity.activity_data or {}
        params = project.baseline_parameters or {}

        # --- Calculate baseline emissions (pre-installation diesel) ---
        baseline_emissions, baseline_log = self._calculate_baseline_emissions(
            data, params
        )

        # --- Calculate project emissions (post-installation residual) ---
        project_emissions, project_log = self._calculate_project_emissions(
            data, params
        )

        # --- Calculate solar generation estimate (for analog fallback) ---
        solar_gen_kwh, solar_log = self._estimate_solar_generation(data, params)

        # --- Calculate gross emission reduction ---
        gross_reduction_kg = max(0.0, baseline_emissions - project_emissions)

        # --- Apply uncertainty discount based on data source tier ---
        data_source = data.get("data_source", "analog_manual")
        uncertainty_discount = UNCERTAINTY_DISCOUNTS.get(
            data_source, UNCERTAINTY_DISCOUNTS["analog_manual"]
        )
        after_uncertainty = gross_reduction_kg * (1.0 - uncertainty_discount)

        # --- Apply leakage factor ---
        leakage_factor = float(
            params.get("leakage_factor", DEFAULT_LEAKAGE_FACTOR)
        )
        net_reduction_kg = after_uncertainty * (1.0 - leakage_factor)

        # --- Convert kgCO2 → tCO2e ---
        net_tco2e = round(net_reduction_kg / 1000.0, 4)

        # --- Determine if this is a monthly or annual calculation ---
        is_monthly = data.get(
            "is_monthly_check",
            params.get("is_monthly_check", True),
        )
        final_tco2e = round(net_tco2e / 12.0, 4) if is_monthly else net_tco2e

        # --- Build the auditor-traceable calculation log ---
        calculation_log = {
            "methodology": "ENERGY_DISPLACEMENT",
            "version": "1.0",
            "mrv_data_source": data_source,
            "baseline": baseline_log,
            "project": project_log,
            "solar_estimation": solar_log,
            "reductions": {
                "gross_reduction_kgCO2": round(gross_reduction_kg, 2),
                "uncertainty_discount_pct": round(uncertainty_discount * 100, 1),
                "after_uncertainty_kgCO2": round(after_uncertainty, 2),
                "leakage_factor_pct": round(leakage_factor * 100, 1),
                "net_reduction_kgCO2": round(net_reduction_kg, 2),
                "net_reduction_tCO2e": net_tco2e,
                "prorated_monthly": is_monthly,
                "final_tCO2e": final_tco2e,
            },
            "formula_trace": (
                "Net = (Baseline_kgCO2 - Project_kgCO2) "
                "× (1 - Uncertainty%) × (1 - Leakage%)"
            ),
        }

        # --- Persist immutable calculation record ---
        calc = CarbonCalculation(
            project_id=project.id,
            activity_id=activity.id,
            methodology_used="ENERGY_DISPLACEMENT",
            tco2e_generated=max(0.0, final_tco2e),
            calculation_log=calculation_log,
            status="calculated",
        )
        self.db.add(calc)

        # --- Update associated property sustainability metrics ---
        if activity.property_id:
            await self._update_property_metrics(
                activity.property_id, final_tco2e, solar_gen_kwh, calc
            )

        await self.db.commit()
        await self.db.refresh(calc)
        return calc

    # =========================================================================
    # Portfolio Aggregation — Get totals across all energy displacement calcs
    # =========================================================================

    async def get_portfolio_metrics(self) -> Dict[str, Any]:
        """
        Aggregate portfolio-level metrics for all energy displacement projects.
        Returns total CO2 reduced, total energy generation, project count,
        and estimated portfolio value.
        """
        result = await self.db.execute(
            select(
                func.sum(CarbonCalculation.tco2e_generated),
                func.count(CarbonCalculation.id),
            ).where(
                CarbonCalculation.methodology_used == "ENERGY_DISPLACEMENT"
            )
        )
        row = result.one()
        total_tco2e = round(row[0] or 0.0, 4)
        total_calcs = row[1] or 0

        # Estimate portfolio value at premium pricing ($30/tCO2e for high-integrity energy)
        ENERGY_CREDIT_PRICE_USD = 30.00
        estimated_value = round(total_tco2e * ENERGY_CREDIT_PRICE_USD, 2)

        return {
            "total_tco2e_reduced": total_tco2e,
            "total_calculations": total_calcs,
            "estimated_value_usd": estimated_value,
            "credit_price_per_tco2e": ENERGY_CREDIT_PRICE_USD,
            "methodology": "ENERGY_DISPLACEMENT",
        }

    # =========================================================================
    # Private — Baseline Emission Calculation
    # =========================================================================

    def _calculate_baseline_emissions(
        self, data: dict, params: dict
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate annual baseline emissions from pre-installation diesel/petrol
        generator usage.

        Formula:
            Baseline_kgCO2 = fuel_rate_lph × daily_runtime × days_per_year
                             × emission_factor_kgCO2_per_L
        """
        # Extract baseline parameters (activity data overrides project defaults)
        fuel_type = data.get(
            "baseline_generator_type",
            params.get("baseline_generator_type", "diesel"),
        )
        fuel_rate_lph = float(
            data.get(
                "baseline_fuel_consumption_lph",
                params.get("baseline_fuel_consumption_lph", 5.0),
            )
        )
        daily_runtime = float(
            data.get(
                "baseline_avg_daily_runtime_hrs",
                params.get("baseline_avg_daily_runtime_hrs", 12.0),
            )
        )
        days_per_year = int(
            data.get(
                "baseline_operating_days_per_year",
                params.get("baseline_operating_days_per_year", 365),
            )
        )
        emission_factor = FUEL_EMISSION_FACTORS.get(fuel_type, 2.68)

        # Core calculation
        annual_fuel_litres = fuel_rate_lph * daily_runtime * days_per_year
        baseline_kg_co2 = annual_fuel_litres * emission_factor

        log = {
            "fuel_type": fuel_type,
            "fuel_rate_lph": fuel_rate_lph,
            "daily_runtime_hrs": daily_runtime,
            "days_per_year": days_per_year,
            "emission_factor_kgCO2_per_L": emission_factor,
            "annual_fuel_litres": round(annual_fuel_litres, 2),
            "baseline_kgCO2": round(baseline_kg_co2, 2),
        }

        return baseline_kg_co2, log

    # =========================================================================
    # Private — Project Emission Calculation (Post-Installation Residual)
    # =========================================================================

    def _calculate_project_emissions(
        self, data: dict, params: dict
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate annual project emissions from residual fossil fuel use
        after hybrid system installation (backup diesel + gas generator).

        Assumes backup diesel operates at reduced runtime post-installation.
        Gas generator emissions are based on estimated fuel consumption.
        """
        project_kg_co2 = 0.0
        log: Dict[str, Any] = {"components": []}

        # --- Residual Diesel Backup ---
        diesel_backup_kva = float(data.get("diesel_backup_capacity_kva", 0.0))
        if diesel_backup_kva > 0:
            # Estimate reduced diesel runtime (default: 10% of baseline runtime)
            baseline_runtime = float(
                data.get(
                    "baseline_avg_daily_runtime_hrs",
                    params.get("baseline_avg_daily_runtime_hrs", 12.0),
                )
            )
            backup_runtime_fraction = float(
                params.get("diesel_backup_runtime_fraction", 0.10)
            )
            backup_runtime = baseline_runtime * backup_runtime_fraction
            backup_fuel_rate = float(
                params.get("diesel_backup_fuel_rate_lph",
                           data.get("baseline_fuel_consumption_lph", 5.0) * 0.5)
            )
            days_per_year = int(
                data.get(
                    "baseline_operating_days_per_year",
                    params.get("baseline_operating_days_per_year", 365),
                )
            )
            diesel_kg = (
                backup_fuel_rate * backup_runtime * days_per_year * 2.68
            )
            project_kg_co2 += diesel_kg
            log["components"].append({
                "source": "diesel_backup",
                "capacity_kva": diesel_backup_kva,
                "runtime_hrs_day": round(backup_runtime, 2),
                "fuel_rate_lph": backup_fuel_rate,
                "annual_kgCO2": round(diesel_kg, 2),
            })

        # --- Gas Generator ---
        gas_capacity_kva = float(
            data.get("gas_generator_capacity_kva", 0.0)
        )
        if gas_capacity_kva > 0:
            # Estimate gas generator runtime (default: 20% of total load)
            gas_runtime = float(params.get("gas_runtime_hrs_day", 4.0))
            gas_fuel_m3_hr = float(
                params.get("gas_fuel_m3_per_hr", gas_capacity_kva * 0.25)
            )
            days_per_year = int(
                data.get(
                    "baseline_operating_days_per_year",
                    params.get("baseline_operating_days_per_year", 365),
                )
            )
            gas_ef = FUEL_EMISSION_FACTORS.get("natural_gas", 1.89)
            gas_kg = gas_fuel_m3_hr * gas_runtime * days_per_year * gas_ef
            project_kg_co2 += gas_kg
            log["components"].append({
                "source": "gas_generator",
                "capacity_kva": gas_capacity_kva,
                "runtime_hrs_day": gas_runtime,
                "fuel_m3_per_hr": gas_fuel_m3_hr,
                "annual_kgCO2": round(gas_kg, 2),
            })

        log["total_project_kgCO2"] = round(project_kg_co2, 2)
        return project_kg_co2, log

    # =========================================================================
    # Private — Solar Generation Estimation (Analog Fallback)
    # =========================================================================

    def _estimate_solar_generation(
        self, data: dict, params: dict
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Estimate annual solar PV generation in kWh.

        Formula:
            generation_kwh = capacity_kwp × sun_hours × efficiency × 365
        """
        solar_kwp = float(data.get("solar_capacity_kwp", 0.0))
        sun_hours = float(
            data.get(
                "avg_sun_hours",
                params.get("avg_sun_hours", 5.0),
            )
        )
        efficiency = float(
            data.get(
                "system_efficiency",
                params.get("system_efficiency", DEFAULT_SYSTEM_EFFICIENCY),
            )
        )

        annual_kwh = solar_kwp * sun_hours * efficiency * 365.0

        log = {
            "solar_capacity_kwp": solar_kwp,
            "avg_sun_hours": sun_hours,
            "system_efficiency": efficiency,
            "estimated_annual_kwh": round(annual_kwh, 2),
            "estimated_annual_mwh": round(annual_kwh / 1000.0, 3),
        }

        return annual_kwh, log

    # =========================================================================
    # Private — Resolve Project
    # =========================================================================

    async def _resolve_project(
        self, project_id: Optional[uuid.UUID]
    ) -> Project:
        """Find or validate the energy displacement project."""
        if project_id:
            proj_res = await self.db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = proj_res.scalar_one_or_none()
            if not project:
                raise ValueError("Project not found")
            return project

        # Auto-detect ENERGY_DISPLACEMENT project
        proj_res = await self.db.execute(
            select(Project)
            .where(Project.methodology_id == "ENERGY_DISPLACEMENT")
            .limit(1)
        )
        project = proj_res.scalar_one_or_none()
        if not project:
            raise ValueError(
                "No Energy Displacement project found. "
                "Please create a project with methodology_id='ENERGY_DISPLACEMENT'."
            )
        return project

    # =========================================================================
    # Private — Update Property Sustainability Metrics
    # =========================================================================

    async def _update_property_metrics(
        self,
        property_id: uuid.UUID,
        tco2e: float,
        solar_gen_kwh: float,
        calc: CarbonCalculation,
    ) -> None:
        """Update the associated property with energy displacement metrics."""
        from app.models.property import Property
        from sqlalchemy.orm.attributes import flag_modified

        prop_res = await self.db.execute(
            select(Property).where(Property.id == property_id)
        )
        prop = prop_res.scalar_one_or_none()
        if not prop:
            return

        metrics = prop.sustainability_metrics or {}
        metrics["carbon_offset_kg"] = round(tco2e * 1000, 2)
        metrics["solar_generation_kwh"] = round(solar_gen_kwh, 2)
        metrics["solar_generation_mwh"] = round(solar_gen_kwh / 1000.0, 3)
        metrics["status"] = "Verified MRV"
        metrics["methodology"] = "ENERGY_DISPLACEMENT"
        metrics["last_calculation_date"] = (
            calc.created_at.isoformat() if calc.created_at else "Just now"
        )

        # Energy score grading based on annual CO2 offset
        if tco2e > 50.0:
            score = "A+"
        elif tco2e > 20.0:
            score = "A"
        elif tco2e > 5.0:
            score = "B"
        else:
            score = "C"
        metrics["energy_score"] = score

        prop.sustainability_metrics = metrics
        flag_modified(prop, "sustainability_metrics")
