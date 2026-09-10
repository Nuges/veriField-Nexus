// =============================================================================

// VeriField Nexus — Universal AI Assistant & Guidance Surface (CIOS Level 5)

// =============================================================================

// Embedded contextual AI assistant present across every page and sector,

// providing explainable recommendations, role guidance, and instant action buttons.

// Connected to the backend AI orchestrator via /api/v1/ai/chat.

// =============================================================================



"use client";



import React, { useState } from "react";
import { usePathname } from "next/navigation";
import { useWorkspace } from "@/context/WorkspaceContext";
import { getContextualInsight } from "@/lib/aiOrchestrator";
import { chatWithAI, AIChatResponse, fetchProjects, submitITMOAuthorization, downloadArticle6PackageZip, executeCarbonMinting, generateAndDownloadReport } from "@/lib/api";
import {
  Bot,
  Sparkles,
  ArrowRight,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Send,
  AlertTriangle,
  CheckCircle2,
  Shield,
  X,
  Check,
  Download,
  Loader2,
  FileText,
  Globe,
  Copy,
  Coins,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";

interface ChatMessage {
  role: "user" | "ai";
  text: string;
  confidence?: number;
  sourceModule?: string;
  recommendations?: Array<{ type: string; action: string; priority: string }>;
}

export default function UniversalAIAssistant() {
  const pathname = usePathname();
  const { activeSector, user } = useWorkspace();
  const [isExpanded, setIsExpanded] = useState(true);
  const [isDismissed, setIsDismissed] = useState(true);
  const [query, setQuery] = useState("");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ITMO Authorization Modal State
  const [isITMOModalOpen, setIsITMOModalOpen] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [acquiringParty, setAcquiringParty] = useState("Swiss Federal Office for the Environment (FOEN)");
  const [authorizedUseScope, setAuthorizedUseScope] = useState("NDC Achievement");
  const [isSubmittingITMO, setIsSubmittingITMO] = useState(false);
  const [itmoResult, setItmoResult] = useState<any>(null);
  const [itmoError, setItmoError] = useState<string | null>(null);
  const [isDownloadingZip, setIsDownloadingZip] = useState(false);
  const [showDossierModal, setShowDossierModal] = useState(false);
  const [copied, setCopied] = useState(false);

  // Cryptographic Credit Issuance & Serial Sealing Modal State
  const [isMintModalOpen, setIsMintModalOpen] = useState(false);
  const [targetChain, setTargetChain] = useState("internal-ledger");
  const [recipientWallet, setRecipientWallet] = useState("VF_Treasury_Custody_Account");
  const [isMinting, setIsMinting] = useState(false);
  const [mintResult, setMintResult] = useState<any>(null);
  const [mintError, setMintError] = useState<string | null>(null);

  // Report Generation & Download Modal State
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [reportType, setReportType] = useState("MRV_CARBON_LEDGER");
  const [reportStandard, setReportStandard] = useState("VERRA");
  const [reportTitle, setReportTitle] = useState("");
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);
  const [reportSuccess, setReportSuccess] = useState<string | null>(null);

  const role = user?.role || "ADMIN";
  const insight = getContextualInsight(pathname, activeSector, role);



  const handleSend = async (e: React.FormEvent) => {

    e.preventDefault();

    if (!query.trim() || isThinking) return;



    const userMsg = query.trim();

    setQuery("");

    setError(null);

    setChatHistory((prev) => [...prev, { role: "user", text: userMsg }]);

    setIsThinking(true);



    try {

      const result: AIChatResponse = await chatWithAI(userMsg, {

        page: pathname,

        sector: activeSector,

      });



      setChatHistory((prev) => [

        ...prev,

        {

          role: "ai",

          text: result.response,

          confidence: result.confidence,

          sourceModule: result.source_module,

          recommendations: result.recommendations,

        },

      ]);

    } catch (err: any) {

      const errorMsg = err?.message || "Unable to reach the AI service. Please try again.";

      setError(errorMsg);

      setChatHistory((prev) => [

        ...prev,

        {

          role: "ai",

          text: "I'm having trouble connecting to the intelligence service. Please check your connection and try again.",

          confidence: 0,

        },

      ]);

    } finally {

      setIsThinking(false);

    }

  };



  const getPriorityColor = (priority: string) => {

    switch (priority?.toUpperCase()) {

      case "HIGH": return "text-red-400 bg-red-500/10 border-red-500/30";

      case "MEDIUM": return "text-yellow-400 bg-yellow-500/10 border-yellow-500/30";

      case "LOW": return "text-blue-400 bg-blue-500/10 border-blue-500/30";

      default: return "text-gray-400 bg-gray-500/10 border-gray-500/30";

    }

  };



  if (pathname === "/dashboard/ai") {
    return null;
  }

  const displayTitle = insight.pageTitle === "Decision Support"
    ? "Decision Support"
    : `${insight.pageTitle} Guidance`;

  return (
    <>
      {isDismissed ? (
        <div className="fixed bottom-5 right-5 z-40">
          <button
            onClick={() => setIsDismissed(false)}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-full bg-[var(--color-surface)] border border-[var(--color-border)] text-xs font-semibold text-[var(--color-text-primary)] hover:border-[#008A5E]/40 hover:text-[#008A5E] transition-all shadow-md hover:shadow-lg cursor-pointer backdrop-blur-sm"
            title="Open Decision Support Panel"
          >
            <HelpCircle size={14} className="text-[#008A5E]" />
            <span>Decision Support</span>
          </button>
        </div>
      ) : (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-xs animate-fade-in">
          <div className="w-full max-w-lg bg-[var(--color-surface)] border-l border-[var(--color-border)] h-full flex flex-col shadow-2xl overflow-hidden">
            {/* Header Surface */}
            <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-surface)] shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-[#008A5E] flex items-center justify-center shrink-0">
                  <HelpCircle size={16} />
                </div>
                <div>
                  <h2 className="font-semibold text-xs text-[var(--color-text-primary)]">
                    {displayTitle}
                  </h2>
                  <p className="text-[11px] text-[var(--color-text-secondary)] mt-0.5 leading-tight line-clamp-1">
                    {insight.aiRecommendation}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => setIsDismissed(true)}
                  className="p-1 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                  title="Close guidance panel"
                  aria-label="Close guidance panel"
                >
                  <X size={15} />
                </button>
              </div>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar text-xs">
              {/* Quick Action Button Box */}
              <div className="p-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <span className="text-[10px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider">Recommended Next Action</span>
                  <p className="text-xs font-semibold text-[var(--color-text-primary)] truncate mt-0.5">{insight.whatToDoNext}</p>
                </div>
                <div className="shrink-0">
                  {insight.nextActionLabel === "Submit ITMO Authorization" ? (
                    <button
                      onClick={() => {
                        setIsITMOModalOpen(true);
                        setItmoResult(null);
                        setItmoError(null);
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
                      className="px-3 py-1.5 rounded-md bg-[#008A5E] text-white font-semibold text-xs hover:bg-[#00734E] transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
                    >
                      <span>{insight.nextActionLabel}</span>
                      <ArrowRight size={13} />
                    </button>
                  ) : (insight.nextActionLabel === "Execute Minting" || insight.nextActionLabel === "Issue & Seal Credits") ? (
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
                      className="px-3 py-1.5 rounded-md bg-[#008A5E] text-white font-semibold text-xs hover:bg-[#00734E] transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
                    >
                      <Shield size={13} />
                      <span>{insight.nextActionLabel}</span>
                      <ArrowRight size={13} />
                    </button>
                  ) : insight.nextActionLabel === "Download Report" ? (
                    <button
                      onClick={() => {
                        setIsReportModalOpen(true);
                        setReportError(null);
                        setReportSuccess(null);
                        const secLabel = (activeSector || "Sector").replace("_", " ").toUpperCase();
                        setReportTitle(`${secLabel} Verified Carbon Abatement & MRV Report`);
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
                      className="px-3 py-1.5 rounded-md bg-[#008A5E] text-white font-semibold text-xs hover:bg-[#00734E] transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
                    >
                      <Download size={13} />
                      <span>{insight.nextActionLabel}</span>
                      <ArrowRight size={13} />
                    </button>
                  ) : (
                    <Link
                      href={insight.nextActionHref}
                      className="px-3 py-1.5 rounded-md bg-[#008A5E] text-white font-semibold text-xs hover:bg-[#00734E] transition-colors flex items-center gap-1.5"
                    >
                      <span>{insight.nextActionLabel}</span>
                      <ArrowRight size={13} />
                    </Link>
                  )}
                </div>
              </div>

              {/* Contextual Purpose & Impact */}
              <div className="grid grid-cols-1 gap-2.5">
                <div className="p-3 rounded-md bg-[var(--color-background)] border border-[var(--color-border)]">
                  <h4 className="font-semibold text-[var(--color-text-primary)] text-xs mb-1">Purpose</h4>
                  <p className="text-[var(--color-text-secondary)] text-[11px] leading-relaxed">{insight.purpose}</p>
                </div>

                <div className="p-3 rounded-md bg-[var(--color-background)] border border-[var(--color-border)]">
                  <h4 className="font-semibold text-[var(--color-text-primary)] text-xs mb-1">Impact</h4>
                  <p className="text-[var(--color-text-secondary)] text-[11px] leading-relaxed">{insight.whyItMatters}</p>
                </div>
              </div>

              {/* Interactive Chat Stream */}
              <div className="space-y-2 pt-2 border-t border-[var(--color-border)]">
                <div className="flex items-center justify-between text-[11px] font-bold text-[var(--color-text-secondary)]">
                  <span>Decision Support Query</span>
                  <span className="font-mono text-[10px] text-[#008A5E]">
                    <Shield size={10} className="inline mr-1" />
                    Operational Reasoning
                  </span>
                </div>

                {chatHistory.length > 0 && (
                  <div className="max-h-64 overflow-y-auto space-y-2 p-2 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] custom-scrollbar">
                    {chatHistory.map((msg, idx) => (
                      <div key={idx}>
                        <div
                          className={`p-2 rounded-lg text-xs whitespace-pre-line ${
                            msg.role === "user"
                              ? "bg-[#008A5E]/10 text-[#008A5E] font-bold ml-auto max-w-[80%]"
                              : "bg-[var(--color-surface)] text-[var(--color-text-primary)] max-w-[90%]"
                          }`}
                        >
                          {msg.text}
                        </div>

                        {msg.role === "ai" && msg.confidence !== undefined && msg.confidence > 0 && (
                          <div className="flex items-center gap-2 mt-1 ml-1">
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-[#008A5E]">
                              {(msg.confidence * 100).toFixed(0)}% confidence
                            </span>
                            {msg.sourceModule && (
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">
                                {msg.sourceModule}
                              </span>
                            )}
                          </div>
                        )}

                        {msg.role === "ai" && msg.recommendations && msg.recommendations.length > 0 && (
                          <div className="mt-2 space-y-1 ml-1">
                            {msg.recommendations.slice(0, 3).map((rec, ri) => (
                              <div
                                key={ri}
                                className={`flex items-start gap-2 p-2 rounded-lg border text-[11px] ${getPriorityColor(rec.priority)}`}
                              >
                                {rec.priority === "HIGH" ? <AlertTriangle size={12} className="shrink-0 mt-0.5" /> : <CheckCircle2 size={12} className="shrink-0 mt-0.5" />}
                                <div>
                                  <span className="font-bold text-[10px] uppercase">{rec.priority}</span>
                                  <p className="mt-0.5 font-medium">{rec.action}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                    {isThinking && (
                      <div className="p-2 rounded-lg bg-[var(--color-surface)] text-[var(--color-text-secondary)] text-xs animate-pulse flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full border-2 border-[#008A5E] border-t-transparent animate-spin" />
                        <span>Evaluating operational context...</span>
                      </div>
                    )}
                  </div>
                )}

                {error && (
                  <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-1.5">
                    <AlertTriangle size={13} className="shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <form onSubmit={handleSend} className="flex gap-2 pt-1">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Ask about project status, risk levels, verification..."
                    className="flex-1 bg-[var(--color-background)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[#008A5E]"
                    disabled={isThinking}
                  />
                  <button
                    type="submit"
                    disabled={isThinking || !query.trim()}
                    className="px-3 py-2 rounded-lg bg-[#008A5E] text-white font-semibold text-xs hover:bg-[#00734E] transition-all flex items-center gap-1 shrink-0 cursor-pointer disabled:opacity-50"
                  >
                    <span>{isThinking ? "..." : "Ask"}</span>
                    <Send size={11} />
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      )}



      {/* Article 6.2 ITMO Authorization Modal */}
      {isITMOModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-xl rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between bg-gradient-to-r from-emerald-950/30 to-transparent">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center">
                  <Globe size={20} />
                </div>
                <div>
                  <h3 className="text-base font-bold text-[var(--color-text-primary)]">
                    UNFCCC Article 6.2 ITMO Authorization
                  </h3>
                  <p className="text-xs text-[var(--color-text-secondary)]">
                    Paris Agreement Host Party Registry & Bilateral Cooperative Approach
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsITMOModalOpen(false)}
                className="p-2 rounded-lg hover:bg-slate-800 text-[var(--color-text-muted)] hover:text-white transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 space-y-4 overflow-y-auto flex-1 text-xs">
              {itmoResult ? (
                /* Success State */
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 space-y-2">
                    <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                      <CheckCircle2 size={18} />
                      <span>{itmoResult.message}</span>
                    </div>
                    <p className="text-[var(--color-text-secondary)] leading-relaxed">
                      Sovereign Article 6.2 ITMO authorization successfully registered and cryptographically sealed on the VeriField ledger.
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2.5 font-mono text-[11px]">
                    <div className="flex justify-between py-1 border-b border-[var(--color-border)]">
                      <span className="text-[var(--color-text-secondary)]">Status:</span>
                      <span className="text-emerald-400 font-bold">AUTHORIZED (STAGE 8)</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[var(--color-border)]">
                      <span className="text-[var(--color-text-secondary)]">ITMO Serial Number:</span>
                      <span className="text-[var(--color-text-primary)] font-bold">{itmoResult.serial_number}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[var(--color-border)]">
                      <span className="text-[var(--color-text-secondary)]">Cooperative Approach ID:</span>
                      <span className="text-[var(--color-text-primary)]">{itmoResult.cooperative_approach_id}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[var(--color-border)]">
                      <span className="text-[var(--color-text-secondary)]">Acquiring Party DNA:</span>
                      <span className="text-[var(--color-text-primary)]">{itmoResult.acquiring_party}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[var(--color-border)]">
                      <span className="text-[var(--color-text-secondary)]">Cumulative Volume:</span>
                      <span className="text-emerald-400 font-bold">{itmoResult.cumulative_itmos_tco2e} tCO2e</span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-[var(--color-text-secondary)]">Attestation Hash:</span>
                      <span className="text-[var(--color-text-muted)] truncate max-w-[200px]">{itmoResult.dossier_sha256}</span>
                    </div>
                  </div>

                  <div className="flex gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowDossierModal(!showDossierModal)}
                      className="flex-1 py-2.5 px-3 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] hover:border-emerald-500 text-xs font-semibold text-center text-[var(--color-text-primary)] flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                    >
                      <FileText size={14} className="text-emerald-400" />
                      <span>{showDossierModal ? "Hide Dossier" : "View Structured Dossier"}</span>
                    </button>
                    <button
                      type="button"
                      disabled={isDownloadingZip}
                      onClick={async () => {
                        try {
                          setIsDownloadingZip(true);
                          await downloadArticle6PackageZip("ARTICLE6_2", itmoResult.project_id);
                        } catch (err: any) {
                          alert("Download failed: " + (err?.message || "Unknown error"));
                        } finally {
                          setIsDownloadingZip(false);
                        }
                      }}
                      className="flex-1 py-2.5 px-3 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-xs font-semibold text-center text-white flex items-center justify-center gap-1.5 transition-colors shadow-md shadow-emerald-500/20 cursor-pointer disabled:opacity-50"
                    >
                      {isDownloadingZip ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
                      <span>{isDownloadingZip ? "Downloading..." : "Download Package ZIP"}</span>
                    </button>
                  </div>

                  {showDossierModal && itmoResult.dossier && (
                    <div className="mt-3 p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-mono text-emerald-400 font-bold">
                          Article 6.2 Compliance Dossier (JSON)
                        </span>
                        <button
                          type="button"
                          onClick={() => {
                            navigator.clipboard.writeText(JSON.stringify(itmoResult.dossier, null, 2));
                            setCopied(true);
                            setTimeout(() => setCopied(false), 2000);
                          }}
                          className="px-2 py-1 rounded bg-slate-800 text-slate-300 hover:text-white text-[10px] flex items-center gap-1 cursor-pointer transition-colors"
                        >
                          <Copy size={11} />
                          <span>{copied ? "Copied!" : "Copy JSON"}</span>
                        </button>
                      </div>
                      <pre className="text-[10px] font-mono text-slate-300 overflow-x-auto max-h-60 p-2 rounded bg-slate-900/80 border border-slate-800 leading-tight">
                        {JSON.stringify(itmoResult.dossier, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ) : (
                /* Form State */
                <form
                  onSubmit={async (e) => {
                    e.preventDefault();
                    const projIdToSubmit = selectedProjectId || (projects.length > 0 ? projects[0].id : "");
                    if (!projIdToSubmit) {
                      setItmoError("Please select a project.");
                      return;
                    }
                    setIsSubmittingITMO(true);
                    setItmoError(null);
                    try {
                      const res = await submitITMOAuthorization({
                        project_id: projIdToSubmit,
                        acquiring_party: acquiringParty,
                        authorized_use_scope: authorizedUseScope,
                      });
                      setItmoResult(res);
                    } catch (err: any) {
                      setItmoError(err?.message || "Failed to authorize ITMO. Ensure the project is approved and you have ORG_ADMIN permissions.");
                    } finally {
                      setIsSubmittingITMO(false);
                    }
                  }}
                  className="space-y-4"
                >
                  {itmoError && (
                    <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 flex items-center gap-2">
                      <AlertTriangle size={15} className="shrink-0" />
                      <span>{itmoError}</span>
                    </div>
                  )}

                  {/* Project Selector */}
                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1.5">
                      Select Mitigation Project
                    </label>
                    <select
                      value={selectedProjectId}
                      onChange={(e) => setSelectedProjectId(e.target.value)}
                      required
                      className="w-full px-3 py-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
                    >
                      {projects.length === 0 && <option value="">Loading enrolled projects...</option>}
                      {projects.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name} ({p.country || "Nigeria"}) — {p.sector || "Clean Energy / MRV"}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Host Party DNA */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1.5">
                        Host Party DNA
                      </label>
                      <input
                        type="text"
                        value="Nigeria (NCCC Registry)"
                        disabled
                        className="w-full px-3 py-2 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs text-[var(--color-text-muted)] cursor-not-allowed"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1.5">
                        Authorized Use Scope
                      </label>
                      <select
                        value={authorizedUseScope}
                        onChange={(e) => setAuthorizedUseScope(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
                      >
                        <option value="NDC Achievement">NDC Achievement</option>
                        <option value="Other International Mitigation Purposes (OIMP)">OIMP (CORSIA / Voluntary)</option>
                      </select>
                    </div>
                  </div>

                  {/* Acquiring Party DNA */}
                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1.5">
                      Acquiring Party / Bilateral Partner DNA
                    </label>
                    <input
                      type="text"
                      value={acquiringParty}
                      onChange={(e) => setAcquiringParty(e.target.value)}
                      required
                      placeholder="e.g. Swiss Federal Office for the Environment (FOEN)"
                      className="w-full px-3 py-2 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
                    />
                  </div>

                  {/* Pre-Validation Checklist */}
                  <div className="p-3 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-1.5">
                    <p className="text-[11px] font-bold text-[var(--color-text-primary)] uppercase tracking-wider mb-1">
                      Pre-Validation Checklist (Decision 2/CMA.3)
                    </p>
                    <div className="flex items-center gap-2 text-[11px] text-emerald-400">
                      <Check size={13} />
                      <span>Host Party NDC alignment verified</span>
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-emerald-400">
                      <Check size={13} />
                      <span>Additionality & AST baseline calculation sealed</span>
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-emerald-400">
                      <Check size={13} />
                      <span>Corresponding Adjustment lifecycle sequence protected</span>
                    </div>
                  </div>

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={isSubmittingITMO || projects.length === 0}
                    className="w-full py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white font-bold text-xs disabled:opacity-50 flex items-center justify-center gap-2 transition-all cursor-pointer shadow-lg shadow-emerald-500/20"
                  >
                    {isSubmittingITMO ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        <span>Validating & Authorizing ITMO...</span>
                      </>
                    ) : (
                      <>
                        <Shield size={15} />
                        <span>Pre-Validate & Authorize ITMO</span>
                      </>
                    )}
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      )}

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
                      }}
                      className="flex-1 py-2 px-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] hover:border-emerald-500 text-xs font-semibold text-center text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                    >
                      <span>Close</span>
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
                    } catch (err: any) {
                      setMintError(err?.message || "Failed to execute cryptographic issuance. Ensure carbon records are verified.");
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

      {/* Interactive Report Generation & Download Modal */}
      {isReportModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                  <FileText size={16} />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-[var(--color-text-primary)]">
                    Generate & Download Official Carbon Report
                  </h3>
                  <p className="text-[11px] text-[var(--color-text-secondary)]">
                    VeriField Nexus dMRV • Tamper-Evident Report Engine
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsReportModalOpen(false)}
                className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] p-1 rounded-lg transition-colors cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setIsGeneratingReport(true);
                setReportError(null);
                setReportSuccess(null);

                const orgIdToUse = user?.organization_id;
                const projIdToUse = selectedProjectId || (projects.length > 0 ? projects[0].id : undefined);

                try {
                  if (reportType === "REGISTRY_ZIP") {
                    if (!projIdToUse) {
                      throw new Error("Please select a project to compile a certified registry submission ZIP package.");
                    }
                    await downloadArticle6PackageZip(reportStandard, projIdToUse);
                    setReportSuccess(`Successfully compiled and downloaded ${reportStandard} submission package ZIP!`);
                  } else {
                    if (!orgIdToUse) {
                      throw new Error("Organization context is required. Please ensure your account is assigned to an active organization.");
                    }
                    await generateAndDownloadReport(
                      orgIdToUse,
                      projIdToUse || undefined,
                      reportTitle || "Verified Project Carbon Ledger & MRV Report"
                    );
                    setReportSuccess("ReportLab PDF report compiled and downloaded successfully!");
                  }
                  setTimeout(() => {
                    setIsReportModalOpen(false);
                  }, 2500);
                } catch (err: any) {
                  setReportError(err?.message || "Failed to generate report. Please verify project data.");
                } finally {
                  setIsGeneratingReport(false);
                }
              }}
              className="space-y-4 text-xs"
            >
              {reportError && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 flex items-center gap-2">
                  <AlertTriangle size={15} className="shrink-0" />
                  <span>{reportError}</span>
                </div>
              )}

              {reportSuccess && (
                <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center gap-2">
                  <CheckCircle2 size={15} className="shrink-0" />
                  <span>{reportSuccess}</span>
                </div>
              )}

              {/* Report Format Selection */}
              <div>
                <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1.5">
                  Report Type & Deliverable Format
                </label>
                <select
                  value={reportType}
                  onChange={(e) => setReportType(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
                >
                  <option value="MRV_CARBON_LEDGER">Verified Carbon Ledger & Performance Report (PDF)</option>
                  <option value="ESG_ABATEMENT_FORECAST">Executive ESG & Abatement Forecast Report (PDF)</option>
                  <option value="REGISTRY_ZIP">Certified Registry Submission Package (Multi-Format ZIP: PDF + DOCX + CSV + JSON)</option>
                </select>
              </div>

              {/* Registry Standard Selector (if ZIP) */}
              {reportType === "REGISTRY_ZIP" && (
                <div>
                  <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1.5">
                    Target Registry Standard
                  </label>
                  <select
                    value={reportStandard}
                    onChange={(e) => setReportStandard(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
                  >
                    <option value="VERRA">Verra Verified Carbon Standard (VCS v4.4/v5.0)</option>
                    <option value="GOLD_STANDARD">Gold Standard for the Global Goals (GS4GG v2.2)</option>
                    <option value="ARTICLE6_2">UNFCCC Article 6.2 ITMO Cooperative Approach</option>
                    <option value="NCCC">Nigeria National Council on Climate Change (NCCC/NCMAP)</option>
                  </select>
                </div>
              )}

              {/* Project Scope */}
              <div>
                <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1.5">
                  Project Scope
                </label>
                <select
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
                >
                  <option value="">All Projects & Activities across Organization</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.country || "Nigeria"}) — {p.sector || "Clean Sector"}
                    </option>
                  ))}
                </select>
              </div>

              {/* Report Title */}
              <div>
                <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1.5">
                  Document Title & Header
                </label>
                <input
                  type="text"
                  value={reportTitle}
                  onChange={(e) => setReportTitle(e.target.value)}
                  required
                  placeholder="e.g. Hybrid Energy Sector Verified Carbon Abatement Report"
                  className="w-full px-3 py-2 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
                />
              </div>

              {/* Attestation Box */}
              <div className="p-3 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-1.5">
                <p className="text-[11px] font-bold text-[var(--color-text-primary)] uppercase tracking-wider mb-1">
                  Cryptographic Integrity Guarantees
                </p>
                <div className="flex items-center gap-2 text-[11px] text-emerald-400">
                  <Check size={13} />
                  <span>Compiled dynamically from real-time database telemetry</span>
                </div>
                <div className="flex items-center gap-2 text-[11px] text-emerald-400">
                  <Check size={13} />
                  <span>ReportLab publication styling with dynamic page numbering & headers</span>
                </div>
                <div className="flex items-center gap-2 text-[11px] text-emerald-400">
                  <Check size={13} />
                  <span>SHA-256 tamper-evident digital seal embedded in document trailer</span>
                </div>
              </div>

              {/* Action Button */}
              <button
                type="submit"
                disabled={isGeneratingReport}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white font-bold text-xs disabled:opacity-50 flex items-center justify-center gap-2 transition-all cursor-pointer shadow-lg shadow-emerald-500/20"
              >
                {isGeneratingReport ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span>Compiling & Attesting Document...</span>
                  </>
                ) : (
                  <>
                    <Download size={15} />
                    <span>Compile & Download Document</span>
                  </>
                )}
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
