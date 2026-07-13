import React from "react";
import { DynamicMetric, MetricDefinition } from "./DynamicMetric";

export interface DashboardWidget {
  id: string;
  type: "metric" | "chart" | "grid";
  span?: 1 | 2 | 3 | 4;
  config: any; // Can be a metric definition or chart config
}

export interface DashboardMetadata {
  id: string;
  title: string;
  widgets: DashboardWidget[];
}

interface DynamicDashboardProps {
  metadata: DashboardMetadata;
}

export function DynamicDashboard({ metadata }: DynamicDashboardProps) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">{metadata.title}</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metadata.widgets.map((widget) => {
          // Calculate span classes
          const colSpanClass = widget.span === 2 ? "lg:col-span-2" :
                               widget.span === 3 ? "lg:col-span-3" :
                               widget.span === 4 ? "lg:col-span-4" : "";

          if (widget.type === "metric") {
            return (
              <div key={widget.id} className={colSpanClass}>
                <DynamicMetric metadata={widget.config as MetricDefinition} />
              </div>
            );
          }
          
          if (widget.type === "chart") {
            return (
              <div key={widget.id} className={`p-6 rounded-2xl border border-slate-200/60 bg-white shadow-sm flex items-center justify-center min-h-[300px] ${colSpanClass}`}>
                <p className="text-sm text-slate-400 font-medium">DynamicChart Component Placeholder ({widget.id})</p>
              </div>
            );
          }

          return null;
        })}
      </div>
    </div>
  );
}
