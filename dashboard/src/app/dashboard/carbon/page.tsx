"use client";

import { useEffect, useState } from "react";
import { Leaf, RefreshCw, Send, BookOpen, AlertCircle, TrendingUp, DollarSign, X } from "lucide-react";
import { fetchCarbonLedger, issueVerraCredits, issueGoldStandardCredits } from "@/lib/api";

export default function CarbonLedgerPage() {
  const [ledger, setLedger] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isIssuing, setIsIssuing] = useState(false);
  const [issuanceResult, setIssuanceResult] = useState<any>(null);
  const [selectedLog, setSelectedLog] = useState<any>(null);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const res = await fetchCarbonLedger();
      setLedger(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleIssue = async (registry: "Verra" | "Gold Standard") => {
    if (!confirm(`Are you sure you want to lock these credits and push to the ${registry} Registry?`)) return;
    setIsIssuing(true);
    try {
      const result = registry === "Verra" ? await issueVerraCredits() : await issueGoldStandardCredits();
      setIssuanceResult(result);
      loadData();
    } catch (err) {
      console.error(err);
      alert("Failed to issue credits.");
    } finally {
      setIsIssuing(false);
    }
  };

  // Dynamic Carbon Pricing based on Methodology and Market Integrity
  // High-integrity MRV commands premium floor prices
  const PRICING_MAP: Record<string, number> = {
    "VM0006": 25.00,  // High-Integrity Cookstoves (Verra)
    "TPDDTEC": 25.00, // High-Integrity Thermal Energy (Gold Standard)
    "AR-ACM0003": 18.50, // Afforestation/Reforestation
    "DEFAULT": 10.00
  };

  const getPrice = (methodology: string) => PRICING_MAP[methodology] || PRICING_MAP["DEFAULT"];

  // Calculate metrics
  const totalTco2e = ledger.reduce((acc, c) => acc + (c.tco2e || c.tco2e_generated || 0), 0);
  
  const estimatedRevenue = ledger.reduce((acc, c) => {
    const volume = c.tco2e || c.tco2e_generated || 0;
    const price = getPrice(c.methodology);
    return acc + (volume * price);
  }, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight flex items-center gap-2">
            <Leaf className="text-emerald-500" /> Carbon Ledger
          </h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">
            Immutable log of all deterministically calculated carbon credits ready for registry issuance.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={loadData} 
            className="p-2 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            <RefreshCw size={18} className={isLoading ? "animate-spin" : ""} />
          </button>
          <button 
            onClick={() => handleIssue("Verra")}
            disabled={isIssuing || ledger.filter(l => l.status === "calculated").length === 0}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-500 text-white font-medium hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/20"
          >
            {isIssuing ? <RefreshCw size={18} className="animate-spin" /> : <Send size={18} />}
            Push to Verra
          </button>
          <button 
            onClick={() => handleIssue("Gold Standard")}
            disabled={isIssuing || ledger.filter(l => l.status === "calculated").length === 0}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-500 text-white font-medium hover:bg-amber-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-amber-500/20"
          >
            {isIssuing ? <RefreshCw size={18} className="animate-spin" /> : <Send size={18} />}
            Push to Gold Standard
          </button>
        </div>
      </div>

      {/* Issuance Success Banner */}
      {issuanceResult && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl flex items-start gap-3 animate-fade-in-up">
          <div className="p-2 bg-emerald-500/20 rounded-lg shrink-0 mt-0.5">
            <Send className="text-emerald-400" size={18} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-emerald-400">{issuanceResult.registry} Registry Push Successful</h3>
            <p className="text-sm text-[var(--color-text-secondary)] mt-1">
              Successfully requested issuance for {issuanceResult.total_tco2e} tCO2e across {issuanceResult.payload_size} activities. An audit pack has been generated and securely transmitted to {issuanceResult.registry}.
            </p>
          </div>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-fade-in-up animation-delay-100">
        <div className="bg-[var(--color-card)] border border-[var(--color-border)] p-5 rounded-2xl">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-[var(--color-text-secondary)]">Total Verified Carbon</h3>
            <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-400">
              <Leaf size={20} />
            </div>
          </div>
          <div className="text-3xl font-bold text-[var(--color-text-primary)]">
            {totalTco2e.toFixed(4)} <span className="text-sm text-[var(--color-text-secondary)] font-normal">tCO2e</span>
          </div>
        </div>

        <div className="bg-[var(--color-card)] border border-[var(--color-border)] p-5 rounded-2xl">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-[var(--color-text-secondary)]">Estimated Value</h3>
            <div className="p-2 bg-blue-500/10 rounded-lg text-blue-400">
              <DollarSign size={20} />
            </div>
          </div>
          <div className="text-3xl font-bold text-[var(--color-text-primary)]">
            ${estimatedRevenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <p className="text-xs text-[var(--color-text-muted)] mt-2">Dynamically calculated by methodology</p>
        </div>

        <div className="bg-[var(--color-card)] border border-[var(--color-border)] p-5 rounded-2xl">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-[var(--color-text-secondary)]">Pending Issuance</h3>
            <div className="p-2 bg-amber-500/10 rounded-lg text-amber-400">
              <TrendingUp size={20} />
            </div>
          </div>
          <div className="text-3xl font-bold text-[var(--color-text-primary)]">
            {ledger.filter(l => l.status === "calculated").length} <span className="text-sm text-[var(--color-text-secondary)] font-normal">Records</span>
          </div>
        </div>
      </div>

      {/* Ledger Table */}
      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl overflow-hidden animate-fade-in-up animation-delay-200">
        <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between">
          <h2 className="font-semibold text-[var(--color-text-primary)]">Calculation Ledger</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[var(--color-surface)] border-b border-[var(--color-border)]">
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Calc ID</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Methodology</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider text-right">Volume (tCO2e)</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider text-right">Est. Value</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider text-center">Status</th>
                <th className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {isLoading && ledger.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-[var(--color-text-secondary)]">Loading ledger...</td>
                </tr>
              ) : ledger.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-12 text-center">
                    <div className="flex flex-col items-center justify-center">
                      <div className="w-12 h-12 rounded-full bg-[var(--color-surface)] flex items-center justify-center mb-3">
                        <AlertCircle className="text-[var(--color-text-muted)]" size={24} />
                      </div>
                      <p className="text-[var(--color-text-secondary)] font-medium">No calculations yet</p>
                      <p className="text-[var(--color-text-muted)] text-sm mt-1">Approve some activities to generate credits.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                ledger.map((row) => (
                  <tr key={row.id} className="hover:bg-[var(--color-surface)] transition-colors group">
                    <td className="p-4">
                      <span className="text-sm text-[var(--color-text-secondary)] font-mono">{row.id.substring(0, 8)}...</span>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <BookOpen size={16} className="text-[var(--color-text-muted)]" />
                        <span className="text-sm font-medium text-[var(--color-text-primary)]">{row.methodology}</span>
                      </div>
                    </td>
                    <td className="p-4 text-right">
                      <span className="text-sm font-bold text-emerald-400">+{row.tco2e || row.tco2e_generated}</span>
                    </td>
                    <td className="p-4 text-right">
                      <span className="text-sm text-[var(--color-text-primary)]">
                        ${((row.tco2e || row.tco2e_generated) * getPrice(row.methodology)).toFixed(2)}
                      </span>
                      <span className="block text-xs text-[var(--color-text-muted)]">
                        @ ${getPrice(row.methodology)}/t
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${
                        row.status === "calculated" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                        row.status === "pending_issuance" ? "bg-blue-500/10 text-blue-400 border-blue-500/20" :
                        "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      }`}>
                        {row.status === "calculated" ? "Pending Registry" : 
                         row.status === "pending_issuance" ? "Awaiting Issuance" : "Issued"}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <button 
                        onClick={() => setSelectedLog(row)}
                        className="text-sm text-emerald-500 hover:text-emerald-400 font-medium transition-colors"
                      >
                        View Audit Log
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Audit Log Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col overflow-hidden shadow-2xl">
            <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-surface)]">
              <div>
                <h3 className="text-lg font-bold text-[var(--color-text-primary)]">Calculation Audit Log</h3>
                <p className="text-sm text-[var(--color-text-secondary)]">ID: <span className="font-mono text-emerald-400">{selectedLog.id}</span></p>
              </div>
              <button 
                onClick={() => setSelectedLog(null)}
                className="p-2 rounded-xl hover:bg-[var(--color-card)] border border-transparent hover:border-[var(--color-border)] text-[var(--color-text-secondary)] transition-all"
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto space-y-6 flex-1 custom-scrollbar">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-[var(--color-surface)] p-4 rounded-xl border border-[var(--color-border)]">
                  <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-1">Methodology</p>
                  <p className="font-semibold text-[var(--color-text-primary)]">{selectedLog.methodology}</p>
                </div>
                <div className="bg-[var(--color-surface)] p-4 rounded-xl border border-[var(--color-border)]">
                  <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-1">Generated Volume</p>
                  <p className="font-bold text-emerald-400">+{selectedLog.tco2e || selectedLog.tco2e_generated} tCO2e</p>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
                  <BookOpen size={16} className="text-emerald-500" /> Traceable Formula
                </h4>
                <div className="bg-slate-900 border border-slate-700 rounded-xl p-4 font-mono text-sm text-emerald-300 overflow-x-auto">
                  {selectedLog.calculation_log?.formula_trace || "Formula not recorded"}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">Deterministic Inputs</h4>
                <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl overflow-hidden">
                  <table className="w-full text-left text-sm">
                    <tbody className="divide-y divide-[var(--color-border)]">
                      {Object.entries(selectedLog.calculation_log?.inputs || {}).map(([key, value]) => (
                        <tr key={key}>
                          <td className="p-3 font-medium text-[var(--color-text-secondary)]">{key}</td>
                          <td className="p-3 font-mono text-[var(--color-text-primary)] text-right">{String(value)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">Complete Raw JSON</h4>
                <pre className="bg-slate-900 border border-slate-700 rounded-xl p-4 overflow-x-auto text-xs text-slate-300 font-mono">
                  {JSON.stringify(selectedLog.calculation_log, null, 2)}
                </pre>
              </div>
            </div>
            
            <div className="p-5 border-t border-[var(--color-border)] bg-[var(--color-surface)] flex justify-end">
              <button 
                onClick={() => setSelectedLog(null)}
                className="px-5 py-2 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-medium hover:bg-slate-800 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
