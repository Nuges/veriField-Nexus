from typing import Tuple

from app.domains.cookstoves.schemas import UsageSurveyCreate

from app.domains.cookstoves.models import HouseholdBeneficiary, CookstoveDevice



class CookstoveQuantificationEngine:

    """

    Clean Cookstove Quantification Engine (Verra VMR0006 / Gold Standard TPDDTEC compliant).

    """

    @staticmethod

    def calculate_emissions_reduction(

        data: UsageSurveyCreate,

        household: HouseholdBeneficiary,

        stove: CookstoveDevice

    ) -> Tuple[float, bool, str]:

        """

        Calculates Annualized CO2e Emissions Reduction (tonnes CO2e/year) from fuel savings.

        Also runs AI fraud detection (e.g. unrealistic usage hours, stacking with wood, zero fuel with high usage).

        """

        if not data.is_stove_in_use:

            return 0.0, False, None



        # Wood/Charcoal Baseline Emission Factor (t CO2e / tonne biomass)

        # NCV = 0.015 TJ/tonne, EF = 112 t CO2e/TJ -> ~1.68 t CO2e per tonne biomass

        ef_biomass = 1.68

        f_nrb = 0.85 # Non-renewable biomass fraction (default regional parameter)



        # Saved Fuel per day (kg)

        baseline_daily_kg = household.baseline_fuel_kg_per_day

        project_daily_kg = data.fuel_consumed_kg_per_day



        saved_kg_per_day = max(0.0, baseline_daily_kg - project_daily_kg)

        annual_saved_tonnes = (saved_kg_per_day * 365.0) / 1000.0



        # Annual Emission Reduction (t CO2e)

        annual_reduction_tco2e = round(annual_saved_tonnes * f_nrb * ef_biomass, 3)



        # AI Fraud Detection Rules

        has_fraud = False

        reasons = []



        if data.reported_daily_usage_hours > 14.0:

            has_fraud = True

            reasons.append(f"Unrealistic daily usage duration ({data.reported_daily_usage_hours} hrs/day).")



        if data.fuel_consumed_kg_per_day == 0 and data.reported_daily_usage_hours > 1.0:

            has_fraud = True

            reasons.append("Zero fuel consumption reported despite active cooking usage hours.")



        if not data.is_primary_cooking_method and data.fuel_consumed_kg_per_day < (baseline_daily_kg * 0.2):

            has_fraud = True

            reasons.append("Stove stacking mismatch: secondary stove reported with >80% fuel reduction.")



        if data.thermal_tampering_detected:

            has_fraud = True

            reasons.append("Physical or thermal tampering flagged during field survey.")



        fraud_reason_str = "; ".join(reasons) if has_fraud else None



        return annual_reduction_tco2e, has_fraud, fraud_reason_str
