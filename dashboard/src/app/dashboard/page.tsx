"use client";

import { useEffect, useState } from "react";
import { DynamicDashboard, DashboardMetadata } from "@/components/dynamic/DynamicDashboard";
import { Loader2 } from "lucide-react";

export default function DashboardRoot() {
  const [metadata, setMetadata] = useState<DashboardMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const res = await fetch("/api/v1/methodologies");
        if (!res.ok) throw new Error("Failed to fetch methodology metadata");
        const data = await res.json();
        
        // Wrap the response in a DashboardMetadata structure
        setMetadata({
          id: "root-dashboard",
          title: "Universal CIOS Dashboard",
          widgets: Array.isArray(data) ? data.map((item, index) => ({
            id: `widget-${index}`,
            type: "metric",
            span: 1,
            config: {
              label: item.name || "Metric",
              value: item.value || "0",
              change: item.change || undefined
            }
          })) : (data.widgets || [])
        });
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchMetadata();
  }, []);

  if (loading) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center space-y-4">
        <Loader2 className="animate-spin text-emerald-500" size={32} />
        <p className="text-slate-500 text-sm animate-pulse">Loading dynamic metadata...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-500/10 border border-red-500/20 p-4 rounded-xl">
          <p className="text-red-500 font-semibold">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {metadata && <DynamicDashboard metadata={metadata} />}
    </div>
  );
}
