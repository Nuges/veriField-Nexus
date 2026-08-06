from typing import Tuple, Optional, List

from app.domains.energy.schemas import EnergyTelemetryCreate


class EnergyQuantificationEngine:
    """
    Diesel Displacement CO2 Avoidance Quantification Engine.

    Calculates net CO2e avoided by displacing diesel generation with
    solar PV and battery storage. Applies anomaly detection for
    impossible generation values and fuel accounting inconsistencies.
    """

    @staticmethod
    def calculate_co2_avoidance(
        data: EnergyTelemetryCreate,
        baseline_diesel_ef_kg_kwh: float,
        capacity_kwp: float,
    ) -> Tuple[float, float, bool, Optional[str]]:
        """
        Returns (clean_kwh, net_co2e_avoided_tonnes, has_anomaly, anomaly_reason).

        Parameters:
            data: telemetry reading
            baseline_diesel_ef_kg_kwh: asset's baseline diesel emission factor (kg CO2e / kWh)
            capacity_kwp: asset's installed solar capacity (kWp)
        """
        clean_kwh = data.solar_generation_kwh + data.battery_discharge_kwh
        net_co2e_t = round((clean_kwh * baseline_diesel_ef_kg_kwh) / 1000.0, 3)

        has_anomaly = False
        reasons: List[str] = []

        # Inverter over-generation check (capacity factor > 100%)
        if data.solar_generation_kwh > (capacity_kwp * 24.0):
            has_anomaly = True
            reasons.append("Solar generation exceeds physical theoretical maximum array capacity.")

        # Fuel accounting inconsistency
        if data.diesel_fuel_consumed_liters > 0 and data.diesel_generation_kwh == 0:
            has_anomaly = True
            reasons.append("Diesel fuel consumed without registered electrical generation.")

        anomaly_str = "; ".join(reasons) if has_anomaly else None

        return clean_kwh, net_co2e_t, has_anomaly, anomaly_str
