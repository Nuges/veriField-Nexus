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
  Cpu,
  Database,
  Sliders,
  Settings,
  Plus
} from "lucide-react";
import { 
  fetchCarbonLedger, 
  issueVerraCredits, 
  issueGoldStandardCredits,
  fetchCsiLedger,
  fetchCsiParameters,
  updateCsiParameter,
  createCsiBundle,
  syncBundleToRegistry,
  fetchActivities,
  fetchProjects
} from "@/lib/api";
import { useToast } from "@/components/Toast";

import { useWorkspace } from "@/context/WorkspaceContext";

export default function CarbonLedgerPage() {
  const { filterCarbonLedger } = useWorkspace();
  const toast = useToast();
  
  // Standard view states
  const [ledger, setLedger] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isIssuing, setIsIssuing] = useState(false);
  const [issuanceResult, setIssuanceResult] = useState<any>(null);
  const [selectedLog, setSelectedLog] = useState<any>(null);

  // CSI module states
  const [activeSubTab, setActiveSubTab] = useState<"registries" | "csi_sinks" | "csi_parameters">("registries");
  const [csiLedger, setCsiLedger] = useState<any[]>([]);
  const [csiParameters, setCsiParameters] = useState<any[]>([]);
  const [csiActivities, setCsiActivities] = useState<any[]>([]);
  const [selectedCsiActivities, setSelectedCsiActivities] = useState<string[]>([]);
  const [csiBundleName, setCsiBundleName] = useState("");
  const [isBundling, setIsBundling] = useState(false);
  const [syncingBundles, setSyncingBundles] = useState<Record<string, boolean>>({});

  // Carbon projects for bundling
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");

  // Parameter editing states
  const [editingParam, setEditingParam] = useState<any | null>(null);
  const [newParamVal, setNewParamVal] = useState<number>(0);
  const [isSavingParam, setIsSavingParam] = useState(false);

  const loadCsiData = async () => {
    try {
      const ledgerRes = await fetchCsiLedger();
      setCsiLedger(ledgerRes.data || []);
      
      const paramsRes = await fetchCsiParameters();
      setCsiParameters(paramsRes || []);
      
      const actRes = await fetchActivities();
      const biocharActs = (actRes.activities || []).filter(
        (a: any) => a.activity_type === "BIOCHAR_C_SINK" && a.status === "verified" && !a.c_sink_unit_id
      );
      setCsiActivities(biocharActs);

      const projRes = await fetchProjects();
      const items = projRes.items || [];
      setProjects(items);
      if (items.length > 0) {
        setSelectedProjectId(items[0].id);
      }
    } catch (err) {
      console.error("CSI loading error:", err);
    }
  };

  const handleSelectCsiActivity = (id: string) => {
    if (selectedCsiActivities.includes(id)) {
      setSelectedCsiActivities(selectedCsiActivities.filter(aId => aId !== id));
    } else {
      setSelectedCsiActivities([...selectedCsiActivities, id]);
    }
  };

  const handleSelectAllCsiActivities = () => {
    if (selectedCsiActivities.length === csiActivities.length) {
      setSelectedCsiActivities([]);
    } else {
      setSelectedCsiActivities(csiActivities.map(a => a.id));
    }
  };

  const handleCreateBundle = async () => {
    if (!csiBundleName.trim()) {
      toast.error("Validation Error", "Please provide a name for the C-Sink Bundle.");
      return;
    }
    if (!selectedProjectId) {
      toast.error("Validation Error", "Please select a target Carbon Project.");
      return;
    }
    if (selectedCsiActivities.length === 0) {
      toast.error("Validation Error", "Please select at least one activity to bundle.");
      return;
    }

    setIsBundling(true);
    try {
      const res = await createCsiBundle({
        name: csiBundleName,
        project_id: selectedProjectId,
        activity_ids: selectedCsiActivities
      });
      toast.success("Bundle Created", `Successfully compiled C-Sink Unit Bundle: ${res.name || csiBundleName}`);
      setSelectedCsiActivities([]);
      setCsiBundleName("");
      await loadCsiData();
    } catch (err: any) {
      console.error(err);
      toast.error("Bundling Failed", err.message || "Failed to create C-Sink Unit Bundle.");
    } finally {
      setIsBundling(false);
    }
  };

  const handleSyncBundle = async (bundleId: string) => {
    setSyncingBundles(prev => ({ ...prev, [bundleId]: true }));
    try {
      const res = await syncBundleToRegistry(bundleId);
      if (res.status === "success" || res.status === "already_synced") {
        toast.success("Registry Synced", res.message || "Successfully synchronized with CSI Registry.");
      } else {
        toast.error("Sync Failed", res.errors?.join(", ") || "Failed to synchronize with CSI Registry.");
      }
      await loadCsiData();
    } catch (err: any) {
      console.error(err);
      toast.error("Sync Failed", err.message || "Error communicating with CSI Registry API.");
    } finally {
      setSyncingBundles(prev => ({ ...prev, [bundleId]: false }));
    }
  };

  const handleEditParamClick = (param: any) => {
    setEditingParam(param);
    setNewParamVal(param.value);
  };

  const handleSaveParam = async () => {
    if (!editingParam) return;
    setIsSavingParam(true);
    try {
      await updateCsiParameter(editingParam.id, newParamVal);
      toast.success("Parameter Updated", `Successfully updated parameter: ${editingParam.id}`);
      setEditingParam(null);
      await loadCsiData();
    } catch (err: any) {
      console.error(err);
      toast.error("Update Failed", err.message || "Failed to update parameter.");
    } finally {
      setIsSavingParam(false);
    }
  };

  const loadData = async () => {
    setIsLoading(true);
    try {
      const res = await fetchCarbonLedger(true);
      setLedger(res.data);
      await loadCsiData();
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

  
  // Filter ledger calculations based on active sector context
  const isolatedLedger = filterCarbonLedger(ledger);

  // Aggregate Metrics
  const totalTco2e = isolatedLedger.reduce((acc, c) => acc + (c.tco2e || c.tco2 || c.tco2e_generated || 0), 0);
  
  const estimatedRevenue = isolatedLedger.reduce((acc, c) => acc + (c.estimated_value || 0), 0);

  const pendingCount = isolatedLedger.filter(l => l.status === "calculated").length;

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
            <Leaf className="text-[#00B47A]" size={20} />{' '}
            {activeSubTab === "registries" && "Deterministic Issuance Ledger"}
            {activeSubTab === "csi_sinks" && "CSI C-Sink Bundling Hub"}
            {activeSubTab === "csi_parameters" && "CSI Parameters Ledger"}
          </h1>
          <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">
            {activeSubTab === "registries" && "Audit immutable carbon credit quantifications calculated under Verra and Gold Standard methodologies."}
            {activeSubTab === "csi_sinks" && "Aggregate verified biochar C-sink applications into audit-grade carbon units for Carbon Standards International (CSI)."}
            {activeSubTab === "csi_parameters" && "Configure and inspect version-controlled emission factors, security margins, and methane avoidance parameters."}
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
          
          {activeSubTab === "registries" && (
            <>
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
            </>
          )}
        </div>
      </div>

      {/* 🧭 SUB-TAB NAVIGATION */}
      <div className="flex border-b border-[var(--color-border)] gap-2">
        <button
          onClick={() => setActiveSubTab("registries")}
          className={`px-4 py-2.5 text-xs font-bold uppercase tracking-wider border-b-2 transition-all flex items-center gap-1.5 ${
            activeSubTab === "registries"
              ? "border-[#00B47A] text-[#00B47A]"
              : "border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
          }`}
        >
          <Layers size={14} /> Verra & Gold Standard (Energy)
        </button>
        <button
          onClick={() => setActiveSubTab("csi_sinks")}
          className={`px-4 py-2.5 text-xs font-bold uppercase tracking-wider border-b-2 transition-all flex items-center gap-1.5 ${
            activeSubTab === "csi_sinks"
              ? "border-[#00B47A] text-[#00B47A]"
              : "border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
          }`}
        >
          <Cpu size={14} /> CSI C-Sink Bundling Hub
        </button>
        <button
          onClick={() => setActiveSubTab("csi_parameters")}
          className={`px-4 py-2.5 text-xs font-bold uppercase tracking-wider border-b-2 transition-all flex items-center gap-1.5 ${
            activeSubTab === "csi_parameters"
              ? "border-[#00B47A] text-[#00B47A]"
              : "border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
          }`}
        >
          <Sliders size={14} /> CSI Parameters Ledger
        </button>
      </div>

      {/* ========================================================================= */}
      {/* 📊 TAB 1: REGISTRIES (VERRA & GOLD STANDARD) */}
      {/* ========================================================================= */}
      {activeSubTab === "registries" && (
        <>
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
                  ) : isolatedLedger.length === 0 ? (
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
                    isolatedLedger.map((row) => (
                      <tr key={row.id} className="hover:bg-[var(--color-background)]/20 transition-colors group">
                        <td className="p-4">
                          <span className="text-xs font-mono font-bold text-[var(--color-text-secondary)] bg-[var(--color-background)] border border-[var(--color-border)] px-2 py-0.5 rounded">
                            {row.id.substring(0, 12)}...
                          </span>
                        </td>
                        <td className="p-4">
                          <div className="flex items-center gap-2">
                            <BookOpen size={13} className="text-[#00B47A]" />
                            <span className="text-xs font-bold text-[var(--color-text-primary)]">
                              {row.methodology}
                            </span>
                          </div>
                        </td>
                        <td className="p-4 text-right">
                          <span className="text-xs font-black text-[#00B47A] tracking-tight">
                            +{row.tco2e || row.tco2e_generated} t
                          </span>
                        </td>
                        <td className="p-4 text-right">
                          <div className="text-xs font-bold text-blue-400">
                            ${(row.estimated_value || 0).toFixed(2)}
                          </div>
                          <div className="text-[9px] text-[var(--color-text-muted)] mt-0.5 font-mono">
                            @ ${row.unit_price || 0}/t
                          </div>
                        </td>
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
        </>
      )}

      {/* ========================================================================= */}
      {/* 📊 TAB 2: CSI C-SINK BUNDLING HUB */}
      {/* ========================================================================= */}
      {activeSubTab === "csi_sinks" && (() => {
        // Compute bundling parameters preview
        const securityMargin = csiParameters.find(p => p.id === "margin_of_security")?.value ?? 0.90;
        const selectedActivitiesData = csiActivities.filter(a => selectedCsiActivities.includes(a.id));
        const totalSelectedWeightKg = selectedActivitiesData.reduce((acc, a) => acc + parseFloat(a.activity_data?.batch_weight_kg || 0), 0);
        
        const estimatedCsiCo2e = selectedActivitiesData.reduce((acc, a) => {
          const weight = parseFloat(a.activity_data?.batch_weight_kg || 0);
          const moisture = parseFloat(a.activity_data?.moisture_content_pct || 0) / 100;
          const carbon = parseFloat(a.activity_data?.lab_carbon_content_pct || 0) / 100;
          return acc + (weight * carbon * 3.67 * (1 - moisture) * securityMargin / 1000.0);
        }, 0);

        const isBelowCsiThreshold = selectedCsiActivities.length > 0 && estimatedCsiCo2e < 1.0;

        // Group activities in csiLedger by bundle_id
        const csiBundlesMap: Record<string, {
          bundleId: string;
          name: string;
          activities: any[];
          totalCo2e: number;
          syncStatus: string;
          registryTxId?: string;
          matrix: string;
          qrIds: string[];
        }> = {};
        
        csiLedger.forEach(item => {
          if (item.bundle_id) {
            if (!csiBundlesMap[item.bundle_id]) {
              csiBundlesMap[item.bundle_id] = {
                bundleId: item.bundle_id,
                name: item.bundle_name || `Bundle-${item.bundle_id.substring(0, 8).toUpperCase()}`,
                activities: [],
                totalCo2e: 0,
                syncStatus: item.sync_status || "bundled",
                registryTxId: item.registry_tx_id,
                matrix: item.application_matrix || "Unknown",
                qrIds: []
              };
            }
            csiBundlesMap[item.bundle_id].activities.push(item);
            csiBundlesMap[item.bundle_id].totalCo2e += item.tco2e_generated;
            if (item.qr_id && !csiBundlesMap[item.bundle_id].qrIds.includes(item.qr_id)) {
              csiBundlesMap[item.bundle_id].qrIds.push(item.qr_id);
            }
          }
        });
        const csiBundlesList = Object.values(csiBundlesMap);

        return (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Left Column: Unbundled logs */}
              <div className="lg:col-span-2 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-sm overflow-hidden flex flex-col">
                <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-background)]/50">
                  <h2 className="text-xs font-bold uppercase tracking-wider">Unbundled verified C-Sinks</h2>
                  <div className="text-[9px] font-extrabold text-[#00B47A] bg-[#00B47A]/5 border border-[#00B47A]/15 px-2 py-0.5 rounded uppercase">
                    {csiActivities.length} available logs
                  </div>
                </div>
                
                <div className="overflow-x-auto flex-1">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-[var(--color-background)]/40 border-b border-[var(--color-border)]">
                        <th className="p-3 text-center w-10">
                          <input
                            type="checkbox"
                            checked={csiActivities.length > 0 && selectedCsiActivities.length === csiActivities.length}
                            onChange={handleSelectAllCsiActivities}
                            className="rounded border-[var(--color-border)] text-[#00B47A] focus:ring-[#00B47A]"
                          />
                        </th>
                        <th className="p-3 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Tracking ID / QR</th>
                        <th className="p-3 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Production Date</th>
                        <th className="p-3 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-right">Net Yield (kg)</th>
                        <th className="p-3 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-right">Carbon (%)</th>
                        <th className="p-3 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-right">Moisture (%)</th>
                        <th className="p-3 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Application Matrix</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--color-border)]/70">
                      {csiActivities.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="p-16 text-center text-xs text-[var(--color-text-secondary)]">
                            No unbundled verified biochar C-sink logs available. Submit verification entries from the field app.
                          </td>
                        </tr>
                      ) : (
                        csiActivities.map(act => {
                          const actData = act.activity_data || {};
                          return (
                            <tr key={act.id} className="hover:bg-[var(--color-background)]/20 transition-colors">
                              <td className="p-3 text-center">
                                <input
                                  type="checkbox"
                                  checked={selectedCsiActivities.includes(act.id)}
                                  onChange={() => handleSelectCsiActivity(act.id)}
                                  className="rounded border-[var(--color-border)] text-[#00B47A] focus:ring-[#00B47A]"
                                />
                              </td>
                              <td className="p-3 font-mono text-xs text-[var(--color-text-primary)]">
                                <div className="font-bold flex items-center gap-1">
                                  <span className="text-[#00B47A]">●</span> {actData.qr_id || "N/A"}
                                </div>
                                <div className="text-[10px] text-[var(--color-text-secondary)]">{act.id.substring(0, 8)}...</div>
                              </td>
                              <td className="p-3 text-xs text-[var(--color-text-secondary)]">
                                {act.captured_at ? new Date(act.captured_at).toLocaleDateString() : "N/A"}
                              </td>
                              <td className="p-3 text-xs font-bold text-right text-[var(--color-text-primary)]">
                                {parseFloat(actData.batch_weight_kg || 0).toFixed(1)}
                              </td>
                              <td className="p-3 text-xs text-right text-[var(--color-text-primary)] font-mono">
                                {parseFloat(actData.lab_carbon_content_pct || 0).toFixed(2)}%
                              </td>
                              <td className="p-3 text-xs text-right text-[var(--color-text-primary)] font-mono">
                                {parseFloat(actData.moisture_content_pct || 0).toFixed(2)}%
                              </td>
                              <td className="p-3 text-xs text-[var(--color-text-secondary)] font-medium capitalize">
                                {(actData.application_matrix || "").replace("_", " ")}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Right Column: Bundling Panel */}
              <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm space-y-6 self-start">
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">Unit Compiler</h3>
                  <p className="text-[10px] text-[var(--color-text-secondary)] mt-0.5">Combine identical carbon logs to create tradable units.</p>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-[10px] font-extrabold text-[var(--color-text-secondary)] uppercase mb-1.5">Bundle Name</label>
                    <input
                      type="text"
                      value={csiBundleName}
                      onChange={(e) => setCsiBundleName(e.target.value)}
                      placeholder="e.g. Rice Husk Biochar Q2 2026"
                      className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl p-3 text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]/50 transition-colors"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] font-extrabold text-[var(--color-text-secondary)] uppercase mb-1.5">Carbon Project Context</label>
                    {projects.length === 0 ? (
                      <div className="text-xs text-red-400 p-2 bg-red-950/20 border border-red-900/30 rounded-xl">
                        No Projects configured. Seed database or call API.
                      </div>
                    ) : (
                      <select
                        value={selectedProjectId}
                        onChange={(e) => setSelectedProjectId(e.target.value)}
                        className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl p-3 text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]/50 transition-colors"
                      >
                        {projects.map(p => (
                          <option key={p.id} value={p.id}>{p.project_code} — {p.name}</option>
                        ))}
                      </select>
                    )}
                  </div>
                </div>

                {/* Bundle Summary */}
                <div className="bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl p-4.5 space-y-3.5">
                  <h4 className="text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Aggregation Summary</h4>
                  <div className="grid grid-cols-2 gap-3.5">
                    <div>
                      <div className="text-[9px] text-[var(--color-text-muted)] uppercase font-semibold">Selected Logs</div>
                      <div className="text-sm font-black mt-0.5">{selectedCsiActivities.length}</div>
                    </div>
                    <div>
                      <div className="text-[9px] text-[var(--color-text-muted)] uppercase font-semibold">Dry Weight</div>
                      <div className="text-sm font-black mt-0.5">{(totalSelectedWeightKg).toFixed(1)} kg</div>
                    </div>
                    <div className="col-span-2 border-t border-[var(--color-border)]/50 pt-2.5">
                      <div className="text-[9px] text-[var(--color-text-muted)] uppercase font-semibold">Total C-Sink Offset</div>
                      <div className="text-2xl font-black text-[#00B47A] flex items-baseline gap-1 mt-1.5 tracking-tight">
                        {selectedCsiActivities.length === 0 ? "0.0000" : estimatedCsiCo2e.toFixed(4)}
                        <span className="text-xs font-bold text-[var(--color-text-muted)] font-mono">tCO2e</span>
                      </div>
                    </div>
                  </div>

                  {isBelowCsiThreshold && (
                    <div className="p-2.5 bg-amber-500/10 border border-amber-500/20 text-[10px] text-amber-400 rounded-lg font-medium leading-normal flex items-start gap-2 animate-pulse">
                      <AlertCircle size={14} className="shrink-0 mt-0.5" />
                      <span>
                        CSI requires C-sink units to represent at least 1.0 tCO2e offset volume. Select additional logs.
                      </span>
                    </div>
                  )}
                </div>

                {/* Bundling Action Button */}
                <button
                  onClick={handleCreateBundle}
                  disabled={isBundling || selectedCsiActivities.length === 0 || isBelowCsiThreshold}
                  className="w-full flex items-center justify-center gap-2 px-3.5 py-3 rounded-xl bg-[#00B47A] text-white text-xs font-bold hover:bg-[#00B47A]/95 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-[#00B47A]/25 active:scale-95 uppercase tracking-wider"
                >
                  {isBundling ? <RefreshCw size={14} className="animate-spin" /> : <Plus size={14} />}
                  Compile C-Sink Unit
                </button>
              </div>
            </div>

            {/* Bundled C-Sink Units list */}
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-sm overflow-hidden">
              <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-background)]/50">
                <h2 className="text-xs font-bold uppercase tracking-wider">CSI Bundled Carbon Units</h2>
                <div className="text-[9px] font-extrabold text-[#00B47A] bg-[#00B47A]/5 border border-[#00B47A]/15 px-2 py-0.5 rounded uppercase">
                  {csiBundlesList.length} Units Compiled
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-[var(--color-background)]/40 border-b border-[var(--color-border)]">
                      <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Bundle Unit Description</th>
                      <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-center">Logs Bundled</th>
                      <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Application Matrix</th>
                      <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-right">Total volume (tCO2e)</th>
                      <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-center">CSI Registry Status</th>
                      <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-right">Synchronization Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--color-border)]/70">
                    {csiBundlesList.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="p-16 text-center text-xs text-[var(--color-text-secondary)]">
                          No compiled units found. Complete log aggregation above.
                        </td>
                      </tr>
                    ) : (
                      csiBundlesList.map(bundle => (
                        <tr key={bundle.bundleId} className="hover:bg-[var(--color-background)]/20 transition-colors">
                          <td className="p-4">
                            <div className="font-bold text-xs text-[var(--color-text-primary)]">{bundle.name}</div>
                            <div className="text-[10px] font-mono text-[var(--color-text-secondary)] mt-0.5">UUID: {bundle.bundleId}</div>
                          </td>
                          <td className="p-4 text-center text-xs font-semibold text-[var(--color-text-secondary)]">
                            {bundle.activities.length} records
                          </td>
                          <td className="p-4 text-xs font-semibold text-[var(--color-text-secondary)] capitalize">
                            {bundle.matrix.replace("_", " ")}
                          </td>
                          <td className="p-4 text-right">
                            <span className="text-xs font-black text-[#00B47A] tracking-tight">
                              +{bundle.totalCo2e.toFixed(4)} tCO2e
                            </span>
                          </td>
                          <td className="p-4 text-center">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-[8px] font-extrabold uppercase border tracking-wider ${
                              bundle.syncStatus === "SUCCESS" ? "bg-[#00B47A]/10 text-[#00B47A] border-[#00B47A]/20" :
                              bundle.syncStatus === "FAILED" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                              "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            }`}>
                              {bundle.syncStatus === "SUCCESS" ? "Registry Synced" :
                               bundle.syncStatus === "FAILED" ? "Sync Failed" : "Awaiting Sync"}
                            </span>
                            {bundle.registryTxId && (
                              <div className="text-[8px] font-mono text-[var(--color-text-muted)] mt-1.5 break-all select-all max-w-[120px] mx-auto">
                                Tx: {bundle.registryTxId}
                              </div>
                            )}
                          </td>
                          <td className="p-4 text-right">
                            <button
                              onClick={() => handleSyncBundle(bundle.bundleId)}
                              disabled={syncingBundles[bundle.bundleId]}
                              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-[10px] font-bold uppercase transition-all shadow-sm active:scale-95 ml-auto ${
                                bundle.syncStatus === "SUCCESS"
                                  ? "bg-emerald-950/20 border border-emerald-900/30 text-emerald-400 hover:bg-emerald-950/30"
                                  : "bg-[#00B47A] border border-[#00B47A] text-white hover:bg-[#00B47A]/95"
                              }`}
                            >
                              {syncingBundles[bundle.bundleId] ? (
                                <RefreshCw size={11} className="animate-spin" />
                              ) : (
                                <Send size={11} />
                              )}
                              {bundle.syncStatus === "SUCCESS" ? "Re-sync Registry" : "Sync CSI Registry"}
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
        );
      })()}

      {/* ========================================================================= */}
      {/* 📊 TAB 3: CSI PARAMETERS LEDGER */}
      {/* ========================================================================= */}
      {activeSubTab === "csi_parameters" && (
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-sm overflow-hidden">
          <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-background)]/50">
            <h2 className="text-xs font-bold uppercase tracking-wider">CSI Environmental Parameters</h2>
            <div className="text-[9px] font-extrabold text-[#00B47A] bg-[#00B47A]/5 border border-[#00B47A]/15 px-2 py-0.5 rounded uppercase">
              {csiParameters.length} active factors
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[var(--color-background)]/40 border-b border-[var(--color-border)]">
                  <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Parameter ID / Key</th>
                  <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-right">value</th>
                  <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Description</th>
                  <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Methodology Reference</th>
                  <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Last Modified</th>
                  <th className="p-4 text-[10px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)]/70">
                {csiParameters.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-16 text-center text-xs text-[var(--color-text-secondary)]">
                      No parameters returned from database. Reloading...
                    </td>
                  </tr>
                ) : (
                  csiParameters.map(param => (
                    <tr key={param.id} className="hover:bg-[var(--color-background)]/20 transition-colors">
                      <td className="p-4 font-mono font-bold text-xs text-[var(--color-text-primary)]">
                        {param.id}
                      </td>
                      <td className="p-4 text-xs font-black text-right text-[#00B47A] font-mono">
                        {Number(param.value || 0).toFixed(4)}
                      </td>
                      <td className="p-4 text-xs text-[var(--color-text-secondary)] max-w-sm whitespace-normal leading-relaxed">
                        {param.description}
                      </td>
                      <td className="p-4 text-xs text-[var(--color-text-muted)]">
                        {param.source_reference || "System Default"}
                      </td>
                      <td className="p-4 text-[10px] text-[var(--color-text-muted)]">
                        {param.updated_at ? new Date(param.updated_at).toLocaleString() : "System Initial"}
                      </td>
                      <td className="p-4 text-right">
                        <button
                          onClick={() => handleEditParamClick(param)}
                          className="text-xs font-extrabold text-[#00B47A] hover:text-[#00B47A]/80 uppercase tracking-wider transition-colors active:scale-95"
                        >
                          Modify
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      </div>

      {/* ========================================================================= */}
      {/* 🧭 PARAMETER EDITING MODAL */}
      {/* ========================================================================= */}
      {editingParam && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
          onClick={() => setEditingParam(null)}
        >
          <div 
            className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl w-full max-w-md flex flex-col overflow-hidden shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4.5 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-background)]/50">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider">Modify Parameter Value</h3>
                <p className="text-[10px] text-[var(--color-text-secondary)] mt-0.5">RULE: <span className="font-mono text-[#00B47A] font-bold">{editingParam.id}</span></p>
              </div>
              
              <button 
                onClick={() => setEditingParam(null)}
                className="p-1.5 rounded-lg hover:bg-[var(--color-surface)] border border-transparent hover:border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-red-500 transition-all"
              >
                <X size={18} />
              </button>
            </div>
            
            <div className="p-6 space-y-4 text-xs">
              <div className="bg-[var(--color-background)] p-3.5 rounded-xl border border-[var(--color-border)] text-[var(--color-text-secondary)] leading-relaxed">
                {editingParam.description}
              </div>

              <div>
                <label className="block text-[10px] font-extrabold text-[var(--color-text-secondary)] uppercase mb-1.5">New Value</label>
                <input
                  type="number"
                  step="any"
                  value={newParamVal}
                  onChange={(e) => setNewParamVal(parseFloat(e.target.value) || 0)}
                  className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl p-3 text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]/50 transition-colors font-mono font-bold"
                />
              </div>
            </div>
            
            <div className="p-4 border-t border-[var(--color-border)] bg-[var(--color-background)]/50 flex justify-end gap-2.5">
              <button 
                onClick={() => setEditingParam(null)}
                className="px-4 py-2 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs font-bold hover:bg-[var(--color-background)] transition-all uppercase tracking-wider"
              >
                Cancel
              </button>
              <button 
                onClick={handleSaveParam}
                disabled={isSavingParam}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#00B47A] text-white text-xs font-bold hover:bg-[#00B47A]/95 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-[#00B47A]/25 active:scale-95 uppercase tracking-wider"
              >
                {isSavingParam ? <RefreshCw size={12} className="animate-spin" /> : null}
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

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
