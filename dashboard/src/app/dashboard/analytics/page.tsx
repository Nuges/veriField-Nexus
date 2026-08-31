// =============================================================================
// VeriField Nexus — Sector Analytics & MRV Verification Page
// =============================================================================

"use client";

import React, { useEffect, useState } from "react";
import {
  BarChart3,
  TrendingUp,
  ShieldCheck,
  Flame,
  Zap,
  RefreshCw,
  FileText,
  Download,
  CheckCircle2,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import ChartRenderer from "@/components/dashboard/ChartRenderer";
import { fetchActivities, generateAndDownloadReport, downloadArticle6PackageZip, fetchProjects } from "@/lib/api";

export default function AnalyticsPage() {
  const { activeSector, activeMethodology, user } = useWorkspace();
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);
  const [isDownloadingZip, setIsDownloadingZip] = useState(false);
  const [actionMessage, setActionMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

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

  const handleDownloadMRVPdf = async () => {
    setIsDownloadingPdf(true);
    setActionMessage(null);
    try {
      const orgIdToUse = user?.organization_id;
      if (!orgIdToUse) {
        throw new Error("Organization context is required. Please ensure your account is assigned to an active organization.");
      }

      // Fetch projects to resolve primary project ID if available
      const projectsRes = await fetchProjects().catch(() => ({ items: [] }));
      const primaryProjId = projectsRes.items && projectsRes.items.length > 0 ? projectsRes.items[0].id : undefined;

      const reportTitle = `${secName} Quantitative Carbon Performance & MRV Report`;
      await generateAndDownloadReport(orgIdToUse, primaryProjId, reportTitle);
      setActionMessage({ type: "success", text: "MRV Carbon Ledger PDF Report successfully compiled and downloaded!" });
    } catch (err: any) {
      console.error(err);
      setActionMessage({ type: "error", text: err?.message || "Failed to compile MRV report." });
    } finally {
      setIsDownloadingPdf(false);
      setTimeout(() => setActionMessage(null), 5000);
    }
  };

  const handleDownloadRegistryZip = async () => {
    setIsDownloadingZip(true);
    setActionMessage(null);
    try {
      const projectsRes = await fetchProjects().catch(() => ({ items: [] }));
      if (!projectsRes.items || projectsRes.items.length === 0) {
        throw new Error("No active projects found to compile registry submission package.");
      }
      const primaryProjId = projectsRes.items[0].id;
      await downloadArticle6PackageZip("VERRA", primaryProjId);
      setActionMessage({ type: "success", text: "Certified Multi-Format Registry Package ZIP downloaded!" });
    } catch (err: any) {
      console.error(err);
      setActionMessage({ type: "error", text: err?.message || "Failed to download submission package." });
    } finally {
      setIsDownloadingZip(false);
      setTimeout(() => setActionMessage(null), 5000);
    }
  };

  return (
    <div className="space-y-6">
      {/* Alert Notifications */}
      {actionMessage && (
        <div
          className={`p-3.5 rounded-xl border flex items-center gap-2.5 text-xs animate-fade-in ${
            actionMessage.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
              : "bg-red-500/10 border-red-500/30 text-red-400"
          }`}
        >
          {actionMessage.type === "success" ? <CheckCircle2 size={16} className="shrink-0" /> : <AlertTriangle size={16} className="shrink-0" />}
          <span>{actionMessage.text}</span>
        </div>
      )}

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
            Methodology:{" "}
            <span className="font-mono font-bold text-[var(--color-text-primary)]">
              {activeMethodology ||
                (activeSector === "hybrid_energy"
                  ? "ACM0002"
                  : activeSector === "biochar"
                  ? "VM0042"
                  : activeSector === "ev_mobility"
                  ? "AMS-III.C"
                  : "AMS-II.G")}
            </span>{" "}
            (Read-Only Certified)
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleDownloadMRVPdf}
            disabled={isDownloadingPdf}
            className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs transition flex items-center gap-1.5 shadow-sm disabled:opacity-50 cursor-pointer"
          >
            {isDownloadingPdf ? <Loader2 size={13} className="animate-spin" /> : <FileText size={13} />}
            <span>{isDownloadingPdf ? "Compiling PDF..." : "Download MRV PDF"}</span>
          </button>

          <button
            onClick={handleDownloadRegistryZip}
            disabled={isDownloadingZip}
            className="px-3 py-1.5 rounded-xl bg-[var(--color-background)] hover:bg-slate-100 dark:hover:bg-slate-800 text-[var(--color-text-primary)] border border-[var(--color-border)] font-semibold text-xs transition flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
          >
            {isDownloadingZip ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
            <span>{isDownloadingZip ? "Building ZIP..." : "Export Registry ZIP"}</span>
          </button>

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
