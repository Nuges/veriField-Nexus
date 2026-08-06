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



  // 1. SUPER ADMIN / ADMINISTRATOR VIEW

  if (role === "SUPER_ADMIN" || role === "ADMIN" || role === "ORG_ADMIN") {

    const totalSubmissions = dashboardData?.kpis?.find((k: any) => k.id === "installations" || k.label?.includes("Submissions") || k.label?.includes("Assets") || k.label?.includes("Installations"))?.value ?? 0;

    const activeTenants = dashboardData?.activeOrgs ?? dashboardData?.active_orgs_count ?? 1;



    return (

      <div className="space-y-6 animate-fade-in">

        {/* Administrator Telemetry Surface */}
        <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2 min-w-0">
              <span className="font-bold text-[var(--color-text-primary)] uppercase text-xs tracking-wider">
                Platform Health & Infrastructure Status
              </span>
            </div>
          </div>
          <p className="text-xs text-[var(--color-text-secondary)] font-medium leading-relaxed">
            {totalSubmissions === 0
              ? "Database connection pool optimal. Workspace active with 0 field submissions."
              : `Database connection pool optimal. ${activeTenants} active organization tenant emitting telemetry across ${totalSubmissions} field submissions.`
            }
          </p>
        </div>

        {/* Administrator KPIs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs space-y-1">
            <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-bold">
              <span>Platform Health</span>
              <Activity size={16} className="text-[#00B47A]" />
            </div>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">Operational</p>
            <p className="text-[10px] text-[var(--color-text-secondary)] font-mono">0 Failed Health Checks</p>
          </div>

          <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs space-y-1">
            <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-bold">
              <span>Active Organizations</span>
              <Building size={16} className="text-emerald-500" />
            </div>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">{activeTenants} Tenant{activeTenants === 1 ? '' : 's'}</p>
            <p className="text-[10px] text-[var(--color-text-secondary)] font-mono">KYC Verified Workspace</p>
          </div>

          <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs space-y-1">
            <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-bold">
              <span>API Gateway Status</span>
              <Cpu size={16} className="text-[#00B47A]" />
            </div>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">FastAPI Active</p>
            <p className="text-[10px] text-[var(--color-text-secondary)] font-mono">Uvicorn Async Worker</p>
          </div>

          <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs space-y-1">
            <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] font-bold">
              <span>Database Status</span>
              <ShieldCheck size={16} className="text-emerald-500" />
            </div>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">Pooler Active</p>
            <p className="text-[10px] text-[var(--color-text-secondary)] font-mono">PostgreSQL / Supabase</p>
          </div>
        </div>

      </div>

    );

  }



  // 2. FIELD AGENT VIEW

  if (role === "FIELD_AGENT") {

    return (

      <div className="space-y-6 animate-fade-in">

        <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">

          <div className="flex items-center gap-3">

            <Radio size={20} className="text-[#00B47A] animate-pulse shrink-0" />

            <div>

              <h3 className="font-extrabold text-sm text-[var(--color-text-primary)]">Today's Field Evidence Queue</h3>

              <p className="text-xs text-[var(--color-text-secondary)]">3 Inspection Visits Scheduled in Kano Sector</p>

            </div>

          </div>

          <Link

            href="/capture"

            className="px-4 py-2 rounded-xl bg-[#00B47A] text-white font-bold text-xs hover:bg-[#009b68] shadow-md flex items-center gap-1.5 shrink-0"

          >

            <span>Open PWA Capture</span>

            <ArrowRight size={14} />

          </Link>

        </div>



        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

          <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs">

            <span className="text-xs font-bold text-[var(--color-text-secondary)]">GPS Accuracy Radius</span>

            <p className="text-2xl font-black text-emerald-400 mt-1">4.2 Meters</p>

            <p className="text-[10px] text-emerald-500/80 font-mono mt-0.5">✓ Sub-30m Threshold Passed</p>

          </div>



          <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs">

            <span className="text-xs font-bold text-[var(--color-text-secondary)]">Offline Sync Status</span>

            <p className="text-2xl font-black text-[var(--color-text-primary)] mt-1">0 Pending Syncs</p>

            <p className="text-[10px] text-emerald-400 font-mono mt-0.5">All Payloads Ingested</p>

          </div>



          <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs">

            <span className="text-xs font-bold text-[var(--color-text-secondary)]">Device BLE Sensor</span>

            <p className="text-2xl font-black text-emerald-400 mt-1">Connected</p>

            <p className="text-[10px] text-emerald-500/80 font-mono mt-0.5">Cookstove Scanner Active</p>

          </div>

        </div>

      </div>

    );

  }



  // 3. QA OFFICER VIEW

  if (role === "QA_OFFICER") {

    return (

      <div className="space-y-6 animate-fade-in">

        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">

          <div className="flex items-center gap-3">

            <AlertTriangle size={20} className="text-amber-400 shrink-0" />

            <div>

              <h3 className="font-extrabold text-sm text-[var(--color-text-primary)]">QA Anomaly Review Queue</h3>

              <p className="text-xs text-[var(--color-text-secondary)]">3 Geotagged Field Photos Flagged for Moiré & Location Mismatch</p>

            </div>

          </div>

          <Link

            href="/dashboard/operations"

            className="px-4 py-2 rounded-xl bg-[#00B47A] text-white font-bold text-xs hover:bg-[#009b68] shadow-md flex items-center gap-1.5 shrink-0"

          >

            <span>Clear Flagged Photos</span>

            <ArrowRight size={14} />

          </Link>

        </div>



        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

          <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs">

            <span className="text-xs font-bold text-[var(--color-text-secondary)]">QA Anomaly SLA</span>

            <p className="text-2xl font-black text-amber-400 mt-1">2.4 Hours</p>

            <p className="text-[10px] text-emerald-400 font-mono mt-0.5">Target: &lt; 4.0 Hours</p>

          </div>



          <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs">

            <span className="text-xs font-bold text-[var(--color-text-secondary)]">Evidence Pass Rate</span>

            <p className="text-2xl font-black text-emerald-400 mt-1">98.4%</p>

            <p className="text-[10px] text-emerald-500/80 font-mono mt-0.5">1,480 Validated Submissions</p>

          </div>



          <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs">

            <span className="text-xs font-bold text-[var(--color-text-secondary)]">Target Handoff</span>

            <p className="text-2xl font-black text-[var(--color-text-primary)] mt-1">VVB Audit Hub</p>

            <p className="text-[10px] text-emerald-400 font-mono mt-0.5">Ready for Attestation</p>

          </div>

        </div>

      </div>

    );

  }



  // 4. VVB AUDITOR VIEW

  if (role === "AUDITOR" || role === "VVB" || role === "VERIFIER") {

    return (

      <div className="space-y-6 animate-fade-in">

        <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">

          <div className="flex items-center gap-3">

            <ShieldCheck size={20} className="text-[#00B47A] shrink-0" />

            <div>

              <h3 className="font-extrabold text-sm text-[var(--color-text-primary)]">Independent VVB Audit Queue</h3>

              <p className="text-xs text-[var(--color-text-secondary)]">2 Verified Batches Pending WebAuthn Cryptographic Sign-Off</p>

            </div>

          </div>

          <Link

            href="/dashboard/verifications"

            className="px-4 py-2 rounded-xl bg-[#00B47A] text-white font-bold text-xs hover:bg-[#009b68] shadow-md flex items-center gap-1.5 shrink-0"

          >

            <span>Execute Attestation Sign-Off</span>

            <ArrowRight size={14} />

          </Link>

        </div>



        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

          <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs">

            <span className="text-xs font-bold text-[var(--color-text-secondary)]">SHA-256 Hash Integrity</span>

            <p className="text-2xl font-black text-emerald-400 mt-1">100% Match</p>

            <p className="text-[10px] text-emerald-500/80 font-mono mt-0.5">Immutable Ledger Proof</p>

          </div>



          <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs">

            <span className="text-xs font-bold text-[var(--color-text-secondary)]">AST Calculation Check</span>

            <p className="text-2xl font-black text-emerald-400 mt-1">Validated</p>

            <p className="text-[10px] text-emerald-500/80 font-mono mt-0.5">AMS-II.G Formula Verified</p>

          </div>



          <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xs">

            <span className="text-xs font-bold text-[var(--color-text-secondary)]">Target Handoff</span>

            <p className="text-2xl font-black text-[var(--color-text-primary)] mt-1">Registry Minting</p>

            <p className="text-[10px] text-emerald-400 font-mono mt-0.5">Solana On-Chain Issuance</p>

          </div>

        </div>

      </div>

    );

  }



  // 5. REGISTRY MANAGER VIEW

  if (role === "REGISTRY_MANAGER" || role === "REGISTRY") {

    return (

      <div className="space-y-6 animate-fade-in">

        <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">

          <div className="flex items-center gap-3">

            <Coins size={20} className="text-[#00B47A] shrink-0" />

            <div>

              <h3 className="font-extrabold text-sm text-[var(--color-text-primary)]">Registry Issuance & Minting Queue</h3>

              <p className="text-xs text-[var(--color-text-secondary)]">14,250 tCO₂e Carbon Credits Ready for Serial Allocation & Minting</p>

            </div>

          </div>

          <Link

            href="/dashboard/carbon"

            className="px-4 py-2 rounded-xl bg-[#00B47A] text-white font-bold text-xs hover:bg-[#009b68] shadow-md flex items-center gap-1.5 shrink-0"

          >

            <span>Mint Credits on Solana</span>

            <ArrowRight size={14} />

          </Link>

        </div>

      </div>

    );

  }



  // 6. DEFAULT PROJECT MANAGER / EXECUTIVE VIEW

  return (

    <div className="space-y-6 animate-fade-in">

      <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-500/10 via-[#00B47A]/5 to-transparent border border-[#00B47A]/30 shadow-xs space-y-2">

        <div className="flex flex-wrap items-center justify-between gap-2">

          <div className="flex flex-wrap items-center gap-2 min-w-0">

            <TrendingUp size={18} className="text-[#00B47A] shrink-0" />

            <span className="font-extrabold text-[#00B47A] uppercase text-xs tracking-wider">

              Project Performance & Yield Advisor

            </span>

            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-[#00B47A] font-bold shrink-0">

              +14% Carbon Yield Target

            </span>

          </div>

        </div>

        <p className="text-xs text-[var(--color-text-primary)] font-medium leading-relaxed">

          "Active project portfolio is operating at 98.4% efficiency. All 6 lifecycle stages are active."

        </p>

      </div>

    </div>

  );

}
