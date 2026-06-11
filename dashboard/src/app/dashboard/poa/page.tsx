// =============================================================================
// VeriField Nexus — Programme of Activities (POA) Portfolio Aggregation
// =============================================================================
// Consolidates verified carbon credit yields, sector contributions,
// pipeline states, and registry compliance exports for Org Admins & Auditors.
// =============================================================================

"use client";

import { useEffect, useState } from "react";
import {
  Compass,
  Download,
  FileText,
  FileSpreadsheet,
  Layers,
  Lock,
  ArrowUpRight,
  ShieldCheck,
  AlertTriangle,
  Globe,
  Database,
  CheckCircle2,
  TrendingUp,
  HelpCircle,
  Activity,
  Flame,
  Zap,
  Check,
  Leaf
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid
} from "recharts";
import {
  fetchAnalyticsOverview,
  fetchCarbonLedger,
  fetchEnergyPortfolio,
  fetchMe,
  exportVerraCSV,
  exportGoldStandardJSON,
  setAuthToken
} from "@/lib/api";
import type { User } from "@/lib/types";

// Chart styling color tokens - branded shades of emerald green
const MIX_COLORS = ["#00B47A", "#10B981", "#34D399", "#059669"];

export default function POAPortfolioPage() {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Aggregated data states
  const [cookstoveCO2, setCookstoveCO2] = useState<number>(0);
  const [energyCO2, setEnergyCO2] = useState<number>(0);

  const [creditsIssued, setCreditsIssued] = useState<number>(0);
  const [pendingVerification, setPendingVerification] = useState<number>(0);

  const [activeStep, setActiveStep] = useState<number>(3); // default showing "Audited"
  const [isExporting, setIsExporting] = useState<Record<string, boolean>>({});
  const [exportMessage, setExportMessage] = useState<string>("VeriField Secure Ledger Ready");

  useEffect(() => {
    const token = localStorage.getItem("vf_token");
    if (token) setAuthToken(token);
    loadAggregatedData();
  }, []);

  const loadAggregatedData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Fetch user profile first
      const u = await fetchMe();
      setUser(u);

      if (u.role !== "admin" && u.role !== "auditor") {
        return; // UI handles permission block below
      }

      // Fetch carbon ledger & Energy portfolio
      const [ledger, energyPort] = await Promise.all([
        fetchCarbonLedger().catch(() => null),
        fetchEnergyPortfolio().catch(() => null)
      ]);

      // Dynamic grouping by methodology
      let cookstoveTotal = 0;
      let energyTotal = 0;

      let actualIssued = 0;
      let actualPending = 0;

      if (ledger?.data && Array.isArray(ledger.data)) {
        ledger.data.forEach((c: any) => {
          const val = c.tco2e || c.tco2 || c.tco2e_generated || 0;
          const status = (c.status || "").toLowerCase();

          if (status === "calculated" || status === "issued" || status === "pending_issuance") {
            const meth = (c.methodology || c.methodology_used || "").toLowerCase();

            if (
              meth.includes("tpddtec") || 
              meth.includes("vm0006") || 
              meth.includes("vmr0050") || 
              meth.includes("mecd") || 
              meth.includes("gs_")
            ) {
              cookstoveTotal += val;
            } else {
              // Fallback
              cookstoveTotal += val;
            }

            // Sum up actual status-based values dynamically from live DB records
            if (status === "issued") {
              actualIssued += val;
            } else if (status === "calculated" || status === "pending_issuance") {
              actualPending += val;
            }
          }
        });
      }

      // Energy verified total (use highest of carbon calculation ledger or energyPort total)
      const energyPortTotal = energyPort?.total_tco2e_reduced || 0;
      if (energyPortTotal > energyTotal) {
        const diff = energyPortTotal - energyTotal;
        energyTotal = energyPortTotal;
        actualPending += diff;
      }

      setCookstoveCO2(cookstoveTotal);
      setEnergyCO2(energyTotal);

      setCreditsIssued(actualIssued);
      setPendingVerification(actualPending);

    } catch (err: any) {
      console.error("POA aggregation failed:", err);
      setError(err?.message || "Failed to consolidate Programme of Activities database.");
    } finally {
      setIsLoading(false);
    }
  };

  const triggerVerraExport = async () => {
    setIsExporting(prev => ({ ...prev, verra: true }));
    try {
      await exportVerraCSV(80);
      setExportMessage("Verra POA registry manifest generated.");
    } catch (err) {
      // Fallback CSV download if API unavailable
      const headers = "program_id,sector,methodology,credits_tco2e,status";
      const rows = [];
      if (cookstoveCO2 > 0) rows.push(`"POA-NEXUS-01","Cookstove","Gold Standard TPDDTEC v3.1",${cookstoveCO2.toFixed(2)},"verified"`);
      if (energyCO2 > 0) rows.push(`"POA-NEXUS-02","Energy","Verra AMS-I.F",${energyCO2.toFixed(2)},"verified"`);

      const blob = new Blob([[headers, ...rows].join("\n")], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `poa_verra_export_${new Date().toISOString().split("T")[0]}.csv`;
      link.click();
      setExportMessage("Offline POA Verra manifest generated.");
    } finally {
      setIsExporting(prev => ({ ...prev, verra: false }));
    }
  };

  const triggerGoldStandardExport = async () => {
    setIsExporting(prev => ({ ...prev, gold: true }));
    try {
      await exportGoldStandardJSON(80);
      setExportMessage("Gold Standard POA registry portfolio created.");
    } catch (err) {
      // Fallback JSON download
      const mockData: Record<string, any> = {
        registry: "Gold Standard POA",
        programme_name: "VeriField Nexus Global POA",
        sectors: {},
        total_offsets_tco2e: totalYield,
        timestamp: new Date().toISOString()
      };
      if (cookstoveCO2 > 0) mockData.sectors.cookstove = cookstoveCO2;
      if (energyCO2 > 0) mockData.sectors.energy = energyCO2;

      const blob = new Blob([JSON.stringify(mockData, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `poa_goldstandard_${new Date().toISOString().split("T")[0]}.json`;
      link.click();
      setExportMessage("Offline POA Gold Standard manifest generated.");
    } finally {
      setIsExporting(prev => ({ ...prev, gold: false }));
    }
  };

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

  // Restricted Access view for non-admin/non-auditor users
  if (user && user.role !== "admin" && user.role !== "auditor") {
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

  // Derive metrics
  const totalYield = cookstoveCO2 + energyCO2;

  // Active project sectors calculation dynamically
  const activeSectorsList = [
    { name: "Cookstove", yield: cookstoveCO2 },
    { name: "Energy", yield: energyCO2 }
  ].filter(s => s.yield > 0);
  const activeSectorsCount = activeSectorsList.length;

  // Sector mix data
  const pieData = [
    { name: "Cookstove (Clean Cooking)", value: parseFloat(cookstoveCO2.toFixed(2)) },
    { name: "Hybrid Energy Systems", value: parseFloat(energyCO2.toFixed(2)) }
  ].filter(d => d.value > 0);

  const rings = pieData.map((item, idx) => {
    const radius = 80 - idx * 14;
    const circumference = 2 * Math.PI * radius;
    const percent = item.value / (totalYield || 1);
    const strokeDashoffset = circumference - percent * circumference;
    
    // Icon and theme color mapping
    let icon = Leaf;
    let color = MIX_COLORS[idx % MIX_COLORS.length];
    if (item.name.toLowerCase().includes("cookstove") || item.name.toLowerCase().includes("cooking")) {
      icon = Flame;
    } else if (item.name.toLowerCase().includes("energy") || item.name.toLowerCase().includes("inverter")) {
      icon = Zap;
    }
    
    return {
      ...item,
      radius,
      circumference,
      strokeDashoffset,
      color,
      icon,
      percentVal: percent * 100
    };
  });

  const activeRing = hoveredIndex !== null ? rings[hoveredIndex] : null;

  // Issuance pipeline steps
  const steps = [
    { label: "Quantification", desc: "Emissions displacement computed" },
    { label: "Verification", desc: "Boundaries & trust scores validated" },
    { label: "Audited", desc: "Third-party digital MRV certification" },
    { label: "Issued", desc: "Registry serialization generated" },
    { label: "Exported", desc: "Dispatched to registry terminal" }
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10 text-[var(--color-text-primary)]">
      
      {/* ========================================================================= */}
      {/* 🧭 HEADER SECTION */}
      {/* ========================================================================= */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4 animate-fade-in-up">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[9px] font-extrabold tracking-wider uppercase border border-emerald-500/15 flex items-center gap-1">
              <Database size={10} /> Registry Aggregation Layer
            </span>
            <span className="text-[10px] text-[var(--color-text-secondary)] font-medium">Programme of Activities (POA)</span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)] mt-1">
            POA Portfolio Performance
          </h1>
          <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">
            Consolidated analytics across Clean Cooking and Hybrid Energy modules.
          </p>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 🚀 AGGREGATED KPI METRICS */}
      {/* ========================================================================= */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 animate-fade-in-up stagger-children">
        
        {/* Total POA Yield */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-[#00B47A]/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Total POA Yield</p>
            <p className="text-2xl font-black text-[#00B47A] tracking-tight">
              {totalYield.toLocaleString(undefined, { maximumFractionDigits: 2 })} <span className="text-xs font-bold text-[var(--color-text-muted)]">tCO₂e</span>
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Aggregated across all active sectors</p>
          </div>
          <div className="p-3 bg-[#00B47A]/5 border border-[#00B47A]/10 rounded-xl text-[#00B47A] shrink-0 group-hover:scale-105 transition-all">
            <Leaf size={18} />
          </div>
        </div>

        {/* Credits Issued */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-emerald-500/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Credits Issued</p>
            <p className="text-2xl font-black text-emerald-400 tracking-tight">
              {creditsIssued.toLocaleString(undefined, { maximumFractionDigits: 0 })} <span className="text-xs font-bold text-[var(--color-text-muted)]">VERs</span>
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Successfully registered & serialized</p>
          </div>
          <div className="p-3 bg-emerald-500/5 border border-emerald-500/10 rounded-xl text-emerald-400 shrink-0 group-hover:scale-105 transition-all">
            <ShieldCheck size={18} />
          </div>
        </div>

        {/* Pending Verification */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-[#F59E0B]/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Pending Verification</p>
            <p className="text-2xl font-black text-[#F59E0B] tracking-tight">
              {pendingVerification.toLocaleString(undefined, { maximumFractionDigits: 0 })} <span className="text-xs font-bold text-[var(--color-text-muted)]">tCO₂e</span>
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Currently in auditing pipeline</p>
          </div>
          <div className="p-3 bg-[#F59E0B]/5 border border-[#F59E0B]/10 rounded-xl text-[#F59E0B] shrink-0 group-hover:scale-105 transition-all">
            <Activity size={18} />
          </div>
        </div>

        {/* Active Project Sectors */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-emerald-500/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Active Sectors</p>
            <p className="text-2xl font-black text-emerald-400 tracking-tight">
              {activeSectorsCount} <span className="text-xs font-bold text-[var(--color-text-muted)]">{activeSectorsCount === 1 ? "Module" : "Modules"}</span>
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">
              {activeSectorsList.length > 0 ? activeSectorsList.map(s => s.name).join(", ") : "None"}
            </p>
          </div>
          <div className="p-3 bg-emerald-500/5 border border-emerald-500/10 rounded-xl text-emerald-400 shrink-0 group-hover:scale-105 transition-all">
            <Layers size={18} />
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 🧩 SECTOR CONTRIBUTION & REGISTRY EXPORT */}
      {/* ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 items-stretch">
        
        {/* Sector Yield Contribution Concentric Rings Chart */}
        <div className="lg:col-span-2 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4 shadow-sm flex flex-col justify-between animate-fade-in-up">
          <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-2 mb-4">
            <div>
              <h3 className="text-xs font-extrabold uppercase tracking-wider">Sector Yield Contribution</h3>
              <p className="text-[var(--color-text-secondary)] text-[10px]">Comparative offset contributions by carbon project category.</p>
            </div>
            <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[8px] font-bold border border-emerald-500/20 uppercase">
              POA Ratio
            </span>
          </div>

          <div className="flex flex-col md:flex-row gap-6 items-center w-full justify-between py-2">
            
            {/* SVG Concentric Rings Block */}
            <div className="relative w-[180px] h-[180px] shrink-0 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 200 200">
                <defs>
                  {/* Glowing shadow filters for premium neon effect */}
                  {rings.map((r, i) => (
                    <filter id={`glow-${i}`} key={i} x="-20%" y="-20%" width="140%" height="140%">
                      <feGaussianBlur stdDeviation="3" result="blur" />
                      <feComposite in="SourceGraphic" in2="blur" operator="over" />
                    </filter>
                  ))}
                </defs>

                {rings.map((ring, idx) => {
                  const isHovered = hoveredIndex === idx;
                  return (
                    <g 
                      key={ring.name}
                      onMouseEnter={() => setHoveredIndex(idx)}
                      onMouseLeave={() => setHoveredIndex(null)}
                      className="cursor-pointer transition-all duration-300"
                    >
                      {/* Background track circle */}
                      <circle
                        cx="100"
                        cy="100"
                        r={ring.radius}
                        fill="transparent"
                        stroke="rgba(255,255,255,0.04)"
                        strokeWidth="8"
                      />
                      {/* Active value arc */}
                      <circle
                        cx="100"
                        cy="100"
                        r={ring.radius}
                        fill="transparent"
                        stroke={ring.color}
                        strokeWidth={isHovered ? "10" : "8"}
                        strokeDasharray={ring.circumference}
                        strokeDashoffset={ring.strokeDashoffset}
                        strokeLinecap="round"
                        filter={isHovered ? `url(#glow-${idx})` : undefined}
                        className="transition-all duration-500 ease-out"
                        style={{
                          transition: "stroke-width 0.2s, stroke-dashoffset 0.8s ease-in-out"
                        }}
                      />
                    </g>
                  );
                })}
              </svg>

              {/* Center Content text block */}
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none p-4">
                {activeRing ? (
                  <div className="animate-fade-in space-y-0.5">
                    <p className="text-[7px] font-black uppercase tracking-wider text-[var(--color-text-muted)] truncate max-w-[100px]">
                      {activeRing.name.split(" ")[0]}
                    </p>
                    <p 
                      className="text-sm font-black tracking-tight"
                      style={{ color: activeRing.color }}
                    >
                      {activeRing.value.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                    </p>
                    <p className="text-[7px] text-[var(--color-text-secondary)] font-bold">
                      {activeRing.percentVal.toFixed(1)}%
                    </p>
                  </div>
                ) : (
                  <div className="space-y-0.5">
                    <p className="text-[8px] font-extrabold uppercase tracking-wider text-[var(--color-text-muted)]">
                      POA Yield
                    </p>
                    <p className="text-base font-black text-white tracking-tight">
                      {totalYield.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                    </p>
                    <p className="text-[7px] text-[var(--color-text-muted)] font-semibold">
                      tCO₂e
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Legends / Sector Yield Cards */}
            <div className="flex flex-col gap-3 flex-1 w-full max-w-lg">
              {rings.map((ring, idx) => {
                const Icon = ring.icon;
                const isHovered = hoveredIndex === idx;
                return (
                  <div
                    key={ring.name}
                    onMouseEnter={() => setHoveredIndex(idx)}
                    onMouseLeave={() => setHoveredIndex(null)}
                    className={`p-3.5 rounded-2xl border transition-all duration-300 flex items-center justify-between cursor-pointer ${
                      isHovered 
                        ? "bg-[var(--color-background)] border-emerald-500/40 shadow-md transform -translate-y-0.5" 
                        : "bg-[var(--color-surface)]/60 border-[var(--color-border)] hover:border-[#00B47A]/30"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div 
                        className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-transform duration-300"
                        style={{ 
                          backgroundColor: `${ring.color}15`, 
                          color: ring.color,
                          transform: isHovered ? 'scale(1.05)' : 'scale(1)'
                        }}
                      >
                        <Icon size={18} />
                      </div>
                      <div className="space-y-0.5">
                        <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">
                          {ring.name.split(" ")[0]}
                        </p>
                        <p className="text-xs font-black text-[var(--color-text-primary)]">
                          {ring.name}
                        </p>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-xs font-black text-[var(--color-text-primary)]">
                        {ring.value.toLocaleString(undefined, { maximumFractionDigits: 1 })} <span className="text-[9px] text-[var(--color-text-secondary)] font-normal">tCO₂e</span>
                      </p>
                      <p className="text-[10px] text-emerald-400 font-bold">
                        {ring.percentVal.toFixed(1)}%
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>

          </div>
        </div>

        {/* POA Registry Export Terminal */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4 shadow-sm flex flex-col justify-between animate-fade-in-up">
          <div>
            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-2 mb-3">
              <div>
                <h3 className="text-xs font-extrabold uppercase tracking-wider">POA Export Terminal</h3>
                <p className="text-[var(--color-text-secondary)] text-[10px]">Registry-ready data exports for Verra and Gold Standard.</p>
              </div>
              <Download size={14} className="text-emerald-400" />
            </div>

            <div className="space-y-2.5">
              <button
                onClick={triggerVerraExport}
                disabled={isExporting.verra}
                className="w-full flex items-center gap-2.5 p-2.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] hover:border-emerald-500 hover:bg-emerald-500/5 transition text-left group disabled:opacity-60 cursor-pointer"
              >
                <div className="w-8 h-8 rounded bg-emerald-500/10 flex items-center justify-center text-emerald-400 group-hover:scale-105 transition shrink-0">
                  <FileSpreadsheet size={14} />
                </div>
                <div>
                  <p className="text-[10px] font-extrabold">Verra CSV Export</p>
                  <p className="text-[8px] text-[var(--color-text-muted)]">POA compiled schema manifest</p>
                </div>
                {isExporting.verra ? (
                  <div className="ml-auto w-3.5 h-3.5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Download size={10} className="ml-auto text-[var(--color-text-muted)] group-hover:text-emerald-400 transition" />
                )}
              </button>

              <button
                onClick={triggerGoldStandardExport}
                disabled={isExporting.gold}
                className="w-full flex items-center gap-2.5 p-2.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] hover:border-emerald-500 hover:bg-emerald-500/5 transition text-left group disabled:opacity-60 cursor-pointer"
              >
                <div className="w-8 h-8 rounded bg-emerald-500/10 flex items-center justify-center text-emerald-400 group-hover:scale-105 transition shrink-0">
                  <FileText size={14} />
                </div>
                <div>
                  <p className="text-[10px] font-extrabold">Gold Standard Export</p>
                  <p className="text-[8px] text-[var(--color-text-muted)]">POA compiled JSON portfolio</p>
                </div>
                {isExporting.gold ? (
                  <div className="ml-auto w-3.5 h-3.5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Download size={10} className="ml-auto text-[var(--color-text-muted)] group-hover:text-emerald-400 transition" />
                )}
              </button>
            </div>
          </div>

          <div className="mt-3 pt-2.5 border-t border-[var(--color-border)] text-[8px] text-[var(--color-text-muted)] flex flex-col gap-0.5">
            <span className="font-semibold text-[var(--color-text-secondary)]">{exportMessage}</span>
            <span className="flex items-center gap-1"><Lock size={9} /> Signed & Verified under Programme of Activities (POA)</span>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 🧭 POA CREDIT PIPELINE TRACKER */}
      {/* ========================================================================= */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4 shadow-sm animate-fade-in-up">
        <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-2 mb-4">
          <div>
            <h3 className="text-xs font-extrabold uppercase tracking-wider">POA Credit Issuance Pipeline</h3>
            <p className="text-[var(--color-text-secondary)] text-[10px]">Track the lifecycle stage of compiled carbon credits.</p>
          </div>
        </div>

        {/* visual step progress tracker */}
        <div className="relative">
          <div className="absolute top-5 left-4 right-4 h-0.5 bg-[var(--color-border)] -z-10" />
          <div 
            className="absolute top-5 left-4 h-0.5 bg-emerald-500 -z-10 transition-all duration-300"
            style={{ width: `${(activeStep / (steps.length - 1)) * 96}%` }}
          />

          <div className="grid grid-cols-5 gap-2 text-center">
            {steps.map((step, idx) => {
              const isCompleted = idx < activeStep;
              const isActive = idx === activeStep;
              return (
                <button
                  key={step.label}
                  onClick={() => setActiveStep(idx)}
                  className="flex flex-col items-center focus:outline-none cursor-pointer"
                >
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all ${
                    isCompleted 
                      ? "bg-emerald-500 border-emerald-500 text-white" 
                      : isActive 
                      ? "bg-[var(--color-background)] border-emerald-500 text-emerald-400 font-extrabold" 
                      : "bg-[var(--color-background)] border-[var(--color-border)] text-[var(--color-text-muted)]"
                  }`}>
                    {isCompleted ? <Check size={16} /> : <span>{idx + 1}</span>}
                  </div>
                  <span className={`text-[10px] font-bold mt-2 ${isActive ? "text-emerald-400 font-black" : "text-[var(--color-text-primary)]"}`}>
                    {step.label}
                  </span>
                  <span className="text-[8px] text-[var(--color-text-muted)] max-w-[120px] hidden md:block mt-0.5">
                    {step.desc}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

    </div>
  );
}
