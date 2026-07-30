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

import { chatWithAI, AIChatResponse } from "@/lib/api";

import { Bot, Sparkles, ArrowRight, HelpCircle, ChevronDown, ChevronUp, Send, AlertTriangle, CheckCircle2, Shield } from "lucide-react";

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

    <div className="my-6 rounded-2xl bg-gradient-to-r from-emerald-500/10 via-[#00B47A]/5 to-transparent border border-[#00B47A]/30 shadow-sm overflow-hidden transition-all duration-300">

      {/* AI Header Surface */}

      <div className="p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">

        <div className="flex items-center gap-3">

          <div>

            <div className="flex items-center gap-2">

              <span className="font-extrabold text-xs text-[#00B47A] uppercase tracking-wider">

                {insight.pageTitle} AI Assistant

              </span>

            </div>

            <p className="text-xs text-[var(--color-text-primary)] font-medium mt-0.5 leading-snug">

              &quot;{insight.aiRecommendation}&quot;

            </p>

          </div>

        </div>



        <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">

          <button

            onClick={() => setIsExpanded(!isExpanded)}

            className="px-3 py-1.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs font-bold text-[var(--color-text-primary)] hover:bg-[var(--color-background)] transition-all flex items-center gap-1.5 cursor-pointer"

          >

            <HelpCircle size={14} className="text-[#00B47A]" />

            <span>{isExpanded ? "Hide Guidance" : "Context & Guidance"}</span>

            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}

          </button>



          <Link

            href={insight.nextActionHref}

            className="px-4 py-1.5 rounded-xl bg-[#00B47A] text-slate-950 font-extrabold text-xs hover:bg-[#009b68] transition-all flex items-center gap-1.5 shadow-xs"

          >

            <span>{insight.nextActionLabel}</span>

            <ArrowRight size={14} />

          </Link>

        </div>

      </div>



      {/* Expanded Contextual Guidance & Interactive Assistant Panel */}

      {isExpanded && (

        <div className="p-4 border-t border-[#00B47A]/20 bg-[var(--color-surface)] space-y-4 animate-fade-in text-xs">

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

            <div className="p-3 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)]">

              <h4 className="font-extrabold text-[var(--color-text-primary)] text-xs mb-1">What This Screen Does</h4>

              <p className="text-[var(--color-text-secondary)] text-[11px] leading-relaxed">{insight.purpose}</p>

            </div>



            <div className="p-3 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)]">

              <h4 className="font-extrabold text-[var(--color-text-primary)] text-xs mb-1">Why It Matters</h4>

              <p className="text-[var(--color-text-secondary)] text-[11px] leading-relaxed">{insight.whyItMatters}</p>

            </div>



            <div className="p-3 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)]">

              <h4 className="font-extrabold text-[var(--color-text-primary)] text-xs mb-1">Recommended Next Step</h4>

              <p className="text-[#00B47A] font-bold text-[11px] leading-relaxed">{insight.whatToDoNext}</p>

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

    </div>

  );

}
