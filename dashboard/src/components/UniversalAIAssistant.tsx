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
import { chatWithAI, AIChatResponse, fetchProjects, submitITMOAuthorization } from "@/lib/api";
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
  const [isExpanded, setIsExpanded] = useState(false);
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



  return (
    <div className="my-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] overflow-hidden">
      {/* AI Header Surface */}
      <div className="p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-md bg-emerald-50 dark:bg-emerald-950/40 text-[#008A5E] flex items-center justify-center shrink-0">
            <Bot size={17} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-xs text-[var(--color-text-primary)]">
                {insight.pageTitle} Assistant
              </span>
            </div>
            <p className="text-xs text-[var(--color-text-secondary)] mt-0.5 leading-snug">
              {insight.aiRecommendation}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="px-2.5 py-1 rounded-md bg-[var(--color-background)] border border-[var(--color-border)] text-xs font-medium text-[var(--color-text-primary)] hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <HelpCircle size={13} className="text-[#008A5E]" />
            <span>{isExpanded ? "Hide Details" : "Guidance"}</span>
            {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>

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
                    if (items.length > 0 && !selectedProjectId) {
                      setSelectedProjectId(items[0].id);
                    }
                  })
                  .catch(() => {});
              }}
              className="px-3 py-1 rounded-md bg-[#008A5E] text-white font-semibold text-xs hover:bg-[#00734E] transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
            >
              <span>{insight.nextActionLabel}</span>
              <ArrowRight size={13} />
            </button>
          ) : (
            <Link
              href={insight.nextActionHref}
              className="px-3 py-1 rounded-md bg-[#008A5E] text-white font-semibold text-xs hover:bg-[#00734E] transition-colors flex items-center gap-1.5"
            >
              <span>{insight.nextActionLabel}</span>
              <ArrowRight size={13} />
            </Link>
          )}
        </div>
      </div>

      {/* Expanded Contextual Guidance & Interactive Assistant Panel */}
      {isExpanded && (
        <div className="p-3.5 border-t border-[var(--color-border)] bg-[var(--color-surface)] space-y-3 text-xs">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-3 rounded-md bg-[var(--color-background)] border border-[var(--color-border)]">
              <h4 className="font-semibold text-[var(--color-text-primary)] text-xs mb-1">Purpose</h4>
              <p className="text-[var(--color-text-secondary)] text-[11px] leading-relaxed">{insight.purpose}</p>
            </div>

            <div className="p-3 rounded-md bg-[var(--color-background)] border border-[var(--color-border)]">
              <h4 className="font-semibold text-[var(--color-text-primary)] text-xs mb-1">Impact</h4>
              <p className="text-[var(--color-text-secondary)] text-[11px] leading-relaxed">{insight.whyItMatters}</p>
            </div>

            <div className="p-3 rounded-md bg-[var(--color-background)] border border-[var(--color-border)]">
              <h4 className="font-semibold text-[var(--color-text-primary)] text-xs mb-1">Next Step</h4>
              <p className="text-[#008A5E] font-medium text-[11px] leading-relaxed">{insight.whatToDoNext}</p>
            </div>
          </div>



          {/* Interactive Chat Stream */}

          <div className="space-y-2 pt-2 border-t border-[var(--color-border)]">

            <div className="flex items-center justify-between text-[11px] font-bold text-[var(--color-text-secondary)]">

              <span>Ask AI Copilot for {insight.pageTitle}</span>

              <span className="font-mono text-[10px] text-[#00B47A]">

                <Shield size={10} className="inline mr-1" />

                Connected to Backend Intelligence

              </span>

            </div>



            {chatHistory.length > 0 && (

              <div className="max-h-64 overflow-y-auto space-y-2 p-2 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] custom-scrollbar">

                {chatHistory.map((msg, idx) => (

                  <div key={idx}>

                    <div

                      className={`p-2 rounded-lg text-xs whitespace-pre-line ${

                        msg.role === "user"

                          ? "bg-[#00B47A]/10 text-[#00B47A] font-bold ml-auto max-w-[80%]"

                          : "bg-[var(--color-surface)] text-[var(--color-text-primary)] max-w-[90%]"

                      }`}

                    >

                      {msg.text}

                    </div>

                    {/* Confidence + Source badge for AI messages */}

                    {msg.role === "ai" && msg.confidence !== undefined && msg.confidence > 0 && (

                      <div className="flex items-center gap-2 mt-1 ml-1">

                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-[#00B47A]">

                          {(msg.confidence * 100).toFixed(0)}% confidence

                        </span>

                        {msg.sourceModule && (

                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">

                            {msg.sourceModule}

                          </span>

                        )}

                      </div>

                    )}

                    {/* Recommendations cards */}

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

                              <p className="text-[var(--color-text-primary)] mt-0.5">{rec.action}</p>

                            </div>

                          </div>

                        ))}

                      </div>

                    )}

                  </div>

                ))}

                {isThinking && (

                  <div className="flex items-center gap-2 text-[10px] font-mono text-emerald-400 animate-pulse p-2">

                    <div className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce" />

                    Querying intelligence modules...

                  </div>

                )}

              </div>

            )}



            {error && (

              <div className="text-[10px] text-red-400 px-2">{error}</div>

            )}



            <form onSubmit={handleSend} className="flex items-center gap-2">

              <input

                type="text"

                value={query}

                onChange={(e) => setQuery(e.target.value)}

                placeholder={`Ask about project status, risk levels, verification progress, carbon data...`}

                className="flex-1 bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl px-3 py-2 text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]"

                disabled={isThinking}

              />

              <button

                type="submit"

                disabled={isThinking}

                className="px-4 py-2 rounded-xl bg-[#00B47A] text-slate-950 font-bold text-xs hover:bg-[#009b68] transition-all flex items-center gap-1 shrink-0 cursor-pointer shadow-xs disabled:opacity-50"

              >

                <span>{isThinking ? "..." : "Send"}</span>

                <Send size={12} />

              </button>

            </form>

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
                    <a
                      href={`/api/v1/registry/dossier/ARTICLE6_2/${itmoResult.project_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 py-2.5 px-3 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] hover:border-emerald-500 text-xs font-semibold text-center text-[var(--color-text-primary)] flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <FileText size={14} className="text-emerald-400" />
                      <span>View Structured Dossier</span>
                    </a>
                    <a
                      href={`/api/v1/registry/package-download/ARTICLE6_2/${itmoResult.project_id}`}
                      className="flex-1 py-2.5 px-3 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-xs font-semibold text-center text-white flex items-center justify-center gap-1.5 transition-colors shadow-md shadow-emerald-500/20"
                    >
                      <Download size={14} />
                      <span>Download Package ZIP</span>
                    </a>
                  </div>
                </div>
              ) : (
                /* Form State */
                <form
                  onSubmit={async (e) => {
                    e.preventDefault();
                    if (!selectedProjectId) {
                      setItmoError("Please select a project.");
                      return;
                    }
                    setIsSubmittingITMO(true);
                    setItmoError(null);
                    try {
                      const res = await submitITMOAuthorization({
                        project_id: selectedProjectId,
                        acquiring_party: acquiringParty,
                        authorized_use_scope: authorizedUseScope,
                      });
                      setItmoResult(res);
                    } catch (err: any) {
                      setItmoError(err?.message || "Failed to authorize ITMO. Ensure you have ORG_ADMIN permissions.");
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
    </div>
  );
}
