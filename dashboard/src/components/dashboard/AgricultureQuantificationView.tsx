// =============================================================================
// VeriField Nexus — Agriculture MRV Phase 3B-0: VM0042 v2.2 Methodology Prerequisite Engine
// =============================================================================
// Strict Bridge: QA-Accepted Evidence -> Authoritative Prerequisite Assessment Dossiers
// Note: Methodology Prerequisites ONLY. Strictly NO SOC stock, dSOC, or tCO2e calculation.
// =============================================================================

"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Lock,
  RefreshCw,
  Clock,
  HelpCircle,
  Eye,
  FileCheck,
  Hash,
  Database,
  Layers,
  ArrowRight,
  Filter,
  AlertOctagon,
  Copy,
  Check,
  Sparkles,
  Compass,
  FileText,
  Sliders,
  History,
  GitBranch,
  TrendingUp,
  Scale,
} from "lucide-react";
import {
  fetchQuantificationReadiness,
  fetchEligibleMeasurements,
  fetchQuantificationSnapshots,
  createQuantificationSnapshot,
  fetchPrerequisiteReadiness,
  evaluatePrerequisites,
  lockPrerequisiteAssessment,
  fetchPrerequisiteAssessments,
  fetchPrerequisiteAssessmentDetail,
  evaluateSOCStock,
  calculateSOCStock,
  fetchSOCStockResults,
  fetchSOCStockResultDetail,
  fetchSOCStockResultComponents,
  evaluateSOCChange,
  finalizeSOCChange,
  fetchSOCChangeResults,
  fetchSOCChangeResultDetail,
  fetchSOCChangeResultComponents,
  evaluateNetGHG,
  finalizeNetGHG,
  fetchNetGHGResults,
  fetchNetGHGResultDetail,
  fetchNetGHGResultComponents,
  type QuantificationReadinessData,
  type EligibleMeasurementSetData,
  type QuantificationSnapshotItem,
  type PrerequisiteEvaluationData,
  type PrerequisiteAssessmentItem,
  type PrerequisiteDimensionItem,
  type SOCStockResultItem,
  type SOCStockEvaluationData,
  type SOCChangeResultItem,
  type SOCChangeEvaluationData,
  type AgricultureNetGHGResultItem,
  type NetGHGEvaluationData,
  type AgricultureVintageGHGResultItem,
} from "@/lib/api";

interface Props {
  projectId: string;
  userRole?: string;
}

export function AgricultureQuantificationView({ projectId, userRole }: Props) {
  const [activeTab, setActiveTab] = useState<
    "prerequisites" | "dimensions" | "routemap" | "assessments" | "eligible" | "excluded" | "snapshots" | "soc_stock" | "soc_change" | "net_ghg"
  >("prerequisites");
  const [datasetFilter, setDatasetFilter] = useState<"all" | "baseline" | "project">("all");
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Phase 3A Data states
  const [readiness, setReadiness] = useState<QuantificationReadinessData | null>(null);
  const [eligibleSet, setEligibleSet] = useState<EligibleMeasurementSetData | null>(null);
  const [snapshots, setSnapshots] = useState<QuantificationSnapshotItem[]>([]);
  const [selectedSnapshot, setSelectedSnapshot] = useState<QuantificationSnapshotItem | null>(null);

  // Phase 3B-0 Prerequisite states
  const [prereqEval, setPrereqEval] = useState<PrerequisiteEvaluationData | null>(null);
  const [assessments, setAssessments] = useState<PrerequisiteAssessmentItem[]>([]);
  const [selectedAssessment, setSelectedAssessment] = useState<PrerequisiteAssessmentItem | null>(null);
  const [runPowerAnalysis, setRunPowerAnalysis] = useState<boolean>(false);
  const [targetMdd, setTargetMdd] = useState<number>(1.5);

  // Phase 3B-1 SOC Stock states
  const [socStockResults, setSocStockResults] = useState<SOCStockResultItem[]>([]);
  const [selectedSocStock, setSelectedSocStock] = useState<SOCStockResultItem | null>(null);
  const [socEvaluation, setSocEvaluation] = useState<SOCStockEvaluationData | null>(null);
  const [esmAlgorithm, setEsmAlgorithm] = useState<string>("ELLERT_BETTANY_1995");
  const [socPeriodType, setSocPeriodType] = useState<"BASELINE" | "MONITORING">("BASELINE");
  const [targetDepthCm, setTargetDepthCm] = useState<number>(30);
  const [customRefMass, setCustomRefMass] = useState<string>("");
  const [selectedPrereqForSoc, setSelectedPrereqForSoc] = useState<string>("");
  const [socStockNotes, setSocStockNotes] = useState<string>("");

  // Phase 3B-2 SOC Stock Change & Uncertainty states
  const [socChangeResults, setSocChangeResults] = useState<SOCChangeResultItem[]>([]);
  const [selectedSocChange, setSelectedSocChange] = useState<SOCChangeResultItem | null>(null);
  const [socChangeEvaluation, setSocChangeEvaluation] = useState<SOCChangeEvaluationData | null>(null);
  const [socChangeBaselineStockId, setSocChangeBaselineStockId] = useState<string>("");
  const [socChangeMonitoringStockId, setSocChangeMonitoringStockId] = useState<string>("");
  const [socChangePrereqId, setSocChangePrereqId] = useState<string>("");
  const [socChangeLabMethod, setSocChangeLabMethod] = useState<string>("DRY_COMBUSTION");
  const [socChangeLabQa, setSocChangeLabQa] = useState<boolean>(true);
  const [socChangeLabProficiency, setSocChangeLabProficiency] = useState<boolean>(true);
  const [socChangeNotes, setSocChangeNotes] = useState<string>("");

  // Phase 3B-3 Net GHG & VCU Readiness states
  const [netGhgResults, setNetGhgResults] = useState<AgricultureNetGHGResultItem[]>([]);
  const [selectedNetGhg, setSelectedNetGhg] = useState<AgricultureNetGHGResultItem | null>(null);
  const [netGhgEvaluation, setNetGhgEvaluation] = useState<NetGHGEvaluationData | null>(null);
  const [selectedSocChangeForNetGhg, setSelectedSocChangeForNetGhg] = useState<string>("");
  const [selectedPrereqForNetGhg, setSelectedPrereqForNetGhg] = useState<string>("");
  const [netGhgStartDate, setNetGhgStartDate] = useState<string>("2023-01-01");
  const [netGhgEndDate, setNetGhgEndDate] = useState<string>("2024-12-31");
  const [netGhgFossilBsl, setNetGhgFossilBsl] = useState<string>("40000");
  const [netGhgFossilWp, setNetGhgFossilWp] = useState<string>("20000");
  const [netGhgFossilEf, setNetGhgFossilEf] = useState<string>("0.001");
  const [netGhgLeakageDecline, setNetGhgLeakageDecline] = useState<string>("2.0");
  const [netGhgNprRating, setNetGhgNprRating] = useState<string>("15.0");
  const [netGhgNotes, setNetGhgNotes] = useState<string>("");

  // Create Snapshot Modal
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [snapContext, setSnapContext] = useState<"BASELINE" | "MONITORING">("BASELINE");
  const [snapNotes, setSnapNotes] = useState<string>("");

  // Lock Prerequisite Assessment Modal
  const [showLockPrereqModal, setShowLockPrereqModal] = useState<boolean>(false);
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string>("");
  const [prereqLockNotes, setPrereqLockNotes] = useState<string>("");

  const isFieldAgent = (userRole || "").toUpperCase() === "FIELD_AGENT";

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [r, e, s, pEval, pAssess, socResults, socChangeList, netGhgList] = await Promise.all([
        fetchQuantificationReadiness(projectId),
        fetchEligibleMeasurements(projectId),
        fetchQuantificationSnapshots(projectId),
        fetchPrerequisiteReadiness(projectId, runPowerAnalysis, targetMdd),
        fetchPrerequisiteAssessments(projectId),
        fetchSOCStockResults(projectId),
        fetchSOCChangeResults(projectId),
        fetchNetGHGResults(projectId),
      ]);
      setReadiness(r);
      setEligibleSet(e);
      setSnapshots(s);
      setPrereqEval(pEval);
      setAssessments(pAssess);
      setSocStockResults(socResults || []);
      setSocChangeResults(socChangeList || []);
      setNetGhgResults(netGhgList || []);

      if (pAssess && pAssess.length > 0) {
        if (!selectedPrereqForSoc) setSelectedPrereqForSoc(pAssess[0].id);
        if (!socChangePrereqId) setSocChangePrereqId(pAssess[0].id);
        if (!selectedPrereqForNetGhg) setSelectedPrereqForNetGhg(pAssess[0].id);
      }

      if (socChangeList && socChangeList.length > 0) {
        if (!selectedSocChangeForNetGhg) setSelectedSocChangeForNetGhg(socChangeList[0].id);
      }

      if (socResults && socResults.length > 0) {
        const b =
          socResults.find((x) => x.measurement_period_type === "BASELINE" && x.aggregation_level === "PROJECT") ||
          socResults.find((x) => x.measurement_period_type === "BASELINE");
        const m =
          socResults.find((x) => x.measurement_period_type === "MONITORING" && x.aggregation_level === "PROJECT") ||
          socResults.find((x) => x.measurement_period_type === "MONITORING");
        if (b && !socChangeBaselineStockId) setSocChangeBaselineStockId(b.id);
        if (m && !socChangeMonitoringStockId) setSocChangeMonitoringStockId(m.id);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load quantification data");
    } finally {
      setLoading(false);
    }
  }, [projectId, runPowerAnalysis, targetMdd, selectedPrereqForSoc, socChangePrereqId, socChangeBaselineStockId, socChangeMonitoringStockId, selectedPrereqForNetGhg, selectedSocChangeForNetGhg]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleEvaluatePrereq = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const result = await evaluatePrerequisites(projectId, {
        run_power_analysis: runPowerAnalysis,
        target_mdd: targetMdd,
      });
      setPrereqEval(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to evaluate prerequisites");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateSnapshot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isFieldAgent) {
      setError("Segregation of Duties: Field Agents are blocked from locking official quantification snapshots.");
      return;
    }
    setActionLoading(true);
    setError(null);
    try {
      await createQuantificationSnapshot(projectId, {
        context: snapContext,
        notes: snapNotes || undefined,
      });
      setShowCreateModal(false);
      setSnapNotes("");
      await loadData();
      setActiveTab("snapshots");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to lock snapshot");
    } finally {
      setActionLoading(false);
    }
  };

  const handleLockPrereqAssessment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isFieldAgent) {
      setError("Segregation of Duties: Field Agents are blocked from locking prerequisite assessments.");
      return;
    }
    setActionLoading(true);
    setError(null);
    try {
      const assessment = await lockPrerequisiteAssessment(projectId, {
        snapshot_id: selectedSnapshotId || undefined,
        notes: prereqLockNotes || undefined,
        run_power_analysis: runPowerAnalysis,
        target_mdd: targetMdd,
      });
      setShowLockPrereqModal(false);
      setPrereqLockNotes("");
      await loadData();
      setSelectedAssessment(assessment);
      setActiveTab("assessments");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to lock prerequisite assessment dossier");
    } finally {
      setActionLoading(false);
    }
  };

  const handleEvaluateSocStock = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const evalData = await evaluateSOCStock(projectId, {
        prerequisite_assessment_id: selectedPrereqForSoc || undefined,
        measurement_period_type: socPeriodType,
        esm_algorithm: esmAlgorithm,
        reference_depth_cm: targetDepthCm,
        reference_soil_mass_t_ha: customRefMass ? parseFloat(customRefMass) : undefined,
      });
      setSocEvaluation(evalData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to evaluate SOC stock preview");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCalculateAuthoritativeStock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isFieldAgent) {
      setError("Segregation of Duties: Field Agents are blocked from calculating or persisting authoritative SOC stock results.");
      return;
    }
    if (!selectedPrereqForSoc) {
      setError("Authoritative SOC stock calculation requires a locked prerequisite assessment dossier.");
      return;
    }
    setActionLoading(true);
    setError(null);
    try {
      const result = await calculateSOCStock(projectId, {
        prerequisite_assessment_id: selectedPrereqForSoc,
        measurement_period_type: socPeriodType,
        esm_algorithm: esmAlgorithm,
        reference_depth_cm: targetDepthCm,
        reference_soil_mass_t_ha: customRefMass ? parseFloat(customRefMass) : undefined,
        notes: socStockNotes || undefined,
      });
      await loadData();
      setSocStockNotes("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to calculate authoritative SOC stock");
    } finally {
      setActionLoading(false);
    }
  };

  const handleSelectSocStockDetail = async (stockId: string) => {
    try {
      const detail = await fetchSOCStockResultDetail(projectId, stockId);
      setSelectedSocStock(detail);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load SOC stock detail");
    }
  };

  const handleEvaluateSocChange = async () => {
    if (!socChangeBaselineStockId || !socChangeMonitoringStockId) {
      setError("Both baseline and monitoring SOC stock results are required to evaluate change.");
      return;
    }
    setActionLoading(true);
    setError(null);
    try {
      const evalData = await evaluateSOCChange(projectId, {
        baseline_stock_result_id: socChangeBaselineStockId,
        monitoring_stock_result_id: socChangeMonitoringStockId,
        prerequisite_assessment_id: socChangePrereqId || undefined,
        laboratory_method: socChangeLabMethod,
        lab_qa_verified: socChangeLabQa,
        active_lab_proficiency: socChangeLabProficiency,
        notes: socChangeNotes || undefined,
      });
      setSocChangeEvaluation(evalData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to evaluate SOC stock change preview");
    } finally {
      setActionLoading(false);
    }
  };

  const handleFinalizeSocChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isFieldAgent) {
      setError("Segregation of Duties: Field Agents are blocked from finalizing or persisting authoritative SOC stock change results.");
      return;
    }
    if (!socChangeBaselineStockId || !socChangeMonitoringStockId) {
      setError("Both baseline and monitoring SOC stock results are required.");
      return;
    }
    if (!socChangePrereqId) {
      setError("Authoritative SOC stock change calculation requires a locked prerequisite assessment dossier.");
      return;
    }
    setActionLoading(true);
    setError(null);
    try {
      const result = await finalizeSOCChange(projectId, {
        baseline_stock_result_id: socChangeBaselineStockId,
        monitoring_stock_result_id: socChangeMonitoringStockId,
        prerequisite_assessment_id: socChangePrereqId,
        laboratory_method: socChangeLabMethod,
        lab_qa_verified: socChangeLabQa,
        active_lab_proficiency: socChangeLabProficiency,
        notes: socChangeNotes || undefined,
      });
      await loadData();
      setSocChangeNotes("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to finalize authoritative SOC stock change");
    } finally {
      setActionLoading(false);
    }
  };

  const handleSelectSocChangeDetail = async (resultId: string) => {
    try {
      const detail = await fetchSOCChangeResultDetail(projectId, resultId);
      setSelectedSocChange(detail);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load SOC stock change detail");
    }
  };

  const handleEvaluateNetGhg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPrereqForNetGhg) {
      setError("Prerequisite assessment dossier is required to evaluate Net GHG reductions & removals.");
      return;
    }
    setActionLoading(true);
    setError(null);
    try {
      const bslQty = parseFloat(netGhgFossilBsl) || 0;
      const wpQty = parseFloat(netGhgFossilWp) || 0;
      const ef = parseFloat(netGhgFossilEf) || 0.001;
      const decline = parseFloat(netGhgLeakageDecline) || 0;
      const npr = netGhgNprRating ? parseFloat(netGhgNprRating) : undefined;

      const evalData = await evaluateNetGHG(projectId, {
        soc_change_result_id: selectedSocChangeForNetGhg || undefined,
        prerequisite_assessment_id: selectedPrereqForNetGhg,
        verification_period_start: netGhgStartDate,
        verification_period_end: netGhgEndDate,
        fossil_fuel_activities_bsl: bslQty > 0 ? [{ quantity: bslQty, emission_factor_tco2e_per_unit: ef }] : [],
        fossil_fuel_activities_wp: wpQty > 0 ? [{ quantity: wpQty, emission_factor_tco2e_per_unit: ef }] : [],
        leakage_data: { production_decline_leakage_tco2e_yr: decline },
        npr_rating_pct: npr,
        notes: netGhgNotes || undefined,
      });
      setNetGhgEvaluation(evalData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to evaluate Net GHG reductions and removals preview");
    } finally {
      setActionLoading(false);
    }
  };

  const handleFinalizeNetGhg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isFieldAgent) {
      setError("Segregation of Duties: Field Agents are blocked from finalizing or persisting authoritative Net GHG results.");
      return;
    }
    if (!selectedPrereqForNetGhg) {
      setError("Authoritative Net GHG calculation requires a locked prerequisite assessment dossier.");
      return;
    }
    setActionLoading(true);
    setError(null);
    try {
      const bslQty = parseFloat(netGhgFossilBsl) || 0;
      const wpQty = parseFloat(netGhgFossilWp) || 0;
      const ef = parseFloat(netGhgFossilEf) || 0.001;
      const decline = parseFloat(netGhgLeakageDecline) || 0;
      const npr = netGhgNprRating ? parseFloat(netGhgNprRating) : undefined;

      const result = await finalizeNetGHG(projectId, {
        soc_change_result_id: selectedSocChangeForNetGhg || undefined,
        prerequisite_assessment_id: selectedPrereqForNetGhg,
        verification_period_start: netGhgStartDate,
        verification_period_end: netGhgEndDate,
        fossil_fuel_activities_bsl: bslQty > 0 ? [{ quantity: bslQty, emission_factor_tco2e_per_unit: ef }] : [],
        fossil_fuel_activities_wp: wpQty > 0 ? [{ quantity: wpQty, emission_factor_tco2e_per_unit: ef }] : [],
        leakage_data: { production_decline_leakage_tco2e_yr: decline },
        npr_rating_pct: npr,
        notes: netGhgNotes || undefined,
      });
      await loadData();
      setSelectedNetGhg(result);
      setNetGhgNotes("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to finalize authoritative Net GHG reductions and removals");
    } finally {
      setActionLoading(false);
    }
  };

  const handleSelectNetGhgDetail = async (resultId: string) => {
    try {
      const detail = await fetchNetGHGResultDetail(projectId, resultId);
      setSelectedNetGhg(detail);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load Net GHG detail");
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "COMPLETE":
      case "READY":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" /> READY
          </span>
        );
      case "READY_WITH_ADVISORY":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20">
            <Sparkles className="w-3.5 h-3.5" /> READY (ADVISORY)
          </span>
        );
      case "NEEDS_REVIEW":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-3.5 h-3.5" /> NEEDS REVIEW
          </span>
        );
      case "INCOMPLETE":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertOctagon className="w-3.5 h-3.5" /> INCOMPLETE
          </span>
        );
      case "BLOCKED":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-600/20 text-rose-300 border border-rose-600/40">
            <AlertOctagon className="w-3.5 h-3.5" /> BLOCKED
          </span>
        );
      case "NOT_APPLICABLE":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
            N/A
          </span>
        );
      case "NOT_CONFIGURED":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
            <HelpCircle className="w-3.5 h-3.5" /> NOT CONFIGURED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
            {status}
          </span>
        );
    }
  };

  const getDepthBadge = (status: string) => {
    switch (status) {
      case "MATCH":
        return <span className="px-2 py-0.5 text-xs rounded bg-emerald-500/10 text-emerald-400 font-mono">MATCH (0-30cm)</span>;
      case "PARTIAL_COVERAGE":
        return <span className="px-2 py-0.5 text-xs rounded bg-amber-500/10 text-amber-400 font-mono">PARTIAL COVERAGE</span>;
      case "OVERLAPPING_INTERVAL":
        return <span className="px-2 py-0.5 text-xs rounded bg-indigo-500/10 text-indigo-400 font-mono">OVERLAPPING</span>;
      case "OUT_OF_SCOPE":
        return <span className="px-2 py-0.5 text-xs rounded bg-rose-500/10 text-rose-400 font-mono">OUT OF SCOPE</span>;
      default:
        return <span className="px-2 py-0.5 text-xs rounded bg-slate-500/10 text-slate-400 font-mono">{status}</span>;
    }
  };

  const baselineList = eligibleSet?.baseline_measurements || [];
  const projectList = eligibleSet?.project_measurements || [];
  const displayedEligible =
    datasetFilter === "baseline"
      ? baselineList
      : datasetFilter === "project"
      ? projectList
      : [...baselineList, ...projectList];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 text-xs font-semibold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase tracking-wider">
                Phase 3B-0 Prerequisite Engine
              </span>
              <span className="text-xs text-slate-400 font-mono">VM0042 v2.2 (C&C 2026-06-11)</span>
              <span className="text-xs text-indigo-400 font-mono px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20">
                {prereqEval?.dimensions?.VCS_PROGRAM_RULESET?.details?.governing_vcs_standard === "VCS_5_0"
                  ? "VCS Standard v5.0"
                  : "VCS Standard v4.7"}
              </span>
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              VM0042 Quantification Methodology Prerequisite Engine
            </h2>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl">
              Strict deterministic gating before Phase 3B quantification. Evaluates ESM depth horizons,
              sampling design, VCS program transition, and methodology locks.
              Zero tCO₂e or carbon estimation arithmetic is executed in this phase.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-xs text-slate-400">Prerequisite Readiness</div>
              <div className="mt-1">
                {prereqEval ? getStatusBadge(prereqEval.overall_status) : getStatusBadge("INCOMPLETE")}
              </div>
            </div>
            <button
              onClick={loadData}
              disabled={loading}
              className="p-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition"
              title="Refresh Data"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={() => setShowLockPrereqModal(true)}
              disabled={isFieldAgent}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition shadow-sm ${
                isFieldAgent
                  ? "bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700"
                  : "bg-emerald-600 hover:bg-emerald-500 text-white"
              }`}
              title={isFieldAgent ? "Field agents cannot lock prerequisite assessments" : "Lock official prerequisite assessment dossier"}
            >
              <Lock className="w-3.5 h-3.5" />
              Lock Prerequisite Dossier
            </button>
          </div>
        </div>

        {isFieldAgent && (
          <div className="mt-4 p-2.5 rounded bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>
              <strong>Segregation of Duties Enforced:</strong> As a Field Agent, you have read-only access to methodology prerequisites and cannot lock official prerequisite assessments.
            </span>
          </div>
        )}

        {error && (
          <div className="mt-4 p-3 rounded bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center gap-2">
            <AlertOctagon className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 text-sm font-medium gap-1 overflow-x-auto">
        <button
          onClick={() => setActiveTab("prerequisites")}
          className={`px-4 py-2.5 rounded-t-lg transition flex items-center gap-2 shrink-0 ${
            activeTab === "prerequisites"
              ? "bg-slate-800 text-emerald-400 border-t-2 border-emerald-500 font-semibold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          Methodology Prerequisites (Phase 3B-0)
        </button>
        <button
          onClick={() => setActiveTab("dimensions")}
          className={`px-4 py-2.5 rounded-t-lg transition flex items-center gap-2 shrink-0 ${
            activeTab === "dimensions"
              ? "bg-slate-800 text-emerald-400 border-t-2 border-emerald-500 font-semibold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Sliders className="w-4 h-4" />
          17 Categorical Dimensions ({prereqEval ? Object.keys(prereqEval.dimensions).length : 17})
        </button>
        <button
          onClick={() => setActiveTab("routemap")}
          className={`px-4 py-2.5 rounded-t-lg transition flex items-center gap-2 shrink-0 ${
            activeTab === "routemap"
              ? "bg-slate-800 text-emerald-400 border-t-2 border-emerald-500 font-semibold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Compass className="w-4 h-4" />
          Quantification Route Map
        </button>
        <button
          onClick={() => setActiveTab("assessments")}
          className={`px-4 py-2.5 rounded-t-lg transition flex items-center gap-2 shrink-0 ${
            activeTab === "assessments"
              ? "bg-slate-800 text-emerald-400 border-t-2 border-emerald-500 font-semibold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <History className="w-4 h-4" />
          Prerequisite Dossiers ({assessments.length})
        </button>
        <button
          onClick={() => setActiveTab("eligible")}
          className={`px-4 py-2.5 rounded-t-lg transition flex items-center gap-2 shrink-0 ${
            activeTab === "eligible"
              ? "bg-slate-800 text-emerald-400 border-t-2 border-emerald-500 font-semibold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Database className="w-4 h-4" />
          Eligible Measurements ({eligibleSet?.total_eligible ?? 0})
        </button>
        <button
          onClick={() => setActiveTab("excluded")}
          className={`px-4 py-2.5 rounded-t-lg transition flex items-center gap-2 shrink-0 ${
            activeTab === "excluded"
              ? "bg-slate-800 text-emerald-400 border-t-2 border-emerald-500 font-semibold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <AlertOctagon className="w-4 h-4" />
          Excluded Measurements ({eligibleSet?.total_excluded ?? 0})
        </button>
        <button
          onClick={() => setActiveTab("snapshots")}
          className={`px-4 py-2.5 rounded-t-lg transition flex items-center gap-2 shrink-0 ${
            activeTab === "snapshots"
              ? "bg-slate-800 text-emerald-400 border-t-2 border-emerald-500 font-semibold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Lock className="w-4 h-4" />
          Phase 3A Snapshots ({snapshots.length})
        </button>
        <button
          onClick={() => setActiveTab("soc_stock")}
          className={`px-4 py-2.5 rounded-t-lg transition flex items-center gap-2 shrink-0 ${
            activeTab === "soc_stock"
              ? "bg-slate-800 text-emerald-400 border-t-2 border-emerald-500 font-semibold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Layers className="w-4 h-4" />
          SOC Stock & ESM (Phase 3B-1) ({socStockResults.length})
        </button>
        <button
          onClick={() => setActiveTab("soc_change")}
          className={`px-4 py-2.5 rounded-t-lg transition flex items-center gap-2 shrink-0 ${
            activeTab === "soc_change"
              ? "bg-slate-800 text-emerald-400 border-t-2 border-emerald-500 font-semibold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          SOC Stock Change & Uncertainty (Phase 3B-2) ({socChangeResults.length})
        </button>
        <button
          onClick={() => setActiveTab("net_ghg")}
          className={`px-4 py-2.5 rounded-t-lg transition flex items-center gap-2 shrink-0 ${
            activeTab === "net_ghg"
              ? "bg-slate-800 text-emerald-400 border-t-2 border-emerald-500 font-semibold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Scale className="w-4 h-4" />
          Net GHG & Issuance Readiness (Phase 3B-3) ({netGhgResults.length})
        </button>
      </div>

      {/* Tab 1: Methodology Prerequisites Dashboard */}
      {activeTab === "prerequisites" && (
        <div className="space-y-6">
          {/* Top Cards: Methodology, VCS Version, Advisory Config */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="text-xs text-slate-400 font-medium mb-1">Authoritative Methodology</div>
              <div className="text-base font-bold text-white flex items-center gap-2">
                <span>{prereqEval?.methodology_code || "VM0042"}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                  v{prereqEval?.methodology_version || "2.2"}
                </span>
              </div>
              <div className="mt-2 text-xs text-slate-400">
                Rule Set: <span className="font-mono text-slate-300">{prereqEval?.rule_set_version || "VM0042_V2_2_CC_2026_06_11"}</span>
              </div>
              <div className="mt-1 text-[11px] text-slate-500">
                C&C Effective: {prereqEval?.corrections_clarifications_version || "2026-06-11"}
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="text-xs text-slate-400 font-medium mb-1">VCS Program Governance</div>
              <div className="text-sm font-bold text-white flex items-center gap-2">
                <span>Governing VCS Standard:</span>
                <span className="text-indigo-400 font-mono">
                  {prereqEval?.dimensions?.VCS_PROGRAM_RULESET?.details?.governing_vcs_standard === "VCS_5_0"
                    ? "VCS Standard v5.0"
                    : "VCS Standard v4.7"}
                </span>
              </div>
              <div className="mt-2 text-xs text-slate-400">
                Template Version: <span className="font-mono text-slate-300">
                  {prereqEval?.dimensions?.VCS_PROGRAM_RULESET?.details?.project_description_template || "VCS_PROJECT_DESCRIPTION_V4.4"}
                </span>
              </div>
              <div className="mt-1 text-xs text-slate-400">
                Template Variant: <span className="font-mono text-slate-300">
                  {prereqEval?.dimensions?.VCS_PROGRAM_RULESET?.details?.v5_template_variant || "NONE"}
                </span>
              </div>
              <div className="mt-1 text-xs text-slate-400">
                Transition Status: <span className="font-mono text-emerald-400">
                  {prereqEval?.dimensions?.VCS_PROGRAM_RULESET?.details?.transition_milestone || "PRE_2027_RETAINED_UNTIL_2030"}
                </span>
              </div>
              <div className="mt-1 text-[11px] text-slate-500">
                Delayed V5 Updates: {prereqEval?.dimensions?.VCS_PROGRAM_RULESET?.details?.delayed_requirement_ids?.length ?? 0} active
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="text-xs text-slate-400 font-medium mb-1">Baseline Look-Back vs Reassessment</div>
              <div className="text-sm font-bold text-white">
                Look-Back: <span className="text-emerald-400 font-mono">{prereqEval?.dimensions?.MANAGEMENT_HISTORY?.details?.historical_lookback_years ?? 3}y</span> (min 3y + rotation)
              </div>
              <div className="mt-2 text-xs text-slate-400">
                Reassessment Cycle: <span className="font-mono text-slate-300">{prereqEval?.dimensions?.MANAGEMENT_HISTORY?.details?.baseline_reassessment_period_years ?? 10}y</span>
              </div>
              <div className="mt-1 text-[11px] text-slate-500">
                Separated per VM0042 Section 8.1
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="text-xs text-slate-400 font-medium mb-1">Sampling Design Advisory (Sec 8.2)</div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-slate-300">Run Power Analysis</span>
                <input
                  type="checkbox"
                  checked={runPowerAnalysis}
                  onChange={(e) => setRunPowerAnalysis(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-950 text-emerald-600 focus:ring-emerald-500 h-4 w-4"
                />
              </div>
              <div className="mt-2 flex items-center justify-between text-xs">
                <span className="text-slate-400">Target MDD (g/kg):</span>
                <input
                  type="number"
                  step="0.1"
                  value={targetMdd}
                  onChange={(e) => setTargetMdd(parseFloat(e.target.value) || 1.5)}
                  disabled={!runPowerAnalysis}
                  className="w-20 px-2 py-1 rounded bg-slate-950 border border-slate-800 text-right text-xs font-mono text-white disabled:opacity-40"
                />
              </div>
              <div className="mt-2 text-[10px] text-slate-500">
                Non-blocking advisory per VM0042 Section 8.2.
              </div>
            </div>
          </div>

          {/* Authoritative Carbon Quantification Status (Phase 3B-0 Strict Null Contract) */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3 mb-3">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-slate-500"></div>
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Authoritative Carbon Quantification
                </span>
                <span data-testid="authoritative-carbon-status" className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                  NOT_CONFIGURED
                </span>
              </div>
              <div className="text-[11px] text-slate-500 font-mono">
                Phase 3B-0 Prerequisite Gate • No estimation arithmetic executed
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-950/50 rounded-lg p-3 border border-slate-800/50">
                <div className="text-[11px] text-slate-400">Total Net Removals</div>
                <div data-testid="net-removals-val" className="text-sm font-mono font-semibold text-slate-400 mt-1">
                  — <span className="text-xs font-normal text-slate-500">(Not configured)</span>
                </div>
              </div>

              <div className="bg-slate-950/50 rounded-lg p-3 border border-slate-800/50">
                <div className="text-[11px] text-slate-400">Total Net Reductions</div>
                <div data-testid="net-reductions-val" className="text-sm font-mono font-semibold text-slate-400 mt-1">
                  — <span className="text-xs font-normal text-slate-500">(Not configured)</span>
                </div>
              </div>

              <div className="bg-slate-950/50 rounded-lg p-3 border border-slate-800/50">
                <div className="text-[11px] text-slate-400">Total Net GHG (tCO₂e)</div>
                <div data-testid="total-net-tco2e-val" className="text-sm font-mono font-semibold text-slate-400 mt-1">
                  — <span className="text-xs font-normal text-slate-500">(Not configured)</span>
                </div>
              </div>

              <div className="bg-slate-950/50 rounded-lg p-3 border border-slate-800/50">
                <div className="text-[11px] text-slate-400">Issuable VCU Credits</div>
                <div data-testid="issuable-credits-val" className="text-sm font-mono font-semibold text-slate-400 mt-1">
                  — <span className="text-xs font-normal text-slate-500">(Not configured)</span>
                </div>
              </div>
            </div>

            <div className="mt-3 text-[11px] text-slate-500 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500/70 shrink-0" />
              <span>
                <strong>Fail-Closed Calculation Contract:</strong> Zero carbon output (0.0 tCO₂e) is strictly prohibited prior to full Phase 3B calculation execution.
              </span>
            </div>
          </div>

          {/* Evaluation Hash Banner */}
          {prereqEval && (
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2 overflow-hidden">
                <Hash className="w-4 h-4 text-emerald-400 shrink-0" />
                <span className="text-xs text-slate-400 font-mono">Prerequisite Evaluation Hash:</span>
                <span data-testid="prereq-eval-hash" className="text-xs font-mono text-slate-200 truncate">
                  {prereqEval.evaluation_hash}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleCopyHash(prereqEval.evaluation_hash)}
                  className="px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex items-center gap-1 shrink-0"
                >
                  {copiedHash === prereqEval.evaluation_hash ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" /> Copied
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" /> Copy SHA-256
                    </>
                  )}
                </button>
                <button
                  onClick={handleEvaluatePrereq}
                  disabled={actionLoading}
                  className="px-3 py-1 text-xs rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition flex items-center gap-1"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${actionLoading ? "animate-spin" : ""}`} />
                  Re-evaluate
                </button>
              </div>
            </div>
          )}

          {/* Blocking Reasons & Advisory Notes */}
          {prereqEval && prereqEval.blocking_reasons.length > 0 && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 space-y-2">
              <div className="font-bold flex items-center gap-2">
                <AlertOctagon className="w-4 h-4 text-rose-400" />
                Methodology Blocking Reasons ({prereqEval.blocking_reasons.length}):
              </div>
              <ul className="list-disc list-inside space-y-1 font-mono text-[11px] text-rose-200">
                {prereqEval.blocking_reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}

          {prereqEval && prereqEval.advisory_notes.length > 0 && (
            <div className="p-4 rounded-xl bg-sky-500/10 border border-sky-500/20 text-xs text-sky-300 space-y-2">
              <div className="font-bold flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-sky-400" />
                Non-Blocking Advisories ({prereqEval.advisory_notes.length}):
              </div>
              <ul className="list-disc list-inside space-y-1 font-mono text-[11px] text-sky-200">
                {prereqEval.advisory_notes.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Quick Summary Grid of 17 Dimensions */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-400" />
                17 Authoritative Methodology Dimensions
              </h3>
              <button
                onClick={() => setActiveTab("dimensions")}
                className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1 font-medium"
              >
                View Full Details <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {prereqEval &&
                Object.entries(prereqEval.dimensions).map(([key, dim]) => (
                  <div
                    key={key}
                    className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 hover:border-slate-700 transition flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className="text-xs font-mono font-medium text-slate-200 truncate" title={key}>
                          {key}
                        </span>
                        {getStatusBadge(dim.status)}
                      </div>
                      <p className="text-[11px] text-slate-400 leading-relaxed line-clamp-2">{dim.message}</p>
                    </div>
                    <div className="mt-2.5 pt-2 border-t border-slate-800 flex items-center justify-between text-[10px] font-mono text-slate-500">
                      <span>{dim.requirement}</span>
                      <span className={dim.blocking ? "text-rose-400 font-semibold" : "text-slate-400"}>
                        {dim.finding_type}
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Full 17 Categorical Dimensions Grid */}
      {activeTab === "dimensions" && (
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-xs text-slate-400 flex items-center justify-between">
            <div>
              <span className="font-semibold text-white">Full Prerequisite Taxonomy:</span> 17 authoritative VM0042 v2.2 dimensions evaluated categorically.
            </div>
            <div className="text-slate-400 font-mono">
              Rule Set: {prereqEval?.rule_set_version || "VM0042_V2_2_CC_2026_06_11"}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {prereqEval &&
              Object.entries(prereqEval.dimensions).map(([key, dim]) => (
                <div
                  key={key}
                  className="bg-slate-900 border border-slate-800 rounded-xl p-4 hover:border-slate-700 transition flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-white">{key}</span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                          {dim.requirement}
                        </span>
                      </div>
                      {getStatusBadge(dim.status)}
                    </div>
                    <div className="text-xs text-slate-300 mb-2">{dim.message}</div>
                    <div className="text-[11px] font-mono text-slate-400 bg-slate-950 p-2.5 rounded-lg border border-slate-800/80 space-y-1">
                      <div>Reason Code: <span className="text-emerald-400 font-semibold">{dim.reason_code}</span></div>
                      <div>Finding Type: <span className={dim.blocking ? "text-rose-400" : "text-sky-400"}>{dim.finding_type}</span></div>
                      {dim.details && Object.keys(dim.details).length > 0 && (
                        <div className="pt-1 mt-1 border-t border-slate-800 text-[10px] text-slate-500 overflow-x-auto">
                          <pre>{JSON.stringify(dim.details, null, 2)}</pre>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Tab 3: Quantification Route Map */}
      {activeTab === "routemap" && (
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-xs text-slate-400 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <span className="font-semibold text-white">VM0042 v2.2 Table 5 Quantification Route Matrix:</span> Canonical component-level routing across 15 GHG sources and carbon pools.
            </div>
            <div className="text-xs font-mono text-emerald-400">
              Table 5 Status: {prereqEval?.dimensions?.QUANTIFICATION_ROUTE?.details?.table5_complete ? "100% COMPLETE" : "VERIFIED"}
            </div>
          </div>

          {/* Table 5 Route Grid */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 font-mono uppercase text-[11px] border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3">Source / Carbon Pool</th>
                    <th className="px-4 py-3">GHG</th>
                    <th className="px-4 py-3">Permitted Approaches (Table 5)</th>
                    <th className="px-4 py-3">Assigned Route</th>
                    <th className="px-4 py-3">Applicable Module / Tool</th>
                    <th className="px-4 py-3">Boundary Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {[
                    { name: "Soil Organic Carbon (SOC)", ghg: "CO2", permitted: "Approach 1, Approach 2", assigned: prereqEval?.dimensions?.QUANTIFICATION_ROUTE?.details?.soc_approach || "APPROACH_2", module: prereqEval?.dimensions?.QUANTIFICATION_ROUTE?.details?.soc_approach === "APPROACH_1" ? "VMD0053 v2.1" : "VM0042 DIRECT ESM", inBoundary: true },
                    { name: "Woody Biomass (Shrubs & Trees)", ghg: "CO2", permitted: "External Tool", assigned: "EXTERNAL_TOOL", module: "CDM AR-TOOL14", inBoundary: prereqEval?.dimensions?.QUANTIFICATION_ROUTE?.details?.includes_woody_biomass ?? false },
                    { name: "Fossil Fuel Combustion", ghg: "CO2", permitted: "Approach 3, External Tool", assigned: "APPROACH_3", module: "IPCC 2006 Tier 1", inBoundary: true },
                    { name: "Liming Application", ghg: "CO2", permitted: "Approach 3", assigned: "APPROACH_3", module: "VM0042 Stoichiometry", inBoundary: true },
                    { name: "Soil Methanogenesis (Rice / Flooded)", ghg: "CH4", permitted: "Approach 1, Approach 3", assigned: prereqEval?.dimensions?.QUANTIFICATION_ROUTE?.details?.soc_approach === "APPROACH_1" ? "APPROACH_1" : "APPROACH_3", module: prereqEval?.dimensions?.QUANTIFICATION_ROUTE?.details?.soc_approach === "APPROACH_1" ? "VMD0053 v2.1" : "IPCC 2019 Flooding", inBoundary: false },
                    { name: "Enteric Fermentation", ghg: "CH4", permitted: "Approach 1, Approach 3", assigned: "APPROACH_3", module: "IPCC 2019 Tier 2", inBoundary: false },
                    { name: "Manure Deposition (CH4)", ghg: "CH4", permitted: "Approach 1, Approach 3", assigned: "APPROACH_3", module: "IPCC 2019 Tier 2", inBoundary: false },
                    { name: "Biomass Burning (Residues)", ghg: "CH4", permitted: "Approach 3", assigned: "APPROACH_3", module: "IPCC 2006 Burning", inBoundary: false },
                    { name: "Direct Soil N2O (Fertilizer & Soil)", ghg: "N2O", permitted: "Approach 1, Approach 3", assigned: prereqEval?.dimensions?.QUANTIFICATION_ROUTE?.details?.soc_approach === "APPROACH_1" ? "APPROACH_1" : "APPROACH_3", module: prereqEval?.dimensions?.QUANTIFICATION_ROUTE?.details?.soc_approach === "APPROACH_1" ? "VMD0053 v2.1" : "IPCC 2019 Refinement", inBoundary: true },
                    { name: "Indirect N2O (Atmospheric Volatilization)", ghg: "N2O", permitted: "Approach 1, Approach 3", assigned: prereqEval?.dimensions?.QUANTIFICATION_ROUTE?.details?.soc_approach === "APPROACH_1" ? "APPROACH_1" : "APPROACH_3", module: prereqEval?.dimensions?.QUANTIFICATION_ROUTE?.details?.soc_approach === "APPROACH_1" ? "VMD0053 v2.1" : "IPCC 2019 EF4", inBoundary: true },
                    { name: "Indirect N2O (Leaching & Runoff)", ghg: "N2O", permitted: "Approach 1, Approach 3", assigned: prereqEval?.dimensions?.QUANTIFICATION_ROUTE?.details?.soc_approach === "APPROACH_1" ? "APPROACH_1" : "APPROACH_3", module: prereqEval?.dimensions?.QUANTIFICATION_ROUTE?.details?.soc_approach === "APPROACH_1" ? "VMD0053 v2.1" : "IPCC 2019 EF5", inBoundary: true },
                    { name: "Nitrogen-Fixing Species", ghg: "N2O", permitted: "Approach 1, Approach 3", assigned: prereqEval?.dimensions?.QUANTIFICATION_ROUTE?.details?.soc_approach === "APPROACH_1" ? "APPROACH_1" : "APPROACH_3", module: prereqEval?.dimensions?.QUANTIFICATION_ROUTE?.details?.soc_approach === "APPROACH_1" ? "VMD0053 v2.1" : "IPCC 2019 Residues", inBoundary: true },
                    { name: "Manure Deposition on Pastures", ghg: "N2O", permitted: "Approach 1, Approach 3", assigned: prereqEval?.dimensions?.QUANTIFICATION_ROUTE?.details?.soc_approach === "APPROACH_1" ? "APPROACH_1" : "APPROACH_3", module: prereqEval?.dimensions?.QUANTIFICATION_ROUTE?.details?.soc_approach === "APPROACH_1" ? "VMD0053 v2.1" : "IPCC 2019 EF3PRP", inBoundary: false },
                    { name: "Biomass Burning (N2O)", ghg: "N2O", permitted: "Approach 3", assigned: "APPROACH_3", module: "IPCC 2006 Burning", inBoundary: false },
                    { name: "Leakage (Production Decline)", ghg: "LEAKAGE", permitted: "Approach 3", assigned: "APPROACH_3", module: "VM0042 C&C 2026-06-11", inBoundary: true },
                  ].map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/40 transition">
                      <td className="px-4 py-2.5 font-medium text-white">{row.name}</td>
                      <td className="px-4 py-2.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          row.ghg === "CO2" ? "bg-emerald-500/10 text-emerald-400" :
                          row.ghg === "CH4" ? "bg-amber-500/10 text-amber-400" :
                          row.ghg === "N2O" ? "bg-indigo-500/10 text-indigo-400" :
                          "bg-rose-500/10 text-rose-400"
                        }`}>
                          {row.ghg}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-slate-400 text-[11px]">{row.permitted}</td>
                      <td className="px-4 py-2.5 text-slate-300 text-[11px]">{row.assigned}</td>
                      <td className="px-4 py-2.5 text-slate-400 text-[11px]">{row.module}</td>
                      <td className="px-4 py-2.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] ${
                          row.inBoundary ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-slate-800 text-slate-500"
                        }`}>
                          {row.inBoundary ? "INCLUDED" : "EXCLUDED"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Prerequisite Dossiers History */}
      {activeTab === "assessments" && (
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-xs text-slate-400 flex items-center justify-between">
            <div>
              <span className="font-semibold text-white">Prerequisite Assessment Dossiers:</span> Locked, cryptographically signed methodology readiness audits.
            </div>
            <div className="text-xs text-slate-500 font-mono">
              Total Dossiers: {assessments.length}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {assessments.length === 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-sm">
                No prerequisite assessment dossiers locked yet. Click "Lock Prerequisite Dossier" above to generate the authoritative Phase 3B-0 record.
              </div>
            ) : (
              assessments.map((a) => (
                <div
                  key={a.id}
                  className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition"
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 text-xs font-mono font-bold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {a.assessment_code} (v{a.version})
                      </span>
                      <span className={`px-2 py-0.5 text-xs font-semibold rounded ${
                        a.status === "LOCKED" ? "bg-emerald-950 text-emerald-300 border border-emerald-800" : "bg-slate-800 text-slate-400"
                      }`}>
                        {a.status}
                      </span>
                      {getStatusBadge(a.overall_readiness)}
                    </div>
                    <div className="text-xs text-slate-400 font-mono">
                      Locked: {a.locked_at ? new Date(a.locked_at).toLocaleString() : "—"}
                    </div>
                  </div>

                  {/* Hash */}
                  <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 flex items-center justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2 overflow-hidden">
                      <Hash className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span data-testid="assessment-hash-value" className="text-xs font-mono text-slate-300 truncate">
                        {a.assessment_hash}
                      </span>
                    </div>
                    <button
                      onClick={() => handleCopyHash(a.assessment_hash)}
                      className="px-2 py-1 text-[11px] rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex items-center gap-1 shrink-0"
                    >
                      {copiedHash === a.assessment_hash ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" /> Copied
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" /> Copy SHA-256
                        </>
                      )}
                    </button>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs mb-3 font-mono">
                    <div className="bg-slate-800/40 p-2 rounded">
                      <div className="text-slate-400 text-[10px]">METHODOLOGY</div>
                      <div className="text-white font-bold">{a.methodology_code} v{a.methodology_version}</div>
                    </div>
                    <div className="bg-slate-800/40 p-2 rounded">
                      <div className="text-slate-400 text-[10px]">VCS STANDARD</div>
                      <div className="text-indigo-400 font-bold">{a.vcs_standard_version}</div>
                    </div>
                    <div className="bg-slate-800/40 p-2 rounded">
                      <div className="text-slate-400 text-[10px]">BLOCKING REASONS</div>
                      <div className="text-rose-400 font-bold">{a.blocking_reasons.length}</div>
                    </div>
                    <div className="bg-slate-800/40 p-2 rounded">
                      <div className="text-slate-400 text-[10px]">ADVISORY NOTES</div>
                      <div className="text-sky-400 font-bold">{a.advisory_notes.length}</div>
                    </div>
                  </div>

                  {a.notes && (
                    <div className="text-xs text-slate-400 mb-3 italic">
                      Notes: {a.notes}
                    </div>
                  )}

                  <div className="flex justify-end pt-2 border-t border-slate-800">
                    <button
                      onClick={() => setSelectedAssessment(a)}
                      className="flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 transition font-medium"
                    >
                      <Eye className="w-3.5 h-3.5" /> Inspect Authoritative Dossier
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab 5: Eligible Measurement Sets (Phase 3A Bridge) */}
      {activeTab === "eligible" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-400" />
              <span className="text-xs font-semibold text-white">Dataset Context:</span>
              <div className="flex bg-slate-800 p-0.5 rounded-lg text-xs">
                <button
                  onClick={() => setDatasetFilter("all")}
                  className={`px-3 py-1 rounded-md transition ${
                    datasetFilter === "all" ? "bg-emerald-600 text-white font-medium" : "text-slate-400 hover:text-white"
                  }`}
                >
                  All ({eligibleSet?.total_eligible ?? 0})
                </button>
                <button
                  onClick={() => setDatasetFilter("baseline")}
                  className={`px-3 py-1 rounded-md transition ${
                    datasetFilter === "baseline" ? "bg-emerald-600 text-white font-medium" : "text-slate-400 hover:text-white"
                  }`}
                >
                  Baseline ({baselineList.length})
                </button>
                <button
                  onClick={() => setDatasetFilter("project")}
                  className={`px-3 py-1 rounded-md transition ${
                    datasetFilter === "project" ? "bg-emerald-600 text-white font-medium" : "text-slate-400 hover:text-white"
                  }`}
                >
                  Project ({projectList.length})
                </button>
              </div>
            </div>

            <div className="text-xs text-slate-400">
              Analyte Canonical Unit: <strong className="text-emerald-400 font-mono">g/kg (Linear Scaling *10)</strong>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-800/80 text-slate-400 uppercase font-mono text-[11px] border-b border-slate-800">
                  <tr>
                    <th className="p-3">Sample Code</th>
                    <th className="p-3">Point Code</th>
                    <th className="p-3">Land Unit / Stratum</th>
                    <th className="p-3">Sampling Date</th>
                    <th className="p-3">SOC Conc (g/kg)</th>
                    <th className="p-3">Depth Alignment</th>
                    <th className="p-3">Bulk Density</th>
                    <th className="p-3">Coarse Frags</th>
                    <th className="p-3">Provenance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {displayedEligible.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="p-8 text-center text-slate-500 font-sans">
                        No eligible measurements found in this category.
                      </td>
                    </tr>
                  ) : (
                    displayedEligible.map((item) => (
                      <tr key={item.physical_sample_id} className="hover:bg-slate-800/40 transition">
                        <td className="p-3 font-semibold text-white">{item.sample_code}</td>
                        <td className="p-3 text-slate-400">{item.point_code}</td>
                        <td className="p-3">
                          <div className="text-white">{item.land_unit_code}</div>
                          <div className="text-[11px] text-slate-500">{item.stratum_code || "No Stratum"}</div>
                        </td>
                        <td className="p-3 text-slate-400">{item.sampling_date}</td>
                        <td className="p-3 text-emerald-400 font-bold">
                          {item.normalized_value} <span className="text-[10px] text-slate-400">g/kg</span>
                          <span className="block text-[10px] text-slate-500 font-normal">
                            ({item.raw_value} {item.raw_unit})
                          </span>
                        </td>
                        <td className="p-3">{getDepthBadge(item.depth_alignment_status)}</td>
                        <td className="p-3">
                          {item.bulk_density_status === "PRESENT" ? (
                            <span className="text-emerald-400 font-bold">
                              {item.bulk_density_normalized_value} {item.bulk_density_normalized_unit}
                            </span>
                          ) : (
                            <span className="text-amber-400">MISSING</span>
                          )}
                        </td>
                        <td className="p-3 text-slate-400">
                          {item.coarse_fragments_status === "MEASURED_ZERO"
                            ? "0% (Zero)"
                            : item.coarse_fragments_status}
                        </td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            {item.provenance_class}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 6: Excluded Measurements */}
      {activeTab === "excluded" && (
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-xs text-slate-400">
            <span className="font-semibold text-white">Exclusion Audit Trail:</span> Physical soil samples excluded from calculation readiness with machine-readable reason codes.
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-800/80 text-slate-400 uppercase font-mono text-[11px] border-b border-slate-800">
                  <tr>
                    <th className="p-3">Sample Code</th>
                    <th className="p-3">Point Code</th>
                    <th className="p-3">Land Unit</th>
                    <th className="p-3">Exclusion Reasons</th>
                    <th className="p-3">Rejection Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {(eligibleSet?.excluded_measurements || []).length === 0 ? (
                    <tr>
                      <td colSpan={5} className="p-8 text-center text-slate-500 font-sans">
                        Zero excluded measurements. All candidate samples passed eligibility criteria.
                      </td>
                    </tr>
                  ) : (
                    eligibleSet?.excluded_measurements.map((item) => (
                      <tr key={item.physical_sample_id} className="hover:bg-slate-800/40 transition">
                        <td className="p-3 font-semibold text-white">{item.sample_code}</td>
                        <td className="p-3 text-slate-400">{item.point_code || "—"}</td>
                        <td className="p-3 text-slate-400">{item.land_unit_code || "—"}</td>
                        <td className="p-3">
                          <div className="flex flex-wrap gap-1">
                            {item.exclusion_reasons.map((r) => (
                              <span
                                key={r}
                                className="px-2 py-0.5 rounded text-[10px] bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold"
                              >
                                {r}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="p-3 text-slate-400 font-sans text-xs">
                          {Object.keys(item.rejection_details || {}).length > 0 ? (
                            <pre className="text-[11px] text-slate-400 font-mono bg-slate-950 p-2 rounded max-w-xs overflow-x-auto">
                              {JSON.stringify(item.rejection_details, null, 2)}
                            </pre>
                          ) : (
                            "—"
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 7: Snapshots & Lineage Viewer (Phase 3A) */}
      {activeTab === "snapshots" && (
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-xs text-slate-400 flex items-center justify-between">
            <div>
              <span className="font-semibold text-white">Immutable Phase 3A Snapshots:</span> Cryptographically hashed with SHA-256 for mathematical provenance.
            </div>
            <div className="text-xs text-slate-500 font-mono">
              Total Snapshots: {snapshots.length}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {snapshots.length === 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-sm">
                No quantification input snapshots created yet.
              </div>
            ) : (
              snapshots.map((snap) => (
                <div
                  key={snap.id}
                  className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition"
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 text-xs font-mono font-bold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {snap.snapshot_code}
                      </span>
                      <span className="px-2 py-0.5 text-xs font-semibold rounded bg-slate-800 text-slate-300">
                        {snap.context}
                      </span>
                      {snap.is_locked && (
                        <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-mono">
                          <Lock className="w-3 h-3" /> LOCKED
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-400 font-mono">
                      Created: {snap.created_at ? new Date(snap.created_at).toLocaleString() : "—"}
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 flex items-center justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2 overflow-hidden">
                      <Hash className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span data-testid="snapshot-hash-value" className="text-xs font-mono text-slate-300 truncate">
                        {snap.snapshot_hash}
                      </span>
                    </div>
                    <button
                      onClick={() => handleCopyHash(snap.snapshot_hash)}
                      className="px-2 py-1 text-[11px] rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex items-center gap-1 shrink-0"
                    >
                      {copiedHash === snap.snapshot_hash ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" /> Copied
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" /> Copy SHA-256
                        </>
                      )}
                    </button>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs mb-3 font-mono">
                    <div className="bg-slate-800/40 p-2 rounded">
                      <div className="text-slate-400 text-[10px]">METHODOLOGY</div>
                      <div className="text-white font-bold">{snap.methodology_code} v{snap.methodology_version}</div>
                    </div>
                    <div className="bg-slate-800/40 p-2 rounded">
                      <div className="text-slate-400 text-[10px]">ELIGIBLE MEASUREMENTS</div>
                      <div className="text-emerald-400 font-bold">{snap.total_eligible_measurements}</div>
                    </div>
                    <div className="bg-slate-800/40 p-2 rounded">
                      <div className="text-slate-400 text-[10px]">EXCLUDED MEASUREMENTS</div>
                      <div className="text-rose-400 font-bold">{snap.total_excluded_measurements}</div>
                    </div>
                    <div className="bg-slate-800/40 p-2 rounded">
                      <div className="text-slate-400 text-[10px]">RULE SET</div>
                      <div className="text-slate-300 truncate">{snap.rule_set_version}</div>
                    </div>
                  </div>

                  {snap.notes && (
                    <div className="text-xs text-slate-400 mb-3 italic">
                      Notes: {snap.notes}
                    </div>
                  )}

                  <div className="flex justify-end pt-2 border-t border-slate-800">
                    <button
                      onClick={() => setSelectedSnapshot(snap)}
                      className="flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 transition font-medium"
                    >
                      <Eye className="w-3.5 h-3.5" /> Inspect Canonical JSON Package
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab 8: Phase 3B-1 SOC Stock & Equivalent Soil Mass Engine */}
      {activeTab === "soc_stock" && (
        <div className="space-y-6">
          {/* Carbon Policy Lock Invariant Banner */}
          <div className="bg-slate-900 border border-amber-500/30 rounded-xl p-4 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="text-xs font-bold text-amber-300 uppercase tracking-wider">
                Authoritative Carbon Quantification: NOT_CONFIGURED
              </div>
              <div className="text-sm font-semibold text-white">
                VM0042 v2.2 Soil Organic Carbon Stock & Equivalent Soil Mass Engine (Phase 3B-1)
              </div>
              <div className="text-xs text-slate-400 leading-relaxed">
                Measured SOC stock and ESM normalization engine active.
                <strong className="text-slate-300 ml-1">
                  Strict Carbon Invariant enforced: No ΔSOC crediting calculation, no 44/12 stoichiometric conversion,
                  no tCO2e credit quantity, and internal ledger minting remains BLOCKED_FOR_AGRICULTURE.
                </strong>
              </div>
            </div>
          </div>

          {/* Engine Configuration & Action Form */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
              <div>
                <h3 className="text-sm font-semibold text-white">Authoritative SOC Stock Calculation Parameters</h3>
                <p className="text-xs text-slate-400">
                  Configure Equivalent Soil Mass (ESM) normalization parameters per VM0042 v2.2 / C&C 2026-06-11.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleEvaluateSocStock}
                  disabled={actionLoading || assessments.length === 0}
                  className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition flex items-center gap-1.5 border border-slate-700"
                >
                  {actionLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Eye className="w-3.5 h-3.5" />}
                  Evaluate Preview
                </button>
              </div>
            </div>

            <form onSubmit={handleCalculateAuthoritativeStock} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                <div>
                  <label className="block text-slate-400 font-medium mb-1">
                    Locked Prerequisite Dossier <span className="text-rose-400">*</span>
                  </label>
                  <select
                    value={selectedPrereqForSoc}
                    onChange={(e) => setSelectedPrereqForSoc(e.target.value)}
                    required
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono text-xs focus:border-emerald-500 focus:outline-none"
                  >
                    {assessments.length === 0 ? (
                      <option value="">No locked prerequisite assessments available</option>
                    ) : (
                      assessments.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.assessment_code} ({a.status}) — {a.assessment_hash.substring(0, 12)}...
                        </option>
                      ))
                    )}
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 font-medium mb-1">Measurement Period Type</label>
                  <select
                    value={socPeriodType}
                    onChange={(e) => setSocPeriodType(e.target.value as "BASELINE" | "MONITORING")}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white text-xs focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="BASELINE">BASELINE (T0 Initial Stock)</option>
                    <option value="MONITORING">MONITORING (T1 Resampling Stock)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 font-medium mb-1">ESM Normalization Algorithm</label>
                  <select
                    value={esmAlgorithm}
                    onChange={(e) => setEsmAlgorithm(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white text-xs focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="ELLERT_BETTANY_1995">Ellert & Bettany (1995) / VM0042 ESM Tool</option>
                    <option value="WENDT_HAUSER_2013">Wendt & Hauser (2013) Spline Interpolation</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 font-medium mb-1">Reference Depth (cm)</label>
                  <input
                    type="number"
                    value={targetDepthCm}
                    onChange={(e) => setTargetDepthCm(Number(e.target.value))}
                    min={10}
                    max={100}
                    step={1}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white text-xs focus:border-emerald-500 focus:outline-none"
                  />
                  <div className="text-[10px] text-slate-500 mt-0.5">Methodology default: 30 cm</div>
                </div>

                <div>
                  <label className="block text-slate-400 font-medium mb-1">
                    Custom Reference Soil Mass (t dry fine soil/ha) <span className="text-slate-500 font-normal">(Optional)</span>
                  </label>
                  <input
                    type="number"
                    value={customRefMass}
                    onChange={(e) => setCustomRefMass(e.target.value)}
                    placeholder="Auto-derived from baseline if omitted"
                    min={100}
                    step={0.1}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white text-xs focus:border-emerald-500 focus:outline-none"
                  />
                  <div className="text-[10px] text-slate-500 mt-0.5">Leave blank for baseline-derived M_ref</div>
                </div>

                <div>
                  <label className="block text-slate-400 font-medium mb-1">Auditor / Verifier Notes</label>
                  <input
                    type="text"
                    value={socStockNotes}
                    onChange={(e) => setSocStockNotes(e.target.value)}
                    placeholder="e.g., Baseline T0 authoritative stock calculation"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-800">
                <div className="text-xs text-slate-400">
                  {isFieldAgent ? (
                    <span className="text-amber-400 flex items-center gap-1">
                      <Lock className="w-3.5 h-3.5" /> Field Agents are restricted to preview only (Segregation of Duties).
                    </span>
                  ) : (
                    <span>Creates an immutable cryptographic stock result and snapshots all component layers.</span>
                  )}
                </div>
                <button
                  type="submit"
                  disabled={actionLoading || isFieldAgent || assessments.length === 0}
                  className={`px-4 py-2 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                    isFieldAgent || assessments.length === 0
                      ? "bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700"
                      : "bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm"
                  }`}
                >
                  {actionLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Lock className="w-3.5 h-3.5" />}
                  Calculate & Persist Authoritative Stock
                </button>
              </div>
            </form>
          </div>

          {/* Real-time Preview Evaluation Card (if evaluated) */}
          {socEvaluation && (
            <div className="bg-slate-900 border border-emerald-500/30 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-emerald-400" />
                  <h4 className="text-sm font-semibold text-white">Evaluation Preview Result</h4>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                    socEvaluation.status === "EVALUATED"
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                  }`}>
                    {socEvaluation.status}
                  </span>
                </div>
                <div className="flex items-center gap-2 font-mono text-xs text-slate-400">
                  <span>SHA-256: {socEvaluation.evaluation_hash.substring(0, 16)}...</span>
                  <button
                    onClick={() => handleCopyHash(socEvaluation.evaluation_hash)}
                    className="p-1 hover:text-white transition"
                    title="Copy Evaluation Hash"
                  >
                    {copiedHash === socEvaluation.evaluation_hash ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>

              {/* Metric Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">Project SOC Stock (ESM)</div>
                  <div className="text-lg font-bold text-emerald-400 font-mono mt-0.5">
                    {socEvaluation.project_soc_stock_t_c_per_ha != null
                      ? `${Number(socEvaluation.project_soc_stock_t_c_per_ha).toFixed(3)} t C/ha`
                      : "N/A"}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">Area-weighted canonical stock</div>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">Reference Soil Mass (M_ref)</div>
                  <div className="text-lg font-bold text-white font-mono mt-0.5">
                    {socEvaluation.reference_soil_mass_t_ha != null
                      ? `${Number(socEvaluation.reference_soil_mass_t_ha).toFixed(2)} t/ha`
                      : "N/A"}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">Target depth: {socEvaluation.reference_depth_cm} cm</div>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">Total Area & Points</div>
                  <div className="text-lg font-bold text-white font-mono mt-0.5">
                    {socEvaluation.sample_point_results?.length || 0} pts
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">
                    {socEvaluation.total_area_ha != null ? `${Number(socEvaluation.total_area_ha).toFixed(1)} ha` : "Project AOI"}
                  </div>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">Carbon Invariant Status</div>
                  <div className="text-sm font-bold text-amber-400 font-mono mt-1">
                    {socEvaluation.carbon_accounting_status}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">tCO2e = null (Stock Only)</div>
                </div>
              </div>

              {/* Sample points breakdown in preview */}
              {socEvaluation.sample_point_results && socEvaluation.sample_point_results.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-slate-950 text-slate-400 font-mono text-[10px] uppercase border-b border-slate-800">
                      <tr>
                        <th className="p-2.5">Point Code</th>
                        <th className="p-2.5">Stratum</th>
                        <th className="p-2.5 text-right">Sampled Depth</th>
                        <th className="p-2.5 text-right">Fine Soil Mass</th>
                        <th className="p-2.5 text-right">Equiv Depth</th>
                        <th className="p-2.5 text-right">Normalized SOC Stock</th>
                        <th className="p-2.5 text-center">Depth Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {socEvaluation.sample_point_results.map((pt: any, idx: number) => (
                        <tr key={idx} className="hover:bg-slate-800/30">
                          <td className="p-2.5 text-white font-semibold">{pt.point_code || pt.sampling_point_id}</td>
                          <td className="p-2.5 text-slate-400">{pt.stratum_code || "Default Stratum"}</td>
                          <td className="p-2.5 text-right text-slate-300">{Number(pt.max_sampled_depth_cm).toFixed(1)} cm</td>
                          <td className="p-2.5 text-right text-slate-300">{Number(pt.total_sampled_mass_t_ha).toFixed(2)} t/ha</td>
                          <td className="p-2.5 text-right text-slate-300">
                            {pt.equivalent_depth_cm != null ? `${Number(pt.equivalent_depth_cm).toFixed(1)} cm` : "—"}
                          </td>
                          <td className="p-2.5 text-right text-emerald-400 font-bold">
                            {Number(pt.soc_stock_t_c_per_ha).toFixed(3)} t C/ha
                          </td>
                          <td className="p-2.5 text-center">
                            <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                              {pt.depth_sufficiency_status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Authoritative Persisted Stock Results List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Database className="w-4 h-4 text-emerald-400" />
                Persisted Authoritative SOC Stock Results ({socStockResults.length})
              </h3>
            </div>

            {socStockResults.length === 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-400 text-xs">
                No authoritative SOC stock results persisted yet. Select a locked prerequisite dossier and click
                "Calculate & Persist Authoritative Stock" to create an immutable result.
              </div>
            ) : (
              <div className="space-y-3">
                {socStockResults.map((stock) => (
                  <div
                    key={stock.id}
                    className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl p-4 transition space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800">
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-sm font-bold text-white">{stock.result_code}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                          {stock.measurement_period_type}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono">
                          {stock.aggregation_level}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                          {stock.result_status}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
                        <span>SHA: {stock.calculation_hash.substring(0, 14)}...</span>
                        <button
                          onClick={() => handleCopyHash(stock.calculation_hash)}
                          className="p-1 hover:text-white transition"
                          title="Copy Calculation Hash"
                        >
                          {copiedHash === stock.calculation_hash ? (
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                      <div className="bg-slate-950 p-2.5 rounded border border-slate-850">
                        <div className="text-[10px] text-slate-400 uppercase">ESM Normalized SOC Stock</div>
                        <div className="text-base font-bold text-emerald-400 mt-0.5">
                          {Number(stock.soc_stock_t_c_per_ha).toFixed(3)} t C/ha
                        </div>
                      </div>
                      <div className="bg-slate-950 p-2.5 rounded border border-slate-850">
                        <div className="text-[10px] text-slate-400 uppercase">Reference Soil Mass (M_ref)</div>
                        <div className="text-base font-bold text-white mt-0.5">
                          {Number(stock.reference_soil_mass_t_ha).toFixed(2)} t/ha
                        </div>
                      </div>
                      <div className="bg-slate-950 p-2.5 rounded border border-slate-850">
                        <div className="text-[10px] text-slate-400 uppercase">Reference / Equiv Depth</div>
                        <div className="text-base font-bold text-slate-300 mt-0.5">
                          {stock.reference_depth_cm} cm
                          {stock.equivalent_depth_cm ? ` (${Number(stock.equivalent_depth_cm).toFixed(1)} cm eq)` : ""}
                        </div>
                      </div>
                      <div className="bg-slate-950 p-2.5 rounded border border-slate-850">
                        <div className="text-[10px] text-slate-400 uppercase">Algorithm & Samples</div>
                        <div className="text-sm font-semibold text-slate-300 mt-0.5 truncate">
                          {stock.esm_algorithm === "ELLERT_BETTANY_1995" ? "Ellert & Bettany (1995)" : stock.esm_algorithm}
                        </div>
                        <div className="text-[10px] text-slate-500">{stock.sample_count} sample points</div>
                      </div>
                    </div>

                    {stock.notes && (
                      <div className="text-xs text-slate-400 italic">Notes: {stock.notes}</div>
                    )}

                    <div className="flex justify-end pt-2 border-t border-slate-800">
                      <button
                        onClick={() => handleSelectSocStockDetail(stock.id)}
                        className="flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 transition font-medium"
                      >
                        <Eye className="w-3.5 h-3.5" /> Inspect Component Profile & Layer Breakdown
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 9: Phase 3B-2 SOC Stock Change & Uncertainty Quantification */}
      {activeTab === "soc_change" && (
        <div className="space-y-6">
          {/* Prominent Scope Boundary & Carbon Invariant Banner */}
          <div className="bg-slate-900 border border-amber-500/40 rounded-xl p-5 shadow-lg relative overflow-hidden">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400 shrink-0 mt-0.5">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 uppercase tracking-wider font-mono">
                    Phase 3B-2 • VM0042 Section 8.5 &amp; 8.6 • Equations (46)-(47), (70)-(74)
                  </span>
                  <span className="text-xs text-slate-400 font-mono">C&amp;C 2026-06-11 QA2 Pathway</span>
                </div>
                <h3 className="text-base font-bold text-white tracking-tight">
                  VM0042 v2.2 Soil Organic Carbon Stock Change &amp; Uncertainty Deduction Engine
                </h3>
                <p className="text-xs text-amber-200/90 mt-1 leading-relaxed">
                  <strong>METHODOLOGY MAPPING &amp; SCOPE BOUNDARY:</strong> Phase 3B-2 authoritatively calculates
                  <strong> VM0042 Eq. (46)</strong> Baseline Scenario SOC Stock Change (ΔCO₂_soil_bsl,t) and
                  <strong> VM0042 Eq. (47)</strong> Project Scenario SOC Stock Change (ΔCO₂_soil_wp,t) in tCO₂e/yr via exact 44/12 conversion.
                  The <strong>QA2 Net SOC Comparative Effect</strong> evaluates (Project - Baseline).
                  Eq. (74) uncertainty deduction percentage (U%) applies directly with <strong>zero deadband</strong> (no 15% threshold)
                  and conservative sign indicator <em>I(ΔCO₂_soil,t)</em>.
                  <span className="text-white font-semibold ml-1">
                    Total Carbon Stock Change Eqs. (44) &amp; (45) are PARTIALLY_CONFIGURED_SOC_ONLY (Tree &amp; Shrub woody biomass pools out of scope).
                    Project net GHG accounting (Table 5 emissions, woody biomass, livestock, leakage, and buffer) is NOT CONFIGURED. Ledger minting remains BLOCKED_FOR_AGRICULTURE.
                  </span>
                </p>
              </div>
            </div>
          </div>

          {/* Configuration & Action Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
              <div>
                <h3 className="text-sm font-semibold text-white">Baseline vs. Monitoring Temporal Pairing Parameters</h3>
                <p className="text-xs text-slate-400">
                  Select baseline (T0) and monitoring (T1) stock results with a locked prerequisite dossier to compute ΔSOC and uncertainty.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleEvaluateSocChange}
                  disabled={actionLoading || !socChangeBaselineStockId || !socChangeMonitoringStockId}
                  className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition flex items-center gap-1.5 border border-slate-700"
                >
                  {actionLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Eye className="w-3.5 h-3.5" />}
                  Evaluate Preview
                </button>
              </div>
            </div>

            {error && (
              <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-center gap-2" data-testid="soc-change-error-alert">
                <AlertOctagon className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleFinalizeSocChange} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                {/* Baseline Stock Result */}
                <div>
                  <label className="block text-slate-400 font-medium mb-1">
                    Baseline Stock Result (t_start) <span className="text-rose-400">*</span>
                  </label>
                  <select
                    value={socChangeBaselineStockId}
                    onChange={(e) => setSocChangeBaselineStockId(e.target.value)}
                    required
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono text-xs focus:border-emerald-500 focus:outline-none"
                  >
                    {(() => {
                      const baselineOptions = socStockResults
                        .filter((s) => s.measurement_period_type === "BASELINE")
                        .sort((a, b) => (a.aggregation_level === "PROJECT" ? -1 : 1));
                      return baselineOptions.length === 0 ? (
                        <option value="">No baseline SOC stock results available</option>
                      ) : (
                        baselineOptions.map((s) => (
                          <option key={s.id} value={s.id}>
                            [{s.aggregation_level}] {s.result_code} — {Number(s.soc_stock_t_c_per_ha).toFixed(3)} t C/ha ({s.esm_algorithm})
                          </option>
                        ))
                      );
                    })()}
                  </select>
                  <div className="text-[10px] text-slate-500 mt-0.5">Authoritative T0 stock result</div>
                </div>

                {/* Monitoring Stock Result */}
                <div>
                  <label className="block text-slate-400 font-medium mb-1">
                    Monitoring Stock Result (t_final) <span className="text-rose-400">*</span>
                  </label>
                  <select
                    value={socChangeMonitoringStockId}
                    onChange={(e) => setSocChangeMonitoringStockId(e.target.value)}
                    required
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono text-xs focus:border-emerald-500 focus:outline-none"
                  >
                    {(() => {
                      const monitoringOptions = socStockResults
                        .filter((s) => s.measurement_period_type === "MONITORING")
                        .sort((a, b) => (a.aggregation_level === "PROJECT" ? -1 : 1));
                      return monitoringOptions.length === 0 ? (
                        <option value="">No monitoring SOC stock results available</option>
                      ) : (
                        monitoringOptions.map((s) => (
                          <option key={s.id} value={s.id}>
                            [{s.aggregation_level}] {s.result_code} — {Number(s.soc_stock_t_c_per_ha).toFixed(3)} t C/ha ({s.esm_algorithm})
                          </option>
                        ))
                      );
                    })()}
                  </select>
                  <div className="text-[10px] text-slate-500 mt-0.5">Authoritative T1 re-measurement result</div>
                </div>

                {/* Locked Prerequisite Dossier */}
                <div>
                  <label className="block text-slate-400 font-medium mb-1">
                    Locked Prerequisite Dossier <span className="text-rose-400">*</span>
                  </label>
                  <select
                    value={socChangePrereqId}
                    onChange={(e) => setSocChangePrereqId(e.target.value)}
                    required
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono text-xs focus:border-emerald-500 focus:outline-none"
                  >
                    {assessments.length === 0 ? (
                      <option value="">No locked prerequisite assessments available</option>
                    ) : (
                      assessments.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.assessment_code} ({a.status}) — {a.assessment_hash.substring(0, 12)}...
                        </option>
                      ))
                    )}
                  </select>
                  <div className="text-[10px] text-slate-500 mt-0.5">Freezes sampling design &amp; VCS rules</div>
                </div>

                {/* Laboratory Analytical Method */}
                <div>
                  <label className="block text-slate-400 font-medium mb-1">Analytical Laboratory Method</label>
                  <select
                    value={socChangeLabMethod}
                    onChange={(e) => setSocChangeLabMethod(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white text-xs focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="DRY_COMBUSTION">Conventional High-Temperature Dry Combustion (VM0042 Preferred)</option>
                    <option value="SPECTROSCOPY_WITH_DIRECT_CALIBRATION">Proximal Sensing / MIR / Vis-NIR Spectroscopy</option>
                    <option value="WET_COMBUSTION_WALKLEY_BLACK">Walkley-Black Acid Digestion (Legacy)</option>
                  </select>
                </div>

                {/* Lab QA & Proficiency Controls */}
                <div className="space-y-2">
                  <label className="block text-slate-400 font-medium">Measurement Error Routing &amp; QC</label>
                  <div className="space-y-1.5 pt-1">
                    <label className="flex items-center gap-2 cursor-pointer text-slate-300">
                      <input
                        type="checkbox"
                        checked={socChangeLabQa}
                        onChange={(e) => setSocChangeLabQa(e.target.checked)}
                        className="rounded bg-slate-950 border-slate-700 text-emerald-500 focus:ring-0 w-3.5 h-3.5"
                      />
                      <span>Laboratory QA/QC &amp; Reference Blanks Verified</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer text-slate-300">
                      <input
                        type="checkbox"
                        checked={socChangeLabProficiency}
                        onChange={(e) => setSocChangeLabProficiency(e.target.checked)}
                        className="rounded bg-slate-950 border-slate-700 text-emerald-500 focus:ring-0 w-3.5 h-3.5"
                      />
                      <span>Active Lab Proficiency Program Certificate on File</span>
                    </label>
                  </div>
                </div>

                {/* Auditor Notes */}
                <div>
                  <label className="block text-slate-400 font-medium mb-1">Auditor / Verifier Notes</label>
                  <input
                    type="text"
                    value={socChangeNotes}
                    onChange={(e) => setSocChangeNotes(e.target.value)}
                    placeholder="e.g., Authoritative QA2 ΔSOC &amp; Eq. (74) deduction"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-slate-800">
                <div className="text-xs text-slate-400">
                  {isFieldAgent ? (
                    <span className="text-amber-400 flex items-center gap-1 font-semibold">
                      <Lock className="w-3.5 h-3.5" /> Field Agents are restricted to preview only (Segregation of Duties).
                    </span>
                  ) : (
                    <span>Creates an immutable cryptographic record of ΔSOC, stoichiometric tCO₂e, and Eq. (74) deduction.</span>
                  )}
                </div>
                <button
                  type="submit"
                  disabled={
                    actionLoading ||
                    isFieldAgent ||
                    !socChangeBaselineStockId ||
                    !socChangeMonitoringStockId ||
                    !socChangePrereqId
                  }
                  className={`px-4 py-2 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                    isFieldAgent || !socChangeBaselineStockId || !socChangeMonitoringStockId || !socChangePrereqId
                      ? "bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700"
                      : "bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm"
                  }`}
                >
                  {actionLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Lock className="w-3.5 h-3.5" />}
                  Finalize &amp; Persist Authoritative ΔSOC
                </button>
              </div>
            </form>
          </div>

          {/* Real-time Preview Evaluation Card (if evaluated) */}
          {socChangeEvaluation && (
            <div className="bg-slate-900 border border-emerald-500/30 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-emerald-400" />
                  <h4 className="text-sm font-semibold text-white">ΔSOC &amp; Uncertainty Preview Evaluation</h4>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                      socChangeEvaluation.status === "EVALUATED"
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                    }`}
                  >
                    {socChangeEvaluation.status}
                  </span>
                </div>
                <div className="flex items-center gap-2 font-mono text-xs text-slate-400">
                  <span>SHA-256: {socChangeEvaluation.evaluation_hash.substring(0, 16)}...</span>
                  <button
                    onClick={() => handleCopyHash(socChangeEvaluation.evaluation_hash)}
                    className="p-1 hover:text-white transition"
                    title="Copy Evaluation Hash"
                  >
                    {copiedHash === socChangeEvaluation.evaluation_hash ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>

              {/* Blocking reasons banner if any */}
              {socChangeEvaluation.blocking_reasons && socChangeEvaluation.blocking_reasons.length > 0 && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs space-y-1">
                  <div className="font-semibold flex items-center gap-1.5 text-rose-400">
                    <AlertOctagon className="w-4 h-4" /> Quantification Evaluation Blocked:
                  </div>
                  {socChangeEvaluation.blocking_reasons.map((r, i) => (
                    <div key={i}>• {r}</div>
                  ))}
                </div>
              )}

              {/* Row 1 Metrics: Rates & Stoichiometry */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">Project SOC Change (Eq. 47)</div>
                  <div className="text-lg font-bold text-emerald-400 font-mono mt-0.5">
                    {Number(socChangeEvaluation.project_soc_change_tco2e_yr ?? 0).toFixed(2)} tCO₂e/yr
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">
                    Rate: {Number(socChangeEvaluation.delta_soc_project_t_c_ha_yr).toFixed(4)} t C/ha/yr
                  </div>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">Baseline SOC Change (Eq. 46)</div>
                  <div className="text-lg font-bold text-slate-300 font-mono mt-0.5">
                    {Number(socChangeEvaluation.baseline_soc_change_tco2e_yr ?? 0).toFixed(2)} tCO₂e/yr
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">
                    Rate: {Number(socChangeEvaluation.delta_soc_baseline_t_c_ha_yr).toFixed(4)} t C/ha/yr
                  </div>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">QA2 Net SOC Effect</div>
                  <div className={`text-lg font-bold font-mono mt-0.5 ${(Number(socChangeEvaluation.qa2_net_soc_effect_tco2e_yr ?? socChangeEvaluation.total_net_delta_co2_tco2e_yr ?? 0) >= 0) ? "text-emerald-400" : "text-rose-400"}`}>
                    {Number(socChangeEvaluation.qa2_net_soc_effect_tco2e_yr ?? socChangeEvaluation.total_net_delta_co2_tco2e_yr ?? 0).toFixed(2)} tCO₂e/yr
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">Project minus Baseline (QA2)</div>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">Sign Indicator I(ΔCO₂)</div>
                  <div className="text-lg font-bold text-indigo-400 font-mono mt-0.5">
                    I = {socChangeEvaluation.sign_indicator != null ? (socChangeEvaluation.sign_indicator >= 0 ? "+1" : "-1") : "+1"}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">Conservative Eq. 44/45 factor</div>
                </div>
              </div>

              {/* Row 2 Metrics: Totals, Uncertainty & Deductions */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">Sampling Uncertainty (U%)</div>
                  <div className="text-lg font-bold text-amber-400 font-mono mt-0.5">
                    {Number(socChangeEvaluation.relative_uncertainty_pct).toFixed(2)}%
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">
                    t_0.667: {Number(socChangeEvaluation.student_t_value_0667).toFixed(4)} (df: {socChangeEvaluation.degrees_of_freedom})
                  </div>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">Eq. (74) Deduction (0% Deadband)</div>
                  <div className="text-lg font-bold text-rose-400 font-mono mt-0.5">
                    {Number(socChangeEvaluation.uncertainty_deduction_pct).toFixed(2)}%
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">Exact Eq. 74 deduction</div>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">Uncertainty-Adjusted Net Effect</div>
                  <div className={`text-lg font-bold font-mono mt-0.5 ${(Number(socChangeEvaluation.uncertainty_adjusted_soc_effect_tco2e_yr ?? socChangeEvaluation.adjusted_net_delta_co2_tco2e_yr ?? 0) >= 0) ? "text-emerald-400" : "text-rose-400"}`}>
                    {Number(socChangeEvaluation.uncertainty_adjusted_soc_effect_tco2e_yr ?? socChangeEvaluation.adjusted_net_delta_co2_tco2e_yr ?? 0).toFixed(2)} tCO₂e/yr
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">Adjusted net SOC effect</div>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">Eq. 44/45 Status</div>
                  <div className="text-xs font-bold text-amber-300 font-mono mt-1 truncate">
                    {socChangeEvaluation.eq44_eq45_status || "PARTIALLY_CONFIGURED_SOC_ONLY"}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">Woody pools out of scope</div>
                </div>
              </div>

              {/* Strata Breakdown Table if present */}
              {socChangeEvaluation.strata_results && socChangeEvaluation.strata_results.length > 0 && (
                <div>
                  <h5 className="text-xs font-semibold text-slate-300 mb-2">Stratified Sampling Analysis (VM0042 Eq. 70 & 71)</h5>
                  <div className="overflow-x-auto border border-slate-800 rounded-lg">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-slate-950 text-slate-400 font-mono text-[10px] uppercase border-b border-slate-800">
                        <tr>
                          <th className="p-2.5">Stratum Code</th>
                          <th className="p-2.5 text-right">Area (ha)</th>
                          <th className="p-2.5 text-right">Area Weight (w_k)</th>
                          <th className="p-2.5 text-right">Baseline SOC (t C/ha)</th>
                          <th className="p-2.5 text-right">Monitoring SOC (t C/ha)</th>
                          <th className="p-2.5 text-right">Net ΔSOC (t C/ha/yr)</th>
                          <th className="p-2.5 text-right">Stratum Variance</th>
                          <th className="p-2.5 text-right">Gross tCO₂e/yr</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {socChangeEvaluation.strata_results.map((st: any, idx: number) => (
                          <tr key={idx} className="hover:bg-slate-800/30">
                            <td className="p-2.5 text-white font-semibold">{st.stratum_code}</td>
                            <td className="p-2.5 text-right text-slate-300">{Number(st.stratum_area_ha).toFixed(1)} ha</td>
                            <td className="p-2.5 text-right text-slate-400">{Number(st.area_weight).toFixed(4)}</td>
                            <td className="p-2.5 text-right text-slate-300">{Number(st.baseline_mean_soc_t_c_per_ha).toFixed(3)}</td>
                            <td className="p-2.5 text-right text-slate-300">{Number(st.monitoring_mean_soc_t_c_per_ha).toFixed(3)}</td>
                            <td className="p-2.5 text-right text-emerald-400 font-bold">
                              {Number(st.delta_soc_net_t_c_ha_yr).toFixed(4)}
                            </td>
                            <td className="p-2.5 text-right text-slate-400">
                              {st.stratum_variance != null ? Number(st.stratum_variance).toExponential(4) : "—"}
                            </td>
                            <td className="p-2.5 text-right text-emerald-400 font-bold">
                              {Number(st.stratum_total_net_delta_co2_tco2e_yr).toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Persisted Authoritative SOC Stock Change Results List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Database className="w-4 h-4 text-emerald-400" />
                Persisted Authoritative SOC Stock Change Results ({socChangeResults.length})
              </h3>
            </div>

            {socChangeResults.length === 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-400 text-xs">
                No authoritative SOC stock change results persisted yet. Select baseline and monitoring SOC stock results,
                verify laboratory QA and prerequisite dossiers, and click &quot;Finalize &amp; Persist Authoritative ΔSOC&quot;.
              </div>
            ) : (
              <div className="space-y-3">
                {socChangeResults.map((result) => (
                  <div
                    key={result.id}
                    className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl p-4 transition space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800">
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-sm font-bold text-white">{result.result_code}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                          {result.quantification_approach}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono">
                          VM0042 v{result.methodology_version}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                          {result.result_status}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
                        <span>SHA: {result.calculation_hash.substring(0, 14)}...</span>
                        <button
                          onClick={() => handleCopyHash(result.calculation_hash)}
                          className="p-1 hover:text-white transition"
                          title="Copy Calculation Hash"
                        >
                          {copiedHash === result.calculation_hash ? (
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 font-mono text-xs">
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Temporal Pairing</div>
                        <div className="text-white font-semibold mt-0.5">
                          {result.t_start?.substring(0, 10)} → {result.t_final?.substring(0, 10)}
                        </div>
                        <div className="text-[10px] text-slate-500">{Number(result.elapsed_years).toFixed(2)} years</div>
                      </div>

                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Project (Eq. 47) / Bsl (Eq. 46)</div>
                        <div className="text-white font-semibold mt-0.5">
                          {Number(result.project_soc_change_tco2e_yr ?? result.total_project_delta_co2_tco2e_yr ?? 0).toFixed(1)} / {Number(result.baseline_soc_change_tco2e_yr ?? result.total_baseline_delta_co2_tco2e_yr ?? 0).toFixed(1)}
                        </div>
                        <div className="text-[10px] text-slate-500">tCO₂e/yr</div>
                      </div>

                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">QA2 Net SOC Effect</div>
                        <div className={`font-bold mt-0.5 ${(Number(result.qa2_net_soc_effect_tco2e_yr ?? result.total_net_delta_co2_tco2e_yr ?? 0) >= 0) ? "text-emerald-400" : "text-rose-400"}`}>
                          {Number(result.qa2_net_soc_effect_tco2e_yr ?? result.total_net_delta_co2_tco2e_yr ?? 0).toFixed(2)} tCO₂e/yr
                        </div>
                        <div className="text-[10px] text-slate-500">Project - Baseline (QA2)</div>
                      </div>

                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Eq. 74 Deduction</div>
                        <div className="text-amber-400 font-bold mt-0.5">
                          {Number(result.uncertainty_deduction_pct).toFixed(2)}%
                        </div>
                        <div className="text-[10px] text-slate-500">U%: {Number(result.relative_uncertainty_pct).toFixed(2)}% (0% deadband)</div>
                      </div>

                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Adjusted Net SOC Effect</div>
                        <div className={`font-bold mt-0.5 ${(Number(result.uncertainty_adjusted_soc_effect_tco2e_yr ?? result.adjusted_net_delta_co2_tco2e_yr ?? 0) >= 0) ? "text-emerald-400" : "text-rose-400"}`}>
                          {Number(result.uncertainty_adjusted_soc_effect_tco2e_yr ?? result.adjusted_net_delta_co2_tco2e_yr ?? 0).toFixed(2)} tCO₂e/yr
                        </div>
                        <div className="text-[10px] text-slate-500">I = {(result.sign_indicator ?? 1) >= 0 ? "+1" : "-1"}</div>
                      </div>
                    </div>

                    {result.notes && <div className="text-xs text-slate-400 italic">Notes: {result.notes}</div>}

                    <div className="flex justify-end pt-2 border-t border-slate-800">
                      <button
                        onClick={() => handleSelectSocChangeDetail(result.id)}
                        className="flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 transition font-medium"
                      >
                        <Eye className="w-3.5 h-3.5" /> Inspect Full Lineage &amp; VM0042 Uncertainty Breakdown
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 10: Phase 3B-3 Net GHG Reductions & Removals + Section 8.7 VCU Readiness */}
      {activeTab === "net_ghg" && (
        <div className="space-y-6">
          {/* Prominent Scope Boundary & Carbon Invariant Banner */}
          <div className="bg-slate-900 border border-emerald-500/40 rounded-xl p-5 shadow-lg relative overflow-hidden">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400 shrink-0 mt-0.5">
                <Scale className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-base font-bold text-white">
                    VM0042 v2.2 Net GHG Reductions &amp; Removals (Eqs. 37–43) + Section 8.7 VCU Readiness
                  </h3>
                  <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                    21 OCT 2025 + C&amp;C 11 JUN 2026
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-mono">
                    INTERNAL VCU READINESS ONLY
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Synthesizes component-level soil organic carbon stock changes, Table 5 baseline and project emission sources,
                  woody biomass pools, and production-decline leakage into gross reductions, gross removals, and net benefits (Eqs. 37–43).
                  Where NPR non-permanence risk buffers are configured, evaluates Section 8.7 internal VCU-readiness deductions (Eqs. 75–79).
                </p>
                <div className="pt-2 flex flex-wrap gap-2 text-[11px] font-mono text-slate-400">
                  <span className="px-2 py-0.5 bg-slate-950 rounded border border-slate-800 text-emerald-400">
                    Gross ER: Eq. 37
                  </span>
                  <span className="px-2 py-0.5 bg-slate-950 rounded border border-slate-800 text-emerald-300">
                    Net ER: Eq. 38
                  </span>
                  <span className="px-2 py-0.5 bg-slate-950 rounded border border-slate-800 text-amber-400">
                    Leakage ER: Eq. 39
                  </span>
                  <span className="px-2 py-0.5 bg-slate-950 rounded border border-slate-800 text-teal-400">
                    Gross CR: Eq. 40
                  </span>
                  <span className="px-2 py-0.5 bg-slate-950 rounded border border-slate-800 text-teal-300">
                    Net CR: Eq. 41
                  </span>
                  <span className="px-2 py-0.5 bg-slate-950 rounded border border-slate-800 text-amber-300">
                    Leakage CR: Eq. 42
                  </span>
                  <span className="px-2 py-0.5 bg-slate-950 rounded border border-slate-800 text-emerald-200 font-bold">
                    Total ERRNET: Eq. 43
                  </span>
                  <span className="px-2 py-0.5 bg-slate-950 rounded border border-slate-800 text-amber-300">
                    Buffer Deductions: Eqs. 75–76
                  </span>
                  <span className="px-2 py-0.5 bg-slate-950 rounded border border-slate-800 text-indigo-300">
                    Internal VCU: Eqs. 77–79
                  </span>
                  <span className="px-2 py-0.5 bg-slate-950 rounded border border-emerald-500/30 text-emerald-300">
                    Eq. 37 Literal Branches: min(0,Δwp)-min(0,Δbsl) (I=1)
                  </span>
                  <span className="px-2 py-0.5 bg-slate-950 rounded border border-rose-500/30 text-rose-300">
                    Eq. 75: No Outer Zero-Clamp
                  </span>
                  <span className="px-2 py-0.5 bg-slate-950 rounded border border-indigo-500/30 text-indigo-300">
                    VMD0054: v1.1 Active Standard / v1.0 Transition
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Configuration & Action Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <h4 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-emerald-400" />
              Configure &amp; Evaluate Net GHG Verification Period
            </h4>

            <form onSubmit={handleFinalizeNetGhg} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
                {/* Prerequisite Dossier Selection */}
                <div>
                  <label className="block text-slate-400 mb-1 font-medium">
                    Prerequisite Assessment Dossier <span className="text-emerald-400">*</span>
                  </label>
                  <select
                    value={selectedPrereqForNetGhg}
                    onChange={(e) => setSelectedPrereqForNetGhg(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono text-xs focus:border-emerald-500 focus:outline-none"
                    required
                  >
                    <option value="">Select locked prerequisite dossier...</option>
                    {assessments.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.assessment_code} (v{a.version}) — {a.rule_set_version}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Phase 3B-2 SOC Change Result Selection */}
                <div>
                  <label className="block text-slate-400 mb-1 font-medium">
                    Phase 3B-2 SOC Stock Change Result (Optional / QA2)
                  </label>
                  <select
                    value={selectedSocChangeForNetGhg}
                    onChange={(e) => setSelectedSocChangeForNetGhg(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono text-xs focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="">None (Fossil fuel / Emission sources only)</option>
                    {socChangeResults.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.result_code} (Net: {Number(s.uncertainty_adjusted_soc_effect_tco2e_yr ?? s.adjusted_net_delta_co2_tco2e_yr ?? 0).toFixed(2)} tCO₂e/yr)
                      </option>
                    ))}
                  </select>
                </div>

                {/* Verification Period Start Date */}
                <div>
                  <label className="block text-slate-400 mb-1 font-medium">
                    Verification Period Start <span className="text-emerald-400">*</span>
                  </label>
                  <input
                    type="date"
                    value={netGhgStartDate}
                    onChange={(e) => setNetGhgStartDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white font-mono text-xs focus:border-emerald-500 focus:outline-none"
                    required
                  />
                </div>

                {/* Verification Period End Date */}
                <div>
                  <label className="block text-slate-400 mb-1 font-medium">
                    Verification Period End <span className="text-emerald-400">*</span>
                  </label>
                  <input
                    type="date"
                    value={netGhgEndDate}
                    onChange={(e) => setNetGhgEndDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white font-mono text-xs focus:border-emerald-500 focus:outline-none"
                    required
                  />
                </div>
              </div>

              {/* Activity Data & Parameters Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3 pt-2 text-xs">
                <div>
                  <label className="block text-slate-400 mb-1 font-medium">
                    Baseline Fossil Fuel (Liters)
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={netGhgFossilBsl}
                    onChange={(e) => setNetGhgFossilBsl(e.target.value)}
                    placeholder="40000"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white font-mono text-xs"
                  />
                  <span className="text-[10px] text-slate-500 mt-0.5 block">Default: 40,000 L</span>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1 font-medium">
                    Project Fossil Fuel (Liters)
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={netGhgFossilWp}
                    onChange={(e) => setNetGhgFossilWp(e.target.value)}
                    placeholder="20000"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white font-mono text-xs"
                  />
                  <span className="text-[10px] text-slate-500 mt-0.5 block">Default: 20,000 L</span>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1 font-medium">
                    Fossil Emission Factor (tCO₂e/L)
                  </label>
                  <input
                    type="number"
                    step="0.0001"
                    value={netGhgFossilEf}
                    onChange={(e) => setNetGhgFossilEf(e.target.value)}
                    placeholder="0.001"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white font-mono text-xs"
                  />
                  <span className="text-[10px] text-slate-500 mt-0.5 block">Authoritative EF</span>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1 font-medium">
                    C&amp;C Production Leakage (tCO₂e/yr)
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={netGhgLeakageDecline}
                    onChange={(e) => setNetGhgLeakageDecline(e.target.value)}
                    placeholder="2.0"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white font-mono text-xs"
                  />
                  <span className="text-[10px] text-slate-500 mt-0.5 block">VMD0054 / TOOL16</span>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1 font-medium">
                    NPR Buffer Rating (%)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={netGhgNprRating}
                    onChange={(e) => setNetGhgNprRating(e.target.value)}
                    placeholder="15.0"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-amber-300 font-mono text-xs"
                  />
                  <span className="text-[10px] text-slate-500 mt-0.5 block">Sec 8.7 Buffer (e.g. 15%)</span>
                </div>
              </div>

              {/* Notes */}
              <div>
                <label className="block text-slate-400 mb-1 font-medium text-xs">
                  Auditor / Verifier Notes &amp; Lineage Justification
                </label>
                <input
                  type="text"
                  value={netGhgNotes}
                  onChange={(e) => setNetGhgNotes(e.target.value)}
                  placeholder="e.g., Annual verification cycle for VM0042 crediting period 2023-2024 with QA2 SOC and conservative leakage."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white text-xs"
                />
              </div>

              {/* Segregation of Duties Notice */}
              {isFieldAgent && (
                <div className="bg-rose-500/10 border border-rose-500/30 p-3 rounded-lg text-rose-300 text-xs flex items-center gap-2">
                  <AlertOctagon className="w-4 h-4 shrink-0" />
                  <span>
                    <strong>Segregation of Duties Enforcement:</strong> Field Agents can preview calculations but are strictly blocked from finalizing authoritative Net GHG records.
                  </span>
                </div>
              )}

              {/* Actions */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={handleEvaluateNetGhg}
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-emerald-400 font-semibold text-xs transition flex items-center gap-2 border border-slate-700"
                >
                  {actionLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Eye className="w-3.5 h-3.5" />}
                  Evaluate Net GHG Preview
                </button>

                <button
                  type="submit"
                  disabled={actionLoading || isFieldAgent}
                  className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition flex items-center gap-2 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {actionLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                  Finalize &amp; Persist Authoritative Net GHG (Eqs. 37–43)
                </button>
              </div>
            </form>
          </div>

          {/* Evaluation Preview Panel */}
          {netGhgEvaluation && (
            <div className="bg-slate-900 border border-emerald-500/30 rounded-xl p-5 shadow-xl space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800">
                <div>
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-emerald-400" />
                    Preview: VM0042 v2.2 Net GHG Reductions &amp; Removals Evaluation
                  </h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Period: {netGhgEvaluation.verification_period_start} to {netGhgEvaluation.verification_period_end} ({Number(netGhgEvaluation.elapsed_years).toFixed(2)} years)
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2.5 py-1 rounded text-xs font-bold font-mono ${netGhgEvaluation.status === "EVALUATED" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-rose-500/20 text-rose-400 border border-rose-500/30"}`}>
                    STATUS: {netGhgEvaluation.status}
                  </span>
                  <span className="px-2.5 py-1 rounded text-xs font-bold font-mono bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                    VCU READINESS: {netGhgEvaluation.vcu_readiness_status}
                  </span>
                </div>
              </div>

              {/* Table 5 Applicability Router Summary */}
              <div>
                <h5 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 font-mono flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-emerald-400" />
                  Table 5 Applicability Router Status
                </h5>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
                  {Object.entries(netGhgEvaluation.applicability_matrix || {}).map(([srcKey, srcVal]: [string, any]) => (
                    <div key={srcKey} className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-[10px]">
                      <div className="text-slate-400 font-mono font-bold truncate">{srcKey}</div>
                      <div className="mt-1">
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono ${
                          srcVal.status === "APPLICABLE_CONFIGURED" ? "bg-emerald-500/20 text-emerald-300" :
                          srcVal.status === "VERIFIED_ACTIVITY_ZERO" ? "bg-slate-800 text-slate-300" :
                          srcVal.status === "NOT_APPLICABLE" ? "bg-slate-800 text-slate-400" :
                          "bg-rose-500/20 text-rose-300"
                        }`}>
                          {srcVal.status}
                        </span>
                      </div>
                      <div className="text-slate-500 mt-1 truncate">
                        {srcVal.quantification_approach || "QA3"}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Core Equations 37–43 Metrics Cards */}
              <div>
                <h5 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 font-mono flex items-center gap-1.5">
                  <Scale className="w-3.5 h-3.5 text-emerald-400" />
                  Core GHG Quantification (Equations 37–43)
                </h5>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <div className="text-[10px] text-slate-400 uppercase">Gross ER (Eq. 37)</div>
                    <div className="text-base font-bold text-emerald-400 font-mono mt-0.5">
                      {Number(netGhgEvaluation.gross_reductions_er_tco2e ?? 0).toFixed(2)}
                    </div>
                    <div className="text-[10px] text-slate-500">tCO₂e (gross)</div>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <div className="text-[10px] text-slate-400 uppercase">Net ER (Eq. 38)</div>
                    <div className="text-base font-bold text-emerald-300 font-mono mt-0.5">
                      {Number(netGhgEvaluation.net_reductions_ernet_tco2e ?? 0).toFixed(2)}
                    </div>
                    <div className="text-[10px] text-slate-500">tCO₂e (net)</div>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <div className="text-[10px] text-slate-400 uppercase">Leakage ER (Eq. 39)</div>
                    <div className="text-base font-bold text-amber-400 font-mono mt-0.5">
                      {Number(netGhgEvaluation.leakage_allocation_er_lker_tco2e ?? 0).toFixed(2)}
                    </div>
                    <div className="text-[10px] text-slate-500">tCO₂e (allocated)</div>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <div className="text-[10px] text-slate-400 uppercase">Gross CR (Eq. 40)</div>
                    <div className="text-base font-bold text-teal-400 font-mono mt-0.5">
                      {Number(netGhgEvaluation.gross_removals_cr_tco2e ?? 0).toFixed(2)}
                    </div>
                    <div className="text-[10px] text-slate-500">tCO₂e (gross)</div>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <div className="text-[10px] text-slate-400 uppercase">Net CR (Eq. 41)</div>
                    <div className="text-base font-bold text-teal-300 font-mono mt-0.5">
                      {Number(netGhgEvaluation.net_removals_crnet_tco2e ?? 0).toFixed(2)}
                    </div>
                    <div className="text-[10px] text-slate-500">tCO₂e (net)</div>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <div className="text-[10px] text-slate-400 uppercase">Leakage CR (Eq. 42)</div>
                    <div className="text-base font-bold text-amber-400 font-mono mt-0.5">
                      {Number(netGhgEvaluation.leakage_allocation_cr_lkcr_tco2e ?? 0).toFixed(2)}
                    </div>
                    <div className="text-[10px] text-slate-500">tCO₂e (allocated)</div>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-lg border border-emerald-500/40">
                    <div className="text-[10px] text-emerald-400 uppercase font-bold">Total ERRNET (Eq. 43)</div>
                    <div className="text-base font-bold text-emerald-300 font-mono mt-0.5">
                      {Number(netGhgEvaluation.total_net_ghg_errnet_tco2e ?? 0).toFixed(2)}
                    </div>
                    <div className="text-[10px] text-slate-400">Total Net tCO₂e</div>
                  </div>
                </div>
              </div>

              {/* Section 8.7 VCU Readiness Panel */}
              <div className="bg-slate-950 p-4 rounded-xl border border-indigo-500/30 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-indigo-400" />
                    <h5 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                      Section 8.7 Internal VCU Readiness Calculation
                    </h5>
                  </div>
                  <div className="text-xs text-slate-400 font-mono">
                    NPR Rating: <strong className="text-amber-300">{netGhgEvaluation.npr_rating_pct != null ? `${Number(netGhgEvaluation.npr_rating_pct).toFixed(2)}%` : "NOT_CONFIGURED"}</strong>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                  <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                    <div className="text-[10px] text-slate-400 uppercase">Buffer ER (Eq. 75)</div>
                    <div className="text-sm font-bold text-rose-400 font-mono mt-0.5">
                      {netGhgEvaluation.buffer_deduction_reductions_tco2e != null ? `${Number(netGhgEvaluation.buffer_deduction_reductions_tco2e).toFixed(2)} tCO₂e` : "N/A"}
                    </div>
                  </div>

                  <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                    <div className="text-[10px] text-slate-400 uppercase">Buffer CR (Eq. 76)</div>
                    <div className="text-sm font-bold text-rose-400 font-mono mt-0.5">
                      {netGhgEvaluation.buffer_deduction_removals_tco2e != null ? `${Number(netGhgEvaluation.buffer_deduction_removals_tco2e).toFixed(2)} tCO₂e` : "N/A"}
                    </div>
                  </div>

                  <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                    <div className="text-[10px] text-slate-400 uppercase">VCU Eligible ER (Eq. 77)</div>
                    <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">
                      {netGhgEvaluation.internal_vcu_eligible_reductions_tco2e != null ? `${Number(netGhgEvaluation.internal_vcu_eligible_reductions_tco2e).toFixed(2)} VCUs` : "N/A"}
                    </div>
                  </div>

                  <div className="bg-slate-900 p-2.5 rounded-lg border border-indigo-500/40">
                    <div className="text-[10px] text-indigo-300 uppercase font-bold">Total VCU Eligible (Eq. 79)</div>
                    <div className="text-sm font-bold text-indigo-200 font-mono mt-0.5">
                      {netGhgEvaluation.internal_vcu_eligible_total_tco2e != null ? `${Number(netGhgEvaluation.internal_vcu_eligible_total_tco2e).toFixed(2)} VCUs` : "N/A"}
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 pt-2 text-[11px] text-slate-400 font-mono border-t border-slate-800/60">
                  <span>• Internal MRV Status: <strong className="text-emerald-400">CALCULATED</strong></span>
                  <span>• VVB Status: <strong className="text-slate-400">NOT_CONFIGURED / EXTERNAL</strong></span>
                  <span>• Registry Status: <strong className="text-slate-400">NOT_CONFIGURED / EXTERNAL</strong></span>
                </div>
              </div>

              {/* Multi-Year Annual Vintage Breakdown Table */}
              {netGhgEvaluation.vintages && netGhgEvaluation.vintages.length > 0 && (
                <div>
                  <h5 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 font-mono flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-emerald-400" />
                    Annual Vintage Breakdown Table
                  </h5>
                  <div className="overflow-x-auto border border-slate-800 rounded-lg">
                    <table className="w-full text-[11px] text-left">
                      <thead className="bg-slate-950 text-slate-400 uppercase text-[9px] border-b border-slate-800">
                        <tr>
                          <th className="p-2">Vintage</th>
                          <th className="p-2 text-right">Gross ER (tCO₂e)</th>
                          <th className="p-2 text-right">Gross CR (tCO₂e)</th>
                          <th className="p-2 text-right">Leakage (tCO₂e)</th>
                          <th className="p-2 text-right">Net ER (tCO₂e)</th>
                          <th className="p-2 text-right">Net CR (tCO₂e)</th>
                          <th className="p-2 text-right text-emerald-400">ERRNET (tCO₂e)</th>
                          <th className="p-2 text-right text-indigo-400">VCU Eligible</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800">
                        {netGhgEvaluation.vintages.map((v: any, vIdx: number) => {
                          const nFmt = (val: any) => { const num = Number(val); return Number.isFinite(num) ? num.toFixed(2) : "0.00"; };
                          return (
                            <tr key={vIdx} className="hover:bg-slate-800/40">
                              <td className="p-2 font-bold text-white font-mono">{v.vintage_year}</td>
                              <td className="p-2 text-right text-slate-300 font-mono">{nFmt(v.gross_reductions_er_tco2e)}</td>
                              <td className="p-2 text-right text-slate-300 font-mono">{nFmt(v.gross_removals_cr_tco2e)}</td>
                              <td className="p-2 text-right text-amber-400 font-mono">{nFmt(v.leakage_tco2e)}</td>
                              <td className="p-2 text-right text-slate-200 font-mono">{nFmt(v.net_reductions_ernet_tco2e)}</td>
                              <td className="p-2 text-right text-slate-200 font-mono">{nFmt(v.net_removals_crnet_tco2e)}</td>
                              <td className="p-2 text-right text-emerald-400 font-bold font-mono">{nFmt(v.total_net_ghg_errnet_tco2e)}</td>
                              <td className="p-2 text-right text-indigo-300 font-mono">
                                {v.internal_vcu_eligible_total_tco2e != null ? nFmt(v.internal_vcu_eligible_total_tco2e) : "—"}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Authoritative Standards & Equation Governance */}
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-[11px] font-mono space-y-1">
                <div className="text-slate-400 font-sans font-semibold">Authoritative Standards &amp; Equation Governance:</div>
                <div className="text-slate-300">
                  • VM0042 Eq. 37: <span className="text-emerald-400">ER_t = ΔE_sources + [min(0,ΔCO2_wp) - min(0,ΔCO2_bsl)] if I=1 else [min-min + max-max] (No Outer Clamp)</span>
                </div>
                <div className="text-slate-300">
                  • VM0042 Eq. 75: <span className="text-rose-400">BuER,t = NPR% × [min(0,ΔCO2_wp) - min(0,ΔCO2_bsl)] (No Outer Zero-Clamp)</span>
                </div>
                <div className="text-slate-300">
                  • VMD0054 Resolution: <span className="text-indigo-400">{netGhgEvaluation.component_breakdown?.vmd0054_version || "VMD0054_1_1_CURRENT"} ({netGhgEvaluation.component_breakdown?.vmd0054_source_equation || "VMD0054_V1.1_EQ13"})</span>
                </div>
              </div>

              {/* Cryptographic Evaluation Hash */}
              <div className="text-[10px] text-slate-500 font-mono flex items-center justify-between border-t border-slate-800 pt-2">
                <span>Deterministic Evaluation Hash: {netGhgEvaluation.evaluation_hash}</span>
                <span className="text-slate-400">SHA-256 Provenance Active</span>
              </div>
            </div>
          )}

          {/* Historical Authoritative Finalized Results List */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  <FileCheck className="w-4 h-4 text-emerald-400" />
                  Authoritative Net GHG &amp; VCU Readiness Records
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Immutable, cryptographically anchored Net GHG evaluations for VeriField agriculture projects.
                </p>
              </div>
              <span className="text-xs px-2.5 py-1 rounded bg-slate-800 text-slate-300 font-mono">
                {netGhgResults.length} Record{netGhgResults.length === 1 ? "" : "s"}
              </span>
            </div>

            {netGhgResults.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-lg">
                No authoritative Net GHG records finalized yet. Configure project parameters above, preview results,
                and click &quot;Finalize &amp; Persist Authoritative Net GHG&quot;.
              </div>
            ) : (
              <div className="space-y-3">
                {netGhgResults.map((r) => {
                  const nFmt = (val: any) => { const num = Number(val); return Number.isFinite(num) ? num.toFixed(2) : "0.00"; };
                  return (
                    <div
                      key={r.id}
                      className="bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl p-4 transition space-y-3"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800">
                        <div>
                          <div className="text-sm font-bold text-white font-mono flex items-center gap-2">
                            <span>{r.result_code}</span>
                            <span className="text-xs font-normal text-slate-400">
                              ({new Date(r.verification_period_start).toLocaleDateString()} to {new Date(r.verification_period_end).toLocaleDateString()})
                            </span>
                          </div>
                          <div className="text-[11px] text-slate-500 mt-0.5">
                            Methodology: {r.methodology_version} • Ruleset: {r.ruleset_version} • Elapsed: {nFmt(r.elapsed_years)} yrs
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            {r.result_status}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/20 text-indigo-400 border border-indigo-500/20">
                            VCU: {r.vcu_readiness_status}
                          </span>
                        </div>
                      </div>

                      {/* Summary Metrics */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase">Net Reductions (Eq. 38)</div>
                          <div className="text-white font-semibold font-mono mt-0.5">
                            {nFmt(r.net_reductions_ernet_tco2e)} tCO₂e
                          </div>
                        </div>

                        <div>
                          <div className="text-[10px] text-slate-500 uppercase">Net Removals (Eq. 41)</div>
                          <div className="text-white font-semibold font-mono mt-0.5">
                            {nFmt(r.net_removals_crnet_tco2e)} tCO₂e
                          </div>
                        </div>

                        <div>
                          <div className="text-[10px] text-slate-500 uppercase">Total Net Benefit (Eq. 43)</div>
                          <div className="text-emerald-400 font-bold font-mono mt-0.5">
                            {nFmt(r.total_net_ghg_errnet_tco2e)} tCO₂e
                          </div>
                        </div>

                        <div>
                          <div className="text-[10px] text-slate-500 uppercase">Internal VCU Eligible (Eq. 79)</div>
                          <div className="text-indigo-300 font-bold font-mono mt-0.5">
                            {r.internal_vcu_eligible_total_tco2e != null ? `${nFmt(r.internal_vcu_eligible_total_tco2e)} VCUs` : "—"}
                          </div>
                        </div>
                      </div>

                      {r.notes && <div className="text-xs text-slate-400 italic">Notes: {r.notes}</div>}

                      <div className="flex justify-between items-center pt-2 border-t border-slate-800">
                        <div className="text-[10px] text-slate-500 font-mono truncate max-w-md">
                          Hash: {r.calculation_hash}
                        </div>
                        <button
                          onClick={() => handleSelectNetGhgDetail(r.id)}
                          className="flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 transition font-medium"
                        >
                          <Eye className="w-3.5 h-3.5" /> Inspect Full Lineage &amp; VCU Deductions
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Inspect SOC Stock Detail Modal */}
      {selectedSocStock && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                  <span>{selectedSocStock.result_code}</span>
                  <span className="text-xs font-normal text-slate-400">({selectedSocStock.measurement_period_type})</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  ESM Algorithm: {selectedSocStock.esm_algorithm} • Reference Mass: {Number(selectedSocStock.reference_soil_mass_t_ha).toFixed(2)} t/ha
                </p>
              </div>
              <button
                onClick={() => setSelectedSocStock(null)}
                className="text-slate-400 hover:text-white text-xs px-2.5 py-1 rounded bg-slate-800 transition"
              >
                Close
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4 text-xs font-mono">
              {/* Component breakdown summary */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950 p-3 rounded-lg border border-slate-800">
                <div>
                  <div className="text-[10px] text-slate-400 uppercase">Normalized SOC Stock</div>
                  <div className="text-base font-bold text-emerald-400">
                    {Number(selectedSocStock.soc_stock_t_c_per_ha).toFixed(3)} t C/ha
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 uppercase">Unadjusted Stock</div>
                  <div className="text-base font-bold text-slate-300">
                    {selectedSocStock.unadjusted_stock_t_c_per_ha != null
                      ? `${Number(selectedSocStock.unadjusted_stock_t_c_per_ha).toFixed(3)} t C/ha`
                      : "—"}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 uppercase">Depth Status</div>
                  <div className="text-sm font-semibold text-white">
                    {selectedSocStock.depth_sufficiency_status}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 uppercase">Carbon Invariant</div>
                  <div className="text-sm font-bold text-amber-400">NOT_CONFIGURED</div>
                </div>
              </div>

              {/* Layer breakdown table if present */}
              {selectedSocStock.layers && selectedSocStock.layers.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold text-slate-300 mb-2 font-sans flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-emerald-400" />
                    Layer-by-Layer Fine Soil Mass & SOC Arithmetic
                  </h4>
                  <div className="overflow-x-auto border border-slate-800 rounded-lg">
                    <table className="w-full text-[11px] text-left">
                      <thead className="bg-slate-950 text-slate-400 uppercase text-[9px] border-b border-slate-800">
                        <tr>
                          <th className="p-2">Layer</th>
                          <th className="p-2 text-right">Depth (cm)</th>
                          <th className="p-2 text-right">Bulk Density (g/cm³)</th>
                          <th className="p-2 text-right">Coarse Frags (%)</th>
                          <th className="p-2 text-right">Fine Soil Mass (t/ha)</th>
                          <th className="p-2 text-right">SOC (g/kg)</th>
                          <th className="p-2 text-right">Layer SOC (t C/ha)</th>
                          <th className="p-2 text-right">Cum Mass (t/ha)</th>
                          <th className="p-2 text-right">Cum SOC (t C/ha)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800">
                        {selectedSocStock.layers.map((lyr, lIdx) => (
                          <tr key={lIdx} className="hover:bg-slate-800/40">
                            <td className="p-2 font-bold text-slate-300">L{lyr.layer_index}</td>
                            <td className="p-2 text-right text-slate-300">{Number(lyr.depth_upper_cm).toFixed(0)} - {Number(lyr.depth_lower_cm).toFixed(0)}</td>
                            <td className="p-2 text-right text-slate-300">{lyr.bulk_density_g_cm3 != null ? Number(lyr.bulk_density_g_cm3).toFixed(3) : "—"}</td>
                            <td className="p-2 text-right text-slate-300">{lyr.coarse_fragment_fraction != null ? `${(Number(lyr.coarse_fragment_fraction) * 100).toFixed(1)}%` : "0.0%"}</td>
                            <td className="p-2 text-right text-white font-semibold">{Number(lyr.layer_soil_mass_t_ha).toFixed(2)}</td>
                            <td className="p-2 text-right text-emerald-400 font-bold">{Number(lyr.soc_concentration_g_kg).toFixed(2)}</td>
                            <td className="p-2 text-right text-emerald-400 font-bold">{Number(lyr.layer_soc_mass_t_c_ha).toFixed(3)}</td>
                            <td className="p-2 text-right text-slate-300">{Number(lyr.cumulative_soil_mass_t_ha).toFixed(2)}</td>
                            <td className="p-2 text-right text-slate-300">{Number(lyr.cumulative_soc_mass_t_c_ha).toFixed(3)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Cryptographic Proof card */}
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1.5 text-[11px]">
                <div className="text-slate-400 font-sans font-semibold">Cryptographic Proof & Lineage:</div>
                <div className="truncate text-slate-300">
                  • Calculation SHA-256: <span className="text-emerald-400">{selectedSocStock.calculation_hash}</span>
                </div>
                <div className="truncate text-slate-300">
                  • Input Snapshot Hash: <span className="text-slate-400">{selectedSocStock.input_snapshot_hash}</span>
                </div>
                <div className="truncate text-slate-300">
                  • Prerequisite Assessment ID: <span className="text-slate-400">{selectedSocStock.prerequisite_assessment_id}</span>
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-slate-800 flex justify-between items-center bg-slate-950/50">
              <div className="text-[11px] text-slate-500">
                Created: {new Date(selectedSocStock.created_at).toLocaleString()}
              </div>
              <button
                onClick={() => setSelectedSocStock(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold transition"
              >
                Close Detail
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Inspect SOC Stock Change Detail Modal */}
      {selectedSocChange && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                  <span>{selectedSocChange.result_code}</span>
                  <span className="text-xs font-normal text-slate-400">({selectedSocChange.quantification_approach})</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Methodology: VM0042 v{selectedSocChange.methodology_version} • Rule Set: {selectedSocChange.corrections_clarifications_version} • Engine: {selectedSocChange.calculation_engine_version}
                </p>
              </div>
              <button
                onClick={() => setSelectedSocChange(null)}
                className="text-slate-400 hover:text-white text-xs px-2.5 py-1 rounded bg-slate-800 transition"
              >
                Close
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4 text-xs font-mono">
              {/* Carbon Invariant & Scope Boundary Guard */}
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-amber-400">
                  <AlertTriangle className="w-4 h-4" /> Scope Boundary &amp; Ledger Protection Active:
                </div>
                <div>• Carbon Accounting Status: <span className="text-white font-bold">{selectedSocChange.carbon_accounting_status}</span></div>
                <div>• Internal Ledger Status: <span className="text-rose-400 font-bold">{selectedSocChange.ledger_status}</span></div>
                <div className="text-[11px] text-amber-400/80">
                  This record is an authoritative SOC stock change component under VM0042. It cannot be minted as standalone carbon credits.
                </div>
              </div>

              {/* Component breakdown summary KPI grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950 p-3 rounded-lg border border-slate-800">
                <div>
                  <div className="text-[10px] text-slate-400 uppercase">Net ΔSOC Rate</div>
                  <div className="text-base font-bold text-emerald-400">
                    {Number(selectedSocChange.delta_soc_net_t_c_ha_yr).toFixed(4)} t C/ha/yr
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 uppercase">Gross Removals (44/12)</div>
                  <div className="text-base font-bold text-white">
                    {Number(selectedSocChange.total_net_delta_co2_tco2e_yr).toFixed(2)} tCO₂e/yr
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 uppercase">Uncertainty Deduction</div>
                  <div className="text-base font-bold text-rose-400">
                    {Number(selectedSocChange.uncertainty_deduction_pct).toFixed(2)}%
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 uppercase">Creditable Net Removals</div>
                  <div className="text-base font-bold text-emerald-400">
                    {Number(selectedSocChange.adjusted_net_delta_co2_tco2e_yr).toFixed(2)} tCO₂e/yr
                  </div>
                </div>
              </div>

              {/* VM0042 Scientific Breakdown Card */}
              <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
                <h4 className="text-xs font-bold text-white font-sans flex items-center gap-1.5">
                  <Scale className="w-3.5 h-3.5 text-emerald-400" />
                  VM0042 Equations &amp; Uncertainty Quantification Audit Trail
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 text-[11px] text-slate-300">
                  <div>
                    <span className="text-slate-500">• Temporal Pairing: </span>
                    <span className="text-white">{selectedSocChange.t_start?.substring(0, 10)} → {selectedSocChange.t_final?.substring(0, 10)}</span>
                    <span className="text-slate-400"> ({Number(selectedSocChange.elapsed_years).toFixed(2)} yrs)</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Total Project Area: </span>
                    <span className="text-white">{Number(selectedSocChange.total_project_area_ha).toFixed(2)} ha</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Baseline Mean SOC (T0): </span>
                    <span className="text-white">{Number(selectedSocChange.baseline_mean_soc_t_c_per_ha).toFixed(3)} t C/ha</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Monitoring Mean SOC (T1): </span>
                    <span className="text-white">{Number(selectedSocChange.monitoring_mean_soc_t_c_per_ha).toFixed(3)} t C/ha</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Baseline SOC Change (Eq. 46): </span>
                    <span className="text-white">{Number(selectedSocChange.baseline_soc_change_tco2e_yr ?? selectedSocChange.total_baseline_delta_co2_tco2e_yr ?? 0).toFixed(2)} tCO₂e/yr</span>
                    <span className="text-slate-400"> ({Number(selectedSocChange.delta_soc_baseline_t_c_ha_yr).toFixed(4)} t C/ha/yr)</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Project SOC Change (Eq. 47): </span>
                    <span className="text-white">{Number(selectedSocChange.project_soc_change_tco2e_yr ?? selectedSocChange.total_project_delta_co2_tco2e_yr ?? 0).toFixed(2)} tCO₂e/yr</span>
                    <span className="text-slate-400"> ({Number(selectedSocChange.delta_soc_project_t_c_ha_yr).toFixed(4)} t C/ha/yr)</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• QA2 Net SOC Comparative Effect: </span>
                    <span className="text-emerald-400 font-bold">{Number(selectedSocChange.qa2_net_soc_effect_tco2e_yr ?? selectedSocChange.total_net_delta_co2_tco2e_yr ?? 0).toFixed(2)} tCO₂e/yr</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Sign Indicator I(ΔCO₂_soil,t): </span>
                    <span className="text-indigo-400 font-bold">{(selectedSocChange.sign_indicator ?? 1) >= 0 ? "+1" : "-1"}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Exact Stoichiometric 44/12: </span>
                    <span className="text-emerald-400">{Number(selectedSocChange.co2_to_c_ratio).toFixed(6)}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Eq. 44/45 Readiness Status: </span>
                    <span className="text-amber-300 font-mono">{selectedSocChange.eq44_eq45_status || "PARTIALLY_CONFIGURED_SOC_ONLY"}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Eq. (70) Project Stratified Variance: </span>
                    <span className="text-white">{Number(selectedSocChange.variance_delta_soc_project).toExponential(4)}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Eq. (70) Baseline Stratified Variance: </span>
                    <span className="text-white">{Number(selectedSocChange.variance_delta_soc_baseline).toExponential(4)}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Eq. (71) Pooled Total Variance: </span>
                    <span className="text-white">{Number(selectedSocChange.total_variance_delta_soc).toExponential(4)}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Degrees of Freedom Estimator: </span>
                    <span className="text-white">{selectedSocChange.df_estimator || "DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR"} (df: {selectedSocChange.degrees_of_freedom})</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Student&apos;s t Value (p=0.667): </span>
                    <span className="text-white">{Number(selectedSocChange.student_t_value_0667).toFixed(4)}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Relative Uncertainty (U%): </span>
                    <span className="text-amber-400 font-semibold">{Number(selectedSocChange.relative_uncertainty_pct).toFixed(2)}%</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Deadband Override (DEPRECATED — NOT USED): </span>
                    <span className="text-slate-600">{Number(selectedSocChange.allowable_uncertainty_pct || 0).toFixed(2)}% — field retained for schema compatibility; zero deadband per VM0042</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Eq. (74) Deduction Fraction: </span>
                    <span className="text-rose-400 font-semibold">{Number(selectedSocChange.uncertainty_deduction_fraction).toFixed(4)}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Measurement Error Router: </span>
                    <span className="text-white">{selectedSocChange.measurement_error_router}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">• Lab Error Routing Status: </span>
                    <span className="text-emerald-400">{selectedSocChange.measurement_error_status}</span>
                  </div>
                </div>
              </div>

              {/* Strata breakdown table if present */}
              {selectedSocChange.strata_results && selectedSocChange.strata_results.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold text-slate-300 mb-2 font-sans flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-emerald-400" />
                    Stratified Sampling &amp; Covariance Breakdown (Eq. 71)
                  </h4>
                  <div className="overflow-x-auto border border-slate-800 rounded-lg">
                    <table className="w-full text-[11px] text-left">
                      <thead className="bg-slate-950 text-slate-400 uppercase text-[9px] border-b border-slate-800">
                        <tr>
                          <th className="p-2">Stratum</th>
                          <th className="p-2 text-right">Area (ha)</th>
                          <th className="p-2 text-right">Weight (w_k)</th>
                          <th className="p-2 text-right">Baseline Mean (t C/ha)</th>
                          <th className="p-2 text-right">Monitoring Mean (t C/ha)</th>
                          <th className="p-2 text-right">Net ΔSOC (t C/ha/yr)</th>
                          <th className="p-2 text-right">Stratum Variance</th>
                          <th className="p-2 text-right">Gross tCO₂e/yr</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800">
                        {selectedSocChange.strata_results.map((st: any, sIdx: number) => {
                          const sf = (v: any, d: number) => { const n = Number(v); return v != null && Number.isFinite(n) ? n.toFixed(d) : '—'; };
                          const se = (v: any, d: number) => { const n = Number(v); return v != null && Number.isFinite(n) ? n.toExponential(d) : '—'; };
                          return (
                          <tr key={sIdx} className="hover:bg-slate-800/40">
                            <td className="p-2 font-bold text-slate-300">{st.stratum_code}</td>
                            <td className="p-2 text-right text-slate-300">{sf(st.stratum_area_ha ?? st.area_ha, 1)}</td>
                            <td className="p-2 text-right text-slate-400">{sf(st.area_weight, 4)}</td>
                            <td className="p-2 text-right text-slate-300">{sf(st.baseline_mean_soc_t_c_per_ha, 3)}</td>
                            <td className="p-2 text-right text-slate-300">{sf(st.monitoring_mean_soc_t_c_per_ha, 3)}</td>
                            <td className="p-2 text-right text-emerald-400 font-bold">{sf(st.delta_soc_net_t_c_ha_yr, 4)}</td>
                            <td className="p-2 text-right text-slate-400">{se(st.stratum_variance ?? st.stratum_variance_net, 4)}</td>
                            <td className="p-2 text-right text-emerald-400 font-bold">{sf(st.stratum_total_net_delta_co2_tco2e_yr ?? st.total_net_delta_co2_tco2e_yr ?? st.qa2_net_soc_effect_tco2e_yr, 2)}</td>
                          </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Cryptographic Proof & Lineage card */}
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1.5 text-[11px]">
                <div className="text-slate-400 font-sans font-semibold">Cryptographic Proof &amp; Lineage:</div>
                <div className="truncate text-slate-300">
                  • Calculation SHA-256: <span className="text-emerald-400">{selectedSocChange.calculation_hash}</span>
                </div>
                <div className="truncate text-slate-300">
                  • Input Snapshot Hash: <span className="text-slate-400">{selectedSocChange.input_snapshot_hash}</span>
                </div>
                <div className="truncate text-slate-300">
                  • Baseline Stock Result ID: <span className="text-slate-400">{selectedSocChange.baseline_stock_result_id}</span>
                </div>
                <div className="truncate text-slate-300">
                  • Monitoring Stock Result ID: <span className="text-slate-400">{selectedSocChange.monitoring_stock_result_id}</span>
                </div>
                <div className="truncate text-slate-300">
                  • Prerequisite Assessment ID: <span className="text-slate-400">{selectedSocChange.prerequisite_assessment_id}</span>
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-slate-800 flex justify-between items-center bg-slate-950/50">
              <div className="text-[11px] text-slate-500">
                Created: {new Date(selectedSocChange.created_at).toLocaleString()}
              </div>
              <button
                onClick={() => setSelectedSocChange(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold transition"
              >
                Close Detail
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Inspect Net GHG & VCU Readiness Detail Modal */}
      {selectedNetGhg && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                  <span>{selectedNetGhg.result_code}</span>
                  <span className="text-xs font-normal text-slate-400">
                    ({new Date(selectedNetGhg.verification_period_start).toLocaleDateString()} – {new Date(selectedNetGhg.verification_period_end).toLocaleDateString()})
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Ruleset: {selectedNetGhg.ruleset_version} • Engine: {selectedNetGhg.calculation_engine_version}
                </p>
              </div>
              <button
                onClick={() => setSelectedNetGhg(null)}
                className="text-slate-400 hover:text-white text-xs px-2.5 py-1 rounded bg-slate-800 transition"
              >
                Close
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4 text-xs font-mono">
              {/* High-level Summary Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950 p-3 rounded-lg border border-slate-800">
                <div>
                  <div className="text-[10px] text-slate-400 uppercase">Gross Reductions (Eq. 37)</div>
                  <div className="text-base font-bold text-emerald-400">
                    {Number(selectedNetGhg.gross_reductions_er_tco2e).toFixed(2)} tCO₂e
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 uppercase">Gross Removals (Eq. 40)</div>
                  <div className="text-base font-bold text-emerald-400">
                    {Number(selectedNetGhg.gross_removals_cr_tco2e).toFixed(2)} tCO₂e
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 uppercase">Total Net GHG (Eq. 43)</div>
                  <div className="text-base font-bold text-emerald-300">
                    {Number(selectedNetGhg.total_net_ghg_errnet_tco2e).toFixed(2)} tCO₂e
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-indigo-400 uppercase">Internal VCU Eligible</div>
                  <div className="text-base font-bold text-indigo-300">
                    {selectedNetGhg.internal_vcu_eligible_total_tco2e != null ? `${Number(selectedNetGhg.internal_vcu_eligible_total_tco2e).toFixed(2)} VCUs` : "N/A"}
                  </div>
                </div>
              </div>

              {/* Status & Governance Card */}
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                <div className="text-slate-300 font-sans font-semibold">Governance &amp; System Status:</div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                  <div>
                    <span className="text-slate-500">Internal MRV: </span>
                    <span className="text-emerald-400 font-bold">{selectedNetGhg.internal_mrv_status}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">VCU Readiness: </span>
                    <span className="text-indigo-400 font-bold">{selectedNetGhg.vcu_readiness_status}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">VVB Status: </span>
                    <span className="text-slate-400">{selectedNetGhg.vvb_status}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Registry Status: </span>
                    <span className="text-slate-400">{selectedNetGhg.registry_status}</span>
                  </div>
                </div>
              </div>

              {/* Annual Vintages Table */}
              {selectedNetGhg.vintages && selectedNetGhg.vintages.length > 0 && (
                <div>
                  <div className="text-slate-300 font-sans font-semibold mb-2">Annual Vintages Breakdown:</div>
                  <div className="overflow-x-auto border border-slate-800 rounded-lg">
                    <table className="w-full text-[11px] text-left">
                      <thead className="bg-slate-950 text-slate-400 uppercase text-[9px] border-b border-slate-800">
                        <tr>
                          <th className="p-2">Vintage Year</th>
                          <th className="p-2 text-right">Net ER</th>
                          <th className="p-2 text-right">Net CR</th>
                          <th className="p-2 text-right text-emerald-400">Total ERRNET</th>
                          <th className="p-2 text-right text-indigo-400">VCU Eligible</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800">
                        {selectedNetGhg.vintages.map((v) => (
                          <tr key={v.id} className="hover:bg-slate-800/40">
                            <td className="p-2 font-bold text-white">{v.vintage_year}</td>
                            <td className="p-2 text-right text-slate-300">{Number(v.net_reductions_ernet_tco2e).toFixed(2)}</td>
                            <td className="p-2 text-right text-slate-300">{Number(v.net_removals_crnet_tco2e).toFixed(2)}</td>
                            <td className="p-2 text-right text-emerald-400 font-bold">{Number(v.total_net_ghg_errnet_tco2e).toFixed(2)}</td>
                            <td className="p-2 text-right text-indigo-300">{v.internal_vcu_eligible_total_tco2e != null ? Number(v.internal_vcu_eligible_total_tco2e).toFixed(2) : "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Cryptographic Proof & Lineage card */}
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1.5 text-[11px]">
                <div className="text-slate-400 font-sans font-semibold">Cryptographic Proof &amp; Lineage:</div>
                <div className="truncate text-slate-300">
                  • Calculation SHA-256: <span className="text-emerald-400">{selectedNetGhg.calculation_hash}</span>
                </div>
                <div className="truncate text-slate-300">
                  • Input Snapshot Hash: <span className="text-slate-400">{selectedNetGhg.input_snapshot_hash}</span>
                </div>
                <div className="truncate text-slate-300">
                  • Prerequisite Assessment ID: <span className="text-slate-400">{selectedNetGhg.prerequisite_assessment_id}</span>
                </div>
                {selectedNetGhg.soc_change_result_id && (
                  <div className="truncate text-slate-300">
                    • SOC Change Result ID: <span className="text-slate-400">{selectedNetGhg.soc_change_result_id}</span>
                  </div>
                )}
              </div>

              {/* Methodological Parity & VMD0054 Governance Card */}
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1.5 text-[11px]">
                <div className="text-slate-400 font-sans font-semibold">Methodological Parity &amp; VMD0054 Module Governance:</div>
                <div className="text-slate-300">
                  • VM0042 Eq. 37 Form: <span className="text-emerald-400 font-mono">{selectedNetGhg.component_breakdown?.eq37_formula || "ER_t = I(Delta_CO2_wp) * (sum(Delta_E_sources,t) + min(0, Delta_CO2_wp,t) - min(0, Delta_CO2_bsl,t)) + (1 - I(Delta_CO2_wp)) * (sum(Delta_E_sources,t) + min(0, Delta_CO2_wp,t) - min(0, Delta_CO2_bsl,t) + max(0, Delta_CO2_wp,t) - max(0, Delta_CO2_bsl,t))"}</span>
                </div>
                <div className="text-slate-300">
                  • VM0042 Eq. 75 Form: <span className="text-rose-400 font-mono">{selectedNetGhg.component_breakdown?.eq75_formula || "BuER,t = NPR * (I(Delta_CO2_wp) * (min(0, Delta_CO2_wp,t) - min(0, Delta_CO2_bsl,t)) + (1 - I(Delta_CO2_wp)) * (min(0, Delta_CO2_wp,t) - min(0, Delta_CO2_bsl,t) + max(0, Delta_CO2_wp,t) - max(0, Delta_CO2_bsl,t)))"} (No Outer Clamp)</span>
                </div>
                <div className="text-slate-300">
                  • VMD0054 Module Version: <span className="text-indigo-400 font-bold">{selectedNetGhg.component_breakdown?.vmd0054_version || "VMD0054_1_1_CURRENT"}</span>
                </div>
                <div className="text-slate-300">
                  • VMD0054 Source Equation: <span className="text-slate-300 font-mono">{selectedNetGhg.component_breakdown?.vmd0054_source_equation || "VMD0054_V1.1_EQ13"}</span>
                </div>
                <div className="text-slate-300">
                  • Transition Basis: <span className="text-amber-400">{selectedNetGhg.component_breakdown?.vmd0054_transition_basis || "ACTIVE_STANDARD_V1_1"}</span>
                </div>
                <div className="text-slate-300">
                  • Effective Ruleset: <span className="text-slate-400">{selectedNetGhg.component_breakdown?.vmd0054_effective_ruleset || "VMD0054_V1.1_ACTIVE"}</span>
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-slate-800 flex justify-between items-center bg-slate-950/50">
              <div className="text-[11px] text-slate-500">
                Created: {new Date(selectedNetGhg.created_at).toLocaleString()}
              </div>
              <button
                onClick={() => setSelectedNetGhg(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold transition"
              >
                Close Detail
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Inspect Snapshot Modal */}
      {selectedSnapshot && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-white text-sm">
                  Canonical Input Package: {selectedSnapshot.snapshot_code}
                </h3>
                <span className="text-xs font-mono text-emerald-400">{selectedSnapshot.snapshot_hash}</span>
              </div>
              <button
                onClick={() => setSelectedSnapshot(null)}
                className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded bg-slate-800"
              >
                Close
              </button>
            </div>
            <div className="p-4 overflow-y-auto flex-1 font-mono text-xs text-slate-300 bg-slate-950">
              <pre>{JSON.stringify(selectedSnapshot.input_package, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}

      {/* Inspect Assessment Dossier Modal */}
      {selectedAssessment && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-white text-sm">
                  Authoritative Prerequisite Dossier: {selectedAssessment.assessment_code} (v{selectedAssessment.version})
                </h3>
                <span className="text-xs font-mono text-emerald-400">{selectedAssessment.assessment_hash}</span>
              </div>
              <button
                onClick={() => setSelectedAssessment(null)}
                className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded bg-slate-800"
              >
                Close
              </button>
            </div>
            <div className="p-4 overflow-y-auto flex-1 font-mono text-xs text-slate-300 bg-slate-950 space-y-4">
              <div className="p-3 rounded bg-slate-900 border border-slate-800">
                <div className="text-white font-bold mb-1 font-sans text-xs">Methodology & Version Resolution</div>
                <div className="text-slate-400">Methodology: {selectedAssessment.methodology_code} v{selectedAssessment.methodology_version}</div>
                <div className="text-slate-400">Rule Set: {selectedAssessment.rule_set_version}</div>
                <div className="text-slate-400">
                  Governing VCS Standard: {selectedAssessment.vcs_resolution_metadata?.governing_vcs_standard === "VCS_5_0" ? "VCS Standard v5.0" : "VCS Standard v4.7"}
                </div>
                <div className="text-slate-400">
                  Template Version: {selectedAssessment.vcs_resolution_metadata?.project_description_template || "VCS_PROJECT_DESCRIPTION_V4.4"}
                </div>
              </div>

              <div>
                <div className="text-white font-bold mb-1 font-sans text-xs">17 Categorical Dimensions State</div>
                <pre className="p-3 rounded bg-slate-900 border border-slate-800 overflow-x-auto">
                  {JSON.stringify(selectedAssessment.dimensions, null, 2)}
                </pre>
              </div>

              <div>
                <div className="text-white font-bold mb-1 font-sans text-xs">ESM Input Dossier</div>
                <pre className="p-3 rounded bg-slate-900 border border-slate-800 overflow-x-auto">
                  {JSON.stringify(selectedAssessment.esm_input_dossier, null, 2)}
                </pre>
              </div>

              <div>
                <div className="text-white font-bold mb-1 font-sans text-xs">Sampling Design Assessment</div>
                <pre className="p-3 rounded bg-slate-900 border border-slate-800 overflow-x-auto">
                  {JSON.stringify(selectedAssessment.sampling_design_assessment, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Lock Prerequisite Assessment Modal */}
      {showLockPrereqModal && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-md shadow-2xl">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Lock className="w-4 h-4 text-emerald-400" /> Lock Prerequisite Dossier
              </h3>
              <button
                onClick={() => setShowLockPrereqModal(false)}
                className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded bg-slate-800"
              >
                Cancel
              </button>
            </div>

            <form onSubmit={handleLockPrereqAssessment} className="p-5 space-y-4 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Attach Phase 3A Input Snapshot (Optional)</label>
                <select
                  value={selectedSnapshotId}
                  onChange={(e) => setSelectedSnapshotId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono text-xs"
                >
                  <option value="">No snapshot attached (Evaluate project foundation directly)</option>
                  {snapshots.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.snapshot_code} ({s.context}) — {s.snapshot_hash.substring(0, 16)}...
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Auditor / Verifier Notes</label>
                <textarea
                  value={prereqLockNotes}
                  onChange={(e) => setPrereqLockNotes(e.target.value)}
                  placeholder="e.g., Formal VM0042 v2.2 prerequisite evaluation locked prior to crediting cycle."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white placeholder-slate-600 h-20"
                />
              </div>

              <div className="p-3 rounded bg-slate-950 border border-slate-800 text-[11px] text-slate-400 space-y-1">
                <div>• Active Rule Set: <strong className="text-white">VM0042 v2.2 + C&C 2026-06-11</strong></div>
                <div>• Governing VCS Standard: <strong className="text-indigo-400">{prereqEval?.dimensions?.VCS_PROGRAM_RULESET?.details?.governing_vcs_standard === "VCS_5_0" ? "VCS Standard v5.0" : "VCS Standard v4.7"}</strong></div>
                <div>• Template Version: <strong className="text-slate-300">{prereqEval?.dimensions?.VCS_PROGRAM_RULESET?.details?.project_description_template || "VCS_PROJECT_DESCRIPTION_V4.4"}</strong></div>
                <div>• Deterministic SHA-256 hash will freeze the evaluation state.</div>
                <div>• Any subsequent lock creates a new version and marks this superseded.</div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowLockPrereqModal(false)}
                  className="px-3 py-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition flex items-center gap-1.5"
                >
                  {actionLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Lock className="w-3.5 h-3.5" />}
                  Lock Prerequisite Dossier
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
