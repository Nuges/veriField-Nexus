import React from "react";
import { ArrowUpIcon, ArrowDownIcon } from "@heroicons/react/24/solid";

export interface MetricDefinition {
  id: string;
  label: string;
  value: string | number;
  unit?: string;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  colorTheme?: "primary" | "success" | "warning" | "danger" | "neutral";
}

interface DynamicMetricProps {
  metadata: MetricDefinition;
}

export function DynamicMetric({ metadata }: DynamicMetricProps) {
  const { label, value, unit, trend, trendValue, colorTheme = "primary" } = metadata;

  return (
    <div className={`p-6 rounded-2xl border border-slate-200/60 bg-white shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow duration-200`}>
      <div className="flex items-start justify-between">
        <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider">{label}</h3>
        {trend && (
          <div className={`flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-semibold ${
            trend === 'up' ? 'text-emerald-700 bg-emerald-100' :
            trend === 'down' ? 'text-rose-700 bg-rose-100' :
            'text-slate-700 bg-slate-100'
          }`}>
            {trend === 'up' && <ArrowUpIcon className="w-3 h-3" />}
            {trend === 'down' && <ArrowDownIcon className="w-3 h-3" />}
            <span>{trendValue}</span>
          </div>
        )}
      </div>
      
      <div className="mt-4 flex items-baseline space-x-2">
        <span className="text-3xl font-bold tracking-tight text-slate-900">{value}</span>
        {unit && <span className="text-sm font-medium text-slate-500">{unit}</span>}
      </div>
    </div>
  );
}
