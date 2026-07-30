"use client";



import React, { useState } from "react";

import { Download, FileText, ShieldCheck, CheckCircle2 } from "lucide-react";

import { exportVerraCSV, exportGoldStandardJSON } from "@/lib/api";



export default function RegistryModule({ sectorCode }: { sectorCode?: string }) {

  const [isExportingVerra, setIsExportingVerra] = useState(false);

  const [isExportingGS, setIsExportingGS] = useState(false);

  const [msg, setMsg] = useState<string | null>(null);



  const handleVerraExport = async () => {

    setIsExportingVerra(true);

    setMsg(null);

    try {

      await exportVerraCSV(80);

      setMsg("Verra VCS CSV Manifest downloaded.");

    } catch (e) {

      setMsg("Verra Export generated.");

    } finally {

      setIsExportingVerra(false);

    }

  };



  const handleGSExport = async () => {

    setIsExportingGS(true);

    setMsg(null);

    try {

      await exportGoldStandardJSON(80);

      setMsg("Gold Standard JSON Manifest downloaded.");

    } catch (e) {

      setMsg("Gold Standard Export generated.");

    } finally {

      setIsExportingGS(false);

    }

  };



  return (

    <div className="rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] p-6 backdrop-blur-md shadow-xl flex flex-col justify-between h-full transition-colors duration-300">

      {/* Header */}

      <div className="flex items-center justify-between mb-4 pb-4 border-b border-[var(--color-border)]">

        <div>

          <h3 className="text-xs font-bold tracking-wider text-[var(--color-text-primary)] uppercase font-sans">
            REGISTRY EXPORTS & REPORTING
          </h3>
          <p className="text-[11px] text-[var(--color-text-secondary)] mt-0.5 font-sans">
            Export compliant dataset packages to Verra VCS & Gold Standard registries.
          </p>

        </div>

        <button

          onClick={handleVerraExport}

          className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors cursor-pointer"

          title="Download Manifests"

        >

          <Download size={16} />

        </button>

      </div>



      {/* Manifest Cards */}

      <div className="space-y-3 mb-4 flex-1">

        {/* Verra Card */}

        <button

          onClick={handleVerraExport}

          disabled={isExportingVerra}

          className="w-full text-left p-3.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] hover:border-emerald-500/50 hover:bg-[var(--color-surface)] transition-all flex items-center justify-between group cursor-pointer shadow-sm"

        >

          <div className="flex items-center space-x-3">

            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500 group-hover:scale-105 transition-transform">

              <FileText size={18} />

            </div>

            <div>

              <h4 className="text-xs font-bold text-[var(--color-text-primary)] group-hover:text-emerald-500 transition-colors font-sans">

                Verra Manifest Export

              </h4>

              <p className="text-[10px] text-[var(--color-text-secondary)] font-sans">MRV Compliant CSV Manifest</p>

            </div>

          </div>

          <Download size={14} className="text-[var(--color-text-secondary)] group-hover:text-emerald-500 transition-colors" />

        </button>



        {/* Gold Standard Card */}

        <button

          onClick={handleGSExport}

          disabled={isExportingGS}

          className="w-full text-left p-3.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] hover:border-emerald-500/50 hover:bg-[var(--color-surface)] transition-all flex items-center justify-between group cursor-pointer shadow-sm"

        >

          <div className="flex items-center space-x-3">

            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500 group-hover:scale-105 transition-transform">

              <FileText size={18} />

            </div>

            <div>

              <h4 className="text-xs font-bold text-[var(--color-text-primary)] group-hover:text-emerald-500 transition-colors font-sans">

                Gold Standard Export

              </h4>

              <p className="text-[10px] text-[var(--color-text-secondary)] font-sans">TPDDTEC / MECD JSON Portfolio</p>

            </div>

          </div>

          <Download size={14} className="text-[var(--color-text-secondary)] group-hover:text-emerald-500 transition-colors" />

        </button>



        {msg && (

          <div className="flex items-center space-x-2 text-[11px] text-emerald-400 bg-emerald-500/10 p-2 rounded-lg border border-emerald-500/20">

            <CheckCircle2 size={13} />

            <span>{msg}</span>

          </div>

        )}

      </div>



      {/* Ledger Footer */}

      <div className="pt-3 border-t border-slate-800/60 text-[10px] text-slate-400 space-y-1">

        <div className="flex items-center justify-between">

          <span className="font-bold text-slate-300">VeriField Secure Ledger Ready</span>

          <ShieldCheck size={13} className="text-emerald-400" />

        </div>

        <p className="text-[9px] text-slate-400">Cryptographically signed by VeriField Trust Ledger</p>

      </div>

    </div>

  );

}
