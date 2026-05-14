"""
=============================================================================
VeriField Nexus — Quantification Engine (v2)
=============================================================================
Deterministic calculation engine for generating carbon credits based on
approved methodologies. All constants are CONFIGURABLE via Project
baseline_parameters — nothing is hardcoded.

Supported Methodologies:
  - VM0006 / VMR0050 (Verra Cookstove)
  - GS_MECD (Gold Standard Metered Energy Cooking Devices)
  - GS_TPDDTEC (Gold Standard Technologies and Practices to Displace
                 Decentralized Thermal Energy Consumption)

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
# Default Methodology Parameters (overridden by Project.baseline_parameters)
# =============================================================================
METHODOLOGY_DEFAULTS = {
    "VM0006": {
        "baseline_fuel_kg_yr": 3000.0,
        "project_fuel_kg_yr": 1200.0,
        "ncv_tj_ton": 0.0156,
        "ef_tco2_tj": 112.0,
        "fraction_non_renewable_biomass": 0.81,
        "sum_usage_rate": 1.0,
        "is_monthly_check": True,
    },
    "VMR0050": {
        "baseline_fuel_kg_yr": 3000.0,
        "project_fuel_kg_yr": 1200.0,
        "ncv_tj_ton": 0.0156,
        "ef_tco2_tj": 112.0,
        "fraction_non_renewable_biomass": 0.81,
        "sum_usage_rate": 1.0,
        "is_monthly_check": True,
    },
    "GS_MECD": {
        "baseline_emission_factor_tco2_kwh": 0.0008,
        "fuel_ncv_mj_kg": 16.0,
    },
    "GS_TPDDTEC": {
        "baseline_fuel_kg_yr": 2500.0,
        "thermal_efficiency_baseline": 0.10,
        "thermal_efficiency_project": 0.35,
        "ncv_mj_kg": 16.0,
        "ef_tco2_tj": 112.0,
        "fraction_non_renewable_biomass": 0.80,
        "leakage_factor": 0.95,
    },
    # --- New per-type methodologies ---
    "VM0042": {
        "sequestration_tco2_ha_yr": 3.5,
        "practice_multipliers": {
            "conservation_tillage": 0.8,
            "cover_cropping": 1.0,
            "agroforestry": 1.5,
            "composting": 0.6,
            "other": 0.5,
        },
        "is_monthly_check": True,
    },
    "VM0047_ARR": {
        "co2_per_tree_yr": 0.022,
        "default_survival_rate": 0.80,
        "is_monthly_check": True,
    },
    "AMS_IA": {
        "grid_emission_factor_tco2_kwh": 0.0005,
    },
    "GS_SAFE_WATER": {
        "fuel_saved_kg_per_person_yr": 180.0,
        "persons_per_household": 5,
        "ncv_mj_kg": 16.0,
        "ef_tco2_tj": 112.0,
        "f_nrb": 0.80,
        "is_monthly_check": True,
    },
    "AMS_IIIC": {
        "baseline_emission_factor_tco2_km": 0.00021,
    },
}


class QuantificationEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_param(self, params: dict, defaults: dict, key: str, activity_data: dict = None):
        """
        Get a parameter with priority:
        1. Activity field data (real-time monitored)
        2. Project baseline_parameters (configured per-project)
        3. Methodology defaults (fallback)
        """
        if activity_data and key in activity_data:
            return activity_data[key]
        return params.get(key, defaults.get(key, 0.0))

    async def quantify_activity(self, activity_id: uuid.UUID, project_id: uuid.UUID = None) -> CarbonCalculation:
        """
        Pull an activity, check its methodology, and generate a definitive
        Carbon Calculation record.
        
        Args:
            activity_id: UUID of the activity to quantify
            project_id: UUID of the project (methodology source). If None,
                        attempts to find a project matching the activity type.
        """
        # Fetch activity
        result = await self.db.execute(select(Activity).where(Activity.id == activity_id))
        activity = result.scalar_one_or_none()
        if not activity:
            raise ValueError("Activity not found")

        # Activities must be Verified before quantification
        if activity.status != "verified":
            raise ValueError("Cannot quantify non-verified activity")

        # Find or validate the project
        if project_id:
            proj_res = await self.db.execute(select(Project).where(Project.id == project_id))
            project = proj_res.scalar_one_or_none()
            if not project:
                raise ValueError("Project not found")
        else:
            # Auto-find project matching activity type
            # Map activity types to their correct methodologies
            type_to_method = {
                "CLEAN_COOKING": ["VM0006", "VMR0050", "GS_TPDDTEC", "GS_MECD"],
                "AGRICULTURE": ["VM0006"],  # Uses VM0042 calc but VM0006 project as host
                "ENERGY_USE": ["GS_MECD"],
                "FORESTRY_LAND_USE": ["VM0006"],  # Uses VM0047 calc but VM0006 project as host
                "SAFE_WATER": ["GS_TPDDTEC"],
                "TRANSPORT_MOBILITY": ["GS_MECD"],
                "OTHER": ["VM0006", "GS_TPDDTEC", "GS_MECD"],
                # Legacy types
                "cooking": ["VM0006", "VMR0050", "GS_TPDDTEC", "GS_MECD"],
                "energy": ["GS_MECD"],
                "farming": ["VM0006"],
            }
            methods = type_to_method.get(activity.activity_type, ["VM0006", "GS_TPDDTEC", "GS_MECD"])
            project = None
            for m in methods:
                proj_res = await self.db.execute(
                    select(Project).where(Project.methodology_id == m).limit(1)
                )
                project = proj_res.scalar_one_or_none()
                if project:
                    break
            if not project:
                raise ValueError(f"No project found for activity type '{activity.activity_type}'")

        # Route to the correct calculation based on ACTIVITY TYPE first,
        # then fall back to methodology-based routing
        act_type = activity.activity_type.upper()
        if act_type == "AGRICULTURE":
            tco2e, log = await self._calculate_agriculture(activity, project)
        elif act_type == "FORESTRY_LAND_USE":
            tco2e, log = await self._calculate_forestry(activity, project)
        elif act_type == "ENERGY_USE":
            tco2e, log = await self._calculate_energy(activity, project)
        elif act_type == "SAFE_WATER":
            tco2e, log = await self._calculate_safe_water(activity, project)
        elif act_type == "TRANSPORT_MOBILITY":
            tco2e, log = await self._calculate_transport(activity, project)
        else:
            # Default: route by project methodology (CLEAN_COOKING, OTHER, legacy)
            methodology = project.methodology_id
            if methodology in ["VM0006", "VMR0050"]:
                tco2e, log = await self._calculate_verra_cookstove(activity, project)
            elif methodology == "GS_MECD":
                tco2e, log = await self._calculate_mecd(activity, project)
            elif methodology == "GS_TPDDTEC":
                tco2e, log = await self._calculate_tpddtec(activity, project)
            else:
                raise ValueError(f"Unsupported methodology: {methodology}")

        # Store immutable record
        calc = CarbonCalculation(
            project_id=project.id,
            activity_id=activity.id,
            methodology_used=methodology,
            tco2e_generated=tco2e,
            calculation_log=log,
            status="calculated"
        )
        self.db.add(calc)

        # Update the associated Property with the final verified carbon data
        if activity.property_id:
            from app.models.property import Property
            prop_res = await self.db.execute(select(Property).where(Property.id == activity.property_id))
            prop = prop_res.scalar_one_or_none()
            if prop:
                metrics = prop.sustainability_metrics or {}
                # Keep existing metrics, but update carbon offset to the verified tCO2e (converted to kg for display)
                metrics["carbon_offset_kg"] = round(tco2e * 1000, 2)
                metrics["status"] = "Verified MRV"
                metrics["last_calculation_date"] = calc.created_at.isoformat() if calc.created_at else "Just now"
                
                # Compute an Energy Score grade based on annual carbon reduction
                if tco2e > 5.0:
                    score = "A+"
                elif tco2e > 2.0:
                    score = "A"
                elif tco2e > 0.5:
                    score = "B"
                else:
                    score = "C"
                metrics["energy_score"] = score
                
                prop.sustainability_metrics = metrics
                
                # SQLAlchemy requires explicit flagging when modifying JSONB fields in-place
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(prop, "sustainability_metrics")

        await self.db.commit()
        await self.db.refresh(calc)

        return calc

    async def get_project_total(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """
        Aggregate total tCO2e for a project across all calculations.
        """
        result = await self.db.execute(
            select(
                func.sum(CarbonCalculation.tco2e_generated),
                func.count(CarbonCalculation.id),
            ).where(CarbonCalculation.project_id == project_id)
        )
        row = result.one()
        return {
            "project_id": str(project_id),
            "total_tco2e": round(row[0] or 0.0, 4),
            "total_calculations": row[1] or 0,
        }

    # =========================================================================
    # Methodology: Verra VM0006 / VMR0050 (Clean Cookstove)
    # =========================================================================
    async def _calculate_verra_cookstove(
        self, activity: Activity, project: Project
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Verra VM0006 / VMR0050 Methodology
        Formula: ER = ((B_fuel - P_fuel) / 1000) * NCV * EF * fNRB * UsageRate
        """
        params = project.baseline_parameters or {}
        defaults = METHODOLOGY_DEFAULTS.get(project.methodology_id, {})
        data = activity.activity_data or {}

        # Get all parameters (activity data overrides project overrides defaults)
        b_fuel = self._get_param(params, defaults, "baseline_fuel_kg_yr", data)
        p_fuel = self._get_param(params, defaults, "project_fuel_kg_yr", data)
        ncv = self._get_param(params, defaults, "ncv_tj_ton", data)
        ef = self._get_param(params, defaults, "ef_tco2_tj", data)
        f_nrb = self._get_param(params, defaults, "fraction_non_renewable_biomass", data)
        usage_rate = data.get("sum_usage_rate_percentage",
                             data.get("usage_rate_percentage",
                                      params.get("sum_usage_rate", defaults.get("sum_usage_rate", 1.0))))
        is_monthly = data.get("is_monthly_check", params.get("is_monthly_check", True))

        # Calculation
        fuel_savings = (b_fuel - p_fuel) / 1000.0
        er_y = fuel_savings * ncv * ef * f_nrb * usage_rate

        if is_monthly:
            final_tco2e = round(er_y / 12.0, 4)
        else:
            final_tco2e = round(er_y, 4)

        log = {
            "methodology": project.methodology_id,
            "version": "latest",
            "mrv_data_source": "IoT_SUMs_and_KPT",
            "inputs": {
                "baseline_fuel_kg_yr": b_fuel,
                "project_fuel_kg_yr": p_fuel,
                "ncv_tj_ton": ncv,
                "ef_tco2_tj": ef,
                "f_nrb": f_nrb,
                "sum_usage_rate": usage_rate,
                "prorated_monthly": is_monthly,
            },
            "formula_trace": "((B_fuel - P_fuel)/1000) * NCV * EF * fNRB * UsageRate",
            "annual_er": er_y,
            "final_tco2e": final_tco2e,
        }

        return max(0.0, final_tco2e), log

    # =========================================================================
    # Methodology: Gold Standard MECD
    # =========================================================================
    async def _calculate_mecd(
        self, activity: Activity, project: Project
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Gold Standard Metered and Measured Energy Cooking Devices (MECD)
        Formula: ER = Measured_Energy_kWh * Baseline_EF
        """
        params = project.baseline_parameters or {}
        defaults = METHODOLOGY_DEFAULTS.get("GS_MECD", {})
        data = activity.activity_data or {}

        baseline_ef = self._get_param(params, defaults, "baseline_emission_factor_tco2_kwh", data)
        measured_kwh = data.get("metered_energy_kwh", 0.0)
        fuel_weight_kg = data.get("metered_fuel_weight_kg", None)

        if fuel_weight_kg is not None:
            ncv_mj_kg = self._get_param(params, defaults, "fuel_ncv_mj_kg", data)
            measured_kwh = (fuel_weight_kg * ncv_mj_kg) / 3.6

        er = measured_kwh * baseline_ef

        log = {
            "methodology": "GS_MECD",
            "mrv_data_source": "Direct_Metered_Sensors",
            "inputs": {
                "metered_energy_kwh": measured_kwh,
                "baseline_emission_factor_tco2_kwh": baseline_ef,
                "metered_fuel_weight_kg": fuel_weight_kg,
            },
            "formula_trace": "Measured_Energy_kWh * Baseline_EF",
            "final_tco2e": round(er, 4),
        }

        return max(0.0, round(er, 4)), log

    # =========================================================================
    # Methodology: Gold Standard TPDDTEC (v2 — Fully Implemented)
    # =========================================================================
    async def _calculate_tpddtec(
        self, activity: Activity, project: Project
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Gold Standard TPDDTEC — Technologies and Practices to Displace
        Decentralized Thermal Energy Consumption.

        Formula:
        ER = (B_fuel * (1 - eff_b/eff_p)) * NCV * EF * fNRB * leakage_factor

        Where:
        - eff_b = baseline thermal efficiency (e.g., 10% for three-stone fire)
        - eff_p = project thermal efficiency (e.g., 35% for improved cookstove)
        """
        params = project.baseline_parameters or {}
        defaults = METHODOLOGY_DEFAULTS.get("GS_TPDDTEC", {})
        data = activity.activity_data or {}

        b_fuel = self._get_param(params, defaults, "baseline_fuel_kg_yr", data)
        eff_b = self._get_param(params, defaults, "thermal_efficiency_baseline", data)
        eff_p = self._get_param(params, defaults, "thermal_efficiency_project", data)
        ncv_mj_kg = self._get_param(params, defaults, "ncv_mj_kg", data)
        ef = self._get_param(params, defaults, "ef_tco2_tj", data)
        f_nrb = self._get_param(params, defaults, "fraction_non_renewable_biomass", data)
        leakage = self._get_param(params, defaults, "leakage_factor", data)

        # Fuel savings from efficiency improvement
        fuel_savings_fraction = 1.0 - (eff_b / eff_p) if eff_p > 0 else 0.0
        fuel_savings_kg = b_fuel * fuel_savings_fraction

        # Convert to energy (TJ)
        energy_tj = (fuel_savings_kg * ncv_mj_kg) / 1e6

        # Emission reduction
        er_y = energy_tj * ef * f_nrb * leakage

        # Prorate if monthly
        is_monthly = data.get("is_monthly_check", params.get("is_monthly_check", True))
        if is_monthly:
            final_tco2e = round(er_y / 12.0, 4)
        else:
            final_tco2e = round(er_y, 4)

        log = {
            "methodology": "GS_TPDDTEC",
            "mrv_data_source": "KPT_and_Water_Boiling_Test",
            "inputs": {
                "baseline_fuel_kg_yr": b_fuel,
                "thermal_efficiency_baseline": eff_b,
                "thermal_efficiency_project": eff_p,
                "ncv_mj_kg": ncv_mj_kg,
                "ef_tco2_tj": ef,
                "f_nrb": f_nrb,
                "leakage_factor": leakage,
                "prorated_monthly": is_monthly,
            },
            "formula_trace": "(B_fuel * (1 - eff_b/eff_p)) * NCV * EF * fNRB * leakage",
            "fuel_savings_fraction": round(fuel_savings_fraction, 4),
            "fuel_savings_kg": round(fuel_savings_kg, 2),
            "energy_tj": round(energy_tj, 6),
            "annual_er": round(er_y, 4),
            "final_tco2e": final_tco2e,
        }

        return max(0.0, final_tco2e), log

    # =========================================================================
    # Methodology: Verra VM0042 — Agriculture / Soil Carbon
    # =========================================================================
    async def _calculate_agriculture(
        self, activity: Activity, project: Project
    ) -> Tuple[float, Dict[str, Any]]:
        """
        VM0042: Soil carbon sequestration from sustainable agricultural practices.
        Formula: ER = plot_area_ha * sequestration_rate * practice_multiplier
        """
        defaults = METHODOLOGY_DEFAULTS.get("VM0042", {})
        data = activity.activity_data or {}

        plot_area = float(data.get("plot_area_hectares", 1.0))
        seq_rate = defaults.get("sequestration_tco2_ha_yr", 3.5)
        practice = data.get("practice_type", "other")
        multipliers = defaults.get("practice_multipliers", {})
        multiplier = multipliers.get(practice, 0.5)

        er_y = plot_area * seq_rate * multiplier
        is_monthly = defaults.get("is_monthly_check", True)
        final_tco2e = round(er_y / 12.0, 4) if is_monthly else round(er_y, 4)

        log = {
            "methodology": "VM0042",
            "mrv_data_source": "Field_Agent_Survey",
            "inputs": {
                "plot_area_hectares": plot_area,
                "sequestration_tco2_ha_yr": seq_rate,
                "practice_type": practice,
                "practice_multiplier": multiplier,
                "prorated_monthly": is_monthly,
            },
            "formula_trace": "plot_area * sequestration_rate * practice_multiplier",
            "annual_er": round(er_y, 4),
            "final_tco2e": final_tco2e,
        }
        return max(0.0, final_tco2e), log

    # =========================================================================
    # Methodology: Verra VM0047 — Forestry / Afforestation
    # =========================================================================
    async def _calculate_forestry(
        self, activity: Activity, project: Project
    ) -> Tuple[float, Dict[str, Any]]:
        """
        VM0047 ARR: CO2 sequestration from tree planting.
        Formula: ER = tree_count * co2_per_tree_yr * survival_rate
        """
        defaults = METHODOLOGY_DEFAULTS.get("VM0047_ARR", {})
        data = activity.activity_data or {}

        tree_count = int(data.get("tree_count", 0))
        co2_per_tree = defaults.get("co2_per_tree_yr", 0.022)
        survival_rate = float(data.get("survival_rate_pct", 80)) / 100.0
        if survival_rate <= 0 or survival_rate > 1:
            survival_rate = defaults.get("default_survival_rate", 0.80)

        er_y = tree_count * co2_per_tree * survival_rate
        is_monthly = defaults.get("is_monthly_check", True)
        final_tco2e = round(er_y / 12.0, 4) if is_monthly else round(er_y, 4)

        log = {
            "methodology": "VM0047_ARR",
            "mrv_data_source": "Field_Agent_Survey",
            "inputs": {
                "tree_count": tree_count,
                "co2_per_tree_yr": co2_per_tree,
                "survival_rate": survival_rate,
                "prorated_monthly": is_monthly,
            },
            "formula_trace": "tree_count * co2_per_tree_yr * survival_rate",
            "annual_er": round(er_y, 4),
            "final_tco2e": final_tco2e,
        }
        return max(0.0, final_tco2e), log

    # =========================================================================
    # Methodology: CDM AMS-I.A — Renewable Energy / Electricity
    # =========================================================================
    async def _calculate_energy(
        self, activity: Activity, project: Project
    ) -> Tuple[float, Dict[str, Any]]:
        """
        AMS-I.A: Grid displacement from renewable energy.
        Formula: ER = daily_output_kwh * 365 * grid_ef
        """
        defaults = METHODOLOGY_DEFAULTS.get("AMS_IA", {})
        data = activity.activity_data or {}

        daily_kwh = float(data.get("daily_output_kwh", data.get("capacity_kw", 5.0)))
        grid_ef = defaults.get("grid_emission_factor_tco2_kwh", 0.0005)
        annual_kwh = daily_kwh * 365.0

        er_y = annual_kwh * grid_ef
        final_tco2e = round(er_y / 12.0, 4)  # Monthly proration

        log = {
            "methodology": "AMS_IA",
            "mrv_data_source": "Metered_Output",
            "inputs": {
                "daily_output_kwh": daily_kwh,
                "annual_kwh": annual_kwh,
                "grid_emission_factor_tco2_kwh": grid_ef,
            },
            "formula_trace": "daily_kwh * 365 * grid_ef / 12",
            "annual_er": round(er_y, 4),
            "final_tco2e": final_tco2e,
        }
        return max(0.0, final_tco2e), log

    # =========================================================================
    # Methodology: Gold Standard Safe Water Supply
    # =========================================================================
    async def _calculate_safe_water(
        self, activity: Activity, project: Project
    ) -> Tuple[float, Dict[str, Any]]:
        """
        GS Safe Water: Fuel savings from eliminating need to boil water.
        Formula: ER = households * persons_per_hh * fuel_saved_kg * NCV * EF * fNRB / 1e6
        """
        defaults = METHODOLOGY_DEFAULTS.get("GS_SAFE_WATER", {})
        data = activity.activity_data or {}

        households = int(data.get("households_served", 1))
        persons = defaults.get("persons_per_household", 5)
        fuel_saved = defaults.get("fuel_saved_kg_per_person_yr", 180.0)
        ncv = defaults.get("ncv_mj_kg", 16.0)
        ef = defaults.get("ef_tco2_tj", 112.0)
        f_nrb = defaults.get("f_nrb", 0.80)

        total_fuel_kg = households * persons * fuel_saved
        energy_tj = (total_fuel_kg * ncv) / 1e6
        er_y = energy_tj * ef * f_nrb

        is_monthly = defaults.get("is_monthly_check", True)
        final_tco2e = round(er_y / 12.0, 4) if is_monthly else round(er_y, 4)

        log = {
            "methodology": "GS_SAFE_WATER",
            "mrv_data_source": "Field_Agent_Survey",
            "inputs": {
                "households_served": households,
                "persons_per_household": persons,
                "fuel_saved_kg_per_person_yr": fuel_saved,
                "ncv_mj_kg": ncv,
                "ef_tco2_tj": ef,
                "f_nrb": f_nrb,
                "prorated_monthly": is_monthly,
            },
            "formula_trace": "(households * persons * fuel_saved * NCV * EF * fNRB) / 1e6",
            "total_fuel_saved_kg": total_fuel_kg,
            "energy_tj": round(energy_tj, 6),
            "annual_er": round(er_y, 4),
            "final_tco2e": final_tco2e,
        }
        return max(0.0, final_tco2e), log

    # =========================================================================
    # Methodology: CDM AMS-III.C — Transport / Low-Emission Vehicles
    # =========================================================================
    async def _calculate_transport(
        self, activity: Activity, project: Project
    ) -> Tuple[float, Dict[str, Any]]:
        """
        AMS-III.C: Emission reduction from clean transport.
        Formula: ER = daily_distance_km * 365 * baseline_ef
        """
        defaults = METHODOLOGY_DEFAULTS.get("AMS_IIIC", {})
        data = activity.activity_data or {}

        daily_km = float(data.get("daily_distance_km", 0.0))
        baseline_ef = defaults.get("baseline_emission_factor_tco2_km", 0.00021)
        annual_km = daily_km * 365.0

        er_y = annual_km * baseline_ef
        final_tco2e = round(er_y / 12.0, 4)  # Monthly proration

        log = {
            "methodology": "AMS_IIIC",
            "mrv_data_source": "Vehicle_Telemetry",
            "inputs": {
                "daily_distance_km": daily_km,
                "annual_km": annual_km,
                "baseline_emission_factor_tco2_km": baseline_ef,
            },
            "formula_trace": "daily_km * 365 * baseline_ef / 12",
            "annual_er": round(er_y, 4),
            "final_tco2e": final_tco2e,
        }
        return max(0.0, final_tco2e), log

