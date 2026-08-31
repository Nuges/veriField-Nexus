"use client";

import { useEffect, useState } from "react";
import { Leaf, RefreshCw, Send, Layers, Coins, CheckCircle2, Shield, X, Check, Loader2, ExternalLink, AlertTriangle } from "lucide-react";
import { fetchCarbonLedger, fetchProjects, executeCarbonMinting } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { useWorkspace } from "@/context/WorkspaceContext";

export default function CarbonLedgerPage() {
  const { activeSector, activeMethodology, activeProject, filterCarbonLedger } = useWorkspace();
  const toast = useToast();

  const [ledger, setLedger] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Minting state
  const [isMintModalOpen, setIsMintModalOpen] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [targetChain, setTargetChain] = useState("solana-devnet");
  const [recipientWallet, setRecipientWallet] = useState("VF_Treasury_9xQeWv7zP2kM1n4L6sT8");
  const [isMinting, setIsMinting] = useState(false);
  const [mintResult, setMintResult] = useState<any>(null);
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

          <div className="flex items-center gap-2">

            <span className="px-2.5 py-0.5 rounded bg-[#00B47A]/10 text-[#00B47A] text-[9px] font-extrabold tracking-wider uppercase border border-[#00B47A]/20">

              MRV Carbon Ledger

            </span>

          </div>

          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)] mt-1 flex items-center gap-2">

            <Leaf className="text-[#00B47A]" size={20} />

            Deterministic Issuance Ledger

          </h1>

          <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">

            Audit immutable carbon credit quantifications calculated under the active methodology.

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
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white font-bold text-xs flex items-center gap-1.5 transition-all shadow-md shadow-emerald-500/20 active:scale-95 cursor-pointer"
          >
            <Coins size={14} />
            <span>Execute Minting</span>
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

      {/* On-Chain Solana Carbon Credit Minting Modal */}
      {isMintModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-xl rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between bg-gradient-to-r from-emerald-950/30 via-slate-900 to-transparent">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center">
                  <Coins size={20} />
                </div>
                <div>
                  <h3 className="text-base font-bold text-[var(--color-text-primary)] flex items-center gap-2">
                    <span>On-Chain Carbon Credit Minting</span>
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono">
                      Solana / CIOS Ledger
                    </span>
                  </h3>
                  <p className="text-xs text-[var(--color-text-secondary)]">
                    Direct cryptographic token issuance & serial number allocation
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsMintModalOpen(false)}
                className="p-2 rounded-lg hover:bg-slate-800 text-[var(--color-text-muted)] hover:text-white transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 space-y-4 overflow-y-auto flex-1 text-xs">
              {mintResult ? (
                /* Success State */
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 space-y-2">
                    <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                      <CheckCircle2 size={18} />
                      <span>{mintResult.message}</span>
                    </div>
                    <p className="text-[var(--color-text-secondary)] leading-relaxed">
                      Immutable carbon assets successfully issued on-chain and registered to the VeriField sovereign cryptographic ledger.
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2.5 font-mono text-[11px]">
                    <div className="flex justify-between py-1 border-b border-[var(--color-border)]">
                      <span className="text-[var(--color-text-secondary)]">Status:</span>
                      <span className="text-emerald-400 font-bold">MINTED & VERIFIED</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[var(--color-border)]">
                      <span className="text-[var(--color-text-secondary)]">Serial Number:</span>
                      <span className="text-[var(--color-text-primary)] font-bold">{mintResult.serial_number}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[var(--color-border)]">
                      <span className="text-[var(--color-text-secondary)]">Volume Minted:</span>
                      <span className="text-emerald-400 font-bold">{mintResult.total_tco2e} tCO2e</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[var(--color-border)]">
                      <span className="text-[var(--color-text-secondary)]">Target Chain:</span>
                      <span className="text-[var(--color-text-primary)] uppercase">{mintResult.target_chain}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[var(--color-border)]">
                      <span className="text-[var(--color-text-secondary)]">Recipient Wallet:</span>
                      <span className="text-[var(--color-text-primary)] truncate max-w-[220px]">{mintResult.recipient_wallet}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[var(--color-border)]">
                      <span className="text-[var(--color-text-secondary)]">Transaction Hash:</span>
                      <span className="text-blue-400 truncate max-w-[220px]">{mintResult.transaction_signature}</span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-[var(--color-text-secondary)]">Signature Hash:</span>
                      <span className="text-[var(--color-text-muted)] truncate max-w-[220px]">{mintResult.signature_hash}</span>
                    </div>
                  </div>

                  <div className="flex gap-2 pt-2">
                    <a
                      href={mintResult.explorer_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 py-2.5 px-3 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-xs font-semibold text-center text-white flex items-center justify-center gap-1.5 transition-colors shadow-md shadow-purple-500/20"
                    >
                      <ExternalLink size={14} />
                      <span>View on Solana Explorer</span>
                    </a>
                    <button
                      type="button"
                      onClick={() => {
                        setIsMintModalOpen(false);
                        loadData();
                      }}
                      className="flex-1 py-2.5 px-3 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] hover:border-emerald-500 text-xs font-semibold text-center text-[var(--color-text-primary)] flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
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
                    } catch (err: any) {
                      setMintError(err?.message || "Failed to execute on-chain minting. Ensure carbon records are verified.");
                    } finally {
                      setIsMinting(false);
                    }
                  }}
                  className="space-y-4"
                >
                  {mintError && (
                    <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 flex items-center gap-2">
                      <AlertTriangle size={15} className="shrink-0" />
                      <span>{mintError}</span>
                    </div>
                  )}

                  {/* Project Selector */}
                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1.5">
                      Select Project to Mint Credits For
                    </label>
                    <select
                      value={selectedProjectId}
                      onChange={(e) => setSelectedProjectId(e.target.value)}
                      className="w-full px-3 py-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
                    >
                      {projects.length === 0 && <option value="">All Verified Activities in Organization</option>}
                      {projects.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name} ({p.country || "Nigeria"}) — {p.sector || "Clean Energy / MRV"}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Target Blockchain & Recipient */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1.5">
                        Target Ledger / Chain
                      </label>
                      <select
                        value={targetChain}
                        onChange={(e) => setTargetChain(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
                      >
                        <option value="solana-devnet">Solana Devnet (Direct)</option>
                        <option value="solana-mainnet">Solana Mainnet (Beta)</option>
                        <option value="polygon">Polygon PoS</option>
                        <option value="internal-ledger">VeriField Private Ledger</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1.5">
                        Issuance Standard
                      </label>
                      <input
                        type="text"
                        value="VeriField SPL-Token (tCO2e)"
                        disabled
                        className="w-full px-3 py-2 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs text-[var(--color-text-muted)] cursor-not-allowed"
                      />
                    </div>
                  </div>

                  {/* Recipient Wallet */}
                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1.5">
                      Treasury / Recipient Wallet Address
                    </label>
                    <input
                      type="text"
                      value={recipientWallet}
                      onChange={(e) => setRecipientWallet(e.target.value)}
                      required
                      placeholder="e.g. Solana / SPL Wallet Address"
                      className="w-full px-3 py-2 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500 font-mono text-[11px]"
                    />
                  </div>

                  {/* Cryptographic Ledger Safeguards */}
                  <div className="p-3 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-1.5">
                    <p className="text-[11px] font-bold text-[var(--color-text-primary)] uppercase tracking-wider mb-1">
                      Ledger Integrity Checklist
                    </p>
                    <div className="flex items-center gap-2 text-[11px] text-emerald-400">
                      <Check size={13} />
                      <span>AST-sandboxed baseline emission reduction verified</span>
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-emerald-400">
                      <Check size={13} />
                      <span>RSA-2048 Digital Signature & Canonical SHA-256 Hash</span>
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-emerald-400">
                      <Check size={13} />
                      <span>Immutable Audit Trail record written before broadcast</span>
                    </div>
                  </div>

                  {/* Mint Button */}
                  <button
                    type="submit"
                    disabled={isMinting}
                    className="w-full py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white font-bold text-xs disabled:opacity-50 flex items-center justify-center gap-2 transition-all cursor-pointer shadow-lg shadow-emerald-500/20"
                  >
                    {isMinting ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        <span>Signing & Minting On-Chain...</span>
                      </>
                    ) : (
                      <>
                        <Coins size={15} />
                        <span>Execute Cryptographic Minting</span>
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
