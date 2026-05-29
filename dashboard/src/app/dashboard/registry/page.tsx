// =============================================================================
// VeriField Nexus — Registry Export Dashboard
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
  Calendar,
  Layers,
  ArrowRight
} from "lucide-react";
import { exportVerraCSV, exportGoldStandardJSON, issueVerraCredits, issueGoldStandardCredits } from "@/lib/api";
import { useToast } from "@/components/Toast";

type ExportStatus = "idle" | "loading" | "success" | "error";

export default function RegistryExportPage() {
  const toast = useToast();
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
      toast.success("Verra CSV Exported", "Verra-compliant CSV registry export file successfully generated and downloaded.");
      setTimeout(() => setVerraStatus("idle"), 3000);
    } catch (err) {
      console.error(err);
      setVerraStatus("error");
      toast.error("Export Failed", "Could not export Verra CSV file.");
      setTimeout(() => setVerraStatus("idle"), 3000);
    }
  }

  async function handleGoldStandardExport() {
    setGsStatus("loading");
    try {
      const result = await exportGoldStandardJSON(minTrust);
      setLastResult(result);
      setGsStatus("success");
      toast.success("Gold Standard JSON Exported", "Gold Standard compliant registry export file successfully generated.");
      setTimeout(() => setGsStatus("idle"), 5000);
    } catch (err) {
      console.error(err);
      setGsStatus("error");
      toast.error("Export Failed", "Could not export Gold Standard JSON file.");
      setTimeout(() => setGsStatus("idle"), 3000);
    }
  }

  async function handleVerraIssue() {
    setVerraIssueStatus("loading");
    try {
      const result = await issueVerraCredits();
      if (result.detail) {
        toast.warning("Verification Alert", result.detail);
      } else {
        setLastResult(result);
        toast.success("Verra Credits Issued", `Successfully locked and issued ${result.issued_credits} Verra carbon credits.`);
      }
      setVerraIssueStatus("success");
      setTimeout(() => setVerraIssueStatus("idle"), 5000);
    } catch (err) {
      console.error(err);
      setVerraIssueStatus("error");
      toast.error("Issuance Failed", "An error occurred while issuing Verra carbon credits.");
      setTimeout(() => setVerraIssueStatus("idle"), 3000);
    }
  }

  async function handleGsIssue() {
    setGsIssueStatus("loading");
    try {
      const result = await issueGoldStandardCredits();
      if (result.detail) {
        toast.warning("Verification Alert", result.detail);
      } else {
        setLastResult(result);
        toast.success("Gold Standard Credits Issued", `Successfully locked and issued ${result.issued_credits} Gold Standard carbon credits.`);
      }
      setGsIssueStatus("success");
      setTimeout(() => setGsIssueStatus("idle"), 5000);
    } catch (err) {
      console.error(err);
      setGsIssueStatus("error");
      toast.error("Issuance Failed", "An error occurred while issuing Gold Standard carbon credits.");
      setTimeout(() => setGsIssueStatus("idle"), 3000);
    }
  }

  const statusIcon = (s: ExportStatus) => {
    if (s === "loading") return <Loader2 size={15} className="animate-spin text-[#00B47A]" />;
    if (s === "success") return <CheckCircle size={15} className="text-[#00B47A]" />;
    if (s === "error") return <AlertTriangle size={15} className="text-red-400" />;
    return null;
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10 animate-fade-in-up text-[var(--color-text-primary)]">
      
      {/* 👑 TITLE SECTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded bg-[#00B47A]/10 text-[#00B47A] text-[9px] font-extrabold tracking-wider uppercase border border-[#00B47A]/15">
              Registry Export Center
            </span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)] mt-1 flex items-center gap-2">
            <FileDown className="text-[#00B47A]" size={20} /> Official Registry Exports
          </h1>
          <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">
            Compile audit-ready carbon credit exports certified under Verra VCS and Gold Standard registries.
          </p>
        </div>
      </div>

      {/* 📊 TRUST RANGE FILTER */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm">
        <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)] mb-4">
          Export Configuration Parameters
        </h3>
        
        <div className="flex flex-wrap items-end gap-6 max-w-lg">
          <div className="w-full">
            <label className="text-[var(--color-text-secondary)] text-xs font-semibold mb-2 block">
              Minimum Attested Trust Score Threshold
            </label>
            
            <div className="flex items-center gap-4">
              <input
                type="range"
                min={0}
                max={100}
                value={minTrust}
                onChange={(e) => setMinTrust(Number(e.target.value))}
                className="w-full accent-[#00B47A] bg-[var(--color-background)] border border-[var(--color-border)] h-2 rounded-lg cursor-pointer"
              />
              <span className="text-[#00B47A] font-black text-xl min-w-[3ch] tracking-tight bg-[#00B47A]/5 border border-[#00B47A]/15 px-2.5 py-0.5 rounded-lg font-mono">
                {minTrust}
              </span>
            </div>
            
            <p className="text-[var(--color-text-muted)] text-[10px] mt-2 font-medium">
              Only quantified emissions logs with an aggregated trust coefficient ≥ <span className="font-bold text-[#00B47A]">{minTrust}%</span> will be parsed in this run.
            </p>
          </div>
        </div>
      </div>

      {/* 📊 REGISTRY DRIVERS GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        {/* Verra Card */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 flex flex-col justify-between shadow-sm relative overflow-hidden group hover:border-[#00B47A]/30 transition-all">
          <div>
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-[#00B47A]/5 border border-[#00B47A]/10 flex items-center justify-center text-[#00B47A]">
                  <Leaf size={22} />
                </div>
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">
                    Verra VCS Registry
                  </h3>
                  <p className="text-[9px] text-[var(--color-text-muted)] font-mono font-bold mt-0.5">
                    CSV EXPORT • VM0006 PROTOCOL
                  </p>
                </div>
              </div>
            </div>
            
            <p className="text-xs text-[var(--color-text-secondary)] font-medium leading-relaxed mb-5">
              Compile a structured CSV file matching Verra&apos;s VCS uploading protocols. Includes geographical markers, verified ledger calculations, and dynamic double-blind audit keys.
            </p>
          </div>

          <div className="flex gap-2 border-t border-[var(--color-border)]/30 pt-4">
            <button
              onClick={handleVerraExport}
              disabled={verraStatus === "loading"}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-[#00B47A]/10 hover:bg-[#00B47A] text-[#00B47A] hover:text-white text-[10px] font-extrabold uppercase tracking-wider border border-[#00B47A]/25 transition-all disabled:opacity-50 active:scale-95"
            >
              {statusIcon(verraStatus) || <Download size={13} />}
              {verraStatus === "loading" ? "Compiling..." : "Download CSV"}
            </button>
            
            <button
              onClick={handleVerraIssue}
              disabled={verraIssueStatus === "loading"}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-blue-600/10 hover:bg-blue-600 text-blue-400 hover:text-white text-[10px] font-extrabold uppercase tracking-wider border border-blue-500/25 transition-all disabled:opacity-50 active:scale-95"
            >
              {statusIcon(verraIssueStatus) || <Leaf size={13} />}
              {verraIssueStatus === "loading" ? "Issuing..." : "Commit Credits"}
            </button>
          </div>
        </div>

        {/* Gold Standard Card */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 flex flex-col justify-between shadow-sm relative overflow-hidden group hover:border-amber-500/30 transition-all">
          <div>
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-amber-500/5 border border-amber-500/10 flex items-center justify-center text-amber-500">
                  <FileDown size={22} />
                </div>
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">
                    Gold Standard Registry
                  </h3>
                  <p className="text-[9px] text-[var(--color-text-muted)] font-mono font-bold mt-0.5">
                    JSON EXPORT • MECD METHODOLOGY
                  </p>
                </div>
              </div>
            </div>
            
            <p className="text-xs text-[var(--color-text-secondary)] font-medium leading-relaxed mb-5">
              Export high-fidelity JSON arrays compatible with Gold Standard API verification schemas. Attests full telemetry tracking metrics and absolute stove operating logs.
            </p>
          </div>

          <div className="flex gap-2 border-t border-[var(--color-border)]/30 pt-4">
            <button
              onClick={handleGoldStandardExport}
              disabled={gsStatus === "loading"}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-amber-500/10 hover:bg-amber-500 text-amber-500 hover:text-white text-[10px] font-extrabold uppercase tracking-wider border border-amber-500/25 transition-all disabled:opacity-50 active:scale-95"
            >
              {statusIcon(gsStatus) || <Download size={13} />}
              {gsStatus === "loading" ? "Compiling..." : "Export JSON"}
            </button>
            
            <button
              onClick={handleGsIssue}
              disabled={gsIssueStatus === "loading"}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-blue-600/10 hover:bg-blue-600 text-blue-400 hover:text-white text-[10px] font-extrabold uppercase tracking-wider border border-blue-500/25 transition-all disabled:opacity-50 active:scale-95"
            >
              {statusIcon(gsIssueStatus) || <Leaf size={13} />}
              {gsIssueStatus === "loading" ? "Issuing..." : "Commit Credits"}
            </button>
          </div>
        </div>

      </div>

      {/* 🧭 PREVIEW COMPILATION PACK */}
      {lastResult && (
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm animate-fade-in">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)] mb-3.5">
            Active Compilations Summary
          </h3>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 text-xs">
            {lastResult.registry && (
              <div>
                <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Target Registry</p>
                <p className="font-bold text-[var(--color-text-primary)] mt-1">{lastResult.registry}</p>
              </div>
            )}
            {lastResult.total_records !== undefined && (
              <div>
                <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Compiled Records</p>
                <p className="font-bold text-[var(--color-text-primary)] mt-1">{lastResult.total_records}</p>
              </div>
            )}
            {lastResult.total_tco2e !== undefined && (
              <div>
                <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Dispatched tCO2e</p>
                <p className="font-black text-[#00B47A] mt-1">+{lastResult.total_tco2e}</p>
              </div>
            )}
            {lastResult.payload_size !== undefined && (
              <div>
                <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Secure Credits</p>
                <p className="font-black text-blue-400 mt-1">{lastResult.payload_size}</p>
              </div>
            )}
          </div>
          
          {lastResult.action && (
            <div className="flex items-center gap-1.5 text-xs border-t border-[var(--color-border)]/30 pt-3.5 font-bold text-[#00B47A] uppercase tracking-wider">
              <CheckCircle size={14} />
              <span>{lastResult.action}</span>
            </div>
          )}
        </div>
      )}

      {/* 🧭 SYSTEM COMPILATION MANUAL */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm text-xs">
        <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)] mb-4">
          Export Compilation Manual
        </h3>
        
        <div className="space-y-4 text-[var(--color-text-secondary)] font-medium leading-relaxed">
          <div className="flex gap-3">
            <span className="shrink-0 w-5 h-5 rounded-full bg-[#00B47A]/15 text-[#00B47A] flex items-center justify-center text-[10px] font-black font-mono">1</span>
            <p>Select the minimum confidence index score. Activations falling below will be ignored in this run.</p>
          </div>
          <div className="flex gap-3">
            <span className="shrink-0 w-5 h-5 rounded-full bg-[#00B47A]/15 text-[#00B47A] flex items-center justify-center text-[10px] font-black font-mono">2</span>
            <p>Generate and retrieve either Verra VCS (CSV) or Gold Standard MECD (JSON) compiled registry files.</p>
          </div>
          <div className="flex gap-3">
            <span className="shrink-0 w-5 h-5 rounded-full bg-[#00B47A]/15 text-[#00B47A] flex items-center justify-center text-[10px] font-black font-mono">3</span>
            <p>Dispatch the calculations. Committing calculations blocks double-spend claims and updates Carbon Ledger stats.</p>
          </div>
        </div>
      </div>

    </div>
  );
}
