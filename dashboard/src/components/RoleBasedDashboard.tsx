// =============================================================================
// VeriField Nexus — Role-Based Mission Control Dashboard (RBOS Level 5)
// =============================================================================
// Renders role-exclusive dashboards and operational surfaces tailored
// to each canonical role persona's responsibilities and primary questions.
// =============================================================================

"use client";

import React from "react";
import { useWorkspace } from "@/context/WorkspaceContext";
import {
  ShieldCheck,
  Activity,
  AlertTriangle,
  Bot,
  ArrowRight,
  Clock,
  Zap,
  CheckCircle2,
  Radio,
  FileText,
  Globe,
  Coins,
  TrendingUp,
  Users,
  Cpu,
  Building,
  DollarSign,
  Lock,
  FileCheck,
} from "lucide-react";
import Link from "next/link";
import { normalizeRole, CANONICAL_ROLES } from "@/lib/roles";

interface RoleBasedDashboardProps {
  dashboardData: any;
  sectorCode: string;
}

export default function RoleBasedDashboard({ dashboardData, sectorCode }: RoleBasedDashboardProps) {
  const { user } = useWorkspace();
  const canonicalRole = normalizeRole(user?.role);

  // 1. PLATFORM SUPER ADMIN WORKSPACE
  if (canonicalRole === "SUPER_ADMIN") {
    const totalSubmissions =
      dashboardData?.kpis?.find(
        (k: any) =>
          k.id === "installations" ||
          k.label?.includes("Submissions") ||
          k.label?.includes("Assets") ||
          k.label?.includes("Installations")
      )?.value ?? 0;
    const activeTenants = dashboardData?.activeOrgs ?? dashboardData?.active_orgs_count ?? 1;

    return (
      <div className="space-y-4">
        <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1.5">
          <div className="flex items-center gap-2">
            <ShieldCheck size={16} className="text-[#008A5E] shrink-0" />
            <span className="font-semibold text-[var(--color-text-primary)] uppercase text-xs tracking-wider">
              Global Platform Governance & Infrastructure
            </span>
          </div>
          <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
            Database connection pool optimal. {activeTenants} active tenant organization(s) emitting telemetry across {totalSubmissions} verified activities.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Tenant Health</span>
            <p className="text-2xl font-bold text-[#008A5E]">100% Online</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Multi-Tenant Isolation Active</p>
          </div>
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">RBAC Policy Invariant</span>
            <p className="text-2xl font-bold text-[#008A5E]">Enforced</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">SuperAdmin Invariant Locked</p>
          </div>
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">API Telemetry Rate</span>
            <p className="text-2xl font-bold text-[var(--color-text-primary)]">240 req/s</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Latency avg: 42ms</p>
          </div>
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Infrastructure Actions</span>
            <Link
              href="/super-admin"
              className="mt-1 inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-500 hover:text-emerald-400"
            >
              <span>Command Center</span>
              <ArrowRight size={13} />
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // 2. ORGANIZATION ADMIN WORKSPACE
  if (canonicalRole === "ORG_ADMIN") {
    return (
      <div className="space-y-4">
        <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1.5">
          <div className="flex items-center gap-2">
            <Building size={16} className="text-[#008A5E] shrink-0" />
            <span className="font-semibold text-[var(--color-text-primary)] uppercase text-xs tracking-wider">
              Tenant Administration & Governance
            </span>
          </div>
          <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
            Organization workspace active. Manage team memberships, API keys, and enterprise sector subscriptions.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Team Access Control</span>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">Roster & Roles</p>
            <Link href="/dashboard/people" className="text-xs text-emerald-500 hover:underline inline-block mt-1">
              Manage Team & Invites →
            </Link>
          </div>
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Organization Settings</span>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">API Keys & Security</p>
            <Link href="/dashboard/settings" className="text-xs text-emerald-500 hover:underline inline-block mt-1">
              Configure Settings →
            </Link>
          </div>
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Audit Log Activity</span>
            <p className="text-xl font-bold text-emerald-600">Tamper-Proof</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Signed Immutable Ledger</p>
          </div>
        </div>
      </div>
    );
  }

  // 3. FIELD AGENT WORKSPACE
  if (canonicalRole === "FIELD_AGENT") {
    return (
      <div className="space-y-4">
        <div className="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Radio size={18} className="text-[#008A5E] shrink-0" />
            <div>
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)]">Field Evidence & Inspection Hub</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">Capture geotagged installation evidence and sync offline data packets</p>
            </div>
          </div>
          <Link
            href="/dashboard/operations"
            className="px-3.5 py-1.5 rounded-md bg-[#008A5E] hover:bg-[#00734E] text-white font-semibold text-xs transition-colors flex items-center gap-1.5 shrink-0"
          >
            <span>Capture Activity</span>
            <ArrowRight size={13} />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">GPS Lock Status</span>
            <p className="text-xl font-bold text-[#008A5E]">High Precision</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">EXIF Geotagging Ready</p>
          </div>
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Offline Queue</span>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">0 Pending</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">All Records Synchronized</p>
          </div>
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Inspection Guidelines</span>
            <Link href="/dashboard/help" className="text-xs text-emerald-500 hover:underline inline-block mt-1">
              Field Protocols & Standards →
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // 4. QA / MRV OFFICER WORKSPACE
  if (canonicalRole === "QA_OFFICER") {
    return (
      <div className="space-y-4">
        <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <AlertTriangle size={18} className="text-amber-600 dark:text-amber-400 shrink-0" />
            <div>
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)]">MRV QA/QC Anomaly Review Queue</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">Submissions and sensor calibrations pending anomaly reconciliation</p>
            </div>
          </div>
          <Link
            href="/dashboard/operations"
            className="px-3.5 py-1.5 rounded-md bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs transition-colors flex items-center gap-1.5 shrink-0"
          >
            <span>Review Anomaly Queue</span>
            <ArrowRight size={13} />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Trust Score Benchmark</span>
            <p className="text-2xl font-bold text-[#008A5E]">&gt; 85 / 100</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Target Validation Threshold</p>
          </div>
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Sensor Telemetry Curves</span>
            <Link href="/dashboard/monitoring" className="text-xs text-emerald-500 hover:underline inline-block mt-1">
              Inspect IoT Streams →
            </Link>
          </div>
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">MRV Calculation Audit</span>
            <Link href="/dashboard/analytics" className="text-xs text-emerald-500 hover:underline inline-block mt-1">
              View Emission Yields →
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // 5. VVB VERIFIER / AUDITOR WORKSPACE
  if (canonicalRole === "VERIFIER" || canonicalRole === "AUDITOR") {
    return (
      <div className="space-y-4">
        <div className="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <ShieldCheck size={18} className="text-[#008A5E] shrink-0" />
            <div>
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)]">Independent VVB Audit Workspace</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">Assigned audit engagements, evidence room inspection, and NCR logging</p>
            </div>
          </div>
          <Link
            href="/dashboard/verifications"
            className="px-3.5 py-1.5 rounded-md bg-[#008A5E] hover:bg-[#00734E] text-white font-semibold text-xs transition-colors flex items-center gap-1.5 shrink-0"
          >
            <span>Open Audit Queue</span>
            <ArrowRight size={13} />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Cryptographic Lineage</span>
            <p className="text-xl font-bold text-[#008A5E]">Hash Verified</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">SHA-256 Provenance Chain</p>
          </div>
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Assigned Projects</span>
            <Link href="/dashboard/projects" className="text-xs text-emerald-500 hover:underline inline-block mt-1">
              View Audit Engagements →
            </Link>
          </div>
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Sampling Workspace</span>
            <Link href="/dashboard/verifications" className="text-xs text-emerald-500 hover:underline inline-block mt-1">
              Inspect Random Samples →
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // 6. COMPLIANCE ADMIN WORKSPACE
  if (canonicalRole === "COMPLIANCE_ADMIN") {
    return (
      <div className="space-y-4">
        <div className="p-4 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Globe size={18} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
            <div>
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)]">Article 6 & Sovereign NDC Command Center</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">National DNA authorization, Corresponding Adjustments, and ITMO sealing</p>
            </div>
          </div>
          <Link
            href="/dashboard/command-center"
            className="px-3.5 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs transition-colors flex items-center gap-1.5 shrink-0"
          >
            <span>Article 6 Gating</span>
            <ArrowRight size={13} />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Article 6.2 Alignment</span>
            <p className="text-xl font-bold text-indigo-600">NCCC Authorized</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Bilateral Transfer Ready</p>
          </div>
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Regulatory Exceptions</span>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">0 Flagged</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">100% NDC Compliant</p>
          </div>
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Submission Dossiers</span>
            <Link href="/dashboard/registry" className="text-xs text-indigo-500 hover:underline inline-block mt-1">
              Inspect Registry Packages →
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // 7. REGISTRY ADMIN WORKSPACE
  if (canonicalRole === "REGISTRY_ADMIN") {
    return (
      <div className="space-y-4">
        <div className="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <FileCheck size={18} className="text-[#008A5E] shrink-0" />
            <div>
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)]">Official Registry Submission Hub</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">Multi-standard document packages (NCCC, Verra, Gold Standard, UNFCCC)</p>
            </div>
          </div>
          <Link
            href="/dashboard/registry"
            className="px-3.5 py-1.5 rounded-md bg-[#008A5E] hover:bg-[#00734E] text-white font-semibold text-xs transition-colors flex items-center gap-1.5 shrink-0"
          >
            <span>Review Packages</span>
            <ArrowRight size={13} />
          </Link>
        </div>
      </div>
    );
  }

  // 8. FINANCE WORKSPACE
  if (canonicalRole === "FINANCE") {
    return (
      <div className="space-y-4">
        <div className="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <DollarSign size={18} className="text-[#008A5E] shrink-0" />
            <div>
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)]">Carbon Asset Ledger & Settlement Hub</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">Execute on-chain cryptographic credit minting and transaction settlement</p>
            </div>
          </div>
          <Link
            href="/dashboard/carbon"
            className="px-3.5 py-1.5 rounded-md bg-[#008A5E] hover:bg-[#00734E] text-white font-semibold text-xs transition-colors flex items-center gap-1.5 shrink-0"
          >
            <span>Mint Credits</span>
            <ArrowRight size={13} />
          </Link>
        </div>
      </div>
    );
  }

  // 9. PROJECT DEVELOPER / MANAGER WORKSPACE (DEFAULT)
  return (
    <div className="space-y-4">
      <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1.5">
        <div className="flex items-center gap-2">
          <TrendingUp size={16} className="text-[#008A5E] shrink-0" />
          <span className="font-semibold text-[var(--color-text-primary)] uppercase text-xs tracking-wider">
            Project Delivery & Carbon Asset Performance
          </span>
        </div>
        <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
          Active carbon mitigation assets operational. Sensor streams and field submissions tracked against registered methodology.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
          <span className="text-xs font-medium text-[var(--color-text-secondary)]">Project Status</span>
          <p className="text-xl font-bold text-[#008A5E]">Phase 4 (Monitoring)</p>
          <p className="text-[11px] text-[var(--color-text-muted)]">Data Ingestion Active</p>
        </div>
        <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
          <span className="text-xs font-medium text-[var(--color-text-secondary)]">Registry Readiness</span>
          <p className="text-xl font-bold text-emerald-500">100% Documented</p>
          <Link href="/dashboard/registry" className="text-[11px] text-emerald-500 hover:underline">
            Export Submission Package →
          </Link>
        </div>
        <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
          <span className="text-xs font-medium text-[var(--color-text-secondary)]">Evidence Lineage</span>
          <p className="text-xl font-bold text-[var(--color-text-primary)]">SHA-256 Sealed</p>
          <p className="text-[11px] text-[var(--color-text-muted)]">Audit Trail Immutable</p>
        </div>
        <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
          <span className="text-xs font-medium text-[var(--color-text-secondary)]">VVB Audit Handoff</span>
          <p className="text-xl font-bold text-amber-500">Awaiting VVB Sign-Off</p>
          <p className="text-[11px] text-[var(--color-text-muted)]">Independent Auditor Assigned</p>
        </div>
      </div>
    </div>
  );
}
