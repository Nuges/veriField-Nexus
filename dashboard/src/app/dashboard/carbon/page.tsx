"use client";

import { useEffect, useState } from "react";
import { Leaf, RefreshCw, Send, Layers, Coins, CheckCircle2, Shield, X, Check, Loader2, ExternalLink, AlertTriangle } from "lucide-react";
import { fetchCarbonLedger, fetchProjects, executeCarbonMinting, CarbonMintResponse } from "@/lib/api";
import type { Project } from "@/lib/types";
import { useToast } from "@/components/Toast";
import { useWorkspace } from "@/context/WorkspaceContext";

export default function CarbonLedgerPage() {
  const { activeSector, activeMethodology, activeProject, filterCarbonLedger } = useWorkspace();
  const toast = useToast();

  const [ledger, setLedger] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Minting state
  const [isMintModalOpen, setIsMintModalOpen] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [targetChain, setTargetChain] = useState("internal-ledger");
  const [recipientWallet, setRecipientWallet] = useState("VF_Treasury_Custody_Account");
  const [isMinting, setIsMinting] = useState(false);
  const [mintResult, setMintResult] = useState<CarbonMintResponse | null>(null);
  const [mintError, setMintError] = useState<string | null>(null);



  const loadData = async () => {

    setIsLoading(true);

    try {

      const res = await fetchCarbonLedger(true);

      setLedger(res.data || []);

    } catch (err) {

      console.error("Failed to load carbon ledger:", err);

      toast.error("Ledger Sync Failed", "Unable to retrieve the carbon ledger.");

    } finally {

      setIsLoading(false);

    }

  };



  useEffect(() => {

    loadData();

  }, [activeSector, activeMethodology, activeProject]);



  const isolatedLedger = filterCarbonLedger(ledger);

  const totalTco2e = isolatedLedger.reduce((acc, c) => acc + (c.tco2e || c.tco2 || c.tco2e_generated || 0), 0);

  const estimatedRevenue = isolatedLedger.reduce((acc, c) => acc + (c.estimated_value || 0), 0);

  const pendingCount = isolatedLedger.filter(l => l.status === "calculated").length;



  return (

    <div className="space-y-6 max-w-7xl mx-auto pb-10 animate-fade-in-up text-[var(--color-text-primary)] mt-12 md:mt-0">



      {/* 👑 TITLE SECTION */}

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">

        <div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)]">
            Deterministic Issuance Ledger
          </h1>
          <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">
            Audit immutable carbon credit quantifications and cryptographic serial seals under the active methodology.
          </p>
        </div>



        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setIsMintModalOpen(true);
              setMintResult(null);
              setMintError(null);
              fetchProjects()
                .then((r) => {
                  const items = r?.items || [];
                  setProjects(items);
                  if (items.length > 0) {
                    setSelectedProjectId(items[0].id);
                  }
                })
                .catch(() => {});
            }}
            className="px-3.5 py-2 rounded-lg bg-[#008A5E] hover:bg-[#00734E] text-white font-semibold text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Shield size={14} />
            <span>Issue & Seal Credits</span>
          </button>
          <button
            onClick={loadData}
            className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[#00B47A] hover:border-[#00B47A]/30 transition-all shadow-sm active:scale-95 cursor-pointer"
            title="Reload ledger"
          >
            <RefreshCw size={15} className={isLoading ? "animate-spin text-[#00B47A]" : ""} />
          </button>
        </div>

      </div>



      {/* 📊 CORE METRICS CARDS */}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden">

          <div className="space-y-1">

            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Total Verified Offset</p>

            <p className="text-2xl font-black text-[#00B47A] tracking-tight">

              {isLoading ? "..." : totalTco2e.toFixed(4)} <span className="text-xs font-bold text-[var(--color-text-muted)]">tCO2e</span>

            </p>

          </div>

        </div>



        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden">

          <div className="space-y-1">

            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Calculated Floor Value</p>

            <p className="text-2xl font-black text-blue-400 tracking-tight">

              {isLoading ? "..." : `$${estimatedRevenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}

            </p>

          </div>

        </div>



        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden">

          <div className="space-y-1">

            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Unissued Allocations</p>

            <p className="text-2xl font-black text-[var(--color-text-primary)] tracking-tight">

              {isLoading ? "..." : pendingCount} <span className="text-xs font-bold text-[var(--color-text-muted)]">Records</span>

            </p>

          </div>

        </div>

      </div>



      {/* 🧭 CALCULATION LEDGER TABLE */}

      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-sm overflow-hidden">

        <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-background)]/50">

          <h2 className="text-xs font-bold uppercase tracking-wider">Calculation Ledger</h2>

          <div className="text-[9px] font-extrabold text-[#00B47A] bg-[#00B47A]/10 border border-[#00B47A]/20 px-2 py-0.5 rounded uppercase">

            {isolatedLedger.length} active logs

          </div>

        </div>



        <div className="overflow-x-auto">

          <table className="w-full text-left border-collapse">

            <thead>

              <tr className="bg-[var(--color-background)]/40 border-b border-[var(--color-border)]">

                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">ID</th>

                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Methodology</th>

                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-right">Volume (tCO2e)</th>

                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-right">Market Value</th>

                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-center">Status</th>

              </tr>

            </thead>

            <tbody>

              {isolatedLedger.map((row: any) => (

                <tr key={row.id} className="border-b border-[var(--color-border)] hover:bg-[var(--color-surface-hover)] transition-colors">

                  <td className="p-4 text-xs font-mono text-[var(--color-text-secondary)]">{row.id.split("-")[0]}</td>

                  <td className="p-4 text-xs font-bold text-[var(--color-text-primary)]">{row.methodology_code || activeMethodology || "Generic"}</td>

                  <td className="p-4 text-sm font-black text-[var(--color-text-primary)] text-right">

                    {(row.tco2e || row.tco2 || row.tco2e_generated || 0).toFixed(4)}

                  </td>

                  <td className="p-4 text-xs font-bold text-[var(--color-text-secondary)] text-right">

                    ${(row.estimated_value || 0).toFixed(2)}

                  </td>

                  <td className="p-4 text-center">

                    <span className="px-2 py-1 bg-amber-500/10 text-amber-500 text-[10px] font-bold uppercase rounded">

                      {row.status || "Pending"}

                    </span>

                  </td>

                </tr>

              ))}

              {isolatedLedger.length === 0 && !isLoading && (

                <tr>

                  <td colSpan={5} className="p-12 text-center text-[var(--color-text-muted)] text-sm font-mono">

                    No ledger entries found for this context.

                  </td>

                </tr>

              )}

            </tbody>

          </table>

        </div>

      </div>

      {/* Cryptographic Ledger Issuance & Serial Allocation Modal */}
      {isMintModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs animate-fade-in">
          <div className="w-full max-w-xl rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xl overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="p-4.5 border-b border-[var(--color-border)] flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 flex items-center justify-center">
                  <Shield size={18} />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-[var(--color-text-primary)] flex items-center gap-2">
                    <span>Cryptographic Credit Issuance & Serial Sealing</span>
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono">
                      Sovereign CIOS Ledger
                    </span>
                  </h3>
                  <p className="text-xs text-[var(--color-text-secondary)]">
                    Deterministic cryptographic issuance, serial allocation & tamper-evident ledger sealing
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsMintModalOpen(false)}
                className="p-1.5 rounded-md hover:bg-slate-800 text-[var(--color-text-muted)] hover:text-white transition-colors cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 space-y-4 overflow-y-auto flex-1 text-xs">
              {mintResult ? (
                /* Success State */
                <div className="space-y-4">
                  <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30 space-y-1.5">
                    <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs">
                      <CheckCircle2 size={16} />
                      <span>{mintResult.message}</span>
                    </div>
                    <p className="text-[var(--color-text-secondary)] text-xs leading-relaxed">
                      Immutable carbon assets successfully sealed and registered to the sovereign cryptographic ledger.
                    </p>
                  </div>

                  <div className="p-4 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] space-y-2 font-mono text-[11px]">
                    <div className="flex justify-between py-1 border-b border-[var(--color-border)]">
                      <span className="text-[var(--color-text-secondary)]">Status:</span>
                      <span className="text-emerald-400 font-bold">ISSUED & SEALED</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[var(--color-border)]">
                      <span className="text-[var(--color-text-secondary)]">Serial Number:</span>
                      <span className="text-[var(--color-text-primary)] font-bold">{mintResult.serial_number}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[var(--color-border)]">
                      <span className="text-[var(--color-text-secondary)]">Volume Issued:</span>
                      <span className="text-emerald-400 font-bold">{mintResult.total_tco2e} tCO2e</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[var(--color-border)]">
                      <span className="text-[var(--color-text-secondary)]">Target Ledger:</span>
                      <span className="text-[var(--color-text-primary)] uppercase">{mintResult.target_chain}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[var(--color-border)]">
                      <span className="text-[var(--color-text-secondary)]">Custody Account:</span>
                      <span className="text-[var(--color-text-primary)] truncate max-w-[220px]">{mintResult.recipient_wallet}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[var(--color-border)]">
                      <span className="text-[var(--color-text-secondary)]">Transaction Hash:</span>
                      <span className="text-blue-400 truncate max-w-[220px]">{mintResult.transaction_signature}</span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-[var(--color-text-secondary)]">Payload Hash:</span>
                      <span className="text-[var(--color-text-muted)] truncate max-w-[220px]">{mintResult.signature_hash}</span>
                    </div>
                  </div>

                  <div className="flex gap-2 pt-2">
                    <a
                      href={mintResult.explorer_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 py-2 px-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] hover:border-emerald-500 text-xs font-semibold text-center text-[var(--color-text-primary)] flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                    >
                      <Shield size={13} className="text-[#008A5E]" />
                      <span>View Ledger Record</span>
                    </a>
                    <button
                      type="button"
                      onClick={() => {
                        setIsMintModalOpen(false);
                        loadData();
                      }}
                      className="flex-1 py-2 px-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] hover:border-emerald-500 text-xs font-semibold text-center text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                    >
                      <span>Close & Refresh</span>
                    </button>
                  </div>
                </div>
              ) : (
                /* Mint Form State */
                <form
                  onSubmit={async (e) => {
                    e.preventDefault();
                    const projIdToSubmit = selectedProjectId || (projects.length > 0 ? projects[0].id : "");
                    setIsMinting(true);
                    setMintError(null);
                    try {
                      const res = await executeCarbonMinting({
                        project_id: projIdToSubmit || undefined,
                        target_chain: targetChain,
                        recipient_wallet: recipientWallet,
                      });
                      setMintResult(res);
                      loadData();
                    } catch (err: unknown) {
                      const message = err instanceof Error ? err.message : (typeof err === "object" && err !== null && "message" in err ? String((err as { message: unknown }).message) : "Failed to execute cryptographic issuance. Ensure carbon records are verified.");
                      setMintError(message);
                    } finally {
                      setIsMinting(false);
                    }
                  }}
                  className="space-y-4"
                >
                  {mintError && (
                    <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 flex items-center gap-2">
                      <AlertTriangle size={15} className="shrink-0" />
                      <span>{mintError}</span>
                    </div>
                  )}

                  {/* Project Selector */}
                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1.5">
                      Select Project for Credit Issuance
                    </label>
                    <select
                      value={selectedProjectId}
                      onChange={(e) => setSelectedProjectId(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
                    >
                      {projects.length === 0 && <option value="">All Verified Activities in Organization</option>}
                      {projects.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name} ({p.country || "Nigeria"}) — {p.sector || "Clean Energy / MRV"}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Target Ledger & Recipient */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1.5">
                        Target Ledger Architecture
                      </label>
                      <select
                        value={targetChain}
                        onChange={(e) => setTargetChain(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
                      >
                        <option value="internal-ledger">VeriField Sovereign Ledger (Primary)</option>
                        <option value="solana-devnet">Distributed Ledger Sync (Audit Bridge)</option>
                        <option value="polygon">Enterprise Settlement Network</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1.5">
                        Issuance Standard
                      </label>
                      <input
                        type="text"
                        value="VeriField Compliance Standard (tCO2e)"
                        disabled
                        className="w-full px-3 py-2 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-xs text-[var(--color-text-muted)] cursor-not-allowed"
                      />
                    </div>
                  </div>

                  {/* Custody Account / Recipient */}
                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1.5">
                      Treasury Account / Custody Identifier
                    </label>
                    <input
                      type="text"
                      value={recipientWallet}
                      onChange={(e) => setRecipientWallet(e.target.value)}
                      required
                      placeholder="e.g. VF_Treasury_Custody_Account"
                      className="w-full px-3 py-2 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500 font-mono text-[11px]"
                    />
                  </div>

                  {/* Cryptographic Ledger Safeguards */}
                  <div className="p-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] space-y-1.5">
                    <p className="text-[11px] font-bold text-[var(--color-text-primary)] uppercase tracking-wider mb-1">
                      Ledger Integrity Safeguards
                    </p>
                    <div className="flex items-center gap-2 text-[11px] text-emerald-500">
                      <Check size={13} />
                      <span>AST-sandboxed baseline emission reduction verified</span>
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-emerald-500">
                      <Check size={13} />
                      <span>RSA-2048 Digital Signature & Canonical SHA-256 Hash</span>
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-emerald-500">
                      <Check size={13} />
                      <span>Immutable Audit Trail record sealed before broadcast</span>
                    </div>
                  </div>

                  {/* Mint Button */}
                  <button
                    type="submit"
                    disabled={isMinting}
                    className="w-full py-2.5 rounded-lg bg-[#008A5E] hover:bg-[#00734E] text-white font-semibold text-xs disabled:opacity-50 flex items-center justify-center gap-2 transition-colors cursor-pointer"
                  >
                    {isMinting ? (
                      <>
                        <Loader2 size={15} className="animate-spin" />
                        <span>Sealing Ledger & Generating Serial...</span>
                      </>
                    ) : (
                      <>
                        <Shield size={14} />
                        <span>Sign & Execute Ledger Issuance</span>
                      </>
                    )}
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
