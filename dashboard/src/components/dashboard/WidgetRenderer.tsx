"use client";



import React from "react";

import { Leaf, Home, Flame, DollarSign, Zap, Layers, Globe, Fuel, Activity, ShieldCheck } from "lucide-react";



interface KPI {

  code: string;

  label: string;

  value: number | string;

  unit?: string;

  subtext?: string;

  iconName?: string;

  colorTheme?: string;

}



const ICON_MAP: Record<string, any> = {

  Leaf, Home, Flame, DollarSign, Zap, Layers, Globe, Fuel, Activity, ShieldCheck

};



export default function WidgetRenderer({ kpis, sectorCode }: { kpis?: KPI[]; sectorCode?: string }) {

  const code = (sectorCode || "").toUpperCase();



  // Sector Default Fallbacks if backend KPIs are minimal

  const defaultKpis: KPI[] = (() => {

    if (code.includes("COOK") || code.includes("AMS_II_G")) {

      return [

        { code: "co2_reduced", label: "TOTAL CO₂ QUANTIFIED", value: "0", unit: "tCO₂e verified", iconName: "Leaf", colorTheme: "emerald" },

        { code: "households", label: "HOUSEHOLDS REACHED", value: "0", unit: "Stoves deployed in households", iconName: "Home", colorTheme: "blue" },

        { code: "usage_rate", label: "UTILISATION RATE", value: "No data", unit: "Mean daily utilisation rate", iconName: "Flame", colorTheme: "amber" },

        { code: "portfolio_val", label: "ESTIMATED CREDIT VALUE", value: "$0", unit: "At baseline price of $15/tCO2e", iconName: "DollarSign", colorTheme: "emerald" }

      ];

    } else if (code.includes("HYBRID") || code.includes("ENERGY")) {

      return [

        { code: "co2_reduced", label: "TOTAL CO₂ QUANTIFIED", value: "0", unit: "tCO₂e displaced", iconName: "Leaf", colorTheme: "emerald" },

        { code: "active_assets", label: "ACTIVE ENERGY ASSETS", value: "0", unit: "Mini-grids & hybrid units", iconName: "Zap", colorTheme: "blue" },

        { code: "generation", label: "TOTAL GENERATION", value: "0 kWh", unit: "Clean solar generation", iconName: "Layers", colorTheme: "amber" },

        { code: "diesel_avoided", label: "DIESEL AVOIDED", value: "0 L", unit: "Displaced generator fuel", iconName: "Fuel", colorTheme: "emerald" }

      ];

    } else if (code.includes("BIOCHAR")) {

      return [

        { code: "co2_reduced", label: "CARBON REMOVED", value: "0", unit: "tCO₂e permanent sink", iconName: "Leaf", colorTheme: "emerald" },

        { code: "biochar_produced", label: "BIOCHAR PRODUCED", value: "0", unit: "Tonnes high-carbon char", iconName: "Layers", colorTheme: "amber" },

        { code: "permanence", label: "CARBON PERMANENCE", value: "100+ Yrs", unit: "Soil sink durability", iconName: "ShieldCheck", colorTheme: "blue" },

        { code: "credit_val", label: "ESTIMATED CREDIT VALUE", value: "$0", unit: "At CORC price of $150/t", iconName: "DollarSign", colorTheme: "emerald" }

      ];

    } else if (code.includes("EV") || code.includes("MOBILITY")) {
      return [
        { code: "co2_reduced", label: "CO₂ DISPLACED", value: "0", unit: "tCO₂e EV fleet emissions", iconName: "Leaf", colorTheme: "emerald" },
        { code: "charging_sessions", label: "CHARGING SESSIONS", value: "0", unit: "Completed charges", iconName: "Zap", colorTheme: "blue" },
        { code: "active_vehicles", label: "ACTIVE VEHICLES", value: "0", unit: "Monitored EV units", iconName: "Globe", colorTheme: "amber" },
        { code: "credit_val", label: "ESTIMATED CREDIT VALUE", value: "$0", unit: "At baseline price", iconName: "DollarSign", colorTheme: "emerald" }
      ];
    } else {
      // Universal Carbon Assets Default
      return [
        { code: "co2_reduced", label: "TOTAL CO₂ QUANTIFIED", value: "0", unit: "tCO₂e emissions reduced", iconName: "Leaf", colorTheme: "emerald" },
        { code: "active_assets", label: "MONITORED ASSETS", value: "0", unit: "Registered field devices", iconName: "Layers", colorTheme: "blue" },
        { code: "usage_rate", label: "TELEMETRY UPTIME", value: "99.8%", unit: "Operational sensor stream", iconName: "Activity", colorTheme: "amber" },
        { code: "credit_val", label: "ESTIMATED CREDIT VALUE", value: "$0", unit: "At baseline price", iconName: "DollarSign", colorTheme: "emerald" }
      ];
    }

  })();



  const activeKpis = (kpis && kpis.length >= 4) ? kpis : defaultKpis;



  return (

    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full">

      {activeKpis.map((kpi, idx) => {
        const valStr = typeof kpi.value === "number" ? kpi.value.toLocaleString() : kpi.value;

        return (
          <div
            key={idx}
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4 transition-all hover:border-[var(--color-border-hover,rgba(0,180,122,0.3))] flex flex-col justify-between min-h-[110px]"
          >
            <div>
              <span className="text-xs font-semibold tracking-wide text-[var(--color-text-secondary)] uppercase leading-snug">
                {kpi.label}
              </span>
            </div>

            <div className="mt-2">
              <h3 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">
                {valStr}
              </h3>
              {(kpi.subtext || (kpi.unit && valStr !== "No data yet")) && (
                <p className="text-xs text-[var(--color-text-secondary)] leading-normal mt-1">
                  {kpi.subtext || kpi.unit}
                </p>
              )}
            </div>
          </div>
        );
      })}

    </div>

  );

}
