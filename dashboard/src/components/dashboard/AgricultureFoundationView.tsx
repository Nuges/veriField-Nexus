// =============================================================================
// VeriField Nexus — Agriculture MRV Phase 1: Operational Workflow Console
// =============================================================================
// Operational MRV Console covering:
// 1. Foundation Readiness Evaluator (6 Deterministic Categorical Components)
// 2. Methodology Lock & Invariant Snapshot (VM0042 with VT0014 DSM tool)
// 3. Land Management Unit Hierarchy (Parcels, Fields, Monitoring Plots)
// 4. Analytical Stratification & Relational Land Unit Memberships
// 5. Historical Management Baseline & Practice Change Event Logging
// =============================================================================

"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Lock,
  Layers,
  Calendar,
  MapPin,
  RefreshCw,
  Plus,
  FileText,
  Clock,
  HelpCircle,
  TestTube,
  Scale,
} from "lucide-react";
import AgricultureGroundEvidenceView from "./AgricultureGroundEvidenceView";
import { AgricultureQuantificationView } from "./AgricultureQuantificationView";
import {
  fetchProjectFoundation,
  lockProjectMethodology,
  fetchFoundationReadiness,
  fetchGroundEvidenceReadiness,
  fetchLandUnits,
  fetchProjectStrata,
  createProjectStratum,
  addStratumMemberships,
  fetchProjectManagementRecords,
  createProjectManagementRecord,
  type ProjectFoundationData,
  type FoundationReadinessData,
  type GroundEvidenceReadinessData,
  type StratumRecord,
  type ManagementRecordItem,
  type LandUnitRecord,
} from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";

export default function AgricultureFoundationView({ projectId }: { projectId?: string }) {
  let workspaceUser: any = null;
  try {
    const ws = useWorkspace();
    workspaceUser = ws?.user;
  } catch {
    // Rendered outside WorkspaceProvider or during isolated testing
  }
  const userRole = (workspaceUser?.role || "PROJECT_MANAGER").toUpperCase();
  const isAuditor = userRole === "AUDITOR";
  const isFieldAgent = userRole === "FIELD_AGENT";
  const canLockMethodology = !isAuditor && !isFieldAgent;
  const canCreateStratum = !isAuditor && !isFieldAgent;
  const canAssignUnits = !isAuditor && !isFieldAgent;
  const canLogManagement = !isAuditor;

  const [activeSection, setActiveSection] = useState<
    "readiness" | "ground_evidence" | "quantification" | "methodology" | "land_structure" | "strata" | "management"
  >("readiness");

  const [foundation, setFoundation] = useState<ProjectFoundationData | null>(null);
  const [readiness, setReadiness] = useState<FoundationReadinessData | null>(null);
  const [groundReadiness, setGroundReadiness] = useState<GroundEvidenceReadinessData | null>(null);
  const [landUnits, setLandUnits] = useState<LandUnitRecord[]>([]);
  const [strata, setStrata] = useState<StratumRecord[]>([]);
  const [managementRecords, setManagementRecords] = useState<ManagementRecordItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [lockNotes, setLockNotes] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // New Stratum Modal State
  const [showStratumModal, setShowStratumModal] = useState(false);
  const [stratumCode, setStratumCode] = useState("");
  const [stratumName, setStratumName] = useState("");
  const [stratumType, setStratumType] = useState("MANAGEMENT_PRACTICE");
  const [stratumDesc, setStratumDesc] = useState("");

  // New Management Record Modal State
  const [showRecordModal, setShowRecordModal] = useState(false);
  const [recType, setRecType] = useState("TILLAGE");
  const [recCategory, setRecCategory] = useState("BASELINE");
  const [recDate, setRecDate] = useState(new Date().toISOString().split("T")[0]);
  const [recSource, setRecSource] = useState("FIELD_INTERVIEW");
  const [recCorroboration, setRecCorroboration] = useState("NONE");
  const [recDetails, setRecDetails] = useState("");
  const [recLandUnitId, setRecLandUnitId] = useState("");

  // Member assignment modal
  const [assignStratumId, setAssignStratumId] = useState<string | null>(null);
  const [selectedUnitIds, setSelectedUnitIds] = useState<string[]>([]);

  const loadData = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const [fData, rData, grData, luData, sData, mData] = await Promise.all([
        fetchProjectFoundation(projectId),
        fetchFoundationReadiness(projectId),
        fetchGroundEvidenceReadiness(projectId),
        fetchLandUnits(projectId),
        fetchProjectStrata(projectId),
        fetchProjectManagementRecords(projectId),
      ]);
      setFoundation(fData);
      setReadiness(rData);
      setGroundReadiness(grData);
      setLandUnits(luData || []);
      setStrata(sData || []);
      setManagementRecords(mData || []);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load agriculture project data.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleLockMethodology = async () => {
    if (!projectId) return;
    setActionLoading(true);
    setErrorMsg(null);
    try {
      await lockProjectMethodology(projectId, lockNotes);
      setSuccessMsg("Methodology version successfully locked into immutable baseline parameters.");
      setLockNotes("");
      await loadData();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to lock methodology.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateStratum = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId || !stratumCode || !stratumName) return;
    setActionLoading(true);
    try {
      await createProjectStratum(projectId, {
        code: stratumCode,
        name: stratumName,
        stratum_type: stratumType,
        description: stratumDesc,
      });
      setShowStratumModal(false);
      setStratumCode("");
      setStratumName("");
      setStratumDesc("");
      setSuccessMsg(`Stratum '${stratumCode}' created successfully.`);
      await loadData();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to create stratum.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddMemberships = async () => {
    if (!projectId || !assignStratumId || selectedUnitIds.length === 0) return;
    setActionLoading(true);
    try {
      const mems = selectedUnitIds.map((uid) => ({
        land_unit_id: uid,
        valid_from: new Date().toISOString().split("T")[0],
        status: "ACTIVE",
      }));
      await addStratumMemberships(projectId, assignStratumId, mems);
      setAssignStratumId(null);
      setSelectedUnitIds([]);
      setSuccessMsg("Land unit memberships assigned to stratum.");
      await loadData();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to assign memberships.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateManagementRecord = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId || !recType || !recDate) return;
    setActionLoading(true);
    try {
      let parsedDetails = {};
      try {
        parsedDetails = recDetails ? JSON.parse(recDetails) : {};
      } catch {
        parsedDetails = { raw_notes: recDetails };
      }

      await createProjectManagementRecord(projectId, {
        record_type: recType,
        practice_category: recCategory,
        event_date: recDate,
        data_source: recSource,
        corroboration: recCorroboration,
        details: parsedDetails,
        land_unit_id: recLandUnitId || undefined,
        qa_status: "VERIFIED",
      });
      setShowRecordModal(false);
      setRecDetails("");
      setSuccessMsg("Management record logged successfully.");
      await loadData();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to create management record.");
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "COMPLETE":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 size={12} />
            COMPLETE
          </span>
        );
      case "NEEDS_REVIEW":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            <AlertTriangle size={12} />
            NEEDS REVIEW
          </span>
        );
      case "INCOMPLETE":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
            <Clock size={12} />
            INCOMPLETE
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border border-zinc-500/20">
            <HelpCircle size={12} />
            NOT CONFIGURED
          </span>
        );
    }
  };

  if (!projectId) {
    return (
      <div className="p-8 text-center bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl">
        <AlertTriangle className="mx-auto text-amber-500 mb-2" size={28} />
        <h3 className="font-semibold text-sm text-[var(--color-text-primary)]">No Active Agriculture Project</h3>
        <p className="text-xs text-[var(--color-text-secondary)] mt-1">
          Select or register an agriculture project in the workspace to access the Phase 1 MRV operational workflow.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Messages */}
      {errorMsg && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-600 dark:text-red-400 flex items-center justify-between">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="text-xs font-bold ml-2">✕</button>
        </div>
      )}
      {successMsg && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-xs text-emerald-600 dark:text-emerald-400 flex items-center justify-between">
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} className="text-xs font-bold ml-2">✕</button>
        </div>
      )}

      {/* Header / Foundation Readiness Summary Card */}
      <div className="p-5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-[var(--color-border)] pb-3">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                MRV Workflow:
              </span>
              <div data-testid="agri-readiness-overall" className="flex items-center gap-1">
                <span className="text-[10px] text-[var(--color-text-muted)] font-bold">Phase 1:</span>
                {readiness && getStatusBadge(readiness.overall_status)}
              </div>
              {groundReadiness && (
                <div data-testid="agri-ground-evidence-overall" className="flex items-center gap-1">
                  <span className="text-[10px] text-[var(--color-text-muted)] font-bold">Phase 2 Ground:</span>
                  {getStatusBadge(groundReadiness.overall_status)}
                </div>
              )}
            </div>
            <h2 className="text-lg font-bold text-[var(--color-text-primary)] mt-0.5">
              {foundation?.project_name || "Agriculture Project Foundation"}
            </h2>
            <p className="text-xs text-[var(--color-text-secondary)]">
              Project Code: <span className="font-mono font-medium text-[var(--color-text-primary)]">{foundation?.project_code || "UNASSIGNED"}</span> • Crediting:{" "}
              {foundation?.crediting_period?.start || "N/A"} to {foundation?.crediting_period?.end || "N/A"}
            </p>
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] hover:bg-[var(--color-surface)] transition-colors cursor-pointer"
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
            <span>Refresh State</span>
          </button>
        </div>

        {/* 6 Deterministic Component Badges */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5">
          {readiness?.components &&
            Object.entries(readiness.components).map(([key, comp]) => (
              <div
                key={key}
                data-testid={`readiness-comp-${key}`}
                className="p-2.5 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] space-y-1"
              >
                <div className="text-[10px] uppercase font-bold text-[var(--color-text-muted)] tracking-wider">
                  {key.replace(/_/g, " ")}
                </div>
                <div>{getStatusBadge(comp.status)}</div>
                <div className="text-[11px] text-[var(--color-text-secondary)] line-clamp-2 leading-tight">
                  {comp.message}
                </div>
              </div>
            ))}
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex items-center gap-2 border-b border-[var(--color-border)] overflow-x-auto pb-px">
        {[
          { id: "readiness", label: "Foundation Readiness", icon: ShieldCheck },
          { id: "ground_evidence", label: "Ground Evidence & Labs (Phase 2)", icon: TestTube },
          { id: "quantification", label: "Quantification Readiness (Phase 3A)", icon: Scale },
          { id: "methodology", label: "Methodology Lock", icon: Lock },
          { id: "land_structure", label: `Land Units (${landUnits.length})`, icon: MapPin },
          { id: "strata", label: `Strata & Groups (${strata.length})`, icon: Layers },
          { id: "management", label: `Management Baseline (${managementRecords.length})`, icon: Calendar },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeSection === tab.id;
          return (
            <button
              key={tab.id}
              data-testid={`tab-${tab.id}`}
              onClick={() => setActiveSection(tab.id as typeof activeSection)}
              className={`flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold border-b-2 rounded-t-lg transition-all cursor-pointer ${
                isActive
                  ? "border-emerald-500 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 font-bold"
                  : "border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface)]"
              }`}
            >
              <Icon size={13} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* SECTION: GROUND EVIDENCE & LAB ASSAYS (PHASE 2) */}
      {activeSection === "ground_evidence" && (
        <AgricultureGroundEvidenceView projectId={projectId} />
      )}

      {/* SECTION: QUANTIFICATION READINESS & CALCULATION INPUT CONTRACT (PHASE 3A) */}
      {activeSection === "quantification" && (
        <AgricultureQuantificationView projectId={projectId} userRole={userRole} />
      )}

      {/* SECTION 1: FOUNDATION READINESS */}
      {activeSection === "readiness" && readiness?.components && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(readiness.components).map(([compKey, comp]) => (
              <div
                key={compKey}
                className="p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-2.5"
              >
                <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-2">
                  <div className="font-semibold text-xs text-[var(--color-text-primary)] uppercase tracking-wider">
                    {compKey.replace(/_/g, " ")}
                  </div>
                  {getStatusBadge(comp.status)}
                </div>
                <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">{comp.message}</p>
                {comp.details && Object.keys(comp.details).length > 0 && (
                  <div className="p-2.5 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-[11px] font-mono space-y-1">
                    {Object.entries(comp.details).map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <span className="text-[var(--color-text-muted)]">{k}:</span>
                        <span className="text-[var(--color-text-primary)] font-medium">
                          {typeof v === "object" ? JSON.stringify(v) : String(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SECTION 2: METHODOLOGY LOCK */}
      {activeSection === "methodology" && (
        <div className="p-5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
            <div>
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)]">Methodology Version Lock</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">
                Authoritative climate methodology designation and immutable version locking.
              </p>
            </div>
            {foundation && getStatusBadge(foundation.methodology_lock_status === "LOCKED" ? "COMPLETE" : "NEEDS_REVIEW")}
          </div>

          <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-800 dark:text-emerald-300">
            <span className="font-bold">Canonical Specification:</span> VM0042 methodology, using VT0014 digital soil
            mapping tool where applicable.
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="space-y-2 p-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)]">
              <span className="font-semibold text-[var(--color-text-primary)]">Catalogue Assignment</span>
              <div className="space-y-1 text-[var(--color-text-secondary)]">
                <div>
                  Methodology:{" "}
                  <span className="font-mono text-[var(--color-text-primary)] font-medium">
                    {foundation?.methodology?.code || "VM0042"}
                  </span>
                </div>
                <div>
                  Version:{" "}
                  <span className="font-mono text-[var(--color-text-primary)] font-medium">
                    {foundation?.methodology?.version || "2.2"}
                  </span>
                </div>
                <div>
                  Sector Family:{" "}
                  <span className="font-medium text-[var(--color-text-primary)]">
                    {foundation?.sector?.name || "Agriculture & Land Use"}
                  </span>
                </div>
              </div>
            </div>

            <div className="space-y-2 p-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)]">
              <span className="font-semibold text-[var(--color-text-primary)]">Immutable Lock State</span>
              {foundation?.methodology_lock_status === "LOCKED" ? (
                <div data-testid="locked-methodology-badge" className="space-y-1 text-[var(--color-text-secondary)]">
                  <div className="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
                    <CheckCircle2 size={13} /> LOCKED
                  </div>
                  <div>
                    Locked At:{" "}
                    <span className="font-mono text-[var(--color-text-primary)]">
                      {String(foundation.locked_methodology_snapshot?.locked_at || "Recorded")}
                    </span>
                  </div>
                  {Boolean(foundation.locked_methodology_snapshot?.notes) && (
                    <div>
                      Notes: <i>{String(foundation.locked_methodology_snapshot?.notes)}</i>
                    </div>
                  )}
                </div>
              ) : canLockMethodology ? (
                <div className="space-y-2">
                  <p className="text-amber-600 dark:text-amber-400">
                    Methodology selected but unlocked. Lock to freeze rules against catalogue drift.
                  </p>
                  <input
                    type="text"
                    data-testid="input-lock-notes"
                    value={lockNotes}
                    onChange={(e) => setLockNotes(e.target.value)}
                    placeholder="Validation notes / reason for lock..."
                    className="w-full px-2.5 py-1.5 text-xs rounded bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                  />
                  <button
                    data-testid="btn-lock-methodology"
                    onClick={handleLockMethodology}
                    disabled={actionLoading}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs transition-colors flex items-center gap-1.5 cursor-pointer"
                  >
                    <Lock size={12} />
                    <span>{actionLoading ? "Locking..." : "Lock Methodology Version"}</span>
                  </button>
                </div>
              ) : (
                <div data-testid="auditor-restricted-notice" className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-700 dark:text-amber-300">
                  Read-only view: {userRole} is not authorized to lock methodology parameters.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* SECTION 3: LAND STRUCTURE */}
      {activeSection === "land_structure" && (
        <div className="p-5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
            <div>
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)]">
                Land Management Units ({landUnits.length})
              </h3>
              <p className="text-xs text-[var(--color-text-secondary)]">
                Hierarchical parcels, fields, and monitoring plots with WGS84 geodesic area calculations.
              </p>
            </div>
          </div>

          {landUnits.length === 0 ? (
            <div className="p-6 text-center text-xs text-[var(--color-text-muted)] bg-[var(--color-background)] rounded-lg border border-[var(--color-border)]">
              No land units defined yet. Use the API or spatial onboarding to delineate fields and parcels.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-[var(--color-background)] border-b border-[var(--color-border)] text-[var(--color-text-muted)] uppercase tracking-wider font-semibold">
                  <tr>
                    <th className="py-2.5 px-3">Name / Code</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Land Use</th>
                    <th className="py-2.5 px-3">Soil Type</th>
                    <th className="py-2.5 px-3 text-right">Area (ha)</th>
                    <th className="py-2.5 px-3">Boundary Source</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border)]">
                  {landUnits.map((lu) => (
                    <tr key={lu.id} className="hover:bg-[var(--color-background)]/50 transition-colors">
                      <td className="py-2.5 px-3 font-medium text-[var(--color-text-primary)]">
                        {lu.name}
                        {lu.code && <span className="ml-1.5 font-mono text-[10px] text-[var(--color-text-muted)]">[{lu.code}]</span>}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-zinc-500/10 text-zinc-600 dark:text-zinc-400">
                          {lu.unit_type}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-[var(--color-text-secondary)]">{lu.land_use_category || "—"}</td>
                      <td className="py-2.5 px-3 text-[var(--color-text-secondary)]">{lu.soil_type || "—"}</td>
                      <td className="py-2.5 px-3 text-right font-mono font-medium text-[var(--color-text-primary)]">
                        {lu.area_ha.toFixed(2)}
                      </td>
                      <td className="py-2.5 px-3 text-[var(--color-text-muted)] font-mono text-[11px]">
                        {lu.boundary_source}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* SECTION 4: STRATA & MEMBERSHIPS */}
      {activeSection === "strata" && (
        <div className="p-5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
            <div>
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)]">Analytical Strata ({strata.length})</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">
                Stratification groupings (soil texture, baseline practices, topography) for VM0042 / VT0014 analysis.
              </p>
            </div>
            {canCreateStratum && (
              <button
                data-testid="btn-create-stratum"
                onClick={() => setShowStratumModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white transition-colors cursor-pointer"
              >
                <Plus size={13} />
                <span>Create Stratum</span>
              </button>
            )}
          </div>

          {strata.length === 0 ? (
            <div className="p-6 text-center text-xs text-[var(--color-text-muted)] bg-[var(--color-background)] rounded-lg border border-[var(--color-border)]">
              No strata created yet. Delineate analytical strata and assign land units to satisfy stratification requirements.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {strata.map((s) => (
                <div
                  key={s.id}
                  data-testid={`stratum-card-${s.code}`}
                  className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs text-[var(--color-text-primary)] font-mono">{s.code}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                      {s.stratum_type}
                    </span>
                  </div>
                  <h4 className="font-semibold text-xs text-[var(--color-text-primary)]">{s.name}</h4>
                  {s.description && (
                    <p className="text-[11px] text-[var(--color-text-secondary)]">{s.description}</p>
                  )}

                  <div className="pt-2 border-t border-[var(--color-border)] flex items-center justify-between text-xs">
                    <span className="text-[var(--color-text-muted)]">
                      Members: <span data-testid={`stratum-members-${s.code}`} className="font-semibold text-[var(--color-text-primary)]">{s.member_count}</span>
                    </span>
                    <span className="text-[var(--color-text-muted)]">
                      Area:{" "}
                      <span data-testid={`stratum-area-${s.code}`} className="font-mono font-semibold text-[var(--color-text-primary)]">
                        {s.area_ha.toFixed(2)} ha
                      </span>
                    </span>
                    {canAssignUnits && (
                      <button
                        data-testid={`btn-assign-units-${s.code}`}
                        onClick={() => {
                          setAssignStratumId(s.id);
                          setSelectedUnitIds(s.land_unit_ids || []);
                        }}
                        className="px-2.5 py-1 text-[11px] font-semibold rounded bg-[var(--color-surface)] border border-[var(--color-border)] hover:bg-[var(--color-background)] cursor-pointer"
                      >
                        Assign Units
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* SECTION 5: MANAGEMENT BASELINE */}
      {activeSection === "management" && (
        <div className="p-5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
            <div>
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)]">
                Management Baseline & Practice History ({managementRecords.length})
              </h3>
              <p className="text-xs text-[var(--color-text-secondary)]">
                Categorical pre-project baseline and crediting period agricultural practice events with data provenance.
              </p>
            </div>
            {canLogManagement ? (
              <button
                data-testid="btn-log-practice"
                onClick={() => setShowRecordModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white transition-colors cursor-pointer"
              >
                <Plus size={13} />
                <span>Log Practice Event</span>
              </button>
            ) : (
              <div data-testid="auditor-management-notice" className="text-xs text-[var(--color-text-muted)] italic">
                Auditor read-only mode: practice event logging is disabled.
              </div>
            )}
          </div>

          {managementRecords.length === 0 ? (
            <div className="p-6 text-center text-xs text-[var(--color-text-muted)] bg-[var(--color-background)] rounded-lg border border-[var(--color-border)]">
              No management records logged. Document historical baseline management to satisfy MRV baseline requirements.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-[var(--color-background)] border-b border-[var(--color-border)] text-[var(--color-text-muted)] uppercase tracking-wider font-semibold">
                  <tr>
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Category</th>
                    <th className="py-2.5 px-3">Record Type</th>
                    <th className="py-2.5 px-3">Data Source Provenance</th>
                    <th className="py-2.5 px-3">Details</th>
                    <th className="py-2.5 px-3">QA Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border)]">
                  {managementRecords.map((rec) => (
                    <tr key={rec.id} data-testid={`mgmt-row-${rec.record_type}`} className="hover:bg-[var(--color-background)]/50 transition-colors">
                      <td className="py-2.5 px-3 font-mono font-medium text-[var(--color-text-primary)]">
                        {rec.event_date}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            rec.practice_category === "BASELINE"
                              ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                              : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                          }`}
                        >
                          {rec.practice_category}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-medium text-[var(--color-text-primary)]">{rec.record_type}</td>
                      <td className="py-2.5 px-3 font-mono text-[11px] text-[var(--color-text-muted)]">
                        {rec.data_source}
                      </td>
                      <td className="py-2.5 px-3 text-[var(--color-text-secondary)] font-mono text-[11px]">
                        {JSON.stringify(rec.details)}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] bg-zinc-500/10 text-zinc-600 dark:text-zinc-400">
                          {rec.qa_status}
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

      {/* CREATE STRATUM MODAL */}
      {showStratumModal && (
        <div data-testid="modal-create-stratum" className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl shadow-xl p-5 space-y-4">
            <h3 className="font-bold text-sm text-[var(--color-text-primary)]">Create Analytical Stratum</h3>
            <form onSubmit={handleCreateStratum} className="space-y-3 text-xs">
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Stratum Code</label>
                <input
                  type="text"
                  required
                  data-testid="input-stratum-code"
                  value={stratumCode}
                  onChange={(e) => setStratumCode(e.target.value)}
                  placeholder="e.g. STRAT-01"
                  className="w-full px-3 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                />
              </div>
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Stratum Name</label>
                <input
                  type="text"
                  required
                  data-testid="input-stratum-name"
                  value={stratumName}
                  onChange={(e) => setStratumName(e.target.value)}
                  placeholder="e.g. Silt Loam - Reduced Tillage"
                  className="w-full px-3 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                />
              </div>
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Stratum Type</label>
                <select
                  data-testid="select-stratum-type"
                  value={stratumType}
                  onChange={(e) => setStratumType(e.target.value)}
                  className="w-full px-3 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                >
                  <option value="MANAGEMENT_PRACTICE">MANAGEMENT_PRACTICE</option>
                  <option value="SOIL_TYPE">SOIL_TYPE</option>
                  <option value="SOIL_TEXTURE">SOIL_TEXTURE</option>
                  <option value="AGRO_CLIMATIC_ZONE">AGRO_CLIMATIC_ZONE</option>
                  <option value="CROPPING_SYSTEM">CROPPING_SYSTEM</option>
                  <option value="TOPOGRAPHY">TOPOGRAPHY</option>
                  <option value="COMBINED">COMBINED</option>
                </select>
              </div>
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Description (Optional)</label>
                <textarea
                  data-testid="input-stratum-desc"
                  value={stratumDesc}
                  onChange={(e) => setStratumDesc(e.target.value)}
                  rows={2}
                  className="w-full px-3 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowStratumModal(false)}
                  className="px-3 py-1.5 rounded border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-background)] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  data-testid="btn-submit-stratum"
                  disabled={actionLoading}
                  className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold cursor-pointer"
                >
                  {actionLoading ? "Creating..." : "Save Stratum"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ASSIGN MEMBERS MODAL */}
      {assignStratumId && (
        <div data-testid="modal-assign-units" className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-lg bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl shadow-xl p-5 space-y-4">
            <h3 className="font-bold text-sm text-[var(--color-text-primary)]">Assign Land Units to Stratum</h3>
            <p className="text-xs text-[var(--color-text-secondary)]">
              Select land management units to associate with this analytical stratum.
            </p>
            <div className="max-h-60 overflow-y-auto space-y-1.5 border border-[var(--color-border)] p-2 rounded-lg">
              {landUnits.map((lu) => {
                const isSelected = selectedUnitIds.includes(lu.id);
                return (
                  <label
                    key={lu.id}
                    data-testid={`checkbox-unit-${lu.id}`}
                    className="flex items-center gap-2 p-2 rounded hover:bg-[var(--color-background)] text-xs cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={(e) => {
                        if (e.target.checked) setSelectedUnitIds([...selectedUnitIds, lu.id]);
                        else setSelectedUnitIds(selectedUnitIds.filter((id) => id !== lu.id));
                      }}
                      className="rounded"
                    />
                    <span className="font-medium text-[var(--color-text-primary)]">{lu.name}</span>
                    <span className="text-[var(--color-text-muted)] font-mono text-[11px]">
                      ({lu.area_ha.toFixed(2)} ha, {lu.unit_type})
                    </span>
                  </label>
                );
              })}
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setAssignStratumId(null)}
                className="px-3 py-1.5 rounded border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-background)] cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                data-testid="btn-save-assignments"
                onClick={handleAddMemberships}
                disabled={actionLoading}
                className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold cursor-pointer"
              >
                {actionLoading ? "Saving..." : `Assign (${selectedUnitIds.length}) Units`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CREATE MANAGEMENT RECORD MODAL */}
      {showRecordModal && (
        <div data-testid="modal-log-practice" className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl shadow-xl p-5 space-y-4">
            <h3 className="font-bold text-sm text-[var(--color-text-primary)]">Log Management Practice Event</h3>
            <form onSubmit={handleCreateManagementRecord} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[var(--color-text-secondary)] mb-1">Practice Category</label>
                  <select
                    data-testid="select-practice-category"
                    value={recCategory}
                    onChange={(e) => setRecCategory(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                  >
                    <option value="BASELINE">BASELINE (Pre-project)</option>
                    <option value="PROJECT_ACTIVITY">PROJECT_ACTIVITY</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[var(--color-text-secondary)] mb-1">Record Type</label>
                  <select
                    data-testid="select-record-type"
                    value={recType}
                    onChange={(e) => setRecType(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                  >
                    <option value="TILLAGE">TILLAGE</option>
                    <option value="FERTILIZER_SYNTHETIC">FERTILIZER_SYNTHETIC</option>
                    <option value="FERTILIZER_ORGANIC">FERTILIZER_ORGANIC</option>
                    <option value="CROP_ROTATION">CROP_ROTATION</option>
                    <option value="COVER_CROP">COVER_CROP</option>
                    <option value="IRRIGATION">IRRIGATION</option>
                    <option value="RESIDUE_BURNING">RESIDUE_BURNING</option>
                    <option value="GRAZING">GRAZING</option>
                    <option value="OTHER">OTHER</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[var(--color-text-secondary)] mb-1">Event Date</label>
                  <input
                    type="date"
                    required
                    data-testid="input-event-date"
                    value={recDate}
                    onChange={(e) => setRecDate(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                  />
                </div>
                <div>
                  <label className="block text-[var(--color-text-secondary)] mb-1">Data Source</label>
                  <select
                    data-testid="select-data-source"
                    value={recSource}
                    onChange={(e) => setRecSource(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                  >
                    <option value="FIELD_INTERVIEW">FIELD_INTERVIEW</option>
                    <option value="DOCUMENT">DOCUMENT</option>
                    <option value="FIELD_OBSERVATION">FIELD_OBSERVATION</option>
                    <option value="REMOTE_SENSING_CORROBORATED">REMOTE_SENSING_CORROBORATED</option>
                    <option value="REPORTED">REPORTED</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Corroboration Source</label>
                <select
                  data-testid="select-corroboration"
                  value={recCorroboration}
                  onChange={(e) => setRecCorroboration(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                >
                  <option value="NONE">NONE (Uncorroborated)</option>
                  <option value="REMOTE_SENSING">REMOTE_SENSING (Satellite / Spectral proxy)</option>
                  <option value="TELEMETRY">TELEMETRY (IoT / Machinery)</option>
                  <option value="DOCUMENTARY">DOCUMENTARY (Invoices / Weighbills)</option>
                  <option value="FIELD_REOBSERVATION">FIELD_REOBSERVATION (Field check)</option>
                  <option value="OTHER">OTHER (Contextual metadata)</option>
                </select>
              </div>

              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Target Land Unit (Optional)</label>
                <select
                  data-testid="select-target-unit"
                  value={recLandUnitId}
                  onChange={(e) => setRecLandUnitId(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                >
                  <option value="">Project-wide / All Units</option>
                  {landUnits.map((lu) => (
                    <option key={lu.id} value={lu.id}>
                      {lu.name} ({lu.unit_type})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Event Details (JSON or Notes)</label>
                <textarea
                  data-testid="input-event-details"
                  value={recDetails}
                  onChange={(e) => setRecDetails(e.target.value)}
                  rows={2}
                  placeholder='e.g. {"nitrogen_rate_kg_ha": 120, "type": "UREA"}'
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono text-[11px]"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowRecordModal(false)}
                  className="px-3 py-1.5 rounded border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-background)] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  data-testid="btn-submit-practice"
                  disabled={actionLoading}
                  className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold cursor-pointer"
                >
                  {actionLoading ? "Logging..." : "Log Event"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
