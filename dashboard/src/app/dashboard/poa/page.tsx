// =============================================================================

// VeriField Nexus — Programme of Activities (POA) Portfolio Aggregation

// =============================================================================

// Consolidates verified carbon credit yields, sector contributions,

// pipeline states, and registry compliance exports for Org Admins & Auditors.

// =============================================================================



"use client";



import { useEffect, useState, useMemo, useCallback } from "react";
import {
  Download,
  FileText,
  FileSpreadsheet,
  Layers,
  Lock,
  ShieldCheck,
  Activity,
  Flame,
  Zap,
  Check,
  Leaf,
  Sprout,
} from "lucide-react";
import {
  fetchCarbonLedger,
  fetchMe,
  fetchProjects,
  exportVerraCSV,
  exportGoldStandardJSON,
  generateAndDownloadReport,
  setAuthToken,
} from "@/lib/api";
import type { User, Project } from "@/lib/types";
import { useWorkspace } from "@/context/WorkspaceContext";
import { isRouteAuthorized } from "@/lib/roles";
import { canonicalSectorCode, getSectorTerminology } from "@/lib/moduleRegistry";

// Branded color palette for sector contributions
const SECTOR_COLORS: Record<string, string> = {
  agriculture_land_use: "#10B981", // Emerald
  cookstoves: "#F59E0B",           // Amber
  hybrid_energy: "#3B82F6",        // Blue
  biochar: "#00B47A",              // Forest Green
  ev_mobility: "#8B5CF6",          // Purple
};

const CANONICAL_POA_SECTORS = [
  "agriculture_land_use",
  "cookstoves",
  "hybrid_energy",
  "biochar",
  "ev_mobility",
];

export default function POAPortfolioPage() {
  const { moduleRegistry } = useWorkspace();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Aggregated data states
  const [sectorYields, setSectorYields] = useState<Record<string, number>>({});
  const [totalYield, setTotalYield] = useState<number>(0);
  const [creditsIssued, setCreditsIssued] = useState<number>(0);
  const [pendingVerification, setPendingVerification] = useState<number>(0);
  const [participatingSectors, setParticipatingSectors] = useState<string[]>([]);

  const [activeStep, setActiveStep] = useState<number>(3); // default showing "Audited"
  const [isExporting, setIsExporting] = useState<Record<string, boolean>>({});
  const [exportMessage, setExportMessage] = useState<string>("VeriField Secure Ledger Ready");



  const loadAggregatedData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch user profile first
      const u = await fetchMe();
      setUser(u);

      if (!isRouteAuthorized("/dashboard/poa", u?.role)) {
        setIsLoading(false);
        return; // UI handles permission block below
      }

      // Fetch carbon ledger and projects in parallel
      const [ledger, projectsRes] = await Promise.all([
        fetchCarbonLedger().catch(() => null),
        fetchProjects().catch(() => null),
      ]);

      let actualIssued = 0;
      let actualPending = 0;
      let total = 0;
      const yields: Record<string, number> = {};

      if (ledger?.data && Array.isArray(ledger.data)) {
        ledger.data.forEach((c: Record<string, unknown>) => {
          const val = Number(c.tco2e || c.tco2 || c.tco2e_generated || 0);
          const status = (String(c.status || "")).toLowerCase();

          if (status === "calculated" || status === "issued" || status === "pending_issuance") {
            // Resolve canonical sector code
            const item = c;
            const rawCode = item.sector || item.methodology || item.methodology_used || "unknown";
            const canonCode = canonicalSectorCode(String(rawCode));

            yields[canonCode] = (yields[canonCode] || 0) + val;
            total += val;

            if (status === "issued") {
              actualIssued += val;
            } else if (status === "calculated" || status === "pending_issuance") {
              actualPending += val;
            }
          }
        });
      }

      // Determine participating sectors from both configured projects and ledger yields
      const sectorSet = new Set<string>();
      const projectItems: Project[] = Array.isArray(projectsRes?.items)
        ? projectsRes.items
        : Array.isArray(projectsRes)
        ? projectsRes
        : [];

      projectItems.forEach((p) => {
        const item = p as unknown as Record<string, unknown>;
        const raw = item.sector || item.sector_id || item.methodology_id;
        if (raw) {
          const code = canonicalSectorCode(String(raw));
          if (code && code !== "unknown") sectorSet.add(code);
        }
      });

      Object.entries(yields).forEach(([k, y]) => {
        if (y > 0 && k !== "unknown") sectorSet.add(k);
      });

      setSectorYields(yields);
      setTotalYield(total);
      setCreditsIssued(actualIssued);
      setPendingVerification(actualPending);
      setParticipatingSectors(Array.from(sectorSet));

      // Wire activeStep to real backend state
      if (actualIssued > 0) {
        setActiveStep(3); // Issued
      } else if (actualPending > 0) {
        setActiveStep(2); // Audited (Pending issuance)
      } else if (total > 0) {
        setActiveStep(1); // Verification
      } else {
        setActiveStep(0); // Quantification
      }
    } catch (err: unknown) {
      console.error("POA aggregation failed:", err);
      const msg = err instanceof Error ? err.message : "Failed to consolidate Programme of Activities database.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("vf_token");
    if (token) setAuthToken(token);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadAggregatedData();
  }, [loadAggregatedData]);

  const triggerVerraExport = async () => {
    setIsExporting((prev) => ({ ...prev, verra: true }));
    try {
      await exportVerraCSV(80);
      setExportMessage("Verra POA registry manifest generated.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Server Error";
      setExportMessage(`Export failed: ${msg}`);
    } finally {
      setIsExporting((prev) => ({ ...prev, verra: false }));
    }
  };

  const triggerGoldStandardExport = async () => {
    setIsExporting((prev) => ({ ...prev, gold: true }));
    try {
      await exportGoldStandardJSON(80);
      setExportMessage("Gold Standard POA registry portfolio created.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Server Error";
      setExportMessage(`Export failed: ${msg}`);
    } finally {
      setIsExporting((prev) => ({ ...prev, gold: false }));
    }
  };

  // Helper for sector icons
  const getSectorIcon = (code: string) => {
    switch (code) {
      case "agriculture_land_use":
        return Sprout;
      case "cookstoves":
        return Flame;
      case "hybrid_energy":
        return Zap;
      case "biochar":
        return Leaf;
      case "ev_mobility":
        return Activity;
      default:
        return Layers;
    }
  };

  // Sectors to display in the yield breakdown: all 5 canonical sectors
  const displaySectors = useMemo(() => {
    return CANONICAL_POA_SECTORS.map((code) => {
      const terminology = getSectorTerminology(code);
      const registryDef = moduleRegistry?.[code];
      const name = registryDef?.label || registryDef?.name || terminology.sectorName;
      const val = sectorYields[code];
      const isQuantified = typeof val === "number" && val > 0;
      const share = totalYield > 0 && isQuantified ? (val / totalYield) * 100 : null;
      const icon = getSectorIcon(code);
      const color = SECTOR_COLORS[code] || "#10B981";

      return {
        code,
        name,
        isQuantified,
        value: isQuantified ? val : 0,
        share,
        icon,
        color,
      };
    });
  }, [sectorYields, totalYield, moduleRegistry]);

  // Concentric rings data (only sectors with quantified values when totalYield > 0)
  const rings = useMemo(() => {
    if (totalYield <= 0) return [];
    const quantified = displaySectors.filter((s) => s.isQuantified);
    return quantified.map((item, idx) => {
      const radius = 75 - idx * 12;
      const circumference = 2 * Math.PI * radius;
      const percent = totalYield > 0 ? item.value / totalYield : 0;
      const strokeDashoffset = circumference - percent * circumference;

      return {
        ...item,
        radius,
        circumference,
        strokeDashoffset,
        percentVal: percent * 100,
      };
    });
  }, [displaySectors, totalYield]);

  const activeRing = hoveredIndex !== null && hoveredIndex < rings.length ? rings[hoveredIndex] : null;

  // Active Sectors Count & Semantics
  const activeSectorsCount = participatingSectors.length;
  const activeSectorsLabel = activeSectorsCount === 1 ? "Sector" : "Sectors";
  const activeSectorsListText =
    activeSectorsCount > 0
      ? participatingSectors
          .map((code) => moduleRegistry?.[code]?.label || getSectorTerminology(code).sectorName)
          .join(", ")
      : "No participating sectors";

  // Issuance pipeline steps
  const steps = [
    { label: "Quantification", desc: "Emissions displacement computed" },
    { label: "Verification", desc: "Boundaries & trust scores validated" },
    { label: "Audited", desc: "Third-party digital MRV certification" },
    { label: "Issued", desc: "Registry serialization generated" },
    { label: "Exported", desc: "Dispatched to registry terminal" },
  ];

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[400px] space-y-3">
        <div className="w-8 h-8 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />
        <p className="text-[var(--color-text-secondary)] text-xs font-semibold tracking-tight animate-pulse">
          Consolidating Programme of Activities ledger...
        </p>
      </div>
    );
  }

  // Restricted Access view for unauthorized roles
  if (user && !isRouteAuthorized("/dashboard/poa", user?.role)) {
    return (
      <div className="p-8 bg-red-500/10 border border-red-500/20 rounded-2xl max-w-xl mx-auto mt-14 text-center animate-fade-in-up">
        <Lock className="text-red-500 mx-auto mb-4" size={36} />
        <h2 className="text-sm font-bold uppercase tracking-wider text-red-500">Access Restricted</h2>
        <p className="text-xs text-[var(--color-text-secondary)] mt-2">
          The Programme of Activities (POA) Portfolio Aggregation view contains cross-methodology verified data and registry export capabilities. This view is restricted to Org Admins and Auditors.
        </p>
        <div className="mt-4 text-[9px] text-[var(--color-text-muted)] italic">
          Standard User Sandboxed Workspace Sector: {user.sector}
        </div>
      </div>
    );
  }



  return (

    <div className="space-y-6 max-w-7xl mx-auto pb-10 text-[var(--color-text-primary)]">



      {/* ========================================================================= */}

      {/* 🧭 HEADER SECTION */}

      {/* ========================================================================= */}

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4 animate-fade-in-up">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)]">
            POA Portfolio Performance
          </h1>
          <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">
            Consolidated analytics across all methodologies and sectors.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400">
          {error}
        </div>
      )}



      {/* ========================================================================= */}

      {/* 🚀 AGGREGATED KPI METRICS */}

      {/* ========================================================================= */}

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 animate-fade-in-up stagger-children">
        {/* Total POA Yield */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-xs relative overflow-hidden group hover:border-[#00B47A]/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">
              Total POA Yield
            </p>
            <p className="text-2xl font-black text-[#00B47A] tracking-tight">
              {totalYield > 0 ? (
                <>
                  {totalYield.toLocaleString(undefined, { maximumFractionDigits: 2 })}{" "}
                  <span className="text-xs font-bold text-[var(--color-text-muted)]">tCO₂e</span>
                </>
              ) : (
                <>
                  — <span className="text-xs font-bold text-[var(--color-text-muted)]">tCO₂e</span>
                </>
              )}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">
              {totalYield > 0 ? "Aggregated physical carbon yield" : "Not quantified"}
            </p>
          </div>
          <div className="p-3 bg-[#00B47A]/5 border border-[#00B47A]/10 rounded-xl text-[#00B47A] shrink-0 group-hover:scale-105 transition-all">
            <Leaf size={18} />
          </div>
        </div>

        {/* Credits Issued */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-xs relative overflow-hidden group hover:border-emerald-500/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">
              Credits Issued
            </p>
            <p className="text-2xl font-black text-emerald-400 tracking-tight">
              {creditsIssued > 0 ? (
                <>
                  {creditsIssued.toLocaleString(undefined, { maximumFractionDigits: 0 })}{" "}
                  <span className="text-xs font-bold text-[var(--color-text-muted)]">Credits</span>
                </>
              ) : (
                <>
                  0 <span className="text-xs font-bold text-[var(--color-text-muted)]">Credits</span>
                </>
              )}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">
              Successfully serialized registry units
            </p>
          </div>
          <div className="p-3 bg-emerald-500/5 border border-emerald-500/10 rounded-xl text-emerald-400 shrink-0 group-hover:scale-105 transition-all">
            <ShieldCheck size={18} />
          </div>
        </div>

        {/* Pending Verification */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-xs relative overflow-hidden group hover:border-[#F59E0B]/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">
              Pending Verification
            </p>
            <p className="text-2xl font-black text-[#F59E0B] tracking-tight">
              {pendingVerification > 0 ? (
                <>
                  {pendingVerification.toLocaleString(undefined, { maximumFractionDigits: 0 })}{" "}
                  <span className="text-xs font-bold text-[var(--color-text-muted)]">tCO₂e</span>
                </>
              ) : (
                <>
                  — <span className="text-xs font-bold text-[var(--color-text-muted)]">tCO₂e</span>
                </>
              )}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">
              {pendingVerification > 0 ? "Currently in auditing pipeline" : "No pending audits"}
            </p>
          </div>
          <div className="p-3 bg-[#F59E0B]/5 border border-[#F59E0B]/10 rounded-xl text-[#F59E0B] shrink-0 group-hover:scale-105 transition-all">
            <Activity size={18} />
          </div>
        </div>

        {/* Active Project Sectors */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-xs relative overflow-hidden group hover:border-emerald-500/30 transition-all">
          <div className="space-y-1 min-w-0">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">
              Active Sectors
            </p>
            <p className="text-2xl font-black text-emerald-400 tracking-tight">
              {activeSectorsCount}{" "}
              <span className="text-xs font-bold text-[var(--color-text-muted)]">
                {activeSectorsLabel}
              </span>
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium truncate" title={activeSectorsListText}>
              {activeSectorsListText}
            </p>
          </div>
          <div className="p-3 bg-emerald-500/5 border border-emerald-500/10 rounded-xl text-emerald-400 shrink-0 group-hover:scale-105 transition-all">
            <Layers size={18} />
          </div>
        </div>
      </div>

      {/* 🧩 SECTOR CONTRIBUTION & REGISTRY EXPORT */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 items-stretch">
        {/* Sector Yield Contribution Desktop Card */}
        <div data-testid="sector-yield-contribution" className="lg:col-span-2 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-5 shadow-xs flex flex-col justify-between animate-fade-in-up">
          <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3 mb-4">
            <div>
              <h3 className="text-xs font-extrabold uppercase tracking-wider">
                Sector Yield Contribution
              </h3>
              <p className="text-[var(--color-text-secondary)] text-[10px] mt-0.5">
                Comparative carbon yields by canonical programme methodology.
              </p>
            </div>
            <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[9px] font-bold border border-emerald-500/20 uppercase tracking-wide">
              POA Distribution
            </span>
          </div>

          <div className="flex flex-col md:flex-row gap-6 items-center w-full justify-between py-1">
            {/* Left: 30-35% Compact Centered Yield Visualization */}
            <div className="w-full md:w-[32%] shrink-0 flex items-center justify-center">
              <div className="relative w-[170px] h-[170px] flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 180 180">
                  <defs>
                    {rings.map((r, i) => (
                      <filter id={`glow-${i}`} key={i} x="-20%" y="-20%" width="140%" height="140%">
                        <feGaussianBlur stdDeviation="3" result="blur" />
                        <feComposite in="SourceGraphic" in2="blur" operator="over" />
                      </filter>
                    ))}
                  </defs>

                  {/* Empty state background ring */}
                  {rings.length === 0 && (
                    <circle
                      cx="90"
                      cy="90"
                      r="65"
                      fill="transparent"
                      stroke="currentColor"
                      strokeWidth="6"
                      strokeDasharray="4 4"
                      className="text-slate-200 dark:text-slate-800"
                    />
                  )}

                  {rings.map((ring, idx) => {
                    const isHovered = hoveredIndex === idx;
                    return (
                      <g
                        key={ring.name}
                        onMouseEnter={() => setHoveredIndex(idx)}
                        onMouseLeave={() => setHoveredIndex(null)}
                        className="cursor-pointer transition-all duration-300"
                      >
                        <circle
                          cx="90"
                          cy="90"
                          r={ring.radius}
                          fill="transparent"
                          stroke="currentColor"
                          strokeWidth="7"
                          className="text-slate-200 dark:text-slate-800"
                        />
                        <circle
                          cx="90"
                          cy="90"
                          r={ring.radius}
                          fill="transparent"
                          stroke={ring.color}
                          strokeWidth={isHovered ? "9" : "7"}
                          strokeDasharray={ring.circumference}
                          strokeDashoffset={totalYield > 0 ? ring.strokeDashoffset : ring.circumference}
                          strokeLinecap="round"
                          filter={isHovered ? `url(#glow-${idx})` : undefined}
                          className="transition-all duration-500 ease-out"
                          style={{
                            transition: "stroke-width 0.2s, stroke-dashoffset 0.8s ease-in-out",
                          }}
                        />
                      </g>
                    );
                  })}
                </svg>

                {/* Center text in visualization */}
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none p-3">
                  {activeRing ? (
                    <div className="animate-fade-in space-y-0.5">
                      <p className="text-[8px] font-black uppercase tracking-wider text-[var(--color-text-muted)] truncate max-w-[90px]">
                        {activeRing.name}
                      </p>
                      <p className="text-sm font-black tracking-tight" style={{ color: activeRing.color }}>
                        {activeRing.value.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                      </p>
                      <p className="text-[8px] text-[var(--color-text-secondary)] font-bold">
                        {activeRing.percentVal.toFixed(1)}%
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-0.5">
                      <p className="text-[8px] font-extrabold uppercase tracking-wider text-[var(--color-text-muted)]">
                        POA Yield
                      </p>
                      <p className="text-base font-black text-[var(--color-text-primary)] tracking-tight">
                        {totalYield > 0
                          ? totalYield.toLocaleString(undefined, { maximumFractionDigits: 1 })
                          : "—"}
                      </p>
                      <p className="text-[8px] text-[var(--color-text-muted)] font-medium">
                        {totalYield > 0 ? "tCO₂e" : "Not quantified"}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Right: 65-70% Compact 2-Column Responsive Grid */}
            <div className="w-full md:w-[68%] grid grid-cols-1 xl:grid-cols-2 gap-2.5">
              {displaySectors.map((sec, idx) => {
                const Icon = sec.icon;
                const isHovered = hoveredIndex === idx;

                return (
                  <div
                    key={sec.code}
                    onMouseEnter={() => setHoveredIndex(idx)}
                    onMouseLeave={() => setHoveredIndex(null)}
                    className={`p-2.5 rounded-xl border transition-all duration-200 flex items-center justify-between cursor-pointer ${
                      isHovered
                        ? "bg-[var(--color-background)] border-emerald-500/40 shadow-xs"
                        : "bg-[var(--color-surface)]/60 border-[var(--color-border)] hover:border-[#00B47A]/30"
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div
                        className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-transform duration-200"
                        style={{
                          backgroundColor: `${sec.color}15`,
                          color: sec.color,
                          transform: isHovered ? "scale(1.05)" : "scale(1)",
                        }}
                      >
                        <Icon size={16} />
                      </div>
                      <div className="min-w-0">
                        <p className="text-[8px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider truncate">
                          {sec.code.replace(/_/g, " ")}
                        </p>
                        <p className="text-[11px] font-bold text-[var(--color-text-primary)] truncate">
                          {sec.name}
                        </p>
                      </div>
                    </div>

                    <div className="text-right shrink-0 pl-2">
                      <p className="text-[11px] font-black text-[var(--color-text-primary)]">
                        {sec.isQuantified ? (
                          <>
                            {sec.value.toLocaleString(undefined, { maximumFractionDigits: 1 })}{" "}
                            <span className="text-[8px] text-[var(--color-text-secondary)] font-normal">
                              tCO₂e
                            </span>
                          </>
                        ) : (
                          <span className="text-[var(--color-text-muted)]">—</span>
                        )}
                      </p>
                      <p
                        className={`text-[9px] font-bold ${
                          sec.share !== null ? "text-emerald-400" : "text-[var(--color-text-muted)]"
                        }`}
                      >
                        {sec.share !== null ? `${sec.share.toFixed(1)}%` : "Not quantified"}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* POA Registry Export Terminal */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-5 shadow-xs flex flex-col justify-between animate-fade-in-up">
          <div>
            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3 mb-3">
              <div>
                <h3 className="text-xs font-extrabold uppercase tracking-wider">
                  POA Export Terminal
                </h3>
                <p className="text-[var(--color-text-secondary)] text-[10px] mt-0.5">
                  Registry-ready data exports for Verra and Gold Standard.
                </p>
              </div>
              <Download size={14} className="text-emerald-400" />
            </div>

            <div className="space-y-2.5">
              <button
                onClick={triggerVerraExport}
                disabled={isExporting.verra || totalYield === 0}
                className="w-full flex items-center gap-2.5 p-2.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] hover:border-emerald-500 hover:bg-emerald-500/5 transition text-left group disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                title={totalYield === 0 ? "Awaiting quantified portfolio yields" : "Export Verra CSV"}
              >
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 group-hover:scale-105 transition shrink-0">
                  <FileSpreadsheet size={14} />
                </div>
                <div>
                  <p className="text-[10px] font-extrabold">Verra CSV Export</p>
                  <p className="text-[8px] text-[var(--color-text-muted)]">
                    POA compiled schema manifest
                  </p>
                </div>
                {isExporting.verra ? (
                  <div className="ml-auto w-3.5 h-3.5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Download
                    size={10}
                    className="ml-auto text-[var(--color-text-muted)] group-hover:text-emerald-400 transition"
                  />
                )}
              </button>

              <button
                onClick={triggerGoldStandardExport}
                disabled={isExporting.gold || totalYield === 0}
                className="w-full flex items-center gap-2.5 p-2.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] hover:border-emerald-500 hover:bg-emerald-500/5 transition text-left group disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                title={totalYield === 0 ? "Awaiting quantified portfolio yields" : "Export Gold Standard JSON"}
              >
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 group-hover:scale-105 transition shrink-0">
                  <FileText size={14} />
                </div>
                <div>
                  <p className="text-[10px] font-extrabold">Gold Standard Export</p>
                  <p className="text-[8px] text-[var(--color-text-muted)]">
                    POA compiled JSON portfolio
                  </p>
                </div>
                {isExporting.gold ? (
                  <div className="ml-auto w-3.5 h-3.5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Download
                    size={10}
                    className="ml-auto text-[var(--color-text-muted)] group-hover:text-emerald-400 transition"
                  />
                )}
              </button>

              <button
                onClick={async () => {
                  if (!user?.organization_id) {
                    setExportMessage("Organization ID required for report generation.");
                    return;
                  }
                  setIsExporting((prev) => ({ ...prev, pdf: true }));
                  try {
                    await generateAndDownloadReport(
                      user.organization_id,
                      undefined,
                      "VeriField Nexus POA Aggregated MRV Ledger"
                    );
                    setExportMessage("POA MRV PDF report successfully generated & downloaded.");
                  } catch (err: unknown) {
                    const msg = err instanceof Error ? err.message : "Error";
                    setExportMessage(`PDF generation failed: ${msg}`);
                  } finally {
                    setIsExporting((prev) => ({ ...prev, pdf: false }));
                  }
                }}
                disabled={Boolean(isExporting["pdf"]) || totalYield === 0}
                className="w-full flex items-center gap-2.5 p-2.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] hover:border-blue-500 hover:bg-blue-500/5 transition text-left group disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                title={totalYield === 0 ? "Awaiting quantified portfolio yields" : "Generate Official MRV PDF"}
              >
                <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400 group-hover:scale-105 transition shrink-0">
                  <ShieldCheck size={14} />
                </div>
                <div>
                  <p className="text-[10px] font-extrabold text-blue-400">Generate Official MRV PDF</p>
                  <p className="text-[8px] text-[var(--color-text-muted)]">
                    Signed publication-grade certificate
                  </p>
                </div>
                {isExporting["pdf"] ? (
                  <div className="ml-auto w-3.5 h-3.5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Download
                    size={10}
                    className="ml-auto text-[var(--color-text-muted)] group-hover:text-blue-400 transition"
                  />
                )}
              </button>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-[var(--color-border)] text-[8px] text-[var(--color-text-muted)] flex flex-col gap-0.5">
            <span className="font-semibold text-[var(--color-text-secondary)]">{exportMessage}</span>
            <span className="flex items-center gap-1">
              <Lock size={9} /> Signed & Verified under Programme of Activities (POA)
            </span>
          </div>
        </div>
      </div>

      {/* 🧭 POA CREDIT PIPELINE TRACKER */}
      <div data-testid="poa-pipeline-tracker" className="mt-6 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-5 shadow-xs animate-fade-in-up">
        <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3 mb-6">
          <div>
            <h3 className="text-xs font-extrabold uppercase tracking-wider">
              POA Credit Issuance Pipeline
            </h3>
            <p className="text-[var(--color-text-secondary)] text-[10px] mt-0.5">
              Lifecycle progression of compiled carbon credits across verification gates.
            </p>
          </div>
        </div>

        {/* Responsive horizontal scroll container for pipeline */}
        <div className="overflow-x-auto pb-2 custom-scrollbar">
          <div className="min-w-[620px] relative px-6 py-2">
            {/* Connecting line */}
            <div className="absolute top-[30px] left-12 right-12 h-0.5 bg-[var(--color-border)] z-0" />
            <div
              className="absolute top-[30px] left-12 h-0.5 bg-emerald-500 z-0 transition-all duration-300"
              style={{ width: `${(activeStep / (steps.length - 1)) * 88}%` }}
            />

            <div className="grid grid-cols-5 gap-4 text-center relative z-10">
              {steps.map((step, idx) => {
                const isCompleted = idx < activeStep;
                const isActive = idx === activeStep;

                return (
                  <button
                    key={step.label}
                    onClick={() => setActiveStep(idx)}
                    className="flex flex-col items-center focus:outline-none cursor-pointer group"
                  >
                    <div
                      className={`w-11 h-11 rounded-full flex items-center justify-center border-2 transition-all shadow-xs ${
                        isCompleted
                          ? "bg-emerald-500 border-emerald-500 text-white"
                          : isActive
                          ? "bg-[var(--color-surface)] border-emerald-500 text-emerald-400 font-extrabold ring-4 ring-emerald-500/10"
                          : "bg-[var(--color-surface)] border-[var(--color-border)] text-[var(--color-text-muted)] group-hover:border-[#00B47A]/40"
                      }`}
                    >
                      {isCompleted ? <Check size={16} /> : <span className="text-xs font-bold">{idx + 1}</span>}
                    </div>

                    <span
                      className={`text-[11px] font-bold mt-2.5 transition-colors ${
                        isActive
                          ? "text-emerald-400 font-black"
                          : "text-[var(--color-text-primary)] group-hover:text-emerald-400"
                      }`}
                    >
                      {step.label}
                    </span>

                    <span className="text-[9px] text-[var(--color-text-muted)] max-w-[110px] mt-0.5 leading-tight">
                      {step.desc}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
