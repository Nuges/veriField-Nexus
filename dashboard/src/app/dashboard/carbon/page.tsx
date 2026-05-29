"use client";

import { useEffect, useState } from "react";
import { 
  Leaf, 
  RefreshCw, 
  Send, 
  BookOpen, 
  AlertCircle, 
  TrendingUp, 
  DollarSign, 
  X,
  ShieldCheck,
  Calendar,
  Layers,
  ArrowRight,
  Cpu
} from "lucide-react";
import { fetchCarbonLedger, issueVerraCredits, issueGoldStandardCredits } from "@/lib/api";
import { useToast } from "@/components/Toast";

export default function CarbonLedgerPage() {
  const toast = useToast();
  const [ledger, setLedger] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isIssuing, setIsIssuing] = useState(false);
  const [issuanceResult, setIssuanceResult] = useState<any>(null);
  const [selectedLog, setSelectedLog] = useState<any>(null);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const res = await fetchCarbonLedger(true);
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
    if (!confirm(`Are you sure you want to commit these calculations and export to the official ${registry} Registry?`)) return;
    setIsIssuing(true);
    try {
      const result = registry === "Verra" ? await issueVerraCredits() : await issueGoldStandardCredits();
      setIssuanceResult(result);
      toast.success("Registry Issuance Committed", `Successfully committed calculations to the ${registry} Registry.`);
      loadData();
    } catch (err) {
      console.error(err);
      toast.error("Issuance Failed", `Failed to complete API submission to ${registry}.`);
    } finally {
      setIsIssuing(false);
    }
  };

  // Pricing Matrix based on high-integrity telemetry standards
  const PRICING_MAP: Record<string, number> = {
    "VM0006": 25.00,  
    "TPDDTEC": 25.00, 
    "AR-ACM0003": 18.50, 
    "DEFAULT": 10.00
  };

  const getPrice = (methodology: string) => PRICING_MAP[methodology] || PRICING_MAP["DEFAULT"];

  // Aggregate Metrics
  const totalTco2e = ledger.reduce((acc, c) => acc + (c.tco2e || c.tco2 || c.tco2e_generated || 0), 0);
  
  const estimatedRevenue = ledger.reduce((acc, c) => {
    const volume = c.tco2e || c.tco2 || c.tco2e_generated || 0;
    const price = getPrice(c.methodology);
    return acc + (volume * price);
  }, 0);

  const pendingCount = ledger.filter(l => l.status === "calculated").length;

  return (
    <>
      <div className="space-y-6 max-w-7xl mx-auto pb-10 animate-fade-in-up text-[var(--color-text-primary)]">
      
      {/* 👑 TITLE SECTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded bg-[#00B47A]/10 text-[#00B47A] text-[9px] font-extrabold tracking-wider uppercase border border-[#00B47A]/15">
              MRV Carbon Ledger
            </span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)] mt-1 flex items-center gap-2">
            <Leaf className="text-[#00B47A]" size={20} /> Deterministic Issuance Ledger
          </h1>
          <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">
            Audit immutable carbon credit quantifications calculated under Verra and Gold Standard methodologies.
          </p>
        </div>
        
        <div className="flex items-center gap-2 flex-wrap">
          <button 
            onClick={loadData} 
            className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[#00B47A] hover:border-[#00B47A]/30 transition-all shadow-sm active:scale-95"
            title="Reload ledger"
          >
            <RefreshCw size={15} className={isLoading ? "animate-spin text-[#00B47A]" : ""} />
          </button>
          
          <button 
            onClick={() => handleIssue("Verra")}
            disabled={isIssuing || pendingCount === 0}
            className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-blue-600 text-white text-xs font-bold hover:bg-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-blue-600/25 active:scale-95 uppercase tracking-wider"
          >
            {isIssuing ? <RefreshCw size={14} className="animate-spin" /> : <Send size={14} />}
            Push to Verra
          </button>
          
          <button 
            onClick={() => handleIssue("Gold Standard")}
            disabled={isIssuing || pendingCount === 0}
            className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-[#00B47A] text-white text-xs font-bold hover:bg-[#00B47A]/95 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-[#00B47A]/25 active:scale-95 uppercase tracking-wider"
          >
            {isIssuing ? <RefreshCw size={14} className="animate-spin" /> : <Send size={14} />}
            Push to Gold Standard
          </button>
        </div>
      </div>

      {/* 🧭 ISSUANCE BANNER */}
      {issuanceResult && (
        <div className="p-4.5 bg-[#00B47A]/10 border border-[#00B47A]/25 rounded-2xl flex items-start gap-3.5 animate-fade-in">
          <div className="p-2 bg-[#00B47A]/20 rounded-xl text-[#00B47A] shrink-0">
            <ShieldCheck size={18} />
          </div>
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#00B47A]">{issuanceResult.registry} API Dispatch Success</h3>
            <p className="text-xs text-[var(--color-text-secondary)] mt-1 font-medium leading-relaxed">
              Successfully committed {issuanceResult.total_tco2e} tCO2e across {issuanceResult.payload_size} verification instances. The audit bundle has been securely transmitted.
            </p>
          </div>
        </div>
      )}

      {/* 📊 CORE METRICS CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* Total Carbon */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-[#00B47A]/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Total Verified Offset</p>
            <p className="text-2xl font-black text-[#00B47A] tracking-tight">
              {isLoading ? "..." : totalTco2e.toFixed(4)} <span className="text-xs font-bold text-[var(--color-text-muted)]">tCO2e</span>
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Aggregated environmental offsets</p>
          </div>
          <div className="p-3 bg-[#00B47A]/5 border border-[#00B47A]/10 rounded-xl text-[#00B47A] shrink-0 group-hover:bg-[#00B47A] group-hover:text-white transition-all duration-300">
            <Leaf size={18} />
          </div>
        </div>

        {/* Estimated Value */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-blue-500/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Calculated Floor Value</p>
            <p className="text-2xl font-black text-blue-400 tracking-tight">
              {isLoading ? "..." : `$${estimatedRevenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Market pricing based on integrity tier</p>
          </div>
          <div className="p-3 bg-blue-500/5 border border-blue-500/10 rounded-xl text-blue-400 shrink-0 group-hover:bg-blue-500 group-hover:text-white transition-all duration-300">
            <DollarSign size={18} />
          </div>
        </div>

        {/* Pending Records */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-purple-500/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Unissued Allocations</p>
            <p className="text-2xl font-black text-[var(--color-text-primary)] tracking-tight">
              {isLoading ? "..." : pendingCount} <span className="text-xs font-bold text-[var(--color-text-muted)]">Records</span>
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Awaiting registry sync triggers</p>
          </div>
          <div className="p-3 bg-[#00B47A]/5 border border-[#00B47A]/10 rounded-xl text-[#00B47A] shrink-0 group-hover:bg-purple-500 group-hover:text-white transition-all duration-300">
            <TrendingUp size={18} />
          </div>
        </div>

      </div>

      {/* 🧭 CALCULATION LEDGER TABLE */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-background)]/50">
          <h2 className="text-xs font-bold uppercase tracking-wider">Calculation Ledger</h2>
          <div className="text-[9px] font-extrabold text-[#00B47A] bg-[#00B47A]/5 border border-[#00B47A]/15 px-2 py-0.5 rounded uppercase">
            {ledger.length} active logs
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[var(--color-background)]/40 border-b border-[var(--color-border)]">
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Calc Spec ID</th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Methodology Protocol</th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-right">Volume (tCO2e)</th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-right">Est. Market Value</th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-center">Registry Status</th>
                <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-right">Audit Trail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]/70">
              {isLoading && ledger.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-12 text-center">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <div className="w-6 h-6 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />
                      <p className="text-xs text-[var(--color-text-secondary)] font-semibold">Retrieving calculation metrics...</p>
                    </div>
                  </td>
                </tr>
              ) : ledger.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-16 text-center">
                    <div className="flex flex-col items-center justify-center max-w-sm mx-auto">
                      <div className="w-12 h-12 rounded-full bg-[#00B47A]/10 flex items-center justify-center mb-3 border border-[#00B47A]/15 text-[#00B47A]">
                        <AlertCircle size={22} />
                      </div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">Ledger Empty</h3>
                      <p className="text-[var(--color-text-secondary)] text-xs mt-1 leading-relaxed">
                        No offsets have been processed. Approve activities to generate verified ledger logs.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                ledger.map((row) => (
                  <tr key={row.id} className="hover:bg-[var(--color-background)]/20 transition-colors group">
                    
                    {/* ID */}
                    <td className="p-4">
                      <span className="text-xs font-mono font-bold text-[var(--color-text-secondary)] bg-[var(--color-background)] border border-[var(--color-border)] px-2 py-0.5 rounded">
                        {row.id.substring(0, 12)}...
                      </span>
                    </td>

                    {/* Methodology */}
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <BookOpen size={13} className="text-[#00B47A]" />
                        <span className="text-xs font-bold text-[var(--color-text-primary)]">
                          {row.methodology}
                        </span>
                      </div>
                    </td>

                    {/* Volume */}
                    <td className="p-4 text-right">
                      <span className="text-xs font-black text-[#00B47A] tracking-tight">
                        +{row.tco2e || row.tco2e_generated} t
                      </span>
                    </td>

                    {/* Value */}
                    <td className="p-4 text-right">
                      <div className="text-xs font-bold text-blue-400">
                        ${((row.tco2e || row.tco2e_generated) * getPrice(row.methodology)).toFixed(2)}
                      </div>
                      <div className="text-[9px] text-[var(--color-text-muted)] mt-0.5 font-mono">
                        @ ${getPrice(row.methodology)}/t
                      </div>
                    </td>

                    {/* Status */}
                    <td className="p-4 text-center">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[8px] font-extrabold uppercase border tracking-wider ${
                        row.status === "calculated" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                        row.status === "pending_issuance" ? "bg-blue-500/10 text-blue-400 border-blue-500/20" :
                        "bg-[#00B47A]/10 text-[#00B47A] border-[#00B47A]/20"
                      }`}>
                        {row.status === "calculated" ? "Pending Registry" : 
                         row.status === "pending_issuance" ? "Awaiting Issuance" : "Issued"}
                      </span>
                    </td>

                    {/* Action */}
                    <td className="p-4 text-right">
                      <button 
                        onClick={() => setSelectedLog(row)}
                        className="text-xs font-extrabold text-[#00B47A] hover:text-[#00B47A]/80 uppercase tracking-wider transition-colors active:scale-95"
                      >
                        Inspect Formula
                      </button>
                    </td>

                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    {/* 🧭 AUDIT LOG MODAL */}
      {selectedLog && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
          onClick={() => setSelectedLog(null)}
        >
          <div 
            className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            
            {/* Modal Header */}
            <div className="p-4.5 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-background)]/50">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider">Calculation Audit Trail</h3>
                <p className="text-[10px] text-[var(--color-text-secondary)] mt-0.5">SPEC SPECIFICATION: <span className="font-mono text-[#00B47A] font-bold">{selectedLog.id}</span></p>
              </div>
              
              <button 
                onClick={() => setSelectedLog(null)}
                className="p-1.5 rounded-lg hover:bg-[var(--color-surface)] border border-transparent hover:border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-red-500 transition-all"
              >
                <X size={18} />
              </button>
            </div>
            
            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-5 flex-1 custom-scrollbar text-xs">
              
              {/* Methodology / Volume */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-[var(--color-background)] p-4 rounded-xl border border-[var(--color-border)]">
                  <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider mb-1">Standard Protocol</p>
                  <p className="font-bold text-[var(--color-text-primary)]">{selectedLog.methodology}</p>
                </div>
                
                <div className="bg-[var(--color-background)] p-4 rounded-xl border border-[var(--color-border)]">
                  <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider mb-1">Attested Offset</p>
                  <p className="font-black text-[#00B47A]">+{selectedLog.tco2e || selectedLog.tco2e_generated} tCO2e</p>
                </div>
              </div>

              {/* Traceable Formula */}
              <div>
                <h4 className="text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                  <Cpu size={14} className="text-[#00B47A]" /> Traceable Formula
                </h4>
                
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 font-mono text-xs text-[#00B47A] overflow-x-auto shadow-inner leading-relaxed select-all">
                  {selectedLog.calculation_log?.formula_trace || "Formula trace unavailable."}
                </div>
              </div>

              {/* Deterministic Inputs */}
              <div>
                <h4 className="text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider mb-2.5">Deterministic Variables</h4>
                
                <div className="bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl overflow-hidden shadow-sm">
                  <table className="w-full text-left text-xs border-collapse">
                    <tbody className="divide-y divide-[var(--color-border)]">
                      {Object.entries(selectedLog.calculation_log?.inputs || {}).map(([key, value]) => (
                        <tr key={key} className="hover:bg-[var(--color-surface)]/20 transition-colors">
                          <td className="p-3 font-semibold text-[var(--color-text-secondary)]">{key}</td>
                          <td className="p-3 font-mono font-bold text-[var(--color-text-primary)] text-right">{String(value)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Complete JSON Payload */}
              <div>
                <h4 className="text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider mb-2.5">Raw Encrypted Metadata Packet</h4>
                <pre className="bg-slate-950 border border-slate-800 rounded-xl p-4 overflow-x-auto text-[10px] text-slate-400 font-mono shadow-inner leading-relaxed max-h-48 overflow-y-auto select-all">
                  {JSON.stringify(selectedLog.calculation_log, null, 2)}
                </pre>
              </div>

            </div>
            
            {/* Modal Footer */}
            <div className="p-4 border-t border-[var(--color-border)] bg-[var(--color-background)]/50 flex justify-end">
              <button 
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs font-bold hover:bg-[var(--color-background)] transition-all uppercase tracking-wider"
              >
                Close Audit Trail
              </button>
            </div>

          </div>
        </div>
      )}
    </>
  );
}
