"use client";



import React from "react";

import { ResponsiveContainer, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";



interface ChartConfig {

  key: string;

  title: string;

  type?: string;

  dataKeyX?: string;

  dataKeyY?: string;

  fillColor?: string;

  strokeColor?: string;

  data?: any[];

}



export default function ChartRenderer({ charts, sectorCode }: { charts?: ChartConfig[]; sectorCode?: string }) {

  const code = (sectorCode || "").toUpperCase();



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



  const defaultCharts = code.includes("COOK") || code.includes("AMS_II_G")

    ? cookstoveCharts

    : code.includes("HYBRID") || code.includes("ENERGY")

    ? hybridEnergyCharts

    : code.includes("BIOCHAR")

    ? biocharCharts

    : evCharts;



  const hasValidData = (cList?: ChartConfig[]) => {

    if (!cList || cList.length === 0) return false;

    return cList.some(c => c.data && c.data.length > 0 && c.data.some((d: any) => {

      const val = d.value ?? d.reductions ?? d.hours ?? d.kwh ?? d.litres ?? d.tonnes ?? d.stored ?? d.sessions;

      return val !== undefined && val !== null;

    }));

  };



  const activeCharts = hasValidData(charts) ? charts! : defaultCharts;



  return (

    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

      {activeCharts.map((chart, i) => {

        const isArea = chart.type !== "bar";

        const xKey = chart.dataKeyX || "date";

        const yKey = chart.dataKeyY || Object.keys(chart.data?.[0] || {}).find(k => k !== xKey) || "value";

        const fill = chart.fillColor || "#00B47A";



        return (

          <div key={i} className="rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] p-5 backdrop-blur-md shadow-2xl transition-colors duration-300">

            <h4 className="text-[11px] font-black tracking-widest text-[var(--color-text-primary)] uppercase font-sans mb-4">

              {chart.title}

            </h4>



            <div className="h-[220px] w-full">

              <ResponsiveContainer width="100%" height="100%">

                {isArea ? (

                  <AreaChart data={chart.data}>

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

                  <BarChart data={chart.data}>

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

            </div>

          </div>

        );

      })}

    </div>

  );

}
