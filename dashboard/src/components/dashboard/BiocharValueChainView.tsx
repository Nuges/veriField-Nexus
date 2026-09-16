"use client";

import React, { useState, useEffect } from "react";
import {
  Layers,
  Scale,
  GitCommit,
  TreeDeciduous,
  Activity,
  Award,
  ShieldCheck,
  AlertCircle,
  AlertTriangle,
  FileText,
  Calculator,
  Hash,
  RefreshCw,
} from "lucide-react";
import {
  fetchBiocharBatches,
  fetchBiocharSummary,
  fetchBiocharMassBalance,
  fetchBiocharLineage,
  fetchFeedstockLots,
  fetchProductionRuns,
  fetchProductionFacilities,
  fetchPuroRules,
  fetchPuroDependencies,
  fetchPuroEndUseCategories,
  fetchPuroSupplierProfile,
  fetchPuroFacilityProfile,
  fetchPuroCreditingPeriods,
  executePuroQuantification,
  simulatePuroQuantification,
  fetchPuroAudits,
  fetchPuroOutputReports,
  fetchPuroRegistryReadiness,
  type BiocharBatchRecord,
  type BiocharSummary,
  type BiocharMassBalance,
  type BiocharChainOfCustody,
  type FeedstockLotRecord,
  type ProductionRunRecord,
  type ProductionFacilityRecord,
  type PuroRuleDefinitionRecord,
  type PuroNormativeDependencyRecord,
  type PuroEndUseCategoryRecord,
  type PuroSupplierProfileRecord,
  type PuroFacilityProfileRecord,
  type PuroCreditingPeriodRecord,
  type PuroQuantificationBreakdown,
  type PuroAuditWorkflowRecord,
  type PuroOutputReportRecord,
  type PuroRegistryReadiness,
} from "@/lib/api";

export default function BiocharValueChainView({ projectId }: { projectId?: string }) {
  const [activeSection, setActiveSection] = useState<
    "batches" | "feedstock" | "runs" | "mass_balance" | "custody" | "puro"
  >("batches");
  const [batches, setBatches] = useState<BiocharBatchRecord[]>([]);
  const [lots, setLots] = useState<FeedstockLotRecord[]>([]);
  const [runs, setRuns] = useState<ProductionRunRecord[]>([]);
  const [facilities, setFacilities] = useState<ProductionFacilityRecord[]>([]);
  const [summary, setSummary] = useState<BiocharSummary | null>(null);
  const [selectedBatch, setSelectedBatch] = useState<BiocharBatchRecord | null>(null);
  const [massBalance, setMassBalance] = useState<BiocharMassBalance | null>(null);
  const [lineage, setLineage] = useState<BiocharChainOfCustody | null>(null);
  const [loading, setLoading] = useState(true);

  // Puro 2025 V2 State
  const [puroRules, setPuroRules] = useState<PuroRuleDefinitionRecord[]>([]);
  const [puroDeps, setPuroDeps] = useState<PuroNormativeDependencyRecord[]>([]);
  const [puroCategories, setPuroCategories] = useState<PuroEndUseCategoryRecord[]>([]);
  const [supplierProfile, setSupplierProfile] = useState<PuroSupplierProfileRecord | null>(null);
  const [facilityProfile, setFacilityProfile] = useState<PuroFacilityProfileRecord | null>(null);
  const [creditingPeriods, setCreditingPeriods] = useState<PuroCreditingPeriodRecord[]>([]);
  const [audits, setAudits] = useState<PuroAuditWorkflowRecord[]>([]);
  const [outputReports, setOutputReports] = useState<PuroOutputReportRecord[]>([]);
  const [readiness, setReadiness] = useState<PuroRegistryReadiness | null>(null);

  // Quantification parameters state
  const [quantMode, setQuantMode] = useState<"authoritative" | "simulation">("authoritative");
  const [quantBatchId, setQuantBatchId] = useState<string>("");
  const [soilTemp, setSoilTemp] = useState<number>(15.0);
  const [impurityPct, setImpurityPct] = useState<number>(0.0);
  const [feedstockFrac, setFeedstockFrac] = useState<number>(1.0);
  const [eTransport, setETransport] = useState<number>(0.0);
  const [eProcessing, setEProcessing] = useState<number>(0.0);
  const [eApplication, setEApplication] = useState<number>(0.0);
  const [eLeakage, setELeakage] = useState<number>(0.0);

  // Simulation mode specific states
  const [simDryMass, setSimDryMass] = useState<number>(100.0);
  const [simCOrg, setSimCOrg] = useState<number>(80.0);
  const [simMolarHC, setSimMolarHC] = useState<number>(0.35);
  const [simEndUseCat, setSimEndUseCat] = useState<string>("AF1");
  const [simEBiomass, setSimEBiomass] = useState<number>(2.5);
  const [simEProduction, setSimEProduction] = useState<number>(1.0);
  const [simEUse, setSimEUse] = useState<number>(0.5);
  const [simEInfra, setSimEInfra] = useState<number>(5.0);
  const [simEDluc, setSimEDluc] = useState<number>(0.0);

  const [quantResult, setQuantResult] = useState<PuroQuantificationBreakdown | null>(null);
  const [quantLoading, setQuantLoading] = useState<boolean>(false);
  const [quantError, setQuantError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [batchesRes, lotsRes, runsRes, summaryRes, facilitiesRes] = await Promise.all([
          fetchBiocharBatches(projectId),
          fetchFeedstockLots(projectId),
          fetchProductionRuns(projectId),
          fetchBiocharSummary(projectId),
          fetchProductionFacilities(projectId),
        ]);
        setBatches(batchesRes || []);
        setLots(lotsRes || []);
        setRuns(runsRes || []);
        setFacilities(facilitiesRes || []);
        setSummary(summaryRes || null);
        if (batchesRes && batchesRes.length > 0) {
          setSelectedBatch(batchesRes[0]);
          setQuantBatchId(batchesRes[0].id);
        }

        // Load Puro metadata
        try {
          const [rulesRes, depsRes, catsRes] = await Promise.all([
            fetchPuroRules(),
            fetchPuroDependencies(),
            fetchPuroEndUseCategories(),
          ]);
          setPuroRules(rulesRes || []);
          setPuroDeps(depsRes || []);
          setPuroCategories(catsRes || []);
        } catch (puroErr) {
          console.warn("Puro metadata fetch warning:", puroErr);
        }

        // Load project-specific Puro status
        if (projectId) {
          try {
            const [readinessRes, supplierRes] = await Promise.all([
              fetchPuroRegistryReadiness(projectId),
              fetchPuroSupplierProfile(projectId),
            ]);
            setReadiness(readinessRes || null);
            setSupplierProfile(supplierRes || null);
          } catch (projPuroErr) {
            console.warn("Puro project readiness warning:", projPuroErr);
          }
        }

        // Load facility-specific Puro profiles
        if (facilitiesRes && facilitiesRes.length > 0) {
          const targetFacId = facilitiesRes[0].id;
          try {
            const [facProfRes, periodsRes, auditsRes, reportsRes] = await Promise.all([
              fetchPuroFacilityProfile(targetFacId),
              fetchPuroCreditingPeriods(targetFacId),
              fetchPuroAudits(targetFacId),
              fetchPuroOutputReports(targetFacId),
            ]);
            setFacilityProfile(facProfRes || null);
            setCreditingPeriods(periodsRes || []);
            setAudits(auditsRes || []);
            setOutputReports(reportsRes || []);
          } catch (facPuroErr) {
            console.warn("Puro facility profile warning:", facPuroErr);
          }
        }
      } catch (err) {
        console.error("Failed to load biochar data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [projectId]);

  useEffect(() => {
    async function loadBatchDetails() {
      if (!selectedBatch) return;
      try {
        const [mb, co] = await Promise.all([
          fetchBiocharMassBalance(selectedBatch.id),
          fetchBiocharLineage(selectedBatch.id),
        ]);
        setMassBalance(mb);
        setLineage(co);
      } catch (err) {
        console.error("Failed to load batch details:", err);
      }
    }
    loadBatchDetails();
  }, [selectedBatch]);

  async function handleQuantify() {
    const targetBatchId = quantBatchId || selectedBatch?.id;
    setQuantLoading(true);
    setQuantError(null);
    try {
      let res: PuroQuantificationBreakdown;
      if (quantMode === "authoritative") {
        if (!targetBatchId) {
          setQuantError("Please select a valid biochar batch for authoritative quantification.");
          setQuantLoading(false);
          return;
        }
        res = await executePuroQuantification(targetBatchId);
      } else {
        res = await simulatePuroQuantification({
          batch_id: targetBatchId,
          dry_mass_tonnes: Number(simDryMass),
          c_org_pct: Number(simCOrg),
          molar_h_c: Number(simMolarHC),
          soil_temperature_celsius: Number(soilTemp),
          end_use_category_code: simEndUseCat,
          e_biomass: Number(simEBiomass),
          e_production: Number(simEProduction),
          e_use: Number(simEUse),
          e_infra: Number(simEInfra),
          e_dluc: Number(simEDluc),
          is_leakage_mitigated: true,
          ecological_leakage_tco2e: 0.0,
          market_activity_shifting_tco2e: Number(eLeakage),
        }, targetBatchId);
      }
      setQuantResult(res);

      if (projectId) {
        const r = await fetchPuroRegistryReadiness(projectId);
        setReadiness(r);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : (err && typeof err === "object" && "message" in err ? String((err as { message: unknown }).message) : "Failed to execute Puro quantification.");
      setQuantError(msg);
    } finally {
      setQuantLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="p-8 text-center text-xs text-[var(--color-text-secondary)]">
        Loading authoritative Biochar Value-Chain data...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Sub-navigation */}
      <div className="flex items-center gap-2 border-b border-[var(--color-border)] pb-2 overflow-x-auto">
        <button
          onClick={() => setActiveSection("batches")}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
            activeSection === "batches"
              ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/30"
              : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
          }`}
        >
          <Layers size={14} />
          <span>Biochar Batches & Lab</span>
        </button>
        <button
          onClick={() => setActiveSection("feedstock")}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
            activeSection === "feedstock"
              ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/30"
              : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
          }`}
        >
          <TreeDeciduous size={14} />
          <span>Feedstock Lots</span>
        </button>
        <button
          onClick={() => setActiveSection("runs")}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
            activeSection === "runs"
              ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/30"
              : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
          }`}
        >
          <Activity size={14} />
          <span>Production Runs</span>
        </button>
        <button
          onClick={() => setActiveSection("mass_balance")}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
            activeSection === "mass_balance"
              ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/30"
              : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
          }`}
        >
          <Scale size={14} />
          <span>Mass Balance Ledger</span>
        </button>
        <button
          onClick={() => setActiveSection("custody")}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
            activeSection === "custody"
              ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/30"
              : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
          }`}
        >
          <GitCommit size={14} />
          <span>Chain of Custody Trace</span>
        </button>
        <button
          onClick={() => setActiveSection("puro")}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
            activeSection === "puro"
              ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/30"
              : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
          }`}
        >
          <Award size={14} />
          <span>Puro 2025 V2</span>
        </button>
      </div>

      {/* Batches Table & Selection */}
      {activeSection === "batches" && (
        <div className="space-y-4">
          <div className="rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 shadow-xs">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-[var(--color-border)]">
              <div>
                <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">
                  Registered biochar batches & laboratory evidence
                </h4>
                <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                  Physical kiln output reconciled with ASTM/EBC/Puro compliant lab reports.
                </p>
              </div>
              <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-[var(--color-primary)]/10 text-[var(--color-primary)] border border-[var(--color-primary)]/20">
                {batches.length} {batches.length === 1 ? "batch registered" : "batches registered"}
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left font-sans text-xs">
                <thead>
                  <tr className="border-b border-[var(--color-border)] text-[10px] font-black text-[var(--color-text-secondary)] uppercase tracking-wider">
                    <th className="py-2.5 px-3">BATCH NUMBER</th>
                    <th className="py-2.5 px-3">FACILITY / KILN</th>
                    <th className="py-2.5 px-3">YIELD (TONNES)</th>
                    <th className="py-2.5 px-3">MOLAR H/C RATIO</th>
                    <th className="py-2.5 px-3">FIXED CARBON %</th>
                    <th className="py-2.5 px-3">QUALITY GRADE</th>
                    <th className="py-2.5 px-3">STATUS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border)]">
                  {batches.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-6 text-center text-xs text-[var(--color-text-secondary)]">
                        No biochar batches registered for this project.
                      </td>
                    </tr>
                  ) : (
                    batches.map((b) => {
                      const isSelected = selectedBatch?.id === b.id;
                      return (
                        <tr
                          key={b.id}
                          onClick={() => setSelectedBatch(b)}
                          className={`hover:bg-[var(--color-surface-hover)] cursor-pointer transition-colors ${
                            isSelected ? "bg-emerald-500/5" : ""
                          }`}
                        >
                          <td className="py-3 px-3 font-mono font-bold text-emerald-500">
                            {b.batch_number}
                          </td>
                          <td className="py-3 px-3 text-[var(--color-text-primary)]">
                            {b.facility_name} ({b.kiln_id})
                          </td>
                          <td className="py-3 px-3 font-mono font-bold text-[var(--color-text-primary)]">
                            {Number(b.biochar_yield_tonnes).toFixed(2)} t
                          </td>
                          <td className="py-3 px-3 font-mono text-[var(--color-text-primary)]">
                            {b.molar_h_c_ratio !== undefined ? Number(b.molar_h_c_ratio).toFixed(3) : "—"}
                          </td>
                          <td className="py-3 px-3 font-mono text-[var(--color-text-primary)]">
                            {b.fixed_carbon_pct !== undefined ? `${Number(b.fixed_carbon_pct).toFixed(1)}%` : "—"}
                          </td>
                          <td className="py-3 px-3">
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                                b.quality_grade === "GRADE_A"
                                  ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                                  : b.quality_grade === "GRADE_B"
                                  ? "bg-blue-500/10 text-blue-500 border border-blue-500/20"
                                  : "bg-rose-500/10 text-rose-500 border border-rose-500/20"
                              }`}
                            >
                              {b.quality_grade || "UNGRADED"}
                            </span>
                          </td>
                          <td className="py-3 px-3">
                            <span
                              className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                                b.status === "PRODUCED" || b.status === "ACTIVE"
                                  ? "bg-blue-500/10 text-blue-400"
                                  : b.status === "CLOSED"
                                  ? "bg-zinc-500/10 text-zinc-400"
                                  : "bg-amber-500/10 text-amber-400"
                              }`}
                            >
                              {b.status || "PRODUCED"}
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Feedstock Lots View */}
      {activeSection === "feedstock" && (
        <div className="rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-[var(--color-border)]">
            <div>
              <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">
                Feedstock lots & residue sourcing
              </h4>
              <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                Biomass reception ledger with dry mass derivation (ASTM D4442 standard).
              </p>
            </div>
            <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-[var(--color-primary)]/10 text-[var(--color-primary)] border border-[var(--color-primary)]/20">
              {lots.length} {lots.length === 1 ? "lot tracked" : "lots tracked"}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-sans text-xs">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-[10px] font-black text-[var(--color-text-secondary)] uppercase tracking-wider">
                  <th className="py-2.5 px-3">LOT NUMBER</th>
                  <th className="py-2.5 px-3">FEEDSTOCK TYPE</th>
                  <th className="py-2.5 px-3">WET RECEIVED</th>
                  <th className="py-2.5 px-3">MOISTURE %</th>
                  <th className="py-2.5 px-3">DRY MASS (ASTM D4442)</th>
                  <th className="py-2.5 px-3">ALLOCATED</th>
                  <th className="py-2.5 px-3">AVAILABLE</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)]">
                {lots.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-6 text-center text-xs text-[var(--color-text-secondary)]">
                      No feedstock lots registered.
                    </td>
                  </tr>
                ) : (
                  lots.map((l) => (
                    <tr key={l.id} className="hover:bg-[var(--color-surface-hover)]">
                      <td className="py-3 px-3 font-mono font-bold text-[var(--color-text-primary)]">
                        {l.lot_number}
                      </td>
                      <td className="py-3 px-3 text-[var(--color-text-primary)]">{l.feedstock_type}</td>
                      <td className="py-3 px-3 font-mono text-[var(--color-text-primary)]">
                        {Number(l.mass_received_tonnes).toFixed(2)} t
                      </td>
                      <td className="py-3 px-3 font-mono text-[var(--color-text-primary)]">
                        {Number(l.moisture_content_pct).toFixed(1)}%
                      </td>
                      <td className="py-3 px-3 font-mono font-bold text-emerald-500">
                        {Number(l.dry_mass_tonnes).toFixed(2)} t
                      </td>
                      <td className="py-3 px-3 font-mono text-[var(--color-text-secondary)]">
                        {Number(l.allocated_mass_tonnes || 0).toFixed(2)} t
                      </td>
                      <td className="py-3 px-3 font-mono font-bold text-blue-400">
                        {Number(l.available_mass_tonnes || 0).toFixed(2)} t
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Production Runs View */}
      {activeSection === "runs" && (
        <div className="rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-[var(--color-border)]">
            <div>
              <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">
                Production runs & pyrolysis telemetry
              </h4>
              <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                Reactor operational cycles and verified biomass thermal conversion telemetry.
              </p>
            </div>
            <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-[var(--color-primary)]/10 text-[var(--color-primary)] border border-[var(--color-primary)]/20">
              {runs.length} {runs.length === 1 ? "run recorded" : "runs recorded"}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-sans text-xs">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-[10px] font-black text-[var(--color-text-secondary)] uppercase tracking-wider">
                  <th className="py-2.5 px-3">RUN NUMBER</th>
                  <th className="py-2.5 px-3">FEEDSTOCK INPUT</th>
                  <th className="py-2.5 px-3">DRY INPUT</th>
                  <th className="py-2.5 px-3">AVG TEMP (°C)</th>
                  <th className="py-2.5 px-3">RESIDENCE TIME</th>
                  <th className="py-2.5 px-3">BIOCHAR OUTPUT</th>
                  <th className="py-2.5 px-3">QA STATUS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)]">
                {runs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-6 text-center text-xs text-[var(--color-text-secondary)]">
                      No production runs logged.
                    </td>
                  </tr>
                ) : (
                  runs.map((r) => (
                    <tr key={r.id} className="hover:bg-[var(--color-surface-hover)]">
                      <td className="py-3 px-3 font-mono font-bold text-[var(--color-text-primary)]">
                        {r.run_number}
                      </td>
                      <td className="py-3 px-3 font-mono text-[var(--color-text-primary)]">
                        {Number(r.total_feedstock_input_tonnes).toFixed(2)} t
                      </td>
                      <td className="py-3 px-3 font-mono text-[var(--color-text-primary)]">
                        {Number(r.total_feedstock_dry_tonnes).toFixed(2)} t
                      </td>
                      <td className="py-3 px-3 font-mono text-[var(--color-text-primary)]">
                        {Number(r.avg_pyrolysis_temp_celsius).toFixed(0)} °C
                      </td>
                      <td className="py-3 px-3 font-mono text-[var(--color-text-primary)]">
                        {Number(r.residence_time_minutes).toFixed(0)} min
                      </td>
                      <td className="py-3 px-3 font-mono font-bold text-emerald-500">
                        {Number(r.output_biochar_mass_tonnes).toFixed(2)} t
                      </td>
                      <td className="py-3 px-3">
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-500">
                          {r.qa_status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Mass Balance Ledger View */}
      {activeSection === "mass_balance" && (
        <div className="rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-[var(--color-border)]">
            <div>
              <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">
                Material balance & mass conservation ledger
              </h4>
              <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                Deterministic reconciliation: Original Produced = Current Inventory + Terminal End Use + Losses.
              </p>
            </div>
            {massBalance && (
              <span
                className={`text-[10px] font-bold px-2.5 py-1 rounded-full border ${
                  massBalance.is_valid
                    ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/30"
                    : "bg-rose-500/10 text-rose-500 border-rose-500/30"
                }`}
              >
                {massBalance.status}
              </span>
            )}
          </div>

          {massBalance ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-[var(--color-surface-hover)] border border-[var(--color-border)]">
                <p className="text-xs font-medium text-[var(--color-text-secondary)]">Original produced</p>
                <p className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight mt-1">
                  {massBalance.original_produced_mass_tonnes.toFixed(3)} t
                </p>
              </div>
              <div className="p-4 rounded-xl bg-[var(--color-surface-hover)] border border-[var(--color-border)]">
                <p className="text-xs font-medium text-[var(--color-text-secondary)]">Current inventory</p>
                <p className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight mt-1">
                  {massBalance.current_inventory_tonnes.toFixed(3)} t
                </p>
              </div>
              <div className="p-4 rounded-xl bg-[var(--color-surface-hover)] border border-[var(--color-border)]">
                <p className="text-xs font-medium text-[var(--color-text-secondary)]">Terminal end use</p>
                <p className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight mt-1">
                  {massBalance.terminal_end_use_tonnes.toFixed(3)} t
                </p>
              </div>
              <div className="p-4 rounded-xl bg-[var(--color-surface-hover)] border border-[var(--color-border)]">
                <p className="text-xs font-medium text-[var(--color-text-secondary)]">Documented losses</p>
                <p className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight mt-1">
                  {massBalance.documented_losses_tonnes.toFixed(3)} t
                </p>
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-[var(--color-text-secondary)]">
              Select a batch above to inspect its authoritative mass balance reconciliation.
            </div>
          )}
        </div>
      )}

      {/* Chain of Custody View */}
      {activeSection === "custody" && (
        <div className="rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-[var(--color-border)]">
            <div>
              <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">
                Chain of custody & traceability graph
              </h4>
              <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                Upstream to downstream provenance ordered lineage with cryptographic evidence hashes.
              </p>
            </div>
            {lineage && (
              <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-[var(--color-primary)]/10 text-[var(--color-primary)] border border-[var(--color-primary)]/20">
                {lineage.nodes.length} {lineage.nodes.length === 1 ? "lineage node" : "lineage nodes"}
              </span>
            )}
          </div>

          {lineage && lineage.nodes.length > 0 ? (
            <div className="space-y-3">
              {lineage.nodes.map((node, idx) => (
                <div
                  key={node.node_id || idx}
                  className="flex items-start gap-4 p-3 rounded-xl bg-[var(--color-surface-hover)] border border-[var(--color-border)]"
                >
                  <div className="flex flex-col items-center">
                    <span className="w-6 h-6 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/30 flex items-center justify-center text-[10px] font-mono font-bold">
                      {idx + 1}
                    </span>
                    {idx < lineage.nodes.length - 1 && (
                      <div className="w-0.5 h-6 bg-[var(--color-border)] mt-1" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-[var(--color-text-primary)]">
                        {node.title}
                      </span>
                      <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)]">
                        {node.node_type}
                      </span>
                    </div>
                    {node.hash && (
                      <p className="text-[10px] font-mono text-[var(--color-text-secondary)] mt-1 truncate">
                        SHA-256: {node.hash}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-[var(--color-text-secondary)]">
              Select a batch to review its full chain-of-custody trace.
            </div>
          )}
        </div>
      )}

      {/* ─── Puro.earth Biochar Edition 2025 V2 Methodology View ──────────────── */}
      {activeSection === "puro" && (
        <div className="space-y-6">
          {/* Header Banner */}
          <div className="rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 shadow-xs">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[var(--color-border)]">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                    Puro.earth Biochar Edition 2025 V2
                  </span>
                  <span className="text-[11px] font-mono text-[var(--color-text-secondary)]">
                    Approved 27 Nov 2025
                  </span>
                </div>
                <h3 className="text-base font-bold text-[var(--color-text-primary)]">
                  Normative Methodology Alignment & CORC Verification
                </h3>
                <p className="text-xs text-[var(--color-text-secondary)] max-w-3xl">
                  Full implementation across all 11 methodology chapters: exclusive supplier rights,
                  stationary/mobile facility classification, 10-year crediting periods, Table 3.2 End-Use Point of
                  Creation, deterministic CORC / CORC200+ quantification, and audit verification dossier.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                <div className="p-3 rounded-xl bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-left min-w-[140px]">
                  <p className="text-[10px] uppercase font-bold text-[var(--color-text-secondary)]">Registry Status</p>
                  <p className="text-xs font-mono font-bold text-slate-400 mt-0.5">NOT ISSUED</p>
                  <p className="text-[9px] text-[var(--color-text-secondary)]">Requires accredited Auditor audit</p>
                </div>
                <div className="p-3 rounded-xl bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-left min-w-[140px]">
                  <p className="text-[10px] uppercase font-bold text-[var(--color-text-secondary)]">Readiness Gate</p>
                  <p
                    className={`text-xs font-mono font-bold mt-0.5 ${
                      readiness?.readiness_state === "READY_FOR_AUDIT"
                        ? "text-emerald-500"
                        : "text-amber-500"
                    }`}
                  >
                    {readiness?.readiness_state || "READY_FOR_AUDIT"}
                  </p>
                  <p className="text-[9px] text-[var(--color-text-secondary)]">
                    {readiness?.active_blockers?.length || 0} active blockers
                  </p>
                </div>
              </div>
            </div>

            {/* Core Methodology Invariants Summary */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
              <div className="p-3 rounded-lg bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-xs">
                <span className="font-bold text-[var(--color-text-primary)] block">Crediting Period</span>
                <span className="text-[var(--color-text-secondary)] text-[11px]">
                  10 years initial duration. Max 2 renewals (30 years total cap).
                </span>
              </div>
              <div className="p-3 rounded-lg bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-xs">
                <span className="font-bold text-[var(--color-text-primary)] block">Methodology Persistence</span>
                <span className="text-[var(--color-text-secondary)] text-[11px]">
                  Rule 3.5.1: Molar H/Corg strictly &lt; 0.70. Durability model: 200 years (CORC200+) per Table 6.1.
                </span>
              </div>
              <div className="p-3 rounded-lg bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-xs">
                <span className="font-bold text-[var(--color-text-primary)] block">Table 3.2 End-Use</span>
                <span className="text-[var(--color-text-secondary)] text-[11px]">
                  Point of Creation reached only upon verified delivery, GPS & attestation.
                </span>
              </div>
              <div className="p-3 rounded-lg bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-xs">
                <span className="font-bold text-[var(--color-text-primary)] block">Uncertainty Reporting</span>
                <span className="text-[var(--color-text-secondary)] text-[11px]">
                  ISO GUM propagation (Chapter 10) certified confidence interval (CORCs ± U%).
                </span>
              </div>
            </div>
          </div>

          {/* Section: Deterministic Quantification Console */}
          <div className="rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 shadow-xs">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 pb-3 border-b border-[var(--color-border)] gap-2">
              <div>
                <h4 className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
                  <Calculator size={16} className="text-emerald-500" />
                  Deterministic CORC Quantification Console
                </h4>
                <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                  Formula (Section 6.1): CORCs = max(0, C_stored − C_baseline − C_loss − E_project − E_leakage).
                </p>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex p-0.5 rounded-lg bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-xs">
                  <button
                    onClick={() => setQuantMode("authoritative")}
                    className={`px-2.5 py-1 rounded-md font-medium transition-colors cursor-pointer ${
                      quantMode === "authoritative"
                        ? "bg-emerald-600 text-white shadow-xs"
                        : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                    }`}
                  >
                    Authoritative Mode
                  </button>
                  <button
                    onClick={() => setQuantMode("simulation")}
                    className={`px-2.5 py-1 rounded-md font-medium transition-colors cursor-pointer ${
                      quantMode === "simulation"
                        ? "bg-amber-600 text-white shadow-xs"
                        : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                    }`}
                  >
                    Scenario Simulation
                  </button>
                </div>
                <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-emerald-500">
                  Engine v2.0.0
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Quantification Controls */}
              <div className="space-y-4 lg:col-span-1 border-r border-[var(--color-border)] pr-0 lg:pr-6">
                {quantMode === "authoritative" ? (
                  /* Authoritative Mode Controls */
                  <div className="space-y-3">
                    <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-400">
                      <p className="font-semibold flex items-center gap-1.5">
                        <ShieldCheck size={14} /> Authoritative Mode
                      </p>
                      <p className="text-[11px] text-[var(--color-text-secondary)] mt-1">
                        Executes deterministic quantification from certified laboratory assays, facility baseline LCA models, and verified delivery receipts. Produces immutable audit ledger entries.
                      </p>
                    </div>

                    <div>
                      <label className="text-[11px] font-bold text-[var(--color-text-secondary)] uppercase block mb-1">
                        Select Verified Batch
                      </label>
                      <select
                        value={quantBatchId}
                        onChange={(e) => {
                          setQuantBatchId(e.target.value);
                          const matched = batches.find((b) => b.id === e.target.value);
                          if (matched) setSelectedBatch(matched);
                        }}
                        className="w-full text-xs p-2 rounded-lg bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono"
                      >
                        {batches.length === 0 ? (
                          <option value="">No batches registered</option>
                        ) : (
                          batches.map((b) => (
                            <option key={b.id} value={b.id}>
                              {b.batch_number} — {Number(b.biochar_yield_tonnes).toFixed(1)}t (H/C:{" "}
                              {b.molar_h_c_ratio ?? "—"})
                            </option>
                          ))
                        )}
                      </select>
                    </div>

                    {selectedBatch && (
                      <div className="p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-2 text-xs">
                        <div className="flex justify-between items-center">
                          <span className="text-[var(--color-text-secondary)]">Dry Mass:</span>
                          <span className="font-mono font-bold text-[var(--color-text-primary)]">
                            {Number(selectedBatch.biochar_yield_tonnes).toFixed(2)} t
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-[var(--color-text-secondary)]">Molar H/C_org:</span>
                          <div className="flex items-center gap-1.5">
                            <span className="font-mono font-bold text-[var(--color-text-primary)]">
                              {selectedBatch.molar_h_c_ratio ?? "—"}
                            </span>
                            {selectedBatch.molar_h_c_ratio !== undefined && (
                              <span
                                className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                                  Number(selectedBatch.molar_h_c_ratio) < 0.70
                                    ? "bg-emerald-500/10 text-emerald-500"
                                    : "bg-rose-500/10 text-rose-500"
                                }`}
                              >
                                {Number(selectedBatch.molar_h_c_ratio) < 0.70 ? "PASS <0.70" : "FAIL >=0.70"}
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-[var(--color-text-secondary)]">Soil Temp Provenance:</span>
                          <span className="font-mono text-[10px] text-[var(--color-text-secondary)]">
                            Lembrechts et al. (2022) 5–15cm
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-[var(--color-text-secondary)]">LCA Allocation:</span>
                          <span className="font-mono text-[10px] text-emerald-500">
                            Lower Heating Value (LHV)
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  /* Scenario Simulation Controls */
                  <div className="space-y-3">
                    <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-500">
                      <p className="font-semibold flex items-center gap-1.5">
                        <AlertTriangle size={14} /> Scenario Simulation Mode
                      </p>
                      <p className="text-[11px] text-[var(--color-text-secondary)] mt-1">
                        Parameters are user-configured for what-if scenario exploration. Results are computed in-memory and will NOT create authoritative registry records.
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] font-bold text-[var(--color-text-secondary)] uppercase block mb-1">
                          Dry Mass (t)
                        </label>
                        <input
                          type="number"
                          step="1.0"
                          value={simDryMass}
                          onChange={(e) => setSimDryMass(parseFloat(e.target.value) || 0)}
                          className="w-full text-xs p-1.5 rounded bg-[var(--color-surface-hover)] border border-[var(--color-border)] font-mono"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-[var(--color-text-secondary)] uppercase block mb-1">
                          C_org (%)
                        </label>
                        <input
                          type="number"
                          step="0.5"
                          value={simCOrg}
                          onChange={(e) => setSimCOrg(parseFloat(e.target.value) || 0)}
                          className="w-full text-xs p-1.5 rounded bg-[var(--color-surface-hover)] border border-[var(--color-border)] font-mono"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] font-bold text-[var(--color-text-secondary)] uppercase block mb-1">
                          Molar H/C_org
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          value={simMolarHC}
                          onChange={(e) => setSimMolarHC(parseFloat(e.target.value) || 0)}
                          className="w-full text-xs p-1.5 rounded bg-[var(--color-surface-hover)] border border-[var(--color-border)] font-mono"
                        />
                        <span
                          className={`text-[9px] font-bold ${
                            simMolarHC < 0.70 ? "text-emerald-500" : "text-rose-500"
                          }`}
                        >
                          {simMolarHC < 0.70 ? "Eligible (<0.70)" : "Ineligible (>=0.70)"}
                        </span>
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-[var(--color-text-secondary)] uppercase block mb-1">
                          Soil Temp (°C)
                        </label>
                        <input
                          type="number"
                          step="0.5"
                          value={soilTemp}
                          onChange={(e) => setSoilTemp(parseFloat(e.target.value) || 0)}
                          className="w-full text-xs p-1.5 rounded bg-[var(--color-surface-hover)] border border-[var(--color-border)] font-mono"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="text-[10px] font-bold text-[var(--color-text-secondary)] uppercase block mb-1">
                        End-Use Category (Table 3.2)
                      </label>
                      <select
                        value={simEndUseCat}
                        onChange={(e) => setSimEndUseCat(e.target.value)}
                        className="w-full text-xs p-1.5 rounded bg-[var(--color-surface-hover)] border border-[var(--color-border)] font-mono"
                      >
                        {puroCategories.map((c) => (
                          <option key={c.category_code} value={c.category_code}>
                            {c.category_code} — {c.category_name} ({c.is_corc_eligible ? "Eligible" : "Ineligible"})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="border-t border-[var(--color-border)] pt-2 space-y-2">
                      <p className="text-[10px] uppercase font-bold text-[var(--color-text-secondary)]">
                        LCA Project Emissions (tCO₂e)
                      </p>
                      <div className="grid grid-cols-3 gap-1.5">
                        <div>
                          <span className="text-[9px] text-[var(--color-text-secondary)]">E_biomass</span>
                          <input
                            type="number"
                            step="0.1"
                            value={simEBiomass}
                            onChange={(e) => setSimEBiomass(parseFloat(e.target.value) || 0)}
                            className="w-full text-xs p-1 rounded bg-[var(--color-surface-hover)] border border-[var(--color-border)] font-mono"
                          />
                        </div>
                        <div>
                          <span className="text-[9px] text-[var(--color-text-secondary)]">E_production</span>
                          <input
                            type="number"
                            step="0.1"
                            value={simEProduction}
                            onChange={(e) => setSimEProduction(parseFloat(e.target.value) || 0)}
                            className="w-full text-xs p-1 rounded bg-[var(--color-surface-hover)] border border-[var(--color-border)] font-mono"
                          />
                        </div>
                        <div>
                          <span className="text-[9px] text-[var(--color-text-secondary)]">E_use</span>
                          <input
                            type="number"
                            step="0.1"
                            value={simEUse}
                            onChange={(e) => setSimEUse(parseFloat(e.target.value) || 0)}
                            className="w-full text-xs p-1 rounded bg-[var(--color-surface-hover)] border border-[var(--color-border)] font-mono"
                          />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-1.5">
                        <div>
                          <span className="text-[9px] text-[var(--color-text-secondary)]">E_infra</span>
                          <input
                            type="number"
                            step="0.1"
                            value={simEInfra}
                            onChange={(e) => setSimEInfra(parseFloat(e.target.value) || 0)}
                            className="w-full text-xs p-1 rounded bg-[var(--color-surface-hover)] border border-[var(--color-border)] font-mono"
                          />
                        </div>
                        <div>
                          <span className="text-[9px] text-[var(--color-text-secondary)]">E_leakage (L_MA)</span>
                          <input
                            type="number"
                            step="0.1"
                            value={eLeakage}
                            onChange={(e) => setELeakage(parseFloat(e.target.value) || 0)}
                            className="w-full text-xs p-1 rounded bg-[var(--color-surface-hover)] border border-[var(--color-border)] font-mono"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {quantError && (
                  <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs flex items-center gap-2">
                    <AlertCircle size={14} className="shrink-0" />
                    <span>{quantError}</span>
                  </div>
                )}

                <button
                  onClick={handleQuantify}
                  disabled={quantLoading || (quantMode === "authoritative" && batches.length === 0)}
                  className={`w-full py-2.5 px-4 rounded-lg text-white text-xs font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shadow-xs ${
                    quantMode === "authoritative"
                      ? "bg-emerald-600 hover:bg-emerald-500"
                      : "bg-amber-600 hover:bg-amber-500"
                  }`}
                >
                  {quantLoading ? (
                    <>
                      <RefreshCw size={14} className="animate-spin" />
                      <span>Executing Deterministic Math...</span>
                    </>
                  ) : (
                    <>
                      <Calculator size={14} />
                      <span>
                        {quantMode === "authoritative"
                          ? "Execute Authoritative Quantification"
                          : "Run Scenario Simulation"}
                      </span>
                    </>
                  )}
                </button>
              </div>

              {/* Quantification Results Display */}
              <div className="lg:col-span-2 space-y-4">
                {quantResult ? (
                  <div className="space-y-4">
                    {/* Mode Notice Banner */}
                    {quantResult.calculation_mode === "SIMULATION" && (
                      <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs flex items-center justify-between">
                        <span className="font-bold flex items-center gap-2">
                          <AlertTriangle size={15} /> SCENARIO SIMULATION RESULT — NOT AN AUTHORITATIVE AUDIT RECORD
                        </span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20">
                          NON-ISSUABLE
                        </span>
                      </div>
                    )}

                    {/* Top Result Banner */}
                    <div className="p-4 rounded-xl bg-[var(--color-surface-hover)] border border-[var(--color-border)] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                      <div>
                        <span className="text-[10px] uppercase font-bold text-[var(--color-text-secondary)]">
                          Net Quantified Carbon Removal (Section 10 Format)
                        </span>
                        <div className="flex items-baseline gap-2 mt-0.5">
                          <span className="text-3xl font-mono font-bold text-emerald-500">
                            {Number(quantResult.final_corcs_issuable).toFixed(3)}
                          </span>
                          <span className="text-xs font-bold text-[var(--color-text-primary)]">
                            tCO₂e (CORCs)
                          </span>
                        </div>
                        <p className="text-xs font-mono text-[var(--color-text-secondary)] mt-1">
                          Certificate Reporting:{" "}
                          <span className="text-[var(--color-text-primary)] font-semibold">
                            {quantResult.reported_uncertainty_text ||
                              `${Number(quantResult.final_corcs_issuable).toFixed(3)} ± ${Number(
                                quantResult.combined_uncertainty_pct
                              ).toFixed(1)}% tCO₂e`}
                          </span>
                        </p>
                      </div>

                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`text-xs font-mono font-bold px-2.5 py-1 rounded-full border ${
                            quantResult.durability_class === "CORC200+"
                              ? "bg-purple-500/10 text-purple-400 border-purple-500/30"
                              : quantResult.durability_class === "CORC"
                              ? "bg-blue-500/10 text-blue-400 border-blue-500/30"
                              : "bg-rose-500/10 text-rose-500 border-rose-500/30"
                          }`}
                        >
                          {quantResult.durability_class}
                        </span>

                        <span
                          className={`text-xs font-mono font-bold px-2.5 py-1 rounded-full border ${
                            quantResult.calculation_status === "SUCCESS"
                              ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/30"
                              : "bg-amber-500/10 text-amber-500 border-amber-500/30"
                          }`}
                        >
                          {quantResult.calculation_status}
                        </span>

                        <span
                          className={`text-xs font-mono font-bold px-2.5 py-1 rounded-full border ${
                            quantResult.calculation_mode === "AUTHORITATIVE"
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                              : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                          }`}
                        >
                          {quantResult.calculation_mode || "AUTHORITATIVE"}
                        </span>
                      </div>
                    </div>

                    {/* Step by Step Breakdown */}
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      <div className="p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)]">
                        <span className="text-[10px] uppercase font-bold text-[var(--color-text-secondary)]">
                          C_stored (Gross)
                        </span>
                        <p className="text-sm font-mono font-bold text-[var(--color-text-primary)] mt-0.5">
                          {Number(quantResult.c_stored_tco2e).toFixed(3)} t
                        </p>
                        <p className="text-[10px] text-[var(--color-text-secondary)] mt-0.5">
                          Dry Mass: {Number(quantResult.eligible_dry_biochar_mass_tonnes).toFixed(2)} t • C_org: {Number(quantResult.organic_carbon_pct).toFixed(1)}%
                        </p>
                      </div>

                      <div className="p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)]">
                        <span className="text-[10px] uppercase font-bold text-[var(--color-text-secondary)]">
                          Table 6.1 Persistence
                        </span>
                        <p className="text-sm font-mono font-bold text-[var(--color-text-primary)] mt-0.5">
                          PF: {(Number(quantResult.persistence_fraction_pf) * 100).toFixed(2)}%
                        </p>
                        <p className="text-[10px] text-[var(--color-text-secondary)] mt-0.5">
                          M={quantResult.regression_m?.toFixed(2) ?? "—"}, a={quantResult.regression_a?.toFixed(2) ?? "—"} (Ts={quantResult.soil_temperature_celsius ?? 15}°C)
                        </p>
                      </div>

                      <div className="p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)]">
                        <span className="text-[10px] uppercase font-bold text-[var(--color-text-secondary)]">
                          Storage Loss & Baseline
                        </span>
                        <p className="text-sm font-mono font-bold text-[var(--color-text-primary)] mt-0.5">
                          {(Number(quantResult.c_baseline_tco2e) + Number(quantResult.c_loss_tco2e)).toFixed(3)} t
                        </p>
                        <p className="text-[10px] text-[var(--color-text-secondary)] mt-0.5">
                          C_loss: {Number(quantResult.c_loss_tco2e).toFixed(3)} t • Baseline: {Number(quantResult.c_baseline_tco2e).toFixed(3)} t
                        </p>
                      </div>

                      <div className="p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)]">
                        <span className="text-[10px] uppercase font-bold text-[var(--color-text-secondary)]">
                          E_project (LCA Total)
                        </span>
                        <p className="text-sm font-mono font-bold text-[var(--color-text-primary)] mt-0.5">
                          {Number(quantResult.e_project_tco2e).toFixed(3)} t
                        </p>
                        <p className="text-[10px] text-[var(--color-text-secondary)] mt-0.5">
                          E_ops: {Number(quantResult.e_ops_total_tco2e ?? 0).toFixed(3)} t • E_emb: {Number(quantResult.e_emb_annualized_tco2e ?? 0).toFixed(3)} t
                        </p>
                      </div>

                      <div className="p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)]">
                        <span className="text-[10px] uppercase font-bold text-[var(--color-text-secondary)]">
                          E_leakage (Chapter 8)
                        </span>
                        <p className="text-sm font-mono font-bold text-[var(--color-text-primary)] mt-0.5">
                          {Number(quantResult.e_leakage_tco2e).toFixed(3)} t
                        </p>
                        <p className="text-[10px] text-[var(--color-text-secondary)] mt-0.5">
                          L_ECO: {Number(quantResult.leakage_eco_tco2e ?? 0).toFixed(2)} t • L_MA: {Number(quantResult.leakage_ma_tco2e ?? quantResult.e_leakage_tco2e).toFixed(2)} t
                        </p>
                      </div>

                      <div className="p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)]">
                        <span className="text-[10px] uppercase font-bold text-[var(--color-text-secondary)]">
                          Uncertainty (Section 10)
                        </span>
                        <p className="text-sm font-mono font-bold text-[var(--color-text-primary)] mt-0.5">
                          ±{Number(quantResult.combined_uncertainty_pct).toFixed(1)}%
                        </p>
                        <p className="text-[10px] text-emerald-400 mt-0.5">
                          Reported on CORC (No deduction)
                        </p>
                      </div>
                    </div>

                    {/* Full LCA & Leakage Detailed Breakdown */}
                    <div className="p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-2 text-xs">
                      <span className="text-[10px] uppercase font-bold text-[var(--color-text-secondary)] block">
                        Chapter 7 LCA & Chapter 8 Leakage Sub-Components
                      </span>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                        <div className="p-2 rounded bg-[var(--color-surface-hover)]">
                          <span className="text-[10px] text-[var(--color-text-secondary)] block">E_biomass (harvest)</span>
                          <span className="font-mono font-semibold">{quantResult.e_ops_biomass_tco2e !== undefined ? Number(quantResult.e_ops_biomass_tco2e).toFixed(3) : "—"} t</span>
                        </div>
                        <div className="p-2 rounded bg-[var(--color-surface-hover)]">
                          <span className="text-[10px] text-[var(--color-text-secondary)] block">E_production (pyrolysis)</span>
                          <span className="font-mono font-semibold">{quantResult.e_ops_production_tco2e !== undefined ? Number(quantResult.e_ops_production_tco2e).toFixed(3) : "—"} t</span>
                        </div>
                        <div className="p-2 rounded bg-[var(--color-surface-hover)]">
                          <span className="text-[10px] text-[var(--color-text-secondary)] block">E_use (transport & appl.)</span>
                          <span className="font-mono font-semibold">{quantResult.e_ops_use_tco2e !== undefined ? Number(quantResult.e_ops_use_tco2e).toFixed(3) : "—"} t</span>
                        </div>
                        <div className="p-2 rounded bg-[var(--color-surface-hover)]">
                          <span className="text-[10px] text-[var(--color-text-secondary)] block">E_emb (infrastructure)</span>
                          <span className="font-mono font-semibold">{quantResult.e_emb_infra_tco2e !== undefined ? Number(quantResult.e_emb_infra_tco2e).toFixed(3) : "0.000"} t</span>
                        </div>
                      </div>
                    </div>

                    {/* Point of Creation & Hash Seals */}
                    <div className="p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1.5 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-[var(--color-text-secondary)]">Point of Creation:</span>
                        <span className="font-mono font-bold text-[var(--color-text-primary)]">
                          {quantResult.corc_point_status}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[var(--color-text-secondary)]">Calculation Hash (SHA-256):</span>
                        <span className="font-mono text-[10px] text-emerald-500 truncate max-w-[280px]">
                          {quantResult.calculation_hash}
                        </span>
                      </div>
                      {quantResult.superseded_at && (
                        <div className="flex items-center justify-between text-amber-500">
                          <span>Status:</span>
                          <span className="font-mono font-bold">SUPERSEDED by Engine v{quantResult.replacement_engine_version}</span>
                        </div>
                      )}
                    </div>

                    {/* Applied Rules Badges */}
                    {quantResult.rule_references && quantResult.rule_references.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-[10px] uppercase font-bold text-[var(--color-text-secondary)]">
                          Applied Edition 2025 V2 Rules
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {quantResult.rule_references.map((r) => (
                            <span
                              key={r}
                              className="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-[var(--color-text-secondary)]"
                            >
                              {r}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Fail-Closed Warnings */}
                    {quantResult.warnings && quantResult.warnings.length > 0 && (
                      <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-500 text-xs space-y-1">
                        <div className="flex items-center gap-1.5 font-bold">
                          <AlertTriangle size={14} />
                          <span>Quantification Notices & Blockers</span>
                        </div>
                        <ul className="list-disc list-inside text-[11px] space-y-0.5">
                          {quantResult.warnings.map((w, idx) => (
                            <li key={idx}>{w}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="h-full min-h-[220px] flex flex-col items-center justify-center p-8 rounded-xl bg-[var(--color-surface-hover)] border border-dashed border-[var(--color-border)] text-center">
                    <Calculator size={32} className="text-[var(--color-text-secondary)] mb-2 opacity-50" />
                    <p className="text-xs font-semibold text-[var(--color-text-primary)]">
                      Ready for Deterministic CORC Execution
                    </p>
                    <p className="text-[11px] text-[var(--color-text-secondary)] mt-1 max-w-sm">
                      Select Authoritative Mode or Scenario Simulation on the left, then click Execute to calculate verified CORCs according to Edition 2025 Version 2.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Section: Table 3.2 End-Use Disposition Categories */}
          <div className="rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 shadow-xs">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-[var(--color-border)]">
              <div>
                <h4 className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
                  <ShieldCheck size={16} className="text-emerald-500" />
                  Table 3.2 End-Use Disposition & Point of Creation Registry
                </h4>
                <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                  Point of Creation reached only upon verified delivery, GPS coordinates, and application attestation.
                </p>
              </div>
              <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-[var(--color-primary)]/10 text-[var(--color-primary)] border border-[var(--color-primary)]/20">
                {puroCategories.length} categories registered
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {puroCategories.map((cat) => (
                <div
                  key={cat.id}
                  className="p-3.5 rounded-xl bg-[var(--color-surface-hover)] border border-[var(--color-border)] space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                      {cat.category_code}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        cat.is_corc_eligible
                          ? "bg-emerald-500/10 text-emerald-500"
                          : "bg-rose-500/10 text-rose-500"
                      }`}
                    >
                      {cat.is_corc_eligible ? "CORC ELIGIBLE" : "INELIGIBLE"}
                    </span>
                  </div>

                  <div>
                    <h5 className="text-xs font-bold text-[var(--color-text-primary)]">{cat.category_name}</h5>
                    <p className="text-[11px] text-[var(--color-text-secondary)]">
                      Sector: {cat.sector} • {cat.product_type}
                    </p>
                  </div>

                  <div className="pt-1.5 border-t border-[var(--color-border)] text-[10px] text-[var(--color-text-secondary)] space-y-1">
                    <div>
                      <span className="font-semibold text-[var(--color-text-primary)]">Durability:</span>{" "}
                      {cat.default_durability_years} years ({cat.is_corc_eligible ? "CORC200+" : "INELIGIBLE"})
                    </div>
                    <div>
                      <span className="font-semibold text-[var(--color-text-primary)]">Type & Quality:</span>{" "}
                      {cat.application_type || "Standard"} • {cat.min_environmental_quality || "Standard Quality"}
                    </div>
                    {cat.reversal_rules && (
                      <div>
                        <span className="font-semibold text-[var(--color-text-primary)]">Reversal Rules:</span>{" "}
                        <span className="text-amber-400">
                          {typeof cat.reversal_rules === "object"
                            ? JSON.stringify(cat.reversal_rules)
                            : String(cat.reversal_rules)}
                        </span>
                      </div>
                    )}
                    <div>
                      <span className="font-semibold text-[var(--color-text-primary)]">Evidence:</span>{" "}
                      {cat.required_evidence_types?.join(", ") || "Delivery slip & attestation"}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Section: Normative Dependencies & Audit Workflows */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Normative Dependencies */}
            <div className="rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 shadow-xs">
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-[var(--color-border)]">
                <div>
                  <h4 className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
                    <FileText size={16} className="text-emerald-500" />
                    Normative Dependencies
                  </h4>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Edition 2025 V2 external normative standards and verification states.
                  </p>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-[var(--color-text-secondary)]">
                  {puroDeps.length} docs
                </span>
              </div>

              <div className="space-y-2.5">
                {puroDeps.map((dep) => (
                  <div
                    key={dep.id}
                    className="p-3 rounded-lg bg-[var(--color-surface-hover)] border border-[var(--color-border)] flex items-center justify-between text-xs"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-[var(--color-text-primary)]">{dep.code}</span>
                        <span className="text-[10px] text-[var(--color-text-secondary)]">v{dep.version}</span>
                      </div>
                      <p className="text-[11px] text-[var(--color-text-secondary)]">{dep.title}</p>
                    </div>

                    <span
                      className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border shrink-0 ${
                        dep.implementation_state === "VERIFIED"
                          ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                          : "bg-amber-500/10 text-amber-500 border-amber-500/20"
                      }`}
                    >
                      {dep.implementation_state}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Audit Dossier & Reports */}
            <div className="rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 shadow-xs">
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-[var(--color-border)]">
                <div>
                  <h4 className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
                    <ShieldCheck size={16} className="text-emerald-500" />
                    Audit Dossier & Output Reports
                  </h4>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Facility audits, monitoring periods, and cryptographically sealed manifests.
                  </p>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-[var(--color-text-secondary)]">
                  {outputReports.length} reports
                </span>
              </div>

              {outputReports.length > 0 ? (
                <div className="space-y-2.5">
                  {outputReports.map((rep) => (
                    <div
                      key={rep.id}
                      className="p-3 rounded-lg bg-[var(--color-surface-hover)] border border-[var(--color-border)] space-y-1.5 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-[var(--color-text-primary)]">
                          {rep.report_number}
                        </span>
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                          {rep.report_status}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-[var(--color-text-secondary)]">
                        <span>Period: {rep.monitoring_period_id}</span>
                        <span className="font-bold text-emerald-500 font-mono">
                          {Number(rep.total_net_corcs).toFixed(2)} CORCs
                        </span>
                      </div>
                      <p className="text-[10px] font-mono text-[var(--color-text-secondary)] truncate">
                        Manifest SHA-256: {rep.manifest_hash}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-xs text-[var(--color-text-secondary)] space-y-1">
                  <p>No output reports sealed yet for this facility.</p>
                  <p className="text-[11px]">
                    Output reports are compiled upon completing quantified batches within a monitoring period.
                  </p>
                </div>
              )}

              {/* Active Audits Status */}
              <div className="mt-4 pt-3 border-t border-[var(--color-border)]">
                <span className="text-[10px] uppercase font-bold text-[var(--color-text-secondary)] block mb-2">
                  Accredited Auditor Audits ({audits.length})
                </span>
                {audits.length > 0 ? (
                  <div className="space-y-2">
                    {audits.map((a) => (
                      <div
                        key={a.id}
                        className="p-2.5 rounded bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-xs flex items-center justify-between"
                      >
                        <div>
                          <span className="font-semibold text-[var(--color-text-primary)] block">
                            {a.audit_type}
                          </span>
                          <span className="text-[10px] text-[var(--color-text-secondary)]">
                            {a.auditor_organization}
                          </span>
                        </div>
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                          {a.audit_status}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[11px] text-[var(--color-text-secondary)]">
                    No scheduled or active third-party audits registered.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
