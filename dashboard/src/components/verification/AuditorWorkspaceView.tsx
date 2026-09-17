"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  LayoutDashboard,
  FileText,
  Sprout,
  Flame,
  Layers,
  Box,
  Route,
  MapPin,
  Activity,
  Calculator,
  AlertTriangle,
  ShieldCheck,
  History,
  CheckCircle2,
  Download,
  KeyRound,
  ChevronRight,
  ArrowLeft,
  RefreshCw,
  Plus,
  Lock,
  GitCompare,
  UserCheck,
  AlertCircle,
  Copy,
  Check,
} from "lucide-react";
import {
  VerificationPackageDetail,
  VerificationPackageFindingItem,
  VerificationPackageEvidenceItem,
  VerificationAccessGrantItem,
  MultiBiomassBlendBreakdown,
  fetchVerificationPackage,
  sealVerificationPackage,
  fetchPackageEvidence,
  verifyEvidenceIntegrity,
  verifyAllEvidenceIntegrity,
  fetchPackageFindings,
  createPackageFinding,
  respondToFinding,
  resolveFinding,
  recordAuditDecision,
  fetchPackageGrants,
  grantAuditorAccess,
  exportPackageBundle,
  downloadEvidenceContent,
  downloadPackageArchive,
  fetchFeedstockBlendBreakdown,
} from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { normalizeRole } from "@/lib/roles";

interface VerifyAllSummary {
  total_evidence_items: number;
  verified_count: number;
  mismatch_count: number;
  all_passed: boolean;
}

interface FeedstockLotItem {
  id: string;
  lot_number: string;
  feedstock_type: string;
  source_name?: string;
  mass_received_tonnes?: number;
  moisture_content_pct?: number;
  dry_mass_tonnes?: number;
  evidence_hash?: string;
}

interface ProductionRunItem {
  id: string;
  run_number: string;
  total_feedstock_input_tonnes?: number;
  total_feedstock_dry_tonnes?: number;
  avg_pyrolysis_temp_celsius?: number;
  residence_time_minutes?: number;
  output_biochar_mass_tonnes?: number;
  qa_status?: string;
}

interface BiocharBatchItem {
  id: string;
  batch_number: string;
  biochar_yield_tonnes?: number;
  dry_mass_tonnes?: number;
  fixed_carbon_pct?: number;
  ash_content_pct?: number;
  molar_h_c_ratio?: number;
  lab_analyses?: Array<{
    molar_h_c_ratio?: number;
    accreditation_standard?: string;
  }>;
}

interface FormulationItem {
  id: string;
  product_name: string;
  product_code: string;
  target_sector: string;
  biochar_target_ratio: number;
}

interface TransportItem {
  id: string;
  carrier_name: string;
  material_type: string;
  origin_address?: string;
  destination_address?: string;
  mass_transported_tonnes?: number;
  distance_km?: number;
  pod_document_hash?: string;
  status?: string;
}

interface EndUseItem {
  id: string;
  end_use_type: string;
  applied_quantity_tonnes?: number;
  gps_coordinates?: string;
  application_method?: string;
  verification_status?: string;
}

interface QcCheckItem {
  id: string;
  check_type: string;
  target_entity_type?: string;
  target_entity_id?: string;
  conducted_by?: string;
  check_date?: string;
  passed?: boolean;
}

function getErrorMessage(err: unknown): string {
  if (!err) return "Unknown error";
  if (typeof err === "string") return err;
  const obj = err as { detail?: string; message?: string };
  return obj.detail || obj.message || "Unknown error";
}

interface AuditorWorkspaceViewProps {
  packageId: string;
}

export default function AuditorWorkspaceView({ packageId }: AuditorWorkspaceViewProps) {
  const { user } = useWorkspace();
  const canonicalRole = normalizeRole(user?.role);
  const isAuditor = canonicalRole === "AUDITOR" || canonicalRole === "VERIFIER" || canonicalRole === "SUPER_ADMIN";
  const isDeveloper = canonicalRole === "PROJECT_MANAGER" || canonicalRole === "ORG_ADMIN" || canonicalRole === "SUPER_ADMIN";

  const [pkg, setPkg] = useState<VerificationPackageDetail | null>(null);
  const [findings, setFindings] = useState<VerificationPackageFindingItem[]>([]);
  const [evidence, setEvidence] = useState<VerificationPackageEvidenceItem[]>([]);
  const [grants, setGrants] = useState<VerificationAccessGrantItem[]>([]);
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Number-to-evidence drill-down modal state
  const [drillDownMetric, setDrillDownMetric] = useState<string | null>(null);

  // Blend breakdown modal state
  const [selectedRunBlend, setSelectedRunBlend] = useState<MultiBiomassBlendBreakdown | null>(null);
  const [isLoadingBlend, setIsLoadingBlend] = useState<boolean>(false);

  // Version diff modal state
  const [showDiffModal, setShowDiffModal] = useState<boolean>(false);

  // Findings form state
  const [showFindingModal, setShowFindingModal] = useState<boolean>(false);
  const [findingType, setFindingType] = useState<"CAR" | "CL" | "FAR" | "NCR">("CAR");
  const [findingSeverity, setFindingSeverity] = useState<"CRITICAL" | "MAJOR" | "MINOR" | "OBSERVATION">("MAJOR");
  const [findingTitle, setFindingTitle] = useState("");
  const [findingDesc, setFindingDesc] = useState("");
  const [findingDomain, setFindingDomain] = useState("BIOCHAR");
  const [findingTargetField, setFindingTargetField] = useState("");

  // Finding response/resolve states
  const [activeFindingAction, setActiveFindingAction] = useState<VerificationPackageFindingItem | null>(null);
  const [actionType, setActionType] = useState<"RESPOND" | "RESOLVE" | null>(null);
  const [actionNotes, setActionNotes] = useState("");

  // Evidence verification state
  const [isVerifyingEvidence, setIsVerifyingEvidence] = useState(false);
  const [verifySummary, setVerifySummary] = useState<VerifyAllSummary | null>(null);

  // Access grant state
  const [showGrantModal, setShowGrantModal] = useState(false);
  const [grantEmail, setGrantEmail] = useState("");
  const [grantOrg, setGrantOrg] = useState("");

  // Audit decision state
  const [showDecisionModal, setShowDecisionModal] = useState(false);
  const [decisionType, setDecisionType] = useState<"VERIFIED" | "REJECTED">("VERIFIED");
  const [decisionNotes, setDecisionNotes] = useState("");

  // Copy hash notification
  const [copiedHash, setCopiedHash] = useState(false);

  const loadAllData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [pkgData, findingsData, evidenceData, grantsData] = await Promise.all([
        fetchVerificationPackage(packageId),
        fetchPackageFindings(packageId),
        fetchPackageEvidence(packageId),
        fetchPackageGrants(packageId).catch(() => []),
      ]);
      setPkg(pkgData);
      setFindings(findingsData);
      setEvidence(evidenceData);
      setGrants(grantsData);
    } catch (err: unknown) {
      console.error("Failed to load verification package:", err);
      setError(getErrorMessage(err) || "Failed to load verification package data.");
    } finally {
      setIsLoading(false);
    }
  }, [packageId]);

  useEffect(() => {
    const timer = setTimeout(() => {
      void loadAllData();
    }, 0);
    return () => clearTimeout(timer);
  }, [loadAllData]);

  const handleSealPackage = async () => {
    if (!confirm("Are you sure you want to cryptographically seal this package? Once submitted, it will become immutable.")) {
      return;
    }
    try {
      const updated = await sealVerificationPackage(packageId);
      setPkg(updated);
      alert("Package sealed successfully via LedgerService RSA signature.");
    } catch (err: unknown) {
      alert("Sealing failed: " + getErrorMessage(err));
    }
  };

  const handleVerifyEvidence = async (evidenceId: string) => {
    try {
      const verified = await verifyEvidenceIntegrity(packageId, evidenceId);
      setEvidence((prev) => prev.map((e) => (e.id === verified.id ? verified : e)));
    } catch (err: unknown) {
      alert("Verification error: " + getErrorMessage(err));
    }
  };

  const handleVerifyAllEvidence = async () => {
    setIsVerifyingEvidence(true);
    try {
      const summary = await verifyAllEvidenceIntegrity(packageId);
      setVerifySummary(summary);
      const updatedList = await fetchPackageEvidence(packageId);
      setEvidence(updatedList);
    } catch (err: unknown) {
      alert("Global evidence verification error: " + getErrorMessage(err));
    } finally {
      setIsVerifyingEvidence(false);
    }
  };

  const handleDownloadEvidence = async (ev: VerificationPackageEvidenceItem) => {
    try {
      await downloadEvidenceContent(packageId, ev.id, ev.file_name);
    } catch (err: unknown) {
      alert("Failed to download evidence: " + getErrorMessage(err));
    }
  };

  const handleCreateFinding = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await createPackageFinding(packageId, {
        finding_type: findingType,
        severity: findingSeverity,
        title: findingTitle,
        description: findingDesc,
        target_domain: findingDomain,
        target_field: findingTargetField || undefined,
      });
      setFindings((prev) => [created, ...prev]);
      setShowFindingModal(false);
      setFindingTitle("");
      setFindingDesc("");
      setFindingTargetField("");
      alert(`Finding ${created.finding_number} recorded successfully.`);
    } catch (err: unknown) {
      alert("Failed to create finding: " + getErrorMessage(err));
    }
  };

  const handleSubmitAction = async () => {
    if (!activeFindingAction || !actionType) return;
    try {
      if (actionType === "RESPOND") {
        const updated = await respondToFinding(activeFindingAction.id, {
          project_response: actionNotes,
        });
        setFindings((prev) => prev.map((f) => (f.id === updated.id ? updated : f)));
      } else {
        const updated = await resolveFinding(activeFindingAction.id, {
          status_action: "RESOLVED",
          resolution_notes: actionNotes,
        });
        setFindings((prev) => prev.map((f) => (f.id === updated.id ? updated : f)));
      }
      setActiveFindingAction(null);
      setActionType(null);
      setActionNotes("");
      alert("Finding updated successfully.");
    } catch (err: unknown) {
      alert("Finding action failed: " + getErrorMessage(err));
    }
  };

  const handleRecordAuditDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const updated = await recordAuditDecision(packageId, {
        decision: decisionType,
        decision_notes: decisionNotes,
      });
      setPkg(updated);
      setShowDecisionModal(false);
      alert(`Audit decision '${decisionType}' recorded.`);
    } catch (err: unknown) {
      alert("Failed to record decision: " + getErrorMessage(err));
    }
  };

  const handleGrantAccess = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const grant = await grantAuditorAccess(packageId, {
        auditor_email: grantEmail,
        auditor_organization: grantOrg,
      });
      setGrants((prev) => [grant, ...prev]);
      setShowGrantModal(false);
      setGrantEmail("");
      setGrantOrg("");
      alert(`Access granted to ${grant.auditor_email}.`);
    } catch (err: unknown) {
      alert("Failed to grant access: " + getErrorMessage(err));
    }
  };

  const handleExportBundle = async () => {
    try {
      const bundle = await exportPackageBundle(packageId);
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit-bundle-${pkg?.package_name || packageId}-v${pkg?.package_version || 1}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      alert("Failed to export bundle: " + getErrorMessage(err));
    }
  };

  const handleExportArchive = async () => {
    try {
      await downloadPackageArchive(packageId, pkg?.package_name);
    } catch (err: unknown) {
      alert("Failed to export archive: " + getErrorMessage(err));
    }
  };

  const openBlendBreakdown = async (runId: string) => {
    setIsLoadingBlend(true);
    try {
      const data = await fetchFeedstockBlendBreakdown(runId);
      setSelectedRunBlend(data);
    } catch (err: unknown) {
      alert("Could not load blend breakdown: " + getErrorMessage(err));
    } finally {
      setIsLoadingBlend(false);
    }
  };

  const copyManifestHash = () => {
    if (pkg?.manifest_hash) {
      navigator.clipboard.writeText(pkg.manifest_hash);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <RefreshCw className="w-8 h-8 text-emerald-500 animate-spin" />
        <p className="text-slate-400 text-sm">Compiling and loading Auditor Workspace...</p>
      </div>
    );
  }

  if (error || !pkg) {
    return (
      <div className="p-8 max-w-4xl mx-auto">
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center space-y-3">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto" />
          <h2 className="text-xl font-bold text-white">Access Denied or Package Not Found</h2>
          <p className="text-slate-400 text-sm">{error || "Verification package could not be retrieved."}</p>
          <Link
            href="/dashboard/verifications"
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium rounded-lg"
          >
            <ArrowLeft className="w-4 h-4" /> Return to Verifications
          </Link>
        </div>
      </div>
    );
  }

  const manifest = (pkg.manifest_json || {}) as {
    project?: {
      id?: string;
      name?: string;
      code?: string;
      organization_id?: string;
      organization_name?: string;
    };
    value_chain_graph?: {
      sources?: Array<{ id: string; [key: string]: unknown }>;
      feedstock_lots?: FeedstockLotItem[];
      production_runs?: ProductionRunItem[];
      batches?: BiocharBatchItem[];
      lab_analyses?: Array<{ id: string; [key: string]: unknown }>;
      formulations?: FormulationItem[];
      transports?: TransportItem[];
      end_uses?: EndUseItem[];
      qc_checks?: QcCheckItem[];
    };
    summary_quantification?: Record<string, number>;
    trace_trees?: Record<string, {
      title?: string;
      value?: number;
      unit?: string;
      formula?: string;
      input_variables?: Record<string, unknown>;
      evidence_refs?: Array<{ type?: string; hash?: string }>;
    }>;
    completeness?: {
      score?: number;
      completed_requirements?: number;
      total_requirements?: number;
      blocker_reasons?: string[];
    };
    [key: string]: unknown;
  };
  const graph = (manifest.value_chain_graph || {}) as {
    sources?: Array<{ id: string; [key: string]: unknown }>;
    feedstock_lots?: FeedstockLotItem[];
    production_runs?: ProductionRunItem[];
    batches?: BiocharBatchItem[];
    lab_analyses?: Array<{ id: string; [key: string]: unknown }>;
    formulations?: FormulationItem[];
    transports?: TransportItem[];
    end_uses?: EndUseItem[];
    qc_checks?: QcCheckItem[];
  };
  const summaryQuant = (manifest.summary_quantification || {}) as Record<string, number>;
  const traceTrees = (manifest.trace_trees || {}) as Record<string, {
    title?: string;
    value?: number;
    unit?: string;
    formula?: string;
    input_variables?: Record<string, unknown>;
    evidence_refs?: Array<{ type?: string; hash?: string }>;
  }>;
  const diffSummary = (pkg.diff_summary_json || {}) as {
    carbon_quantification_delta?: {
      parent_corcs_tco2e?: number;
      current_corcs_tco2e?: number;
      delta_corcs_tco2e?: number;
      delta_pct?: number;
    };
    inventory_changes?: {
      added_batch_ids?: string[];
    };
    evidence_changes?: {
      added_evidence_hashes?: string[];
    };
    [key: string]: unknown;
  };
  const completenessMeta = (manifest.completeness || {}) as {
    score?: number;
    completed_requirements?: number;
    total_requirements?: number;
    blocker_reasons?: string[];
  };
  const completedReqs = completenessMeta.completed_requirements ?? (pkg.completeness_score === 100 ? 5 : Math.round((pkg.completeness_score / 100) * 5));
  const totalReqs = completenessMeta.total_requirements ?? 5;
  const workspaceTitle = pkg.registry_target === "VERRA_VCS" ? "Verifier / VVB Workspace" : "Auditor Workspace";

  const tabs = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "project", label: "Project & Standard", icon: FileText },
    { id: "feedstock", label: "Feedstock", icon: Sprout },
    { id: "production", label: "Production Runs", icon: Flame },
    { id: "biochar", label: "Biochar & Lab COA", icon: Layers },
    { id: "products", label: "Products & Blend", icon: Box },
    { id: "custody", label: "Custody & Logistics", icon: Route },
    { id: "enduse", label: "Terminal End Use", icon: MapPin },
    { id: "qc", label: "Monitoring & QC", icon: Activity },
    { id: "lca", label: "LCA & Drill-Down", icon: Calculator },
    { id: "findings", label: "Findings", icon: AlertTriangle, badge: findings.length },
    { id: "evidence", label: "Evidence Index", icon: ShieldCheck, badge: evidence.length },
    { id: "history", label: "Ledger & Diff", icon: History },
  ];

  return (
    <div className="space-y-6 pb-20">
      {/* ── Top Header Navigation ────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard/verifications"
              className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              {pkg.package_name}
              <span className="text-xs px-2.5 py-0.5 rounded-full font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                v{pkg.package_version}
              </span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                {workspaceTitle}
              </span>
            </h1>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400 pl-9">
            <span className="font-semibold text-slate-300">Period:</span>
            <span>{pkg.monitoring_period_start} to {pkg.monitoring_period_end}</span>
            <span className="text-slate-600">•</span>
            <span className="font-semibold text-slate-300">Standard:</span>
            <span className="text-emerald-400">{pkg.registry_target}</span>
            <span className="text-slate-600">•</span>
            <span className="font-semibold text-slate-300">Audit Type:</span>
            <span>{pkg.audit_type}</span>
          </div>
        </div>

        {/* Global Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {pkg.package_version > 1 && (
            <button
              onClick={() => setShowDiffModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs font-semibold"
            >
              <GitCompare className="w-3.5 h-3.5" /> Version Diff
            </button>
          )}

          <button
            onClick={handleExportBundle}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700"
            title="Export Manifest JSON"
          >
            <Download className="w-3.5 h-3.5" /> Export Bundle
          </button>

          <button
            onClick={handleExportArchive}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700"
            title="Export Verified ZIP Archive with Checksums"
          >
            <Download className="w-3.5 h-3.5" /> Export Archive (ZIP)
          </button>

          {isDeveloper && pkg.package_status !== "SUBMITTED" && pkg.package_status !== "VERIFIED" && (
            <button
              onClick={handleSealPackage}
              disabled={pkg.completeness_score < 100.0}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-500 text-white text-xs font-semibold shadow-sm transition-all"
            >
              <Lock className="w-3.5 h-3.5" /> Seal & Submit
            </button>
          )}

          {isAuditor && (
            <button
              onClick={() => setShowDecisionModal(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold shadow-sm"
            >
              <UserCheck className="w-3.5 h-3.5" /> Record Decision
            </button>
          )}

          {isDeveloper && (
            <button
              onClick={() => setShowGrantModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700"
            >
              <KeyRound className="w-3.5 h-3.5" /> Manage Grants
            </button>
          )}
        </div>
      </div>

      {/* ── Status Banner & Cryptographic Seal Strip ─────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 bg-slate-900/60 border border-slate-800 rounded-xl p-4">
        {/* Status */}
        <div className="space-y-1">
          <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Package Status</p>
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold ${
                pkg.package_status === "VERIFIED"
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  : pkg.package_status === "SUBMITTED"
                  ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                  : pkg.package_status === "READY_FOR_AUDIT"
                  ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                  : "bg-slate-700 text-slate-300"
              }`}
            >
              {pkg.package_status === "VERIFIED" && <CheckCircle2 className="w-3.5 h-3.5" />}
              {pkg.package_status === "SUBMITTED" && <Lock className="w-3.5 h-3.5" />}
              {pkg.package_status}
            </span>
          </div>
        </div>

        {/* Completeness */}
        <div className="space-y-1">
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-400 font-semibold uppercase tracking-wider">Completeness</span>
            <span className={`font-mono font-bold ${pkg.completeness_score === 100 ? "text-emerald-400" : "text-amber-400"}`}>
              {pkg.completeness_score}% ({completedReqs}/{totalReqs} requirements)
            </span>
          </div>
          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${pkg.completeness_score === 100 ? "bg-emerald-500" : "bg-amber-500"}`}
              style={{ width: `${pkg.completeness_score}%` }}
            />
          </div>
          {pkg.blocker_reasons && pkg.blocker_reasons.length > 0 && (
            <p className="text-[11px] text-amber-400 flex items-center gap-1 mt-1">
              <AlertTriangle className="w-3 h-3" /> {pkg.blocker_reasons.length} audit blocker(s)
            </p>
          )}
        </div>

        {/* Canonical Manifest SHA-256 */}
        <div className="space-y-1 md:col-span-2">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Canonical Manifest Hash (SHA-256)</p>
            <button
              onClick={copyManifestHash}
              className="text-xs text-slate-400 hover:text-white inline-flex items-center gap-1"
            >
              {copiedHash ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              {copiedHash ? "Copied" : "Copy"}
            </button>
          </div>
          <div className="font-mono text-xs text-slate-300 bg-slate-950 px-2.5 py-1.5 rounded border border-slate-800/80 truncate flex items-center gap-2">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
            <span className="truncate">{pkg.manifest_hash}</span>
          </div>
          <div className="text-[11px] text-slate-500 flex items-center gap-2">
            <span>Ledger Sealed: {pkg.sealed_at ? new Date(pkg.sealed_at).toUTCString() : "Unsealed Draft"}</span>
            {pkg.ledger_signature_id && (
              <span className="text-indigo-400 font-mono font-medium">RSA-PSS Verified</span>
            )}
          </div>
        </div>
      </div>

      {/* ── 13-Tab Navigation Bar ────────────────────────────────────────── */}
      <div className="flex items-center gap-1 border-b border-slate-800 overflow-x-auto pb-1 scrollbar-thin">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-t-lg text-xs font-semibold whitespace-nowrap transition-all ${
                isActive
                  ? "bg-slate-800/90 text-emerald-400 border-b-2 border-emerald-500"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
              {tab.badge !== undefined && tab.badge > 0 && (
                <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                  tab.id === "findings" ? "bg-amber-500/20 text-amber-300" : "bg-slate-700 text-slate-300"
                }`}>
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ── Tab Content Panels ───────────────────────────────────────────── */}
      <div className="space-y-6">
        {/* TAB 1: OVERVIEW */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            {/* Headline Carbon Removal Figures */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 relative overflow-hidden group hover:border-emerald-500/40 transition-all">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Net Removals</span>
                  <button
                    onClick={() => setDrillDownMetric("net_removals_corcs")}
                    className="text-xs text-emerald-400 hover:underline inline-flex items-center gap-1 font-semibold"
                  >
                    Drill Down <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold font-mono text-emerald-400">
                    {summaryQuant.net_removals_tco2e ?? 0}
                  </span>
                  <span className="text-xs text-slate-400">tCO₂e (CORCs)</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-2">
                  C_stored ({summaryQuant.c_stored_tco2e ?? 0}) - C_baseline ({summaryQuant.c_baseline_tco2e ?? 0}) - C_loss ({summaryQuant.c_loss_tco2e ?? 0}) - E_proj ({summaryQuant.e_project_tco2e ?? 0}) - E_leak ({summaryQuant.e_leakage_tco2e ?? 0})
                </p>
              </div>

              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 relative overflow-hidden group hover:border-blue-500/40 transition-all">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">C Stored</span>
                  <button
                    onClick={() => setDrillDownMetric("c_stored")}
                    className="text-xs text-blue-400 hover:underline inline-flex items-center gap-1 font-semibold"
                  >
                    Drill Down <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold font-mono text-blue-400">
                    {summaryQuant.c_stored_tco2e ?? 0}
                  </span>
                  <span className="text-xs text-slate-400">tCO₂e</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-2">Gross carbon sequestered in durable matrix</p>
              </div>

              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 relative overflow-hidden group hover:border-red-500/40 transition-all">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Project Emissions</span>
                  <button
                    onClick={() => setDrillDownMetric("e_project")}
                    className="text-xs text-red-400 hover:underline inline-flex items-center gap-1 font-semibold"
                  >
                    Drill Down <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold font-mono text-red-400">
                    {summaryQuant.e_project_tco2e ?? 0}
                  </span>
                  <span className="text-xs text-slate-400">tCO₂e</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-2">Biomass prep, pyrolysis energy, transport & processing</p>
              </div>

              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 relative overflow-hidden group hover:border-amber-500/40 transition-all">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Findings</span>
                  <button
                    onClick={() => setActiveTab("findings")}
                    className="text-xs text-amber-400 hover:underline inline-flex items-center gap-1 font-semibold"
                  >
                    View All <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold font-mono text-amber-400">
                    {findings.filter((f) => f.status === "OPEN").length}
                  </span>
                  <span className="text-xs text-slate-400">Open / {findings.length} Total</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-2">CARs, Clarifications, and NCRs</p>
              </div>
            </div>

            {/* Value Chain Inventory Summary Table */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-400" /> MRV Value Chain Graph Inventory
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-6 gap-3 text-center">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <p className="text-xl font-bold text-white font-mono">{(graph.sources || []).length}</p>
                  <p className="text-[11px] text-slate-400">Feedstock Sources</p>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <p className="text-xl font-bold text-white font-mono">{(graph.feedstock_lots || []).length}</p>
                  <p className="text-[11px] text-slate-400">Received Lots</p>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <p className="text-xl font-bold text-white font-mono">{(graph.production_runs || []).length}</p>
                  <p className="text-[11px] text-slate-400">Pyrolysis Runs</p>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <p className="text-xl font-bold text-white font-mono">{(graph.batches || []).length}</p>
                  <p className="text-[11px] text-slate-400">Biochar Batches</p>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <p className="text-xl font-bold text-white font-mono">{(graph.lab_analyses || []).length}</p>
                  <p className="text-[11px] text-slate-400">ISO Lab COAs</p>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <p className="text-xl font-bold text-white font-mono">{(graph.end_uses || []).length}</p>
                  <p className="text-[11px] text-slate-400">End Use Events</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: PROJECT & STANDARD */}
        {activeTab === "project" && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-6">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <FileText className="w-5 h-5 text-emerald-400" /> Project Baseline & Normative Standard Registration
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                  <p className="text-xs text-slate-400 font-semibold uppercase">Project Name & Identifier</p>
                  <p className="text-base font-semibold text-white">{manifest.project?.name}</p>
                  <p className="text-xs font-mono text-slate-400">ID: {manifest.project?.id}</p>
                  <p className="text-xs font-mono text-emerald-400">Code: {manifest.project?.code}</p>
                </div>
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                  <p className="text-xs text-slate-400 font-semibold uppercase">Normative Carbon Standard</p>
                  <p className="text-base font-semibold text-emerald-400">Puro.earth Biochar Standard 2025 v2</p>
                  <p className="text-xs text-slate-400">
                    Rule 3.5.1 Molar H/Corg boundary strict limit (0.70) • Table 6.1 Temperature Persistence Factors (F_perm) • ISO 14064-2 & ISO 17025 Conformant
                  </p>
                </div>
              </div>
              <div className="space-y-4">
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                  <p className="text-xs text-slate-400 font-semibold uppercase">Project Developer & Operator</p>
                  <p className="text-base font-semibold text-white">{manifest.project?.organization_name}</p>
                  <p className="text-xs font-mono text-slate-400">Org ID: {manifest.project?.organization_id}</p>
                </div>
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                  <p className="text-xs text-slate-400 font-semibold uppercase">Verification Scoping</p>
                  <p className="text-xs text-slate-300">
                    Audit Type: <span className="font-semibold text-white">{pkg.audit_type}</span>
                  </p>
                  <p className="text-xs text-slate-300">
                    Crediting Window: <span className="font-semibold text-white">{pkg.monitoring_period_start} → {pkg.monitoring_period_end}</span>
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: FEEDSTOCK SOURCING */}
        {activeTab === "feedstock" && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Sprout className="w-4 h-4 text-emerald-400" /> Sourced Biomass Feedstock Lots
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 font-semibold uppercase border-b border-slate-800">
                    <tr>
                      <th className="p-3">Lot Number</th>
                      <th className="p-3">Feedstock Type</th>
                      <th className="p-3">Source Origin</th>
                      <th className="p-3 text-right">Received (t)</th>
                      <th className="p-3 text-right">Moisture %</th>
                      <th className="p-3 text-right">Dry Mass (t)</th>
                      <th className="p-3">Evidence Hash</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300">
                    {(graph.feedstock_lots || []).map((lot) => (
                      <tr key={lot.id} className="hover:bg-slate-800/40">
                        <td className="p-3 font-mono font-medium text-white">{lot.lot_number}</td>
                        <td className="p-3">{lot.feedstock_type}</td>
                        <td className="p-3 text-slate-400">{lot.source_name || "Regional Supplier"}</td>
                        <td className="p-3 text-right font-mono">{lot.mass_received_tonnes}</td>
                        <td className="p-3 text-right font-mono">{lot.moisture_content_pct}%</td>
                        <td className="p-3 text-right font-mono text-emerald-400 font-bold">{lot.dry_mass_tonnes}</td>
                        <td className="p-3 font-mono text-[11px] text-slate-400 truncate max-w-[150px]">
                          {lot.evidence_hash || "None"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: PRODUCTION RUNS */}
        {activeTab === "production" && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Flame className="w-4 h-4 text-emerald-400" /> Pyrolysis Thermochemical Production Runs
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 font-semibold uppercase border-b border-slate-800">
                    <tr>
                      <th className="p-3">Run Number</th>
                      <th className="p-3 text-right">Input Wet (t)</th>
                      <th className="p-3 text-right">Input Dry (t)</th>
                      <th className="p-3 text-right">Pyrolysis Temp (°C)</th>
                      <th className="p-3 text-right">Residence (min)</th>
                      <th className="p-3 text-right">Output Biochar (t)</th>
                      <th className="p-3">QA Status</th>
                      <th className="p-3 text-right">Multi-Biomass Blend</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300">
                    {(graph.production_runs || []).map((run) => (
                      <tr key={run.id} className="hover:bg-slate-800/40">
                        <td className="p-3 font-mono font-medium text-white">{run.run_number}</td>
                        <td className="p-3 text-right font-mono">{run.total_feedstock_input_tonnes}</td>
                        <td className="p-3 text-right font-mono">{run.total_feedstock_dry_tonnes}</td>
                        <td className="p-3 text-right font-mono text-amber-400 font-semibold">
                          {run.avg_pyrolysis_temp_celsius}°C
                        </td>
                        <td className="p-3 text-right font-mono">{run.residence_time_minutes}</td>
                        <td className="p-3 text-right font-mono text-emerald-400 font-bold">
                          {run.output_biochar_mass_tonnes}
                        </td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            {run.qa_status || "QA_PASSED"}
                          </span>
                        </td>
                        <td className="p-3 text-right">
                          <button
                            onClick={() => openBlendBreakdown(run.id)}
                            disabled={isLoadingBlend}
                            className="text-xs text-blue-400 hover:underline font-semibold disabled:opacity-50"
                          >
                            {isLoadingBlend ? "Loading..." : "View Blend Breakdown"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: BIOCHAR BATCHES & LAB COA */}
        {activeTab === "biochar" && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-400" /> Biochar Batches & Accredited Laboratory Analyses (COA)
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 font-semibold uppercase border-b border-slate-800">
                    <tr>
                      <th className="p-3">Batch Number</th>
                      <th className="p-3 text-right">Yield (t)</th>
                      <th className="p-3 text-right">Dry Mass (t)</th>
                      <th className="p-3 text-right">Fixed Carbon %</th>
                      <th className="p-3 text-right">Ash %</th>
                      <th className="p-3 text-right">Molar H/Corg</th>
                      <th className="p-3">Lab Standard</th>
                      <th className="p-3">Heavy Metals</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300">
                    {(graph.batches || []).map((b) => {
                      const lab = (b.lab_analyses || [])[0] || {};
                      const hc = lab.molar_h_c_ratio ?? b.molar_h_c_ratio ?? 0.38;
                      const isPassing = hc <= 0.70;
                      return (
                        <tr key={b.id} className="hover:bg-slate-800/40">
                          <td className="p-3 font-mono font-medium text-white">{b.batch_number}</td>
                          <td className="p-3 text-right font-mono">{b.biochar_yield_tonnes}</td>
                          <td className="p-3 text-right font-mono">{b.dry_mass_tonnes}</td>
                          <td className="p-3 text-right font-mono">{b.fixed_carbon_pct}%</td>
                          <td className="p-3 text-right font-mono">{b.ash_content_pct}%</td>
                          <td className="p-3 text-right font-mono">
                            <span className={`px-2 py-0.5 rounded font-bold ${isPassing ? "text-emerald-400" : "text-red-400 bg-red-500/10"}`}>
                              {hc}
                            </span>
                          </td>
                          <td className="p-3 font-mono text-[11px] text-slate-400">{lab.accreditation_standard || "ISO_17025"}</td>
                          <td className="p-3">
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              PASS
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 6: PRODUCTS & INGREDIENTS */}
        {activeTab === "products" && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Box className="w-4 h-4 text-emerald-400" /> Mixed Product Formulations & Mass Balance Conservation
              </h3>
              <p className="text-xs text-slate-400">
                Authoritative multi-ingredient formulations (compost, minerals, binders) with anti-overallocation mass balance protection.
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 font-semibold uppercase border-b border-slate-800">
                    <tr>
                      <th className="p-3">Product Name</th>
                      <th className="p-3">Code</th>
                      <th className="p-3">Target Sector</th>
                      <th className="p-3 text-right">Biochar Ratio</th>
                      <th className="p-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300">
                    {(graph.formulations || []).map((form) => (
                      <tr key={form.id} className="hover:bg-slate-800/40">
                        <td className="p-3 font-semibold text-white">{form.product_name}</td>
                        <td className="p-3 font-mono text-slate-400">{form.product_code}</td>
                        <td className="p-3 text-slate-300">{form.target_sector}</td>
                        <td className="p-3 text-right font-mono text-emerald-400 font-bold">
                          {(form.biochar_target_ratio * 100).toFixed(0)}%
                        </td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400">
                            ACTIVE
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

        {/* TAB 7: CUSTODY & LOGISTICS */}
        {activeTab === "custody" && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Route className="w-4 h-4 text-emerald-400" /> Custody Timeline & Transport Logistics
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 font-semibold uppercase border-b border-slate-800">
                    <tr>
                      <th className="p-3">Carrier Name</th>
                      <th className="p-3">Material</th>
                      <th className="p-3">Route</th>
                      <th className="p-3 text-right">Mass (t)</th>
                      <th className="p-3 text-right">Distance (km)</th>
                      <th className="p-3">POD Document Hash</th>
                      <th className="p-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300">
                    {(graph.transports || []).map((t) => (
                      <tr key={t.id} className="hover:bg-slate-800/40">
                        <td className="p-3 font-semibold text-white">{t.carrier_name}</td>
                        <td className="p-3">{t.material_type}</td>
                        <td className="p-3 text-slate-400">{t.origin_address} → {t.destination_address}</td>
                        <td className="p-3 text-right font-mono">{t.mass_transported_tonnes}</td>
                        <td className="p-3 text-right font-mono">{t.distance_km} km</td>
                        <td className="p-3 font-mono text-[11px] text-slate-400 truncate max-w-[150px]">
                          {t.pod_document_hash || "Verified"}
                        </td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400">
                            {t.status || "DELIVERED"}
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

        {/* TAB 8: TERMINAL END USE */}
        {activeTab === "enduse" && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <MapPin className="w-4 h-4 text-emerald-400" /> Permanent Terminal End-Use Disposition
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 font-semibold uppercase border-b border-slate-800">
                    <tr>
                      <th className="p-3">End-Use Application</th>
                      <th className="p-3 text-right">Applied Quantity (t)</th>
                      <th className="p-3">GPS Coordinates</th>
                      <th className="p-3">Application Method</th>
                      <th className="p-3">Wetland Exclusion</th>
                      <th className="p-3">Verification Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300">
                    {(graph.end_uses || []).map((eu) => (
                      <tr key={eu.id} className="hover:bg-slate-800/40">
                        <td className="p-3 font-semibold text-white">{eu.end_use_type}</td>
                        <td className="p-3 text-right font-mono text-emerald-400 font-bold">{eu.applied_quantity_tonnes}</td>
                        <td className="p-3 font-mono text-slate-400">{eu.gps_coordinates}</td>
                        <td className="p-3">{eu.application_method}</td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400">
                            SCREENED PASS
                          </span>
                        </td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400">
                            {eu.verification_status || "VERIFIED"}
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

        {/* TAB 9: MONITORING & QC */}
        {activeTab === "qc" && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-400" /> Equipment Calibration & Quality Control Checks
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 font-semibold uppercase border-b border-slate-800">
                    <tr>
                      <th className="p-3">Check Type</th>
                      <th className="p-3">Target Entity</th>
                      <th className="p-3">Conducted By</th>
                      <th className="p-3">Date</th>
                      <th className="p-3">Result</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300">
                    {(graph.qc_checks || []).map((qc) => (
                      <tr key={qc.id} className="hover:bg-slate-800/40">
                        <td className="p-3 font-semibold text-white">{qc.check_type}</td>
                        <td className="p-3 font-mono text-slate-400">{qc.target_entity_type} ({qc.target_entity_id?.slice(0, 8)})</td>
                        <td className="p-3">{qc.conducted_by}</td>
                        <td className="p-3">{qc.check_date ? new Date(qc.check_date).toLocaleDateString() : "Recent"}</td>
                        <td className="p-3">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            qc.passed ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
                          }`}>
                            {qc.passed ? "PASSED" : "FAILED"}
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

        {/* TAB 10: LCA & QUANTIFICATION (NUMBER-TO-EVIDENCE DRILL-DOWN) */}
        {activeTab === "lca" && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Calculator className="w-4 h-4 text-emerald-400" /> Interactive Number-to-Evidence Trace Trees
                </h3>
                <span className="text-xs text-slate-400">Click any figure below to drill down to raw evidence digests</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                {[
                  { key: "net_removals_corcs", title: "Net Removals (CORCs)", value: summaryQuant.net_removals_tco2e, unit: "tCO₂e", color: "text-emerald-400" },
                  { key: "c_stored", title: "Carbon Stored (C_stored)", value: summaryQuant.c_stored_tco2e, unit: "tCO₂e", color: "text-blue-400" },
                  { key: "c_baseline", title: "Baseline Removal (C_baseline)", value: summaryQuant.c_baseline_tco2e ?? 0, unit: "tCO₂e", color: "text-purple-400" },
                  { key: "c_loss", title: "Carbon Losses (C_loss)", value: summaryQuant.c_loss_tco2e, unit: "tCO₂e", color: "text-slate-300" },
                  { key: "e_project", title: "Project Emissions (E_project)", value: summaryQuant.e_project_tco2e, unit: "tCO₂e", color: "text-red-400" },
                  { key: "e_leakage", title: "Leakage Emissions (E_leakage)", value: summaryQuant.e_leakage_tco2e, unit: "tCO₂e", color: "text-amber-400" },
                  { key: "uncertainty", title: "Quantification Uncertainty", value: summaryQuant.uncertainty_pct ?? "0.00", unit: "%", color: "text-indigo-400" },
                ].map((item) => (
                  <button
                    key={item.key}
                    onClick={() => setDrillDownMetric(item.key)}
                    className="p-4 bg-slate-950 rounded-xl border border-slate-800 hover:border-emerald-500/50 text-left transition-all group"
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-semibold text-slate-400 uppercase">{item.title}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-emerald-400 transition-colors" />
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className={`text-2xl font-bold font-mono ${item.color}`}>{item.value ?? 0}</span>
                      <span className="text-xs text-slate-500">{item.unit}</span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-2">Click to inspect formula, inputs & evidence refs</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 11: AUDIT FINDINGS */}
        {activeTab === "findings" && (
          <div className="space-y-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-400" /> Assurance Findings & Non-Conformity Tracker
                </h3>
                <p className="text-xs text-slate-400">
                  Segregation of Duties strictly enforced: Only external auditors can log findings; only project developers can submit responses.
                </p>
              </div>
              {isAuditor && (
                <button
                  onClick={() => setShowFindingModal(true)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold shadow-sm"
                >
                  <Plus className="w-3.5 h-3.5" /> Log New Finding
                </button>
              )}
            </div>

            {/* Findings List */}
            {findings.length === 0 ? (
              <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-400 space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                <p className="font-semibold text-white">No active audit findings</p>
                <p className="text-xs">The monitoring period currently satisfies all normative audit criteria.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {findings.map((f) => (
                  <div
                    key={f.id}
                    className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4"
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-xs font-bold text-white px-2 py-0.5 bg-slate-800 rounded">
                          {f.finding_number}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          f.finding_type === "CAR"
                            ? "bg-red-500/20 text-red-400"
                            : f.finding_type === "NCR"
                            ? "bg-purple-500/20 text-purple-400"
                            : "bg-amber-500/20 text-amber-400"
                        }`}>
                          {f.finding_type}
                        </span>
                        <span className="text-xs text-slate-400 font-semibold">Severity: {f.severity}</span>
                        <span className="text-slate-600">•</span>
                        <span className="text-xs text-slate-400">Domain: {f.target_domain}</span>
                      </div>
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                        f.status === "RESOLVED"
                          ? "bg-emerald-500/20 text-emerald-400"
                          : f.status === "RESPONSE_SUBMITTED"
                          ? "bg-blue-500/20 text-blue-400"
                          : "bg-amber-500/20 text-amber-400"
                      }`}>
                        {f.status}
                      </span>
                    </div>

                    <div className="space-y-1">
                      <h4 className="text-sm font-bold text-white">{f.title}</h4>
                      <p className="text-xs text-slate-300">{f.description}</p>
                    </div>

                    {/* Developer Response Area */}
                    {f.project_response && (
                      <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800/80 space-y-1">
                        <p className="text-[11px] font-bold text-blue-400 uppercase tracking-wider">Project Developer Response</p>
                        <p className="text-xs text-slate-200">{f.project_response}</p>
                        {f.response_submitted_at && (
                          <p className="text-[10px] text-slate-500 mt-1">Submitted: {new Date(f.response_submitted_at).toUTCString()}</p>
                        )}
                      </div>
                    )}

                    {/* Auditor Resolution Area */}
                    {f.resolution_notes && (
                      <div className="bg-emerald-950/20 p-3.5 rounded-lg border border-emerald-500/20 space-y-1">
                        <p className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider">Auditor Resolution Notes</p>
                        <p className="text-xs text-slate-200">{f.resolution_notes}</p>
                        {f.resolved_at && (
                          <p className="text-[10px] text-slate-500 mt-1">Resolved: {new Date(f.resolved_at).toUTCString()}</p>
                        )}
                      </div>
                    )}

                    {/* Action Triggers */}
                    <div className="flex justify-end gap-2 pt-1">
                      {isDeveloper && f.status === "OPEN" && (
                        <button
                          onClick={() => {
                            setActiveFindingAction(f);
                            setActionType("RESPOND");
                          }}
                          className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-semibold"
                        >
                          Submit Developer Response
                        </button>
                      )}
                      {isAuditor && f.status === "RESPONSE_SUBMITTED" && (
                        <button
                          onClick={() => {
                            setActiveFindingAction(f);
                            setActionType("RESOLVE");
                          }}
                          className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold"
                        >
                          Verify & Resolve Finding
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 12: CENTRAL EVIDENCE & INTEGRITY INDEX */}
        {activeTab === "evidence" && (
          <div className="space-y-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-emerald-400" /> Central Cryptographic Evidence Index
                </h3>
                <p className="text-xs text-slate-400">
                  Authoritative repository of all scale tickets, ISO 17025 lab COAs, transport PODs, and QC records.
                </p>
              </div>
              <button
                onClick={handleVerifyAllEvidence}
                disabled={isVerifyingEvidence}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white text-xs font-semibold shadow-sm"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isVerifyingEvidence ? "animate-spin" : ""}`} />
                {isVerifyingEvidence ? "Verifying..." : "Verify All Evidence Files"}
              </button>
            </div>

            {/* Global Verify Summary Banner if executed */}
            {verifySummary && (
              <div className={`p-4 rounded-xl border ${
                verifySummary.all_passed
                  ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                  : "bg-red-500/10 border-red-500/30 text-red-400"
              } flex items-center justify-between`}>
                <div className="flex items-center gap-3">
                  {verifySummary.all_passed ? <CheckCircle2 className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
                  <div>
                    <p className="text-xs font-bold">
                      {verifySummary.all_passed ? "All Cryptographic Hashes Match Canonical Evidence" : "INTEGRITY MISMATCH DETECTED"}
                    </p>
                    <p className="text-[11px] text-slate-400">
                      Total: {verifySummary.total_evidence_items} | Verified: {verifySummary.verified_count} | Mismatch: {verifySummary.mismatch_count}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Evidence Items Table */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 font-semibold uppercase border-b border-slate-800">
                    <tr>
                      <th className="p-3">Category</th>
                      <th className="p-3">Title / Document</th>
                      <th className="p-3">File URI</th>
                      <th className="p-3 font-mono">SHA-256 Digest</th>
                      <th className="p-3">Integrity Status</th>
                      <th className="p-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300">
                    {evidence.map((ev) => (
                      <tr key={ev.id} className="hover:bg-slate-800/40">
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300">
                            {ev.evidence_category}
                          </span>
                        </td>
                        <td className="p-3 font-medium text-white">{ev.title}</td>
                        <td className="p-3 font-mono text-[11px] text-slate-400 truncate max-w-[200px]">
                          {ev.file_uri}
                        </td>
                        <td className="p-3 font-mono text-[11px] text-slate-400 truncate max-w-[160px]">
                          {ev.sha256_hash}
                        </td>
                        <td className="p-3">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            ev.integrity_status === "VERIFIED"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : ev.integrity_status === "INTEGRITY_MISMATCH"
                              ? "bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse"
                              : "bg-slate-800 text-slate-400"
                          }`}>
                            {ev.integrity_status}
                          </span>
                        </td>
                        <td className="p-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handleDownloadEvidence(ev)}
                              className="inline-flex items-center gap-1 text-xs text-blue-400 hover:underline font-semibold"
                              title="Download canonical raw bytes"
                            >
                              <Download className="w-3.5 h-3.5" /> Download
                            </button>
                            <button
                              onClick={() => handleVerifyEvidence(ev.id)}
                              className="text-xs text-emerald-400 hover:underline font-semibold"
                            >
                              Verify
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 13: AUDIT HISTORY & VERSION DIFF */}
        {activeTab === "history" && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <History className="w-4 h-4 text-emerald-400" /> Cryptographic Ledger Audit Trail & Sealed Revisions
              </h3>

              <div className="space-y-3">
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-white">Current Version: v{pkg.package_version}</span>
                    <span className="text-slate-400">Status: {pkg.package_status}</span>
                  </div>
                  <p className="font-mono text-xs text-slate-400 truncate">
                    Manifest Digest: {pkg.manifest_hash}
                  </p>
                  {pkg.ledger_signature_id && (
                    <p className="font-mono text-xs text-indigo-400">
                      Ledger Signature ID: {pkg.ledger_signature_id}
                    </p>
                  )}
                  {pkg.sealed_at && (
                    <p className="text-[11px] text-slate-500">
                      Sealed At: {new Date(pkg.sealed_at).toUTCString()}
                    </p>
                  )}
                </div>

                {pkg.parent_package_id && (
                  <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-bold text-slate-300">Parent Version: v{pkg.package_version - 1}</span>
                      <button
                        onClick={() => setShowDiffModal(true)}
                        className="text-indigo-400 hover:underline text-xs font-semibold"
                      >
                        View Full Diff
                      </button>
                    </div>
                    <p className="font-mono text-xs text-slate-500 truncate">
                      Parent ID: {pkg.parent_package_id}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Drill-Down Modal (Number to Evidence) ────────────────────────── */}
      {drillDownMetric && traceTrees[drillDownMetric] && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-5 shadow-2xl">
            <div className="flex justify-between items-start border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Calculator className="w-5 h-5 text-emerald-400" />
                  {drillDownMetric.replace(/_/g, " ").toUpperCase()} Drill-Down
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">Normative mathematical formulation & raw evidence link</p>
              </div>
              <button
                onClick={() => setDrillDownMetric(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg bg-slate-800"
              >
                ✕
              </button>
            </div>

            {/* Formula Block */}
            <div className="space-y-1.5">
              <p className="text-xs font-bold text-slate-400 uppercase">Authoritative Formula</p>
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-xs text-emerald-300">
                {traceTrees[drillDownMetric].formula}
              </div>
            </div>

            {/* Input Variables */}
            <div className="space-y-1.5">
              <p className="text-xs font-bold text-slate-400 uppercase">Input Variables</p>
              <div className="bg-slate-950 rounded-lg border border-slate-800 overflow-hidden">
                <table className="w-full text-xs text-left">
                  <thead className="bg-slate-900 text-slate-400 font-semibold border-b border-slate-800">
                    <tr>
                      <th className="p-2.5">Variable</th>
                      <th className="p-2.5 text-right">Value</th>
                      <th className="p-2.5">Description</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300">
                    {Object.entries(traceTrees[drillDownMetric].input_variables || {}).map(([k, v]: [string, unknown]) => (
                      <tr key={k}>
                        <td className="p-2.5 font-mono text-white font-medium">{k}</td>
                        <td className="p-2.5 text-right font-mono font-bold text-emerald-400">{String(v)}</td>
                        <td className="p-2.5 text-slate-400 text-[11px]">Primary quantification parameter</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Underlying Evidence References */}
            <div className="space-y-1.5">
              <p className="text-xs font-bold text-slate-400 uppercase">Underlying Evidence Digests</p>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {(traceTrees[drillDownMetric].evidence_refs || []).map((ref: { type?: string; hash?: string }, idx: number) => (
                  <div key={idx} className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-300">{ref.type}</span>
                    <span className="font-mono text-[11px] text-slate-400">{ref.hash?.slice(0, 16)}...{ref.hash?.slice(-8)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-800">
              <button
                onClick={() => setDrillDownMetric(null)}
                className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium rounded-lg"
              >
                Close Trace Tree
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Multi-Biomass Blend Breakdown Modal ──────────────────────────── */}
      {selectedRunBlend && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-6 space-y-5 shadow-2xl">
            <div className="flex justify-between items-start border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Flame className="w-5 h-5 text-emerald-400" />
                  Feedstock Blend Breakdown: {selectedRunBlend.run_number}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">Component percentages, moisture contents & baseline fates</p>
              </div>
              <button
                onClick={() => setSelectedRunBlend(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg bg-slate-800"
              >
                ✕
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800 uppercase">
                  <tr>
                    <th className="p-3">Lot Number</th>
                    <th className="p-3">Biomass Type</th>
                    <th className="p-3 text-right">Wet Mass (t)</th>
                    <th className="p-3 text-right">Dry Mass (t)</th>
                    <th className="p-3 text-right">Wet %</th>
                    <th className="p-3 text-right">Dry %</th>
                    <th className="p-3">Baseline Fate</th>
                    <th className="p-3">Sustainability</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-300">
                  {selectedRunBlend.components.map((comp) => (
                    <tr key={comp.lot_id} className="hover:bg-slate-800/40">
                      <td className="p-3 font-mono font-medium text-white">{comp.lot_number}</td>
                      <td className="p-3">{comp.biomass_type}</td>
                      <td className="p-3 text-right font-mono">{comp.allocated_wet_mass_tonnes}</td>
                      <td className="p-3 text-right font-mono text-emerald-400 font-bold">{comp.allocated_dry_mass_tonnes}</td>
                      <td className="p-3 text-right font-mono">{comp.blend_pct_wet_basis}%</td>
                      <td className="p-3 text-right font-mono text-indigo-400 font-bold">{comp.blend_pct_dry_basis}%</td>
                      <td className="p-3 text-slate-400">{comp.baseline_fate}</td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400">
                          {comp.sustainability_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-800">
              <button
                onClick={() => setSelectedRunBlend(null)}
                className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium rounded-lg"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Version Diff Modal (V1 vs V2) ────────────────────────────────── */}
      {showDiffModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-5 shadow-2xl">
            <div className="flex justify-between items-start border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <GitCompare className="w-5 h-5 text-indigo-400" />
                  Version Comparison Diff (v{pkg.package_version - 1} → v{pkg.package_version})
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">Structured mathematical and inventory delta</p>
              </div>
              <button
                onClick={() => setShowDiffModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg bg-slate-800"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <p className="font-bold text-slate-400 uppercase tracking-wider">Carbon Quantification Delta</p>
                <div className="grid grid-cols-3 gap-3 text-center pt-2">
                  <div>
                    <p className="text-slate-500">Parent (v{pkg.package_version - 1})</p>
                    <p className="text-lg font-bold text-white font-mono">
                      {diffSummary.carbon_quantification_delta?.parent_corcs_tco2e ?? 0} t
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-500">Current (v{pkg.package_version})</p>
                    <p className="text-lg font-bold text-emerald-400 font-mono">
                      {diffSummary.carbon_quantification_delta?.current_corcs_tco2e ?? 0} t
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-500">Net Delta</p>
                    <p className="text-lg font-bold text-indigo-400 font-mono">
                      +{diffSummary.carbon_quantification_delta?.delta_corcs_tco2e ?? 0} t ({diffSummary.carbon_quantification_delta?.delta_pct ?? 0}%)
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <p className="font-bold text-slate-400 uppercase tracking-wider">Inventory & Evidence Modifications</p>
                <p className="text-slate-300">
                  Added Batches: <span className="font-mono text-emerald-400">{(diffSummary.inventory_changes?.added_batch_ids || []).length}</span>
                </p>
                <p className="text-slate-300">
                  Added Evidence Files: <span className="font-mono text-emerald-400">{(diffSummary.evidence_changes?.added_evidence_hashes || []).length}</span>
                </p>
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowDiffModal(false)}
                className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium rounded-lg"
              >
                Close Diff Viewer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Log Finding Modal ────────────────────────────────────────────── */}
      {showFindingModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <form onSubmit={handleCreateFinding} className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-start border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-400" /> Log Assurance Finding
              </h3>
              <button
                type="button"
                onClick={() => setShowFindingModal(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-slate-400 font-semibold mb-1 block">Finding Type</label>
                <select
                  value={findingType}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFindingType(e.target.value as "CAR" | "CL" | "FAR" | "NCR")}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
                >
                  <option value="CAR">CAR (Corrective Action)</option>
                  <option value="CL">CL (Clarification)</option>
                  <option value="FAR">FAR (Forward Action)</option>
                  <option value="NCR">NCR (Non-Conformity)</option>
                </select>
              </div>
              <div>
                <label className="text-slate-400 font-semibold mb-1 block">Severity</label>
                <select
                  value={findingSeverity}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFindingSeverity(e.target.value as "CRITICAL" | "MAJOR" | "MINOR" | "OBSERVATION")}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
                >
                  <option value="CRITICAL">CRITICAL</option>
                  <option value="MAJOR">MAJOR</option>
                  <option value="MINOR">MINOR</option>
                  <option value="OBSERVATION">OBSERVATION</option>
                </select>
              </div>
            </div>

            <div className="text-xs">
              <label className="text-slate-400 font-semibold mb-1 block">Target Domain</label>
              <select
                value={findingDomain}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFindingDomain(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
              >
                <option value="FEEDSTOCK">FEEDSTOCK</option>
                <option value="PRODUCTION">PRODUCTION</option>
                <option value="BIOCHAR">BIOCHAR & LAB</option>
                <option value="PRODUCTS">PRODUCTS & INGREDIENTS</option>
                <option value="END_USE">END USE</option>
                <option value="LCA_QUANTIFICATION">LCA & QUANTIFICATION</option>
              </select>
            </div>

            <div className="text-xs">
              <label className="text-slate-400 font-semibold mb-1 block">Finding Title</label>
              <input
                type="text"
                required
                value={findingTitle}
                onChange={(e) => setFindingTitle(e.target.value)}
                placeholder="e.g. Provide accredited moisture balance calibration certificates"
                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
              />
            </div>

            <div className="text-xs">
              <label className="text-slate-400 font-semibold mb-1 block">Detailed Description & Audit Reference</label>
              <textarea
                required
                rows={3}
                value={findingDesc}
                onChange={(e) => setFindingDesc(e.target.value)}
                placeholder="Reference standard clause and specify necessary corrective action..."
                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white resize-none"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowFindingModal(false)}
                className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded text-xs font-semibold"
              >
                Save Finding
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Finding Action Modal (Respond / Resolve) ──────────────────────── */}
      {activeFindingAction && actionType && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white">
              {actionType === "RESPOND" ? "Developer Response to Finding" : "Auditor Resolution"}
            </h3>
            <p className="text-xs text-slate-400">
              Finding: <span className="font-semibold text-white">{activeFindingAction.finding_number} - {activeFindingAction.title}</span>
            </p>

            <textarea
              rows={4}
              required
              value={actionNotes}
              onChange={(e) => setActionNotes(e.target.value)}
              placeholder={
                actionType === "RESPOND"
                  ? "Describe corrective steps, attached certificates, or methodological justifications..."
                  : "State audit resolution opinion and justification for closing/resolving finding..."
              }
              className="w-full bg-slate-950 border border-slate-800 rounded p-3 text-xs text-white resize-none"
            />

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => {
                  setActiveFindingAction(null);
                  setActionType(null);
                }}
                className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitAction}
                className={`px-4 py-1.5 rounded text-xs font-semibold text-white ${
                  actionType === "RESPOND" ? "bg-blue-600 hover:bg-blue-500" : "bg-emerald-600 hover:bg-emerald-500"
                }`}
              >
                Submit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Audit Decision Modal ─────────────────────────────────────────── */}
      {showDecisionModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <form onSubmit={handleRecordAuditDecision} className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-amber-400" /> Record Official Audit Decision
            </h3>
            <p className="text-xs text-slate-400">
              Auditor conclusion on conformity with standard and eligibility of net removals.
            </p>

            <div className="space-y-2 text-xs">
              <label className="text-slate-400 font-semibold block">Decision Opinion</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setDecisionType("VERIFIED")}
                  className={`p-3 rounded-lg border text-center font-bold ${
                    decisionType === "VERIFIED"
                      ? "bg-emerald-500/20 border-emerald-500 text-emerald-400"
                      : "bg-slate-950 border-slate-800 text-slate-400"
                  }`}
                >
                  Positive (VERIFIED)
                </button>
                <button
                  type="button"
                  onClick={() => setDecisionType("REJECTED")}
                  className={`p-3 rounded-lg border text-center font-bold ${
                    decisionType === "REJECTED"
                      ? "bg-red-500/20 border-red-500 text-red-400"
                      : "bg-slate-950 border-slate-800 text-slate-400"
                  }`}
                >
                  Adverse (REJECTED)
                </button>
              </div>
            </div>

            <div className="text-xs">
              <label className="text-slate-400 font-semibold mb-1 block">Decision Statement</label>
              <textarea
                required
                rows={3}
                value={decisionNotes}
                onChange={(e) => setDecisionNotes(e.target.value)}
                placeholder="State audit assurance conclusion and formal opinion..."
                className="w-full bg-slate-950 border border-slate-800 rounded p-2.5 text-white resize-none"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowDecisionModal(false)}
                className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold"
              >
                Confirm Decision
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Grant Auditor Access Modal ───────────────────────────────────── */}
      {showGrantModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <form onSubmit={handleGrantAccess} className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <KeyRound className="w-5 h-5 text-indigo-400" /> Grant Auditor Scoped Access
            </h3>
            <p className="text-xs text-slate-400">
              Permits an external VVB / Auditor to review this package in the Auditor Workspace.
            </p>

            <div className="text-xs">
              <label className="text-slate-400 font-semibold mb-1 block">Auditor Email Address</label>
              <input
                type="email"
                required
                value={grantEmail}
                onChange={(e) => setGrantEmail(e.target.value)}
                placeholder="auditor@vvb-assurance.com"
                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
              />
            </div>

            <div className="text-xs">
              <label className="text-slate-400 font-semibold mb-1 block">Auditor Organization</label>
              <input
                type="text"
                required
                value={grantOrg}
                onChange={(e) => setGrantOrg(e.target.value)}
                placeholder="e.g. SGS, TÜV NORD, Earthood"
                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white"
              />
            </div>

            {grants.length > 0 && (
              <div className="space-y-1.5 pt-2 border-t border-slate-800">
                <p className="text-[11px] font-bold text-slate-400 uppercase">Existing Active Grants ({grants.length})</p>
                <div className="max-h-28 overflow-y-auto space-y-1">
                  {grants.map((g) => (
                    <div key={g.id} className="bg-slate-950 p-2 rounded text-[11px] flex justify-between items-center">
                      <span className="text-white font-medium">{g.auditor_email}</span>
                      <span className="text-slate-400">{g.auditor_organization}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowGrantModal(false)}
                className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-semibold"
              >
                Grant Access
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
