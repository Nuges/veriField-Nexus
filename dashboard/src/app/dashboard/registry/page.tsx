// =============================================================================
// VeriField Nexus — Registry Export Dashboard
// =============================================================================
// Admin page for exporting registry-ready data for Verra and Gold Standard
// carbon credit issuance applications.
// =============================================================================

"use client";

import { useState } from "react";
import {
  FileDown,
  Download,
  Leaf,
  CheckCircle,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { exportVerraCSV, exportGoldStandardJSON, issueVerraCredits, issueGoldStandardCredits } from "@/lib/api";

type ExportStatus = "idle" | "loading" | "success" | "error";

export default function RegistryExportPage() {
  const [minTrust, setMinTrust] = useState(80);
  const [verraStatus, setVerraStatus] = useState<ExportStatus>("idle");
  const [gsStatus, setGsStatus] = useState<ExportStatus>("idle");
  const [verraIssueStatus, setVerraIssueStatus] = useState<ExportStatus>("idle");
  const [gsIssueStatus, setGsIssueStatus] = useState<ExportStatus>("idle");
  const [lastResult, setLastResult] = useState<any>(null);

  async function handleVerraExport() {
    setVerraStatus("loading");
    try {
      await exportVerraCSV(minTrust);
      setVerraStatus("success");
      setTimeout(() => setVerraStatus("idle"), 3000);
    } catch (err) {
      console.error(err);
      setVerraStatus("error");
      setTimeout(() => setVerraStatus("idle"), 3000);
    }
  }

  async function handleGoldStandardExport() {
    setGsStatus("loading");
    try {
      const result = await exportGoldStandardJSON(minTrust);
      setLastResult(result);
      setGsStatus("success");
      setTimeout(() => setGsStatus("idle"), 5000);
    } catch (err) {
      console.error(err);
      setGsStatus("error");
      setTimeout(() => setGsStatus("idle"), 3000);
    }
  }

  async function handleVerraIssue() {
    setVerraIssueStatus("loading");
    try {
      const result = await issueVerraCredits();
      setLastResult(result);
      setVerraIssueStatus("success");
      setTimeout(() => setVerraIssueStatus("idle"), 5000);
    } catch (err) {
      console.error(err);
      setVerraIssueStatus("error");
      setTimeout(() => setVerraIssueStatus("idle"), 3000);
    }
  }

  async function handleGsIssue() {
    setGsIssueStatus("loading");
    try {
      const result = await issueGoldStandardCredits();
      setLastResult(result);
      setGsIssueStatus("success");
      setTimeout(() => setGsIssueStatus("idle"), 5000);
    } catch (err) {
      console.error(err);
      setGsIssueStatus("error");
      setTimeout(() => setGsIssueStatus("idle"), 3000);
    }
  }

  const statusIcon = (s: ExportStatus) => {
    if (s === "loading") return <Loader2 size={18} className="animate-spin" />;
    if (s === "success") return <CheckCircle size={18} className="text-emerald-400" />;
    if (s === "error") return <AlertTriangle size={18} className="text-red-400" />;
    return null;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="animate-fade-in-up">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">
          Registry Export
        </h1>
        <p className="text-[var(--color-text-secondary)] text-sm mt-1">
          Generate audit-ready exports for Verra VCS and Gold Standard carbon credit issuance
        </p>
      </div>

      {/* Trust Score Filter */}
      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5 animate-fade-in-up">
        <h3 className="text-[var(--color-text-primary)] font-semibold mb-3">
          Export Configuration
        </h3>
        <div className="flex flex-wrap items-end gap-6">
          <div>
            <label className="text-[var(--color-text-secondary)] text-xs font-medium mb-1.5 block">
              Minimum Trust Score
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={0}
                max={100}
                value={minTrust}
                onChange={(e) => setMinTrust(Number(e.target.value))}
                className="w-48 accent-emerald-500"
              />
              <span className="text-[var(--color-text-primary)] font-bold text-lg min-w-[3ch]">
                {minTrust}
              </span>
            </div>
            <p className="text-[var(--color-text-muted)] text-xs mt-1">
              Only verified activities with trust ≥ {minTrust} will be exported
            </p>
          </div>
        </div>
      </div>

      {/* Export Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Verra Card */}
        <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-6 animate-fade-in-up">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500/20 to-emerald-600/20 flex items-center justify-center">
                <FileDown size={24} className="text-emerald-400" />
              </div>
              <div>
                <h3 className="text-[var(--color-text-primary)] font-bold text-lg">
                  Verra VCS
                </h3>
                <p className="text-[var(--color-text-muted)] text-xs">
                  CSV format • VM0006 / VMR0050
                </p>
              </div>
            </div>
          </div>
          <p className="text-[var(--color-text-secondary)] text-sm mb-5">
            Generate a CSV file matching Verra&apos;s VCS upload template. Includes
            asset GPS, verification status, methodology, tCO2e, and
            cross-verification layers.
          </p>
          <div className="flex gap-3">
            <button
              onClick={handleVerraExport}
              disabled={verraStatus === "loading"}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500/15 text-emerald-400 font-medium hover:bg-emerald-500/25 transition-all disabled:opacity-50"
            >
              {statusIcon(verraStatus) || <Download size={16} />}
              {verraStatus === "loading" ? "Exporting..." : "Download CSV"}
            </button>
            <button
              onClick={handleVerraIssue}
              disabled={verraIssueStatus === "loading"}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-500/15 text-blue-400 font-medium hover:bg-blue-500/25 transition-all disabled:opacity-50"
            >
              {statusIcon(verraIssueStatus) || <Leaf size={16} />}
              {verraIssueStatus === "loading" ? "Issuing..." : "Issue Credits"}
            </button>
          </div>
        </div>

        {/* Gold Standard Card */}
        <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-6 animate-fade-in-up animation-delay-100">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500/20 to-amber-600/20 flex items-center justify-center">
                <FileDown size={24} className="text-amber-400" />
              </div>
              <div>
                <h3 className="text-[var(--color-text-primary)] font-bold text-lg">
                  Gold Standard
                </h3>
                <p className="text-[var(--color-text-muted)] text-xs">
                  JSON format • MECD / TPDDTEC
                </p>
              </div>
            </div>
          </div>
          <p className="text-[var(--color-text-secondary)] text-sm mb-5">
            Generate a JSON export matching Gold Standard requirements.
            Includes full verification layer attestation and methodology
            traceability.
          </p>
          <div className="flex gap-3">
            <button
              onClick={handleGoldStandardExport}
              disabled={gsStatus === "loading"}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-amber-500/15 text-amber-400 font-medium hover:bg-amber-500/25 transition-all disabled:opacity-50"
            >
              {statusIcon(gsStatus) || <Download size={16} />}
              {gsStatus === "loading" ? "Exporting..." : "Export JSON"}
            </button>
            <button
              onClick={handleGsIssue}
              disabled={gsIssueStatus === "loading"}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-500/15 text-blue-400 font-medium hover:bg-blue-500/25 transition-all disabled:opacity-50"
            >
              {statusIcon(gsIssueStatus) || <Leaf size={16} />}
              {gsIssueStatus === "loading" ? "Issuing..." : "Issue Credits"}
            </button>
          </div>
        </div>
      </div>

      {/* Last Result Preview */}
      {lastResult && (
        <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5 animate-fade-in-up">
          <h3 className="text-[var(--color-text-primary)] font-semibold mb-3">
            Last Export Result
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            {lastResult.registry && (
              <div>
                <p className="text-[var(--color-text-muted)] text-xs">Registry</p>
                <p className="text-[var(--color-text-primary)] font-bold">{lastResult.registry}</p>
              </div>
            )}
            {lastResult.total_records !== undefined && (
              <div>
                <p className="text-[var(--color-text-muted)] text-xs">Records</p>
                <p className="text-[var(--color-text-primary)] font-bold">{lastResult.total_records}</p>
              </div>
            )}
            {lastResult.total_tco2e !== undefined && (
              <div>
                <p className="text-[var(--color-text-muted)] text-xs">Total tCO2e</p>
                <p className="text-emerald-400 font-bold">{lastResult.total_tco2e}</p>
              </div>
            )}
            {lastResult.payload_size !== undefined && (
              <div>
                <p className="text-[var(--color-text-muted)] text-xs">Credits</p>
                <p className="text-blue-400 font-bold">{lastResult.payload_size}</p>
              </div>
            )}
          </div>
          {lastResult.action && (
            <div className="flex items-center gap-2 text-sm">
              <CheckCircle size={16} className="text-emerald-400" />
              <span className="text-emerald-400 font-medium">{lastResult.action}</span>
            </div>
          )}
        </div>
      )}

      {/* Export Guide */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 animate-fade-in-up">
        <h3 className="text-[var(--color-text-primary)] font-semibold mb-3">
          Export Guide
        </h3>
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <div className="flex gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs font-bold">1</span>
            <p>Set the minimum trust score threshold. Higher values = stricter filtering, fewer records.</p>
          </div>
          <div className="flex gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs font-bold">2</span>
            <p>Download the CSV (Verra) or JSON (Gold Standard) export file.</p>
          </div>
          <div className="flex gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs font-bold">3</span>
            <p>Review the export, then click &quot;Issue Credits&quot; to push to the registry API.</p>
          </div>
          <div className="flex gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs font-bold">4</span>
            <p>Credits move to &quot;Pending Issuance&quot; status in the Carbon Ledger until registry confirmation.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
