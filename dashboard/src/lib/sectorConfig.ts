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

export interface FilterOption {
  value: string;
  label: string;
}

export interface SectorConfig {
  id: string;
  label: string;
  badge: string;
  description: string;
  methodology: string;
  registryReference: string;
  activitiesTitle: string;
  activitiesDesc: string;
  filterOptions: FilterOption[];
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
    activitiesTitle: "Field Installation Records",
    activitiesDesc: "Review, filter, and audit near real-time field installation uploads, verification logs, and trust scores.",
    filterOptions: [
      { value: "", label: "All Cookstove Types" },
      { value: "CLEAN_COOKING", label: "Clean Cooking" }
    ],
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
    activitiesTitle: "Energy Telemetry & Site Records",
    activitiesDesc: "Review, filter, and audit smart hybrid energy inverter telemetry records, solar metrics, and logs.",
    filterOptions: [
      { value: "", label: "All Energy Types" },
      { value: "HYBRID_ENERGY", label: "Hybrid Energy" }
    ],
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
  },
  transport: {
    id: "transport",
    label: "Low-Carbon Transport Sector",
    badge: "EV & Fleet MRV",
    description: "Electric vehicle fleet deployment, charging telemetry, and fuel displacement tracking.",
    methodology: "Verra VM0038 / Gold Standard EV",
    registryReference: "Verra VM0038 / GS-EV",
    kpis: [
      {
        key: "co2_displaced",
        label: "Total CO₂ Displaced",
        valueField: "total_reductions_tco2e",
        unit: "tCO₂e",
        iconName: "Leaf",
        colorTheme: "green",
        description: "Verified transport emissions offset"
      },
      {
        key: "fuel_displaced",
        label: "Fuel Displaced",
        valueField: "total_fuel_displaced_liters",
        unit: "Liters",
        iconName: "Fuel",
        colorTheme: "amber",
        description: "Baseline gasoline/diesel avoided"
      },
      {
        key: "ev_fleet",
        label: "Active EVs",
        valueField: "total_installations",
        unit: "Vehicles",
        iconName: "Zap",
        colorTheme: "blue",
        description: "Verified operational EVs"
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
        key: "fuel_displacement",
        title: "Daily Fuel Displaced (Liters)",
        type: "bar",
        dataKeyX: "date",
        dataKeyY: "fuel_displaced",
        fillColor: "rgba(245, 158, 11, 0.15)",
        strokeColor: "#f59e0b"
      }
    ],
    activitiesTitle: "Transport Log",
    activitiesDesc: "Monitor fleet operations.",
    filterOptions: []
  },
  afolu: {
    id: "afolu",
    label: "AFOLU Forestry Sector",
    badge: "Biochar & Reforestation MRV",
    description: "Biomass density monitoring, satellite NDVI integration, and biochar sequestration tracking.",
    methodology: "Verra VM0044 / GS-Biochar",
    registryReference: "Verra VM0044 / GS-Biochar",
    kpis: [
      {
        key: "co2_sequestered",
        label: "Total CO₂ Sequestered",
        valueField: "total_reductions_tco2e",
        unit: "tCO₂e",
        iconName: "Leaf",
        colorTheme: "green",
        description: "Verified biochar/forestry offset"
      },
      {
        key: "ndvi_canopy",
        label: "Mean Canopy NDVI",
        valueField: "mean_canopy_density",
        unit: "Index",
        iconName: "MapPin",
        colorTheme: "emerald",
        description: "Satellite-verified vegetation density"
      },
      {
        key: "active_plots",
        label: "Active Plots",
        valueField: "total_installations",
        unit: "Hectares",
        iconName: "Layers",
        colorTheme: "blue",
        description: "Verified land plots"
      },
      {
        key: "portfolio_value",
        label: "Portfolio Credit Value",
        valueField: "portfolio_value_usd",
        unit: "$",
        iconName: "DollarSign",
        colorTheme: "purple",
        description: "At baseline price of $15/tCO2e"
      }
    ],
    charts: [
      {
        key: "sequestration_over_time",
        title: "Daily Carbon Sequestered (tCO₂e)",
        type: "area",
        dataKeyX: "date",
        dataKeyY: "reductions",
        fillColor: "rgba(16, 185, 129, 0.1)",
        strokeColor: "#10b981"
      },
      {
        key: "ndvi_progression",
        title: "Mean Canopy NDVI Progression",
        type: "line",
        dataKeyX: "date",
        dataKeyY: "ndvi_value",
        fillColor: "transparent",
        strokeColor: "#10b981"
      }
    ],
    activitiesTitle: "Forestry Log",
    activitiesDesc: "Monitor forestry activities.",
    filterOptions: []
  }
};

export function getSectorConfig(sectorId: string): SectorConfig {
  const norm = (sectorId || "cookstove").toLowerCase();
  return SECTOR_CONFIGS[norm] || SECTOR_CONFIGS.cookstove;
}
