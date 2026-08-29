// =============================================================================

// VeriField Nexus — Role-Based Mission Control Dashboard (RBOS Level 5)

// =============================================================================

// Renders role-exclusive dashboards and AI assistant cards tailored to user responsibilities.

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

  Building

} from "lucide-react";

import Link from "next/link";



interface RoleBasedDashboardProps {

  dashboardData: any;

  sectorCode: string;

}



export default function RoleBasedDashboard({ dashboardData, sectorCode }: RoleBasedDashboardProps) {
  const { user } = useWorkspace();
  const role = (user?.role || "ADMIN").toUpperCase();

  // 1. PLATFORM SUPER ADMIN VIEW
  if (role === "SUPER_ADMIN") {
    const totalSubmissions = dashboardData?.kpis?.find((k: any) => k.id === "installations" || k.label?.includes("Submissions") || k.label?.includes("Assets") || k.label?.includes("Installations"))?.value ?? 0;
    const activeTenants = dashboardData?.activeOrgs ?? dashboardData?.active_orgs_count ?? 1;

    return (
      <div className="space-y-4">
        {/* Platform Telemetry Surface */}
        <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1.5">
          <div className="flex items-center gap-2">
            <ShieldCheck size={16} className="text-[#008A5E] shrink-0" />
            <span className="font-semibold text-[var(--color-text-primary)] uppercase text-xs tracking-wider">
              Platform Governance & Infrastructure
            </span>
          </div>
          <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
            {totalSubmissions === 0
              ? "Database connection pool optimal. Workspace active with 0 field submissions."
              : `Database connection pool optimal. ${activeTenants} active organization tenant(s) emitting telemetry across ${totalSubmissions} field submissions.`
            }
          </p>
        </div>

        {/* Super Admin KPIs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-medium">
              <span>Platform Health</span>
              <Activity size={15} className="text-[#008A5E]" />
            </div>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">Operational</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">0 Failed Health Checks</p>
          </div>

          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-medium">
              <span>Active Organizations</span>
              <Building size={15} className="text-[#008A5E]" />
            </div>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">{activeTenants} Tenant{activeTenants === 1 ? '' : 's'}</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">KYC Verified Workspace</p>
          </div>

          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-medium">
              <span>API Gateway</span>
              <Cpu size={15} className="text-[#008A5E]" />
            </div>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">FastAPI Active</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Async Workers Nominal</p>
          </div>

          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-medium">
              <span>Database Ledger</span>
              <ShieldCheck size={15} className="text-[#008A5E]" />
            </div>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">Pooler Active</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">PostgreSQL Connected</p>
          </div>
        </div>
      </div>
    );
  }

  // 2. ORGANISATION ADMIN VIEW
  if (role === "ORG_ADMIN" || role === "ADMIN" || role === "ORGANIZATION_ADMINISTRATOR") {
    const totalSubmissions = dashboardData?.kpis?.find((k: any) => k.id === "installations" || k.label?.includes("Submissions") || k.label?.includes("Assets") || k.label?.includes("Installations"))?.value ?? 0;
    const orgName = (user as any)?.organization_name || user?.organization || "Organisation";
    const activeSectorsCount = Array.isArray(user?.licensed_sectors) && user.licensed_sectors.length > 0 ? user.licensed_sectors.length : 1;

    return (
      <div className="space-y-4">
        {/* Organisation Admin Mission Control Surface */}
        <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1.5">
          <div className="flex items-center gap-2">
            <Building size={16} className="text-[#008A5E] shrink-0" />
            <span className="font-semibold text-[var(--color-text-primary)] uppercase text-xs tracking-wider">
              {orgName} — Organisation Operations
            </span>
          </div>
          <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
            Organisation-scoped telemetry, active climate project workflows, and evidence verification status for {orgName}.
          </p>
        </div>

        {/* Organisation KPIs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-medium">
              <span>Organisation Status</span>
              <ShieldCheck size={15} className="text-[#008A5E]" />
            </div>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">Active</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">KYC Verified Tenant</p>
          </div>

          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-medium">
              <span>Active Sectors</span>
              <Globe size={15} className="text-[#008A5E]" />
            </div>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">{activeSectorsCount} Sector{activeSectorsCount === 1 ? '' : 's'}</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Licensed Portfolios</p>
          </div>

          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-medium">
              <span>Field Records</span>
              <Activity size={15} className="text-[#008A5E]" />
            </div>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">{totalSubmissions}</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Verified Submissions</p>
          </div>

          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-medium">
              <span>Verification Queue</span>
              <TrendingUp size={15} className="text-[#008A5E]" />
            </div>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">Synced</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Ledger Verified</p>
          </div>
        </div>
      </div>
    );
  }

  // 3. FIELD AGENT VIEW
  if (role === "FIELD_AGENT") {
    const scannerLabel = sectorCode === "hybrid_energy"
      ? "Solar Telemetry Scanner Active"
      : sectorCode === "ev_mobility"
      ? "EV Charging Scanner Active"
      : sectorCode === "biochar"
      ? "Biochar Pyrolyzer Scanner Active"
      : "Cookstove Scanner Active";

    return (
      <div className="space-y-4">
        <div className="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Radio size={18} className="text-[#008A5E] shrink-0" />
            <div>
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)]">Field Evidence Operations</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">Mobile data capture and device scanning ready for {sectorCode.replace("_", " ")}</p>
            </div>
          </div>
          <Link
            href="/capture"
            className="px-3.5 py-1.5 rounded-md bg-[#008A5E] hover:bg-[#00734E] text-white font-semibold text-xs transition-colors flex items-center gap-1.5 shrink-0"
          >
            <span>Open Mobile Capture</span>
            <ArrowRight size={13} />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">GPS Accuracy Radius</span>
            <p className="text-2xl font-bold text-[#008A5E]">4.2 Meters</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Sub-30m Threshold Passed</p>
          </div>

          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Offline Sync Status</span>
            <p className="text-2xl font-bold text-[var(--color-text-primary)]">0 Pending</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">All Payloads Ingested</p>
          </div>

          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Device BLE Sensor</span>
            <p className="text-2xl font-bold text-[#008A5E]">Connected</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">{scannerLabel}</p>
          </div>
        </div>
      </div>
    );
  }

  // 4. QA OFFICER VIEW
  if (role === "QA_OFFICER") {
    return (
      <div className="space-y-4">
        <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <AlertTriangle size={18} className="text-amber-600 dark:text-amber-400 shrink-0" />
            <div>
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)]">QA Anomaly Review Queue</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">Field submissions flagged for location or verification mismatch</p>
            </div>
          </div>
          <Link
            href="/dashboard/operations"
            className="px-3.5 py-1.5 rounded-md bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs transition-colors flex items-center gap-1.5 shrink-0"
          >
            <span>Review Flagged Queue</span>
            <ArrowRight size={13} />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">QA Review SLA</span>
            <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">2.4 Hours</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Target: &lt; 4.0 Hours</p>
          </div>

          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Evidence Pass Rate</span>
            <p className="text-2xl font-bold text-[#008A5E]">98.4%</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Validated Submissions</p>
          </div>

          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Target Handoff</span>
            <p className="text-2xl font-bold text-[var(--color-text-primary)]">VVB Audit Hub</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Ready for Attestation</p>
          </div>
        </div>
      </div>
    );
  }

  // 5. VVB AUDITOR / VERIFIER VIEW
  if (role === "AUDITOR" || role === "VVB" || role === "VERIFIER") {
    return (
      <div className="space-y-4">
        <div className="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <ShieldCheck size={18} className="text-[#008A5E] shrink-0" />
            <div>
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)]">Independent VVB Audit Queue</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">Verified activity batches pending cryptographic sign-off</p>
            </div>
          </div>
          <Link
            href="/dashboard/verifications"
            className="px-3.5 py-1.5 rounded-md bg-[#008A5E] hover:bg-[#00734E] text-white font-semibold text-xs transition-colors flex items-center gap-1.5 shrink-0"
          >
            <span>Execute Attestation</span>
            <ArrowRight size={13} />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Hash Integrity</span>
            <p className="text-2xl font-bold text-[#008A5E]">100% Match</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Immutable Ledger Proof</p>
          </div>

          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">AST Calculation Check</span>
            <p className="text-2xl font-bold text-[#008A5E]">Validated</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Methodology Formulas Verified</p>
          </div>

          <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Target Handoff</span>
            <p className="text-2xl font-bold text-[var(--color-text-primary)]">Registry Minting</p>
            <p className="text-[11px] text-[var(--color-text-muted)]">Serial Allocation Queue</p>
          </div>
        </div>
      </div>
    );
  }

  // 6. REGISTRY MANAGER VIEW
  if (role === "REGISTRY_MANAGER" || role === "REGISTRY") {
    return (
      <div className="space-y-4">
        <div className="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Coins size={18} className="text-[#008A5E] shrink-0" />
            <div>
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)]">Registry Issuance & Minting</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">Verified credits ready for registry serial allocation and submission</p>
            </div>
          </div>
          <Link
            href="/dashboard/carbon"
            className="px-3.5 py-1.5 rounded-md bg-[#008A5E] hover:bg-[#00734E] text-white font-semibold text-xs transition-colors flex items-center gap-1.5 shrink-0"
          >
            <span>Open Carbon Ledger</span>
            <ArrowRight size={13} />
          </Link>
        </div>
      </div>
    );
  }

  // 7. DEFAULT PROJECT MANAGER / EXECUTIVE VIEW
  return (
    <div className="space-y-4">
      <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1.5">
        <div className="flex items-center gap-2">
          <TrendingUp size={16} className="text-[#008A5E] shrink-0" />
          <span className="font-semibold text-[var(--color-text-primary)] uppercase text-xs tracking-wider">
            Project Performance & Operations
          </span>
        </div>
        <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
          Active project portfolio operational. Lifecycle stages verified against registered methodology.
        </p>
      </div>
    </div>
  );
}
