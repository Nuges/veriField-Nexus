from typing import Tuple

from app.domains.ev.schemas import EVChargingSessionCreate

from app.domains.ev.models import EVChargingStation



class EVQuantificationEngine:

    """

    EV Fleet & Charging Session Quantification Engine (Verra VM0038 / AMS-III.C. compliant).

    """

    @staticmethod

    def calculate_avoided_emissions(

        data: EVChargingSessionCreate,

        station: EVChargingStation

    ) -> Tuple[float, bool, str]:

        """

        Calculates Net Avoided Emissions (kg CO2e) = Baseline ICE Emissions - EV Electricity Grid Emissions.

        Also runs AI anomaly detection on efficiency (kWh/km) and charge duration.

        """

        # Baseline ICE Factors (g CO2e / km)

        baseline_factors = {

            "ICE_GASOLINE": 190.0,

            "ICE_DIESEL": 230.0,

            "ICE_BUS": 850.0,

            "ICE_TWO_WHEELER": 60.0

        }

        baseline_g_km = baseline_factors.get(data.baseline_vehicle_type, 220.0)



        # 1. Baseline ICE Emissions (kg CO2e)

        baseline_emissions_kg = (data.distance_displaced_km * baseline_g_km) / 1000.0



        # 2. EV Charging Electricity Grid Emissions (kg CO2e)

        # Accounting for renewable source percentage at charging station

        effective_grid_factor = station.grid_emission_factor_kg_kwh * (1.0 - (station.renewable_source_pct / 100.0))

        ev_grid_emissions_kg = data.energy_consumed_kwh * effective_grid_factor



        # 3. Net Avoided Emissions

        net_avoided_kg = round(max(0.0, baseline_emissions_kg - ev_grid_emissions_kg), 2)



        # 4. Anomaly Detection

        has_anomaly = False

        anomaly_reasons = []



        # Consumption efficiency check (kWh per km)

        efficiency_kwh_per_km = data.energy_consumed_kwh / data.distance_displaced_km

        if efficiency_kwh_per_km > 0.8: # > 800 Wh/km for standard vehicle

            has_anomaly = True

            anomaly_reasons.append(f"Abnormally high energy consumption ({round(efficiency_kwh_per_km, 2)} kWh/km).")

        elif efficiency_kwh_per_km < 0.08: # < 80 Wh/km

            has_anomaly = True

            anomaly_reasons.append(f"Implausibly low energy consumption ({round(efficiency_kwh_per_km, 3)} kWh/km).")



        # Session duration vs energy transfer rate check

        duration_hours = (data.end_time - data.start_time).total_seconds() / 3600.0

        if duration_hours > 0:

            avg_kw = data.energy_consumed_kwh / duration_hours

            if avg_kw > (station.max_output_kw * 1.2):

                has_anomaly = True

                anomaly_reasons.append(f"Session charge rate ({round(avg_kw, 1)} kW) exceeded station maximum rating ({station.max_output_kw} kW).")



        if data.battery_state_of_health_pct < 60.0:

            has_anomaly = True

            anomaly_reasons.append("Critical battery degradation flag (<60% SoH).")



        anomaly_str = "; ".join(anomaly_reasons) if has_anomaly else None



        return net_avoided_kg, has_anomaly, anomaly_str
