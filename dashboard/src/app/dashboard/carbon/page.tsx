"use client";



import { useEffect, useState } from "react";

import { Leaf, RefreshCw, Send, Layers } from "lucide-react";

import { fetchCarbonLedger } from "@/lib/api";

import { useToast } from "@/components/Toast";

import { useWorkspace } from "@/context/WorkspaceContext";



export default function CarbonLedgerPage() {

  const { activeSector, activeMethodology, activeProject, filterCarbonLedger } = useWorkspace();

  const toast = useToast();



  const [ledger, setLedger] = useState<any[]>([]);

  const [isLoading, setIsLoading] = useState(true);



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

            onClick={loadData}

            className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[#00B47A] hover:border-[#00B47A]/30 transition-all shadow-sm active:scale-95"

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

    </div>

  );

}
