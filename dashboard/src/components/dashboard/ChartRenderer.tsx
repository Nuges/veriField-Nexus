"use client";



import React from "react";
import { ResponsiveContainer, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import { canonicalSectorCode } from "@/lib/moduleRegistry";



export interface ChartConfig {
  key?: string;
  id?: string;
  title: string;
  type?: string;
  dataKeyX?: string;
  dataKeyY?: string;
  fillColor?: string;
  strokeColor?: string;
  data?: unknown;
}

export default function ChartRenderer({ charts, sectorCode }: { charts?: ChartConfig[]; sectorCode?: string }) {



  // Default Chart Schemas (zeroed baseline when no activity dataset exists)

  const cookstoveCharts: ChartConfig[] = [

    {

      key: "daily_emissions",

      title: "DAILY EMISSION REDUCTIONS (TCO₂E)",

      type: "area",

      dataKeyX: "date",

      dataKeyY: "reductions",

      fillColor: "#00B47A",

      strokeColor: "#10B981",

      data: [

        { date: "Mon", reductions: 0 },

        { date: "Tue", reductions: 0 },

        { date: "Wed", reductions: 0 },

        { date: "Thu", reductions: 0 },

        { date: "Fri", reductions: 0 },

        { date: "Sat", reductions: 0 },

        { date: "Sun", reductions: 0 }

      ]

    },

    {

      key: "daily_usage",

      title: "DAILY HOUSEHOLD COOKSTOVE USAGE (HOURS)",

      type: "bar",

      dataKeyX: "date",

      dataKeyY: "hours",

      fillColor: "#3B82F6",

      strokeColor: "#2563EB",

      data: [

        { date: "Mon", hours: 0 },

        { date: "Tue", hours: 0 },

        { date: "Wed", hours: 0 },

        { date: "Thu", hours: 0 },

        { date: "Fri", hours: 0 },

        { date: "Sat", hours: 0 },

        { date: "Sun", hours: 0 }

      ]

    }

  ];



  const hybridEnergyCharts: ChartConfig[] = [

    {

      key: "daily_generation",

      title: "DAILY GENERATION (KWH)",

      type: "area",

      dataKeyX: "date",

      dataKeyY: "kwh",

      fillColor: "#00B47A",

      strokeColor: "#10B981",

      data: [

        { date: "Mon", kwh: 0 },

        { date: "Tue", kwh: 0 },

        { date: "Wed", kwh: 0 },

        { date: "Thu", kwh: 0 },

        { date: "Fri", kwh: 0 },

        { date: "Sat", kwh: 0 },

        { date: "Sun", kwh: 0 }

      ]

    },

    {

      key: "diesel_avoided",

      title: "DIESEL DISPLACEMENT (LITRES)",

      type: "bar",

      dataKeyX: "date",

      dataKeyY: "litres",

      fillColor: "#F59E0B",

      strokeColor: "#D97706",

      data: [

        { date: "Mon", litres: 0 },

        { date: "Tue", litres: 0 },

        { date: "Wed", litres: 0 },

        { date: "Thu", litres: 0 },

        { date: "Fri", litres: 0 },

        { date: "Sat", litres: 0 },

        { date: "Sun", litres: 0 }

      ]

    }

  ];



  const biocharCharts: ChartConfig[] = [

    {

      key: "biochar_production",

      title: "DAILY BIOCHAR PRODUCTION (TONNES)",

      type: "bar",

      dataKeyX: "date",

      dataKeyY: "tonnes",

      fillColor: "#F59E0B",

      strokeColor: "#D97706",

      data: [

        { date: "Mon", tonnes: 0 },

        { date: "Tue", tonnes: 0 },

        { date: "Wed", tonnes: 0 },

        { date: "Thu", tonnes: 0 },

        { date: "Fri", tonnes: 0 },

        { date: "Sat", tonnes: 0 },

        { date: "Sun", tonnes: 0 }

      ]

    },

    {

      key: "permanent_carbon",

      title: "PERMANENT CARBON STORED (TCO₂E)",

      type: "area",

      dataKeyX: "date",

      dataKeyY: "stored",

      fillColor: "#00B47A",

      strokeColor: "#10B981",

      data: [

        { date: "Mon", stored: 0 },

        { date: "Tue", stored: 0 },

        { date: "Wed", stored: 0 },

        { date: "Thu", stored: 0 },

        { date: "Fri", stored: 0 },

        { date: "Sat", stored: 0 },

        { date: "Sun", stored: 0 }

      ]

    }

  ];



  const evCharts: ChartConfig[] = [

    {

      key: "charging_sessions",

      title: "DAILY CHARGING SESSIONS",

      type: "bar",

      dataKeyX: "date",

      dataKeyY: "sessions",

      fillColor: "#3B82F6",

      strokeColor: "#2563EB",

      data: [

        { date: "Mon", sessions: 0 },

        { date: "Tue", sessions: 0 },

        { date: "Wed", sessions: 0 },

        { date: "Thu", sessions: 0 },

        { date: "Fri", sessions: 0 },

        { date: "Sat", sessions: 0 },

        { date: "Sun", sessions: 0 }

      ]

    },

    {

      key: "power_delivered",

      title: "ELECTRICITY DELIVERED (KWH)",

      type: "area",

      dataKeyX: "date",

      dataKeyY: "kwh",

      fillColor: "#00B47A",

      strokeColor: "#10B981",

      data: [

        { date: "Mon", kwh: 0 },

        { date: "Tue", kwh: 0 },

        { date: "Wed", kwh: 0 },

        { date: "Thu", kwh: 0 },

        { date: "Fri", kwh: 0 },

        { date: "Sat", kwh: 0 },

        { date: "Sun", kwh: 0 }

      ]

    }

  ];



  const agriCharts: ChartConfig[] = [
    {
      key: "field_activities_timeline",
      title: "FIELD ACTIVITIES OVER TIME",
      type: "area",
      dataKeyX: "date",
      dataKeyY: "activities",
      fillColor: "#00B47A",
      strokeColor: "#10B981",
      data: [
        { date: "Mon", activities: 0 },
        { date: "Tue", activities: 0 },
        { date: "Wed", activities: 0 },
        { date: "Thu", activities: 0 },
        { date: "Fri", activities: 0 },
        { date: "Sat", activities: 0 },
        { date: "Sun", activities: 0 },
      ],
    },
    {
      key: "land_units_growth",
      title: "LAND UNITS REGISTERED",
      type: "bar",
      dataKeyX: "date",
      dataKeyY: "units",
      fillColor: "#3B82F6",
      strokeColor: "#2563EB",
      data: [
        { date: "Mon", units: 0 },
        { date: "Tue", units: 0 },
        { date: "Wed", units: 0 },
        { date: "Thu", units: 0 },
        { date: "Fri", units: 0 },
        { date: "Sat", units: 0 },
        { date: "Sun", units: 0 },
      ],
    },
  ];

  const genericCharts: ChartConfig[] = [
    {
      key: "activity_volume",
      title: "ACTIVITY VOLUME OVER TIME",
      type: "area",
      dataKeyX: "date",
      dataKeyY: "count",
      fillColor: "#00B47A",
      strokeColor: "#10B981",
      data: [
        { date: "Mon", count: 0 },
        { date: "Tue", count: 0 },
        { date: "Wed", count: 0 },
        { date: "Thu", count: 0 },
        { date: "Fri", count: 0 },
        { date: "Sat", count: 0 },
        { date: "Sun", count: 0 },
      ],
    },
    {
      key: "registered_entities",
      title: "REGISTERED ENTITIES",
      type: "bar",
      dataKeyX: "date",
      dataKeyY: "entities",
      fillColor: "#3B82F6",
      strokeColor: "#2563EB",
      data: [
        { date: "Mon", entities: 0 },
        { date: "Tue", entities: 0 },
        { date: "Wed", entities: 0 },
        { date: "Thu", entities: 0 },
        { date: "Fri", entities: 0 },
        { date: "Sat", entities: 0 },
        { date: "Sun", entities: 0 },
      ],
    },
  ];

  const canonical = canonicalSectorCode(sectorCode || "").toUpperCase();
  const defaultCharts = canonical === "COOKSTOVES"
    ? cookstoveCharts
    : canonical === "HYBRID_ENERGY"
    ? hybridEnergyCharts
    : canonical === "BIOCHAR"
    ? biocharCharts
    : canonical === "EV_MOBILITY"
    ? evCharts
    : canonical === "AGRICULTURE_LAND_USE"
    ? agriCharts
    : genericCharts;



  const hasValidData = (cList?: ChartConfig[]) => {
    if (!cList || cList.length === 0) return false;
    return cList.some(c => {
      const dataArr = Array.isArray(c.data) ? c.data : [];
      return dataArr.length > 0 && dataArr.some((d: Record<string, unknown>) => {
        const val = (d.value ?? d.reductions ?? d.hours ?? d.kwh ?? d.litres ?? d.tonnes ?? d.stored ?? d.sessions) as unknown;
        return val !== undefined && val !== null;
      });
    });
  };

  const activeCharts = hasValidData(charts) ? charts! : defaultCharts;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {activeCharts.map((chart, i) => {
        const isArea = chart.type !== "bar";
        const rawData = Array.isArray(chart.data) ? chart.data : [];
        const chartData = rawData as Array<Record<string, unknown>>;
        const xKey = chart.dataKeyX || "date";
        const yKey = chart.dataKeyY || Object.keys(chartData[0] || {}).find(k => k !== xKey) || "value";
        const hasPoints = chartData.some(d => {
          const v = d[yKey];
          return v !== null && v !== undefined && Number(v) > 0;
        });
        const fill = chart.fillColor || "#00B47A";

        return (
          <div key={i} className="rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] p-5 backdrop-blur-md shadow-2xl transition-colors duration-300">
            <h4 className="text-[11px] font-black tracking-widest text-[var(--color-text-primary)] uppercase font-sans mb-4">
              {chart.title}
            </h4>

            <div className="h-[220px] w-full">
              {!hasPoints ? (
                <div className="h-full w-full flex flex-col items-center justify-center border border-dashed border-[var(--color-border)] rounded-xl bg-[var(--color-background)] p-4 text-center">
                  <p className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">
                    No activity recorded
                  </p>
                  <p className="text-[11px] text-[var(--color-text-secondary)] mt-1 opacity-70">
                    Data will populate dynamically as field records are logged.
                  </p>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  {isArea ? (
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id={`grad-${i}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={fill} stopOpacity={0.4} />
                          <stop offset="95%" stopColor={fill} stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey={xKey} stroke="#64748b" fontSize={11} tickLine={false} />
                      <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                      <Tooltip
                        contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "8px" }}
                        itemStyle={{ color: "#38bdf8" }}
                      />
                      <Area type="monotone" dataKey={yKey} stroke={fill} fillOpacity={1} fill={`url(#grad-${i})`} strokeWidth={2} />
                    </AreaChart>
                  ) : (
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey={xKey} stroke="#64748b" fontSize={11} tickLine={false} />
                      <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                      <Tooltip
                        contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "8px" }}
                        itemStyle={{ color: "#38bdf8" }}
                      />
                      <Bar dataKey={yKey} fill={fill} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  )}
                </ResponsiveContainer>
              )}
            </div>

          </div>

        );

      })}

    </div>

  );

}
