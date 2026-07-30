// =============================================================================

// VeriField Nexus — Sector Analytics & MRV Verification Page

// =============================================================================



"use client";



import React, { useEffect, useState } from "react";

import { BarChart3, TrendingUp, ShieldCheck, Flame, Zap, RefreshCw, FileText } from "lucide-react";

import { useWorkspace } from "@/context/WorkspaceContext";

import ChartRenderer from "@/components/dashboard/ChartRenderer";

import { fetchActivities } from "@/lib/api";



export default function AnalyticsPage() {

  const { activeSector, activeMethodology } = useWorkspace();

  const [dashboardData, setDashboardData] = useState<any>(null);

  const [isLoading, setIsLoading] = useState(true);



  useEffect(() => {

    async function loadData() {

      setIsLoading(true);

      try {

        const res = await fetchActivities({ per_page: 50 });

        setDashboardData(res);

      } catch (err) {

        console.error("Failed to load analytics dashboard data", err);

      } finally {

        setIsLoading(false);

      }

    }

    loadData();

  }, [activeSector, activeMethodology]);



  const secName = (activeSector || "Clean Cookstoves").replace("_", " ").toUpperCase();



  return (

    <div className="space-y-6">

      {/* Analytics Banner */}

      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">

        <div>

          <div className="flex items-center gap-2 mb-1">

            <span className="w-2 h-2 rounded-full bg-[#00B47A]" />

            <span className="text-[10px] font-black text-[#00B47A] uppercase tracking-wider">

              {secName} SECTOR ANALYTICS

            </span>

          </div>

          <h2 className="text-xl font-bold text-[var(--color-text-primary)]">

            Quantitative Performance & Emissions Reduction Ledger

          </h2>

          <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">

            Methodology: <span className="font-mono font-bold text-[var(--color-text-primary)]">{activeMethodology || "AMS-II.G"}</span> (Read-Only Certified)

          </p>

        </div>



        <div className="flex items-center gap-3">

          <div className="px-3 py-1.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs font-mono font-bold text-emerald-400">

            Trust Rating: 99.4%

          </div>

        </div>

      </div>



      {/* Sector Charts Workspace */}

      <div className="space-y-6">

        <ChartRenderer charts={dashboardData?.charts} sectorCode={activeSector} />

      </div>

    </div>

  );

}
