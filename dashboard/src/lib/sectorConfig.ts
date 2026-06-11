// =============================================================================
// VeriField Nexus — Dynamic Sector Configuration Engine
// =============================================================================
// Drives the dynamic /dashboard UI elements, metric card mappings, recharts,
// methodologies, and data queries based on the user's active sector context.
// Supports: Cookstove and Energy sectors.
// =============================================================================

export interface KPICardDef {
  key: string;
  label: string;
  valueField: string; // matches backend analytics summary keys
  unit: string;
  iconName: string; // matches lucide-react icon names
  colorTheme: "green" | "amber" | "blue" | "purple" | "emerald";
  description: string;
}

export interface ChartDef {
  key: string;
  title: string;
  type: "area" | "bar" | "line";
  dataKeyX: string;
  dataKeyY: string;
  fillColor: string;
  strokeColor: string;
}

export interface SectorConfig {
  id: string;
  label: string;
  badge: string;
  description: string;
  methodology: string;
  registryReference: string;
  kpis: KPICardDef[];
  charts: ChartDef[];
}

export const SECTOR_CONFIGS: Record<string, SectorConfig> = {
  cookstove: {
    id: "cookstove",
    label: "Clean Cooking Sector",
    badge: "Cookstove MRV Engine",
    description: "Stove installation deployment, household usage verification, and biomass displacement tracking.",
    methodology: "Gold Standard TPDDTEC v3.1 / Verra VMR0050",
    registryReference: "Verra VMR0050 & GS-TPDDTEC",
    kpis: [
      {
        key: "co2_reduced",
        label: "Total CO₂ Reduced",
        valueField: "total_reductions_tco2e",
        unit: "tCO₂e",
        iconName: "Leaf",
        colorTheme: "green",
        description: "Verified offset credits"
      },
      {
        key: "households",
        label: "Households Reached",
        valueField: "total_installations",
        unit: "Homes",
        iconName: "Home",
        colorTheme: "blue",
        description: "Stoves deployed in households"
      },
      {
        key: "usage_pct",
        label: "Stove Usage Rate",
        valueField: "active_utilization_rate",
        unit: "%",
        iconName: "Flame",
        colorTheme: "amber",
        description: "Mean daily utilization rate"
      },
      {
        key: "portfolio_value",
        label: "Portfolio Credit Value",
        valueField: "portfolio_value_usd",
        unit: "$",
        iconName: "DollarSign",
        colorTheme: "emerald",
        description: "At baseline price of $15/tCO2e"
      }
    ],
    charts: [
      {
        key: "reductions_over_time",
        title: "Daily Emission Reductions (tCO₂e)",
        type: "area",
        dataKeyX: "date",
        dataKeyY: "reductions",
        fillColor: "rgba(16, 185, 129, 0.1)",
        strokeColor: "#10b981"
      },
      {
        key: "usage_utilization",
        title: "Daily Household Cookstove Usage (Hours)",
        type: "bar",
        dataKeyX: "date",
        dataKeyY: "avg_hours",
        fillColor: "rgba(245, 158, 11, 0.15)",
        strokeColor: "#f59e0b"
      }
    ]
  },
  energy: {
    id: "energy",
    label: "Hybrid Energy Sector",
    badge: "Energy Displacement MRV",
    description: "Smart inverter telemetry monitoring, diesel backup displacement, and clean solar generation tracking.",
    methodology: "Verra AMS-I.F / Gold Standard Renewable Energy",
    registryReference: "Verra AMS-I.F / Gold Standard",
    kpis: [
      {
        key: "co2_displaced",
        label: "Total CO₂ Displaced",
        valueField: "total_reductions_tco2e",
        unit: "tCO₂e",
        iconName: "Leaf",
        colorTheme: "amber",
        description: "Diesel & grid offset carbon credits"
      },
      {
        key: "energy_generated",
        label: "Energy Generated",
        valueField: "total_generation_mwh",
        unit: "MWh",
        iconName: "Zap",
        colorTheme: "blue",
        description: "Clean solar PV energy generation"
      },
      {
        key: "diesel_avoided",
        label: "Total Diesel Avoided",
        valueField: "total_diesel_avoided_liters",
        unit: "Liters",
        iconName: "Fuel",
        colorTheme: "emerald",
        description: "Avoided diesel consumption"
      },
      {
        key: "active_sites",
        label: "Active Sites",
        valueField: "total_installations",
        unit: "Sites",
        iconName: "Layers",
        colorTheme: "purple",
        description: "Verified operational systems"
      }
    ],
    charts: [
      {
        key: "generation_over_time",
        title: "Daily Clean Energy Generation (kWh)",
        type: "area",
        dataKeyX: "date",
        dataKeyY: "generation_kwh",
        fillColor: "rgba(59, 130, 246, 0.1)",
        strokeColor: "#3b82f6"
      },
      {
        key: "diesel_reduction",
        title: "Daily Baseline Diesel Displaced (Liters)",
        type: "bar",
        dataKeyX: "date",
        dataKeyY: "diesel_displaced_liters",
        fillColor: "rgba(245, 158, 11, 0.15)",
        strokeColor: "#f59e0b"
      }
    ]
  }
};

export function getSectorConfig(sectorId: string): SectorConfig {
  const norm = (sectorId || "cookstove").toLowerCase();
  return SECTOR_CONFIGS[norm] || SECTOR_CONFIGS.cookstove;
}
