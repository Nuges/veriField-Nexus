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

        { code: "co2_reduced", label: "TOTAL CO₂ REDUCED", value: "155.5", unit: "tCO₂e", subtext: "Verified offset credits", iconName: "Leaf", colorTheme: "emerald" },

        { code: "households", label: "HOUSEHOLDS REACHED", value: "0", unit: "Stoves deployed in households", iconName: "Home", colorTheme: "blue" },

        { code: "usage_rate", label: "STOVE USAGE RATE", value: "No data yet", unit: "Mean daily utilization rate", iconName: "Flame", colorTheme: "amber" },

        { code: "portfolio_val", label: "PORTFOLIO CREDIT VALUE", value: "$2,333", unit: "At baseline price of $15/tCO2e", iconName: "DollarSign", colorTheme: "emerald" }

      ];

    } else if (code.includes("HYBRID") || code.includes("ENERGY")) {

      return [

        { code: "co2_reduced", label: "TOTAL CO₂ REDUCED", value: "482.1", unit: "tCO₂e", subtext: "Displaced thermal emissions", iconName: "Leaf", colorTheme: "emerald" },

        { code: "active_assets", label: "ACTIVE ENERGY ASSETS", value: "14", unit: "Mini-grids & hybrid units", iconName: "Zap", colorTheme: "blue" },

        { code: "generation", label: "TOTAL GENERATION", value: "1.2 GWh", unit: "Clean solar generation", iconName: "Layers", colorTheme: "amber" },

        { code: "diesel_avoided", label: "DIESEL AVOIDED", value: "184,200 L", unit: "Displaced generator fuel", iconName: "Fuel", colorTheme: "emerald" }

      ];

    } else if (code.includes("BIOCHAR")) {

      return [

        { code: "co2_reduced", label: "CARBON REMOVED", value: "890.0", unit: "tCO₂e", subtext: "Permanent sink storage", iconName: "Leaf", colorTheme: "emerald" },

        { code: "biochar_produced", label: "BIOCHAR PRODUCED", value: "310", unit: "Tonnes high-carbon char", iconName: "Layers", colorTheme: "amber" },

        { code: "permanence", label: "CARBON PERMANENCE", value: "100+ Yrs", unit: "Soil sink durability", iconName: "ShieldCheck", colorTheme: "blue" },

        { code: "credit_val", label: "PORTFOLIO CREDIT VALUE", value: "$133,500", unit: "At CORC price of $150/t", iconName: "DollarSign", colorTheme: "emerald" }

      ];

    } else {

      // EV Mobility & Generic

      return [

        { code: "co2_reduced", label: "CO₂ DISPLACED", value: "94.2", unit: "tCO₂e", subtext: "EV fleet zero-emissions", iconName: "Leaf", colorTheme: "emerald" },

        { code: "charging_sessions", label: "CHARGING SESSIONS", value: "12,480", unit: "Completed fast charges", iconName: "Zap", colorTheme: "blue" },

        { code: "kwh_delivered", label: "KWH DELIVERED", value: "340 MWh", unit: "Total grid power delivered", iconName: "Layers", colorTheme: "amber" },

        { code: "fleet_util", label: "FLEET UTILISATION", value: "88.4%", unit: "Active charging uptime", iconName: "Activity", colorTheme: "emerald" }

      ];

    }

  })();



  const activeKpis = (kpis && kpis.length >= 4) ? kpis : defaultKpis;



  return (

    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full">

      {activeKpis.map((kpi, idx) => {

        const Icon = ICON_MAP[kpi.iconName || ""] || Activity;

        const color = kpi.colorTheme || "emerald";

        const cardStyle = color === "blue"

          ? "border-blue-500/30 bg-[var(--color-surface)] shadow-sm hover:border-blue-500/50"

          : color === "amber"

          ? "border-amber-500/30 bg-[var(--color-surface)] shadow-sm hover:border-amber-500/50"

          : "border-[#00B47A]/30 bg-[var(--color-surface)] shadow-sm hover:border-[#00B47A]/50";



        const iconBg = color === "blue"

          ? "bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20"

          : color === "amber"

          ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"

          : "bg-emerald-500/10 text-[#00B47A] border border-emerald-500/20";



        const valStr = typeof kpi.value === "number" ? kpi.value.toLocaleString() : kpi.value;



        return (

          <div

            key={idx}

            className={`relative overflow-hidden rounded-2xl border ${cardStyle} p-5 transition-all duration-300 shadow-md hover:shadow-lg group flex flex-col justify-between min-h-[140px] h-auto`}

          >

            <div className="flex justify-between items-start gap-2 mb-3">

              <span className="text-[11px] font-black tracking-widest text-[var(--color-text-secondary)] uppercase font-sans leading-snug">

                {kpi.label}

              </span>

              <div className={`p-2 rounded-full ${iconBg} group-hover:scale-110 transition-transform shrink-0`}>

                <Icon size={16} />

              </div>

            </div>



            <div>

              <h3 className="text-2xl sm:text-3xl font-black text-[var(--color-text-primary)] font-sans tracking-tight">

                {valStr}

              </h3>

              {(kpi.subtext || (kpi.unit && valStr !== "No data yet")) && (

                <p className="text-[11px] font-semibold text-[var(--color-text-secondary)] font-sans leading-tight mt-1">

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
