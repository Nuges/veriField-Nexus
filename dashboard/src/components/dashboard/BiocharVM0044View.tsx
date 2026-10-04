"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  AlertCircle,
  AlertTriangle,
  FileCheck2,
  CheckCircle2,
  Flame,
  Scale,
  Calculator,
  Layers,
  ArrowRight,
  TrendingDown,
  RefreshCw,
  Hash,
  Award,
  ExternalLink,
  Lock,
} from "lucide-react";
import {
  fetchVM0044Version,
  fetchVM0044Rules,
  fetchVM0044Dependencies,
  evaluateVM0044Applicability,
  evaluateVM0044Additionality,
  createVM0044Snapshot,
  executeVM0044Calculation,
  fetchVM0044Executions,
  type VM0044MethodologyVersionRecord,
  type VM0044RuleDefinitionRecord,
  type VM0044NormativeDependencyRecord,
  type VM0044ApplicabilityResponse,
  type VM0044AdditionalityResponse,
  type VM0044CalculationResponse,
  type VM0044CalculationExecutionRecord,
  type BiocharBatchRecord,
} from "@/lib/api";

interface BiocharVM0044ViewProps {
  projectId?: string;
  batches: BiocharBatchRecord[];
  onBatchSelect?: (batch: BiocharBatchRecord) => void;
}

export default function BiocharVM0044View({
  projectId,
  batches,
}: BiocharVM0044ViewProps) {
  const [version, setVersion] = useState<VM0044MethodologyVersionRecord | null>(null);
  const [rules, setRules] = useState<VM0044RuleDefinitionRecord[]>([]);
  const [deps, setDeps] = useState<VM0044NormativeDependencyRecord[]>([]);
  const [executions, setExecutions] = useState<VM0044CalculationExecutionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"calculator" | "governance" | "eligibility" | "executions">("calculator");

  // Calculator form state
  const [selectedBatchId, setSelectedBatchId] = useState<string>(batches[0]?.id || "");
  const [techClass, setTechClass] = useState<"HIGH_TECHNOLOGY" | "LOW_TECHNOLOGY">("HIGH_TECHNOLOGY");
  const [gridElectricityKwh, setGridElectricityKwh] = useState<number>(100.0);
  const [fossilFuelLitres, setFossilFuelLitres] = useState<number>(10.0);
  const [biomassTransportKm, setBiomassTransportKm] = useState<number>(45.0);
  const [biocharTransportKm, setBiocharTransportKm] = useState<number>(30.0);
  const [uncertaintyPct, setUncertaintyPct] = useState<number>(0.05);

  // Results state
  const [calcResult, setCalcResult] = useState<VM0044CalculationResponse | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [calcError, setCalcError] = useState<string | null>(null);

  // Applicability & Additionality state
  const [appResponse, setAppResponse] = useState<VM0044ApplicabilityResponse | null>(null);
  const [isEvaluatingApp, setIsEvaluatingApp] = useState(false);
  const [addResponse, setAddResponse] = useState<VM0044AdditionalityResponse | null>(null);
  const [isEvaluatingAdd, setIsEvaluatingAdd] = useState(false);

  // Additionality inputs
  const [regSurplus, setRegSurplus] = useState<boolean>(true);
  const [projectIrr, setProjectIrr] = useState<number>(8.5);
  const [benchmarkIrr, setBenchmarkIrr] = useState<number>(12.0);

  useEffect(() => {
    loadMetadata();
  }, [projectId]);

  useEffect(() => {
    if (batches.length > 0 && !selectedBatchId) {
      setSelectedBatchId(batches[0].id);
    }
  }, [batches]);

  async function loadMetadata() {
    setLoading(true);
    try {
      const [ver, rls, dp, execs] = await Promise.all([
        fetchVM0044Version().catch(() => null),
        fetchVM0044Rules().catch(() => []),
        fetchVM0044Dependencies().catch(() => []),
        fetchVM0044Executions(projectId).catch(() => []),
      ]);
      setVersion(ver);
      setRules(rls);
      setDeps(dp);
      setExecutions(execs);
    } catch (e) {
      console.error("Failed to load VM0044 metadata", e);
    } finally {
      setLoading(false);
    }
  }

  async function handleEvaluateApplicability() {
    if (!projectId) return;
    setIsEvaluatingApp(true);
    try {
      const res = await evaluateVM0044Applicability({
        project_id: projectId,
        batch_id: selectedBatchId || undefined,
      });
      setAppResponse(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      alert(`Applicability evaluation error: ${msg}`);
    } finally {
      setIsEvaluatingApp(false);
    }
  }

  async function handleEvaluateAdditionality() {
    if (!projectId) return;
    setIsEvaluatingAdd(true);
    try {
      const res = await evaluateVM0044Additionality({
        project_id: projectId,
        regulatory_surplus_demonstrated: regSurplus,
        analysis_option: "OPTION_2_BENCHMARK_ANALYSIS",
        project_irr_pct: projectIrr,
        benchmark_irr_pct: benchmarkIrr,
        benchmark_source: "Central Bank Commercial Benchmark Rate 2026",
      });
      setAddResponse(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      alert(`Additionality evaluation error: ${msg}`);
    } finally {
      setIsEvaluatingAdd(false);
    }
  }

  async function handleCalculate(preview: boolean = false) {
    if (!projectId || !selectedBatchId) {
      setCalcError("Please select a valid Project and Biochar Batch.");
      return;
    }
    setIsCalculating(true);
    setCalcError(null);

    try {
      const res = await executeVM0044Calculation({
        project_id: projectId,
        batch_id: selectedBatchId,
        technology_class: techClass,
        grid_electricity_kwh: gridElectricityKwh,
        fossil_fuel_litres: fossilFuelLitres,
        biomass_transport_distance_km: biomassTransportKm,
        biochar_transport_distance_km: biocharTransportKm,
        uncertainty_pct: uncertaintyPct,
        preview,
      });
      setCalcResult(res);
      if (!preview) {
        // Refresh executions list
        const updated = await fetchVM0044Executions(projectId);
        setExecutions(updated);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : (err && typeof err === "object" && "message" in err ? String((err as { message: unknown }).message) : "Calculation failed.");
      setCalcError(msg);
    } finally {
      setIsCalculating(false);
    }
  }

  if (loading) {
    return (
      <div className="p-8 text-center text-xs text-[var(--color-text-secondary)]">
        <RefreshCw size={18} className="animate-spin mx-auto mb-2 opacity-50" />
        Loading Verra VM0044 v1.2 Methodology Engine...
      </div>
    );
  }

  const selectedBatch = batches.find((b) => b.id === selectedBatchId);

  return (
    <div className="space-y-6">
      {/* 1. Methodology Locked Header */}
      <div className="p-5 rounded-xl border border-blue-500/30 bg-gradient-to-r from-blue-950/30 via-slate-900/40 to-emerald-950/20">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-blue-500/20 text-blue-400 border border-blue-500/40">
                VERRA VCS METHODOLOGY
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center gap-1">
                <CheckCircle2 size={10} />
                CCP-ELIGIBLE
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40">
                SCOPE 13 WASTE
              </span>
            </div>
            <h2 className="text-xl font-bold text-[var(--color-text-primary)] tracking-tight">
              {version?.name || "VM0044: Methodology for Biochar Utilization in Soil and Non-Soil Applications"}
            </h2>
            <p className="text-xs text-[var(--color-text-secondary)]">
              Version: <span className="font-mono font-semibold text-blue-300">v{version?.version || "1.2"}</span> |
              Released: <span className="font-mono text-zinc-300">28 June 2024</span> |
              Activity: <span className="text-zinc-300 font-medium">Removals (Carbon Dioxide Removal)</span> |
              Status: <span className="text-emerald-400 font-bold uppercase">{version?.status || "ACTIVE"}</span>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="p-2.5 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-right">
              <span className="text-[10px] uppercase text-[var(--color-text-secondary)] block">FROZEN SPECIFICATION</span>
              <span className="text-xs font-mono font-bold text-blue-400">VM0044 v1.2</span>
            </div>
          </div>
        </div>

        {/* View tabs */}
        <div className="flex items-center gap-2 mt-4 pt-3 border-t border-[var(--color-border)]">
          <button
            data-testid="vm0044-subtab-calculator"
            onClick={() => setActiveTab("calculator")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer ${
              activeTab === "calculator"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-[var(--color-text-secondary)] hover:text-white hover:bg-[var(--color-surface-hover)]"
            }`}
          >
            <Calculator size={14} />
            Quantification Engine
          </button>
          <button
            data-testid="vm0044-subtab-eligibility"
            onClick={() => setActiveTab("eligibility")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer ${
              activeTab === "eligibility"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-[var(--color-text-secondary)] hover:text-white hover:bg-[var(--color-surface-hover)]"
            }`}
          >
            <FileCheck2 size={14} />
            Dual-Gate Eligibility (Section 4 & 7)
          </button>
          <button
            data-testid="vm0044-subtab-governance"
            onClick={() => setActiveTab("governance")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer ${
              activeTab === "governance"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-[var(--color-text-secondary)] hover:text-white hover:bg-[var(--color-surface-hover)]"
            }`}
          >
            <ShieldCheck size={14} />
            Normative Rules & Dependencies ({rules.length})
          </button>
          <button
            data-testid="vm0044-subtab-executions"
            onClick={() => setActiveTab("executions")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer ${
              activeTab === "executions"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-[var(--color-text-secondary)] hover:text-white hover:bg-[var(--color-surface-hover)]"
            }`}
          >
            <Hash size={14} />
            Calculation History ({executions.length})
          </button>
        </div>
      </div>

      {/* 2. TAB CONTENT: Quantification Engine */}
      {activeTab === "calculator" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Input Controls */}
          <div className="lg:col-span-5 space-y-4">
            <div className="p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] space-y-4">
              <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
                <div className="flex items-center gap-2">
                  <Calculator size={16} className="text-blue-400" />
                  <h3 className="text-sm font-bold text-[var(--color-text-primary)]">
                    Calculation Input Parameters
                  </h3>
                </div>
                <span className="text-[10px] font-mono text-[var(--color-text-secondary)]">VM0044 EQS (1)-(15)</span>
              </div>

              {/* Batch Selector */}
              <div>
                <label className="text-xs font-semibold text-[var(--color-text-secondary)] block mb-1.5">
                  Authoritative Biochar Batch
                </label>
                {batches.length > 0 ? (
                  <select
                    value={selectedBatchId}
                    onChange={(e) => setSelectedBatchId(e.target.value)}
                    className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-xs font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-blue-500"
                  >
                    {batches.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.batch_number} — {b.feedstock_type} ({Number(b.biochar_yield_tonnes).toFixed(1)} t)
                      </option>
                    ))}
                  </select>
                ) : (
                  <p className="text-xs text-amber-400">No active biochar batches available in project.</p>
                )}
              </div>

              {selectedBatch && (
                <div className="p-2.5 rounded-lg bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-xs space-y-1">
                  <div className="flex justify-between">
                    <span className="text-[var(--color-text-secondary)]">Feedstock:</span>
                    <span className="font-medium text-[var(--color-text-primary)]">{selectedBatch.feedstock_type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[var(--color-text-secondary)]">Reported Dry Yield:</span>
                    <span className="font-mono font-medium text-[var(--color-text-primary)]">
                      {Number(selectedBatch.biochar_yield_tonnes).toFixed(2)} t
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[var(--color-text-secondary)]">Pyrolysis Temp:</span>
                    <span className="font-mono font-medium text-[var(--color-text-primary)]">
                      {selectedBatch.pyrolysis_temp_celsius && selectedBatch.pyrolysis_temp_celsius > 0 ? `${selectedBatch.pyrolysis_temp_celsius}°C` : "Unmonitored / Low-Tech"}
                    </span>
                  </div>
                </div>
              )}

              {/* Technology Class */}
              <div>
                <label className="text-xs font-semibold text-[var(--color-text-secondary)] block mb-1.5">
                  Technology Classification
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setTechClass("HIGH_TECHNOLOGY")}
                    className={`p-2.5 rounded-lg border text-left cursor-pointer transition-colors ${
                      techClass === "HIGH_TECHNOLOGY"
                        ? "bg-blue-500/10 border-blue-500/50 text-blue-400"
                        : "bg-[var(--color-background)] border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-zinc-500"
                    }`}
                  >
                    <span className="block text-xs font-bold">High-Tech Pyrolysis</span>
                    <span className="block text-[10px] opacity-75">Monitored temp &gt;600°C (PE_P = 0)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setTechClass("LOW_TECHNOLOGY")}
                    className={`p-2.5 rounded-lg border text-left cursor-pointer transition-colors ${
                      techClass === "LOW_TECHNOLOGY"
                        ? "bg-amber-500/10 border-amber-500/50 text-amber-400"
                        : "bg-[var(--color-background)] border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-zinc-500"
                    }`}
                  >
                    <span className="block text-xs font-bold">Low-Tech Kiln</span>
                    <span className="block text-[10px] opacity-75">Kon-Tiki / Retort (Eq 9 Methane PE_P)</span>
                  </button>
                </div>
              </div>

              {/* Pre-Treatment Emissions (PE_D) */}
              <div className="space-y-2 pt-2 border-t border-[var(--color-border)]">
                <span className="text-[11px] font-bold text-[var(--color-text-secondary)] block">
                  Pre-Treatment Energy (Equation 4 / PE_D)
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-[var(--color-text-secondary)] block mb-1">
                      Grid Electricity (kWh)
                    </label>
                    <input
                      type="number"
                      value={gridElectricityKwh}
                      onChange={(e) => setGridElectricityKwh(Number(e.target.value))}
                      className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded px-2.5 py-1.5 text-xs font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-[var(--color-text-secondary)] block mb-1">
                      Fossil Fuel (Litres Diesel)
                    </label>
                    <input
                      type="number"
                      value={fossilFuelLitres}
                      onChange={(e) => setFossilFuelLitres(Number(e.target.value))}
                      className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded px-2.5 py-1.5 text-xs font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Transportation Leakage (LE) */}
              <div className="space-y-2 pt-2 border-t border-[var(--color-border)]">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-[var(--color-text-secondary)]">
                    Transport Distances (TOOL16 Leakage)
                  </span>
                  <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300">
                    ≤200 km = EXEMPT (0 tCO2e)
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-[var(--color-text-secondary)] block mb-1">
                      Biomass Transport (km)
                    </label>
                    <input
                      type="number"
                      value={biomassTransportKm}
                      onChange={(e) => setBiomassTransportKm(Number(e.target.value))}
                      className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded px-2.5 py-1.5 text-xs font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-[var(--color-text-secondary)] block mb-1">
                      Biochar Transport (km)
                    </label>
                    <input
                      type="number"
                      value={biocharTransportKm}
                      onChange={(e) => setBiocharTransportKm(Number(e.target.value))}
                      className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded px-2.5 py-1.5 text-xs font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Uncertainty Deduction */}
              <div className="space-y-2 pt-2 border-t border-[var(--color-border)]">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-[var(--color-text-secondary)]">
                    VCS Uncertainty Margin
                  </span>
                  <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300">
                    &gt;10% = DEDUCTED (VCS s3.17)
                  </span>
                </div>
                <div>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="0.5"
                    value={uncertaintyPct}
                    onChange={(e) => setUncertaintyPct(Number(e.target.value))}
                    className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded px-2.5 py-1.5 text-xs font-mono"
                  />
                  <span className="text-[10px] text-[var(--color-text-secondary)] block mt-1">
                    Value: {(uncertaintyPct * 100).toFixed(1)}% {uncertaintyPct > 0.10 ? "(Deduction applies)" : "(Within 10% threshold, 0 deduction)"}
                  </span>
                </div>
              </div>

              {calcError && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-400 flex items-start gap-2">
                  <AlertCircle size={14} className="shrink-0 mt-0.5" />
                  <span>{calcError}</span>
                </div>
              )}

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => handleCalculate(true)}
                  disabled={isCalculating || !selectedBatchId}
                  className="px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-hover)] text-xs font-semibold text-[var(--color-text-primary)] hover:border-zinc-500 cursor-pointer disabled:opacity-50"
                >
                  Preview Simulation
                </button>
                <button
                  data-testid="vm0044-btn-execute-authoritative"
                  type="button"
                  onClick={() => handleCalculate(false)}
                  disabled={isCalculating || !selectedBatchId}
                  className="px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white shadow-sm flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  {isCalculating ? (
                    <RefreshCw size={14} className="animate-spin" />
                  ) : (
                    <Award size={14} />
                  )}
                  Authoritative Execute
                </button>
              </div>
            </div>
          </div>

          {/* Results Breakdown */}
          <div className="lg:col-span-7 space-y-4">
            {calcResult ? (
              <div data-testid="vm0044-results-container" className="p-5 rounded-xl border border-blue-500/30 bg-[var(--color-surface)] space-y-5">
                <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-[var(--color-text-primary)]">
                        VM0044 v1.2 Quantification Results
                      </h3>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                        calcResult.status === "CALCULATED" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                      }`}>
                        {calcResult.status}
                      </span>
                    </div>
                    <span className="text-[11px] text-[var(--color-text-secondary)] font-mono">
                      Calculation ID: {calcResult.calculation_id.slice(0, 12)}...
                    </span>
                  </div>

                  <div className="text-right">
                    <span className="text-[10px] uppercase font-bold text-[var(--color-text-secondary)] block">
                      NET REMOVALS (ER_y)
                    </span>
                    <span data-testid="vm0044-net-removals-val" className="text-2xl font-mono font-extrabold text-emerald-400">
                      {Number(calcResult.net_removal_tco2e).toFixed(4)} <span className="text-xs font-normal text-zinc-400">tCO2e</span>
                    </span>
                  </div>
                </div>

                {/* Equation Breakdown Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="p-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)]">
                    <span className="text-[10px] text-[var(--color-text-secondary)] uppercase block mb-1">
                      Gross Stored (Eq 2)
                    </span>
                    <span className="text-sm font-mono font-bold text-blue-400">
                      {Number(calcResult.equation_breakdown.gross_co2e_stored_tonnes).toFixed(4)} t
                    </span>
                    <span className="text-[9px] text-[var(--color-text-secondary)] block mt-0.5">
                      PR_de: {Number(calcResult.equation_breakdown.permanence_factor_pr_de).toFixed(2)}
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)]">
                    <span className="text-[10px] text-[var(--color-text-secondary)] uppercase block mb-1">
                      Baseline Emissions
                    </span>
                    <span className="text-sm font-mono font-bold text-zinc-300">
                      {Number(calcResult.equation_breakdown.er_ss_tonnes || 0).toFixed(4)} t
                    </span>
                    <span className="text-[9px] text-[var(--color-text-secondary)] block mt-0.5">
                      BE_SS,y = 0 (Conservative)
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)]">
                    <span className="text-[10px] text-[var(--color-text-secondary)] uppercase block mb-1">
                      Project Emissions (PE)
                    </span>
                    <span className="text-sm font-mono font-bold text-amber-400">
                      -{Number(calcResult.equation_breakdown.pe_ps_total_tonnes || 0).toFixed(4)} t
                    </span>
                    <span className="text-[9px] text-[var(--color-text-secondary)] block mt-0.5">
                      PE_D: {Number(calcResult.equation_breakdown.pe_d_tonnes || 0).toFixed(4)} | PE_P: {Number(calcResult.equation_breakdown.pe_p_tonnes || 0).toFixed(4)}
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)]">
                    <span className="text-[10px] text-[var(--color-text-secondary)] uppercase block mb-1">
                      Uncertainty Deduction
                    </span>
                    <span className="text-sm font-mono font-bold text-purple-400">
                      -{Number(calcResult.equation_breakdown.uncertainty_deduction_tonnes || 0).toFixed(4)} t
                    </span>
                    <span className="text-[9px] text-[var(--color-text-secondary)] block mt-0.5">
                      UD_y (Eq 14)
                    </span>
                  </div>
                </div>

                {/* Mathematical Lineage Trace */}
                <div className="p-4 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] space-y-2 text-xs">
                  <span className="font-bold text-[var(--color-text-primary)] block">
                    Mathematical Expression Lineage:
                  </span>
                  <div className="font-mono text-[11px] text-zinc-300 p-2.5 rounded bg-zinc-950/70 border border-zinc-800 space-y-1">
                    <div>1. CC_stored = {calcResult.equation_breakdown.biochar_dry_mass_tonnes} t × {(Number(calcResult.equation_breakdown.c_org_fraction) * 100).toFixed(1)}% × {calcResult.equation_breakdown.permanence_factor_pr_de} = {Number(calcResult.equation_breakdown.organic_carbon_stored_cc_tonnes).toFixed(4)} tC</div>
                    <div>2. Gross CO2e = {Number(calcResult.equation_breakdown.organic_carbon_stored_cc_tonnes).toFixed(4)} tC × (44/12) = {Number(calcResult.equation_breakdown.gross_co2e_stored_tonnes).toFixed(4)} tCO2e</div>
                    <div>3. Total PE = PE_D ({Number(calcResult.equation_breakdown.pe_d_tonnes).toFixed(4)}) + PE_P ({Number(calcResult.equation_breakdown.pe_p_tonnes).toFixed(4)}) + PE_C ({Number(calcResult.equation_breakdown.pe_c_tonnes).toFixed(4)}) = {Number(calcResult.equation_breakdown.pe_ps_total_tonnes).toFixed(4)} tCO2e</div>
                    <div>4. Net Removals ER_y = Gross ({Number(calcResult.equation_breakdown.gross_co2e_stored_tonnes).toFixed(4)}) - PE ({Number(calcResult.equation_breakdown.pe_ps_total_tonnes).toFixed(4)}) - LE ({Number(calcResult.equation_breakdown.le_total_tonnes).toFixed(4)}) - UD ({Number(calcResult.equation_breakdown.uncertainty_deduction_tonnes).toFixed(4)}) = {Number(calcResult.net_removal_tco2e).toFixed(4)} tCO2e</div>
                  </div>
                </div>

                {/* Cryptographic Lineage & Hashing */}
                <div className="p-3.5 rounded-lg bg-zinc-900/60 border border-[var(--color-border)] space-y-2 text-xs">
                  <span className="text-[10px] uppercase font-bold text-[var(--color-text-secondary)] block">
                    Cryptographic Integrity & Audit Signatures
                  </span>
                  <div className="space-y-1.5 font-mono text-[10px]">
                    <div className="flex items-center justify-between">
                      <span className="text-[var(--color-text-secondary)]">Canonical Snapshot Hash:</span>
                      <span className="text-blue-300 font-semibold truncate max-w-xs">{calcResult.snapshot_hash}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[var(--color-text-secondary)]">Execution Audit Hash:</span>
                      <span className="text-emerald-300 font-semibold truncate max-w-xs">{calcResult.calculation_hash}</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-12 text-center rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] space-y-3">
                <Calculator size={36} className="mx-auto text-[var(--color-text-secondary)] opacity-40" />
                <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">
                  Ready to Execute VM0044 v1.2 Quantification
                </h4>
                <p className="text-xs text-[var(--color-text-secondary)] max-w-md mx-auto">
                  Select an authoritative batch, configure energy and transport parameters, and run the calculation engine to compute permanent carbon removals per Verra VM0044 equations (1)-(15).
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3. TAB CONTENT: Dual-Gate Eligibility */}
      {activeTab === "eligibility" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Gate 1: Applicability Assessment */}
            <div className="p-5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] space-y-4">
              <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
                <div className="flex items-center gap-2">
                  <FileCheck2 size={16} className="text-emerald-400" />
                  <h3 className="text-sm font-bold text-[var(--color-text-primary)]">
                    Gate 1: Section 4 Applicability
                  </h3>
                </div>
                {appResponse && (
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                    appResponse.status === "ELIGIBLE" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-red-500/20 text-red-400 border border-red-500/30"
                  }`}>
                    {appResponse.status}
                  </span>
                )}
              </div>

              <p className="text-xs text-[var(--color-text-secondary)]">
                Evaluates project-level and batch-level compliance with VM0044 Section 4 conditions: Greenfield facility, biogenic waste biomass, verified pyrolysis technology, and approved end uses.
              </p>

              <button
                data-testid="vm0044-btn-evaluate-applicability"
                type="button"
                onClick={handleEvaluateApplicability}
                disabled={isEvaluatingApp || !projectId}
                className="w-full px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white shadow-sm flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                {isEvaluatingApp ? <RefreshCw size={14} className="animate-spin" /> : <ShieldCheck size={14} />}
                Run Section 4 Applicability Audit
              </button>

              {appResponse && (
                <div className="space-y-2 pt-2 border-t border-[var(--color-border)] text-xs">
                  <div className="flex items-center justify-between p-2 rounded bg-[var(--color-background)]">
                    <span>1. Production Facility (Greenfield)</span>
                    <span className={appResponse.facility_check.passed ? "text-emerald-400 font-bold" : "text-red-400 font-bold"}>
                      {appResponse.facility_check.passed ? "PASS" : "FAIL"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded bg-[var(--color-background)]">
                    <span>2. Feedstock Sourcing (Biogenic Waste)</span>
                    <span className={appResponse.feedstock_check.passed ? "text-emerald-400 font-bold" : "text-red-400 font-bold"}>
                      {appResponse.feedstock_check.passed ? "PASS" : "FAIL"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded bg-[var(--color-background)]">
                    <span>3. Process & Safety Standards</span>
                    <span className={appResponse.process_check.passed ? "text-emerald-400 font-bold" : "text-red-400 font-bold"}>
                      {appResponse.process_check.passed ? "PASS" : "FAIL"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded bg-[var(--color-background)]">
                    <span>4. End-Use Verification</span>
                    <span className={appResponse.end_use_check.passed ? "text-emerald-400 font-bold" : "text-red-400 font-bold"}>
                      {appResponse.end_use_check.passed ? "PASS" : "FAIL"}
                    </span>
                  </div>

                  {appResponse.blocking_findings.length > 0 && (
                    <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-400 space-y-1">
                      <span className="font-bold block">Blocking Ineligibility Findings:</span>
                      {appResponse.blocking_findings.map((f, i) => (
                        <div key={i}>• {f}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Gate 2: Additionality Assessment */}
            <div className="p-5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] space-y-4">
              <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
                <div className="flex items-center gap-2">
                  <Award size={16} className="text-blue-400" />
                  <h3 className="text-sm font-bold text-[var(--color-text-primary)]">
                    Gate 2: Section 7 Additionality (VT0008)
                  </h3>
                </div>
                {addResponse && (
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                    addResponse.status === "COMPLETE" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-red-500/20 text-red-400 border border-red-500/30"
                  }`}>
                    {addResponse.status}
                  </span>
                )}
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-xs text-[var(--color-text-secondary)]">Regulatory Surplus Demonstrated</label>
                  <input
                    type="checkbox"
                    checked={regSurplus}
                    onChange={(e) => setRegSurplus(e.target.checked)}
                    className="h-4 w-4 rounded border-zinc-700 bg-zinc-900 text-blue-600 focus:ring-blue-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-[var(--color-text-secondary)] block mb-1">
                      Project IRR without Carbon (%)
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      value={projectIrr}
                      onChange={(e) => setProjectIrr(Number(e.target.value))}
                      className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded px-2.5 py-1.5 text-xs font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-[var(--color-text-secondary)] block mb-1">
                      Benchmark Hurdle IRR (%)
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      value={benchmarkIrr}
                      onChange={(e) => setBenchmarkIrr(Number(e.target.value))}
                      className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded px-2.5 py-1.5 text-xs font-mono"
                    />
                  </div>
                </div>

                <button
                  data-testid="vm0044-btn-evaluate-additionality"
                  type="button"
                  onClick={handleEvaluateAdditionality}
                  disabled={isEvaluatingAdd || !projectId}
                  className="w-full px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white shadow-sm flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  {isEvaluatingAdd ? <RefreshCw size={14} className="animate-spin" /> : <Award size={14} />}
                  Evaluate VT0008 Additionality
                </button>

                {addResponse && (
                  <div className="space-y-2 pt-2 border-t border-[var(--color-border)] text-xs">
                    <div className="flex items-center justify-between p-2 rounded bg-[var(--color-background)]">
                      <span>Step 1: Regulatory Surplus</span>
                      <span className={addResponse.step1_regulatory_surplus ? "text-emerald-400 font-bold" : "text-red-400 font-bold"}>
                        {addResponse.step1_regulatory_surplus ? "PASS" : "FAIL"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded bg-[var(--color-background)]">
                      <span>Step 2: Positive List (Section 4)</span>
                      <span className={addResponse.step2_positive_list ? "text-emerald-400 font-bold" : "text-red-400 font-bold"}>
                        {addResponse.step2_positive_list ? "PASS" : "FAIL"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded bg-[var(--color-background)]">
                      <span>Step 3: Investment Analysis (VT0008)</span>
                      <span className={addResponse.step3_investment_analysis ? "text-emerald-400 font-bold" : "text-red-400 font-bold"}>
                        {addResponse.step3_investment_analysis ? "PASS" : "FAIL"}
                      </span>
                    </div>

                    {addResponse.findings.length > 0 && (
                      <div className="p-3 rounded-lg bg-zinc-900 border border-zinc-800 text-xs text-zinc-300 space-y-1">
                        <span className="font-bold text-[var(--color-text-primary)] block">Additionality Audit Findings:</span>
                        {addResponse.findings.map((f, i) => (
                          <div key={i}>• {f}</div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. TAB CONTENT: Normative Governance */}
      {activeTab === "governance" && (
        <div className="space-y-6">
          {/* Dependencies */}
          <div className="p-5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] space-y-3">
            <h3 className="text-sm font-bold text-[var(--color-text-primary)] flex items-center gap-2">
              <ShieldCheck size={16} className="text-blue-400" />
              Normative Standards & CDM Tool Dependencies ({deps.length})
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {deps.map((d) => (
                <div key={d.id} className="p-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-blue-400">{d.dependency_code}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">
                      v{d.active_version}
                    </span>
                  </div>
                  <span className="font-medium text-[var(--color-text-primary)] block">{d.title}</span>
                  <span className="text-[10px] text-[var(--color-text-secondary)] block">{d.normative_role}</span>
                </div>
              ))}
            </div>
          </div>

          {/* 21 Normative Rules */}
          <div className="p-5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] space-y-3">
            <h3 className="text-sm font-bold text-[var(--color-text-primary)] flex items-center gap-2">
              <FileCheck2 size={16} className="text-emerald-400" />
              VM0044 v1.2 Methodological Rules ({rules.length})
            </h3>
            <div className="space-y-2">
              {rules.map((r) => (
                <div key={r.id} className="p-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-emerald-400">{r.rule_id}</span>
                      <span className="text-[10px] font-mono text-[var(--color-text-secondary)]">Section {r.section}</span>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      {r.requirement_type}
                    </span>
                  </div>
                  <span className="font-semibold text-[var(--color-text-primary)] block">{r.title}</span>
                  <p className="text-[11px] text-[var(--color-text-secondary)]">{r.summary}</p>
                  <div className="pt-1 text-[10px] text-amber-400 font-mono">
                    Fail-closed condition: {r.fail_closed_condition}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 5. TAB CONTENT: Calculation History */}
      {activeTab === "executions" && (
        <div className="p-5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] space-y-3">
          <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
            <h3 className="text-sm font-bold text-[var(--color-text-primary)] flex items-center gap-2">
              <Hash size={16} className="text-purple-400" />
              Persisted VM0044 Calculations ({executions.length})
            </h3>
            <button
              onClick={() => loadMetadata()}
              className="text-xs text-[var(--color-text-secondary)] hover:text-white flex items-center gap-1 cursor-pointer"
            >
              <RefreshCw size={12} />
              Refresh
            </button>
          </div>

          {executions.length > 0 ? (
            <div className="space-y-2">
              {executions.map((x) => (
                <div key={x.id} className="p-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-xs flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-[var(--color-text-primary)]">
                        {x.technology_class}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400">
                        {x.status}
                      </span>
                    </div>
                    <span className="text-[10px] text-[var(--color-text-secondary)] font-mono block mt-1">
                      Hash: {x.calculation_hash}
                    </span>
                  </div>

                  <div className="text-right">
                    <span className="text-base font-mono font-bold text-emerald-400 block">
                      {Number(x.net_removal_tco2e).toFixed(4)} tCO2e
                    </span>
                    <span className="text-[10px] text-[var(--color-text-secondary)]">
                      {new Date(x.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-[var(--color-text-secondary)] py-4 text-center">
              No authoritative VM0044 calculations recorded for this project yet.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
