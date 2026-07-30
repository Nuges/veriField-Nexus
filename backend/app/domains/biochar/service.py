from typing import Dict, Any, Tuple

from app.domains.biochar.schemas import BiocharBatchCreate



class BiocharQuantificationEngine:

    """

    Biochar Carbon Removal Quantification & Quality Engine (Puro.earth / EBC / Verra VM0044 compliant).

    """

    @staticmethod

    def calculate_removal_and_grade(data: BiocharBatchCreate) -> Tuple[float, float, str, bool, str]:

        """

        Calculates Net CO2e Removed (tonnes CO2e), permanence factor, assigns quality grade,

        and runs AI anomaly detection on kiln operation parameters.

        """

        # 1. Permanence Factor based on Molar H/C Ratio (EBC / Puro standard)

        # H/C < 0.4 -> 1000 year permanence (factor ~0.89 - 0.95)

        # H/C 0.4 - 0.7 -> 100 year permanence (factor ~0.70 - 0.85)

        # H/C > 0.7 -> Non-compliant / Rejected

        if data.molar_h_c_ratio < 0.4:

            permanence_factor = 0.90

        elif data.molar_h_c_ratio <= 0.7:

            permanence_factor = 0.75

        else:

            permanence_factor = 0.0



        # 2. Net Carbon Content Removed

        # Net CO2e = Biochar Yield (tonnes) * (Fixed Carbon % / 100) * (44 / 12) * Permanence Factor

        c_to_co2_ratio = 44.0 / 12.0 # 3.667

        gross_co2e_sequestered = data.biochar_yield_tonnes * (data.fixed_carbon_pct / 100.0) * c_to_co2_ratio



        # Subtract operational emissions (drying, kiln auxiliary energy, transport ~ 10-15%)

        operational_deduction_factor = 0.88

        net_co2e_removed = round(gross_co2e_sequestered * operational_deduction_factor * permanence_factor, 2)



        # 3. Quality Grading

        if data.fixed_carbon_pct >= 75.0 and data.molar_h_c_ratio <= 0.4 and data.ash_content_pct <= 10.0:

            quality_grade = "GRADE_A"

        elif data.fixed_carbon_pct >= 60.0 and data.molar_h_c_ratio <= 0.7:

            quality_grade = "GRADE_B"

        else:

            quality_grade = "REJECTED"



        # 4. Anomaly Detection

        has_anomaly = False

        anomaly_reasons = []



        # Yield ratio sanity check (typical biochar yield is 20% - 40% of dry feedstock)

        yield_ratio = data.biochar_yield_tonnes / data.feedstock_weight_tonnes

        if yield_ratio > 0.45:

            has_anomaly = True

            anomaly_reasons.append(f"Abnormally high biochar yield ratio ({round(yield_ratio*100, 1)}% > 45%).")

        elif yield_ratio < 0.10:

            has_anomaly = True

            anomaly_reasons.append(f"Abnormally low yield ratio ({round(yield_ratio*100, 1)}% < 10%). Check kiln combustion.")



        if data.pyrolysis_temp_celsius < 400 and data.molar_h_c_ratio < 0.4:

            has_anomaly = True

            anomaly_reasons.append("Inconsistent pyrolysis temperature vs low H/C ratio reported.")



        anomaly_reason_str = "; ".join(anomaly_reasons) if has_anomaly else None



        return net_co2e_removed, permanence_factor, quality_grade, has_anomaly, anomaly_reason_str
