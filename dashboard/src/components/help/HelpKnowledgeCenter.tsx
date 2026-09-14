// =============================================================================
// VeriField Nexus — Help & Knowledge Centre
// =============================================================================

"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { useSearchParams } from "next/navigation";
import {
  Search,
  ChevronDown,
  Copy,
  Printer,
  ArrowUp,
  X,
} from "lucide-react";
import { useToast } from "@/components/Toast";
import {
  NAV_SECTIONS,
  WORKFLOW_STEPS,
  ROLE_GUIDES,
  GLOSSARY_TERMS,
  FAQS_LIST,
  KEYBOARD_SHORTCUTS,
} from "./HelpData";

export default function HelpKnowledgeCenter() {
  const toast = useToast();
  const searchParams = useSearchParams();

  // Search & Navigation States
  const [globalSearch, setGlobalSearch] = useState("");
  const [activeSectionId, setActiveSectionId] = useState<string>(() => searchParams?.get("section") || "introduction");
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    introduction: true,
    workflow: true,
  });
  const [faqCategoryFilter, setFaqCategoryFilter] = useState<string>("ALL");
  const [showBackToTop, setShowBackToTop] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);

  const mainContainerRef = useRef<HTMLDivElement>(null);

  // Deep linking & state persistence from URL query or localStorage
  useEffect(() => {
    const sectionParam = searchParams?.get("section");
    if (sectionParam) {
      const timer = setTimeout(() => {
        setActiveSectionId(sectionParam);
        setExpandedSections(prev => ({ ...prev, [sectionParam]: true }));
        const el = document.getElementById(`section-${sectionParam}`);
        if (el) el.scrollIntoView({ behavior: "smooth" });
      }, 50);
      return () => clearTimeout(timer);
    } else {
      try {
        const saved = localStorage.getItem("verifield_help_expanded");
        if (saved) {
          const parsed = JSON.parse(saved);
          const timer = setTimeout(() => {
            setExpandedSections(parsed);
          }, 0);
          return () => clearTimeout(timer);
        }
      } catch {}
    }
  }, [searchParams]);

  const toggleSection = (id: string) => {
    setExpandedSections(prev => {
      const next = { ...prev, [id]: !prev[id] };
      try {
        localStorage.setItem("verifield_help_expanded", JSON.stringify(next));
      } catch {}
      return next;
    });
  };

  const expandAll = () => {
    const allExpanded: Record<string, boolean> = {};
    NAV_SECTIONS.forEach(s => (allExpanded[s.id] = true));
    setExpandedSections(allExpanded);
    toast.info("Expanded All", "All documentation sections expanded.");
  };

  const collapseAll = () => {
    setExpandedSections({});
    toast.info("Collapsed All", "All documentation sections collapsed.");
  };

  // Scroll Progress & Back-to-top handler
  useEffect(() => {
    const handleScroll = () => {
      const container = mainContainerRef.current;
      if (!container) return;
      const { scrollTop, scrollHeight, clientHeight } = container;
      const progress = scrollHeight > clientHeight ? (scrollTop / (scrollHeight - clientHeight)) * 100 : 0;
      setScrollProgress(progress);
      setShowBackToTop(scrollTop > 400);
    };

    const container = mainContainerRef.current;
    if (container) {
      container.addEventListener("scroll", handleScroll);
      return () => container.removeEventListener("scroll", handleScroll);
    }
  }, []);

  const scrollToTop = () => {
    if (mainContainerRef.current) {
      mainContainerRef.current.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const copySectionLink = (id: string) => {
    const url = `${window.location.origin}/dashboard/help?section=${id}`;
    navigator.clipboard.writeText(url);
    toast.success("Link Copied", `Direct URL copied for section: ${id}`);
  };

  const handlePrint = () => {
    window.print();
  };

  // Search Engine & Grouped Filtering
  const searchResults = useMemo(() => {
    if (!globalSearch.trim()) return null;
    const q = globalSearch.toLowerCase().trim();

    const matchedSections = NAV_SECTIONS.filter(
      s => s.title.toLowerCase().includes(q) || s.id.toLowerCase().includes(q)
    );

    const matchedFaqs = FAQS_LIST.filter(
      f =>
        f.question.toLowerCase().includes(q) ||
        f.answer.toLowerCase().includes(q) ||
        f.keywords.some(k => k.toLowerCase().includes(q))
    );

    const matchedRoles = ROLE_GUIDES.filter(
      r =>
        r.title.toLowerCase().includes(q) ||
        r.code.toLowerCase().includes(q) ||
        r.purpose.toLowerCase().includes(q)
    );

    const matchedGlossary = GLOSSARY_TERMS.filter(
      g => g.term.toLowerCase().includes(q) || g.definition.toLowerCase().includes(q)
    );

    return { matchedSections, matchedFaqs, matchedRoles, matchedGlossary };
  }, [globalSearch]);

  // Filtered FAQs
  const filteredFaqs = useMemo(() => {
    let list = FAQS_LIST;
    if (faqCategoryFilter !== "ALL") {
      list = list.filter(f => f.category === faqCategoryFilter);
    }
    if (globalSearch.trim()) {
      const q = globalSearch.toLowerCase().trim();
      list = list.filter(
        f =>
          f.question.toLowerCase().includes(q) ||
          f.answer.toLowerCase().includes(q) ||
          f.keywords.some(k => k.toLowerCase().includes(q))
      );
    }
    return list;
  }, [faqCategoryFilter, globalSearch]);

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-[var(--color-background)] text-[var(--color-text-primary)] overflow-hidden font-sans">
      {/* Scroll Reading Progress Indicator */}
      <div className="w-full bg-[var(--color-border)] h-0.5 shrink-0">
        <div
          className="bg-emerald-600 dark:bg-emerald-500 h-full transition-all duration-150"
          style={{ width: `${Math.min(100, Math.max(0, scrollProgress))}%` }}
        />
      </div>

      {/* Header */}
      <header className="px-6 py-4 border-b border-[var(--color-border)] bg-[var(--color-surface)] flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 shrink-0">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-[var(--color-text-primary)]">
            Help & Knowledge Centre
          </h1>
          <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
            Guides for projects, field operations, verification, and platform administration.
          </p>
        </div>

        {/* Search & Actions Strip */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Search Input */}
          <div className="relative w-full sm:w-72">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] pointer-events-none" />
            <input
              type="text"
              value={globalSearch}
              onChange={e => setGlobalSearch(e.target.value)}
              placeholder="Search documentation..."
              aria-label="Search documentation"
              className="w-full h-8 pl-8 pr-7 rounded-md bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-emerald-500 transition-colors"
            />
            {globalSearch && (
              <button
                onClick={() => setGlobalSearch("")}
                aria-label="Clear search"
                className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] p-0.5 cursor-pointer"
              >
                <X size={13} />
              </button>
            )}
          </div>

          {/* Understated Action Controls */}
          <button
            onClick={expandAll}
            className="h-8 px-2.5 rounded-md text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-subtle)] transition-colors cursor-pointer"
          >
            Expand all
          </button>
          <span className="text-[var(--color-border)]">·</span>
          <button
            onClick={collapseAll}
            className="h-8 px-2.5 rounded-md text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-subtle)] transition-colors cursor-pointer"
          >
            Collapse all
          </button>
          <span className="text-[var(--color-border)]">·</span>
          <button
            onClick={handlePrint}
            aria-label="Print documentation"
            title="Print documentation"
            className="h-8 px-2 rounded-md text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-subtle)] flex items-center justify-center transition-colors cursor-pointer"
          >
            <Printer size={14} />
          </button>
        </div>
      </header>

      {/* Main Workspace Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar Navigation */}
        <aside className="w-64 xl:w-72 border-r border-[var(--color-border)] bg-[var(--color-surface)] overflow-y-auto p-3 shrink-0 hidden lg:flex lg:flex-col justify-between space-y-4">
          <div className="space-y-1">
            <div className="text-[11px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider px-2.5 mb-2">
              Documentation Index
            </div>
            <nav className="space-y-0.5">
              {NAV_SECTIONS.map(s => {
                const isActive = activeSectionId === s.id;

                return (
                  <button
                    key={s.id}
                    onClick={() => {
                      setActiveSectionId(s.id);
                      setExpandedSections(prev => ({ ...prev, [s.id]: true }));
                      const el = document.getElementById(`section-${s.id}`);
                      if (el) el.scrollIntoView({ behavior: "smooth" });
                    }}
                    title={s.title}
                    aria-current={isActive ? "true" : undefined}
                    className={`w-full h-8 flex items-center px-2.5 rounded-md text-xs transition-colors text-left truncate cursor-pointer ${
                      isActive
                        ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 font-medium"
                        : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-subtle)] hover:text-[var(--color-text-primary)]"
                    }`}
                  >
                    <span className="truncate">{s.title}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Minimal Human Assistance Block */}
          <div className="pt-3 border-t border-[var(--color-border)] mt-auto px-2.5 space-y-1">
            <p className="text-xs font-medium text-[var(--color-text-primary)]">Need help?</p>
            <p className="text-[11px] text-[var(--color-text-secondary)] leading-normal">
              Contact support at{" "}
              <a href="mailto:support@verifield.io" className="text-emerald-600 dark:text-emerald-400 hover:underline">
                support@verifield.io
              </a>
            </p>
          </div>
        </aside>

        {/* Right Main Content Scrollable Area */}
        <main ref={mainContainerRef} className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8 relative pb-28">
          <div className="max-w-4xl mx-auto space-y-3.5">
            {/* Mobile / Tablet Section Selector */}
            <div className="lg:hidden bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-3">
              <label htmlFor="mobile-section-select" className="block text-[11px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-1.5">
                Jump to Section
              </label>
              <select
                id="mobile-section-select"
                value={activeSectionId}
                onChange={(e) => {
                  const id = e.target.value;
                  setActiveSectionId(id);
                  setExpandedSections(prev => ({ ...prev, [id]: true }));
                  const el = document.getElementById(`section-${id}`);
                  if (el) el.scrollIntoView({ behavior: "smooth" });
                }}
                className="w-full h-8 px-2.5 rounded-md bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
              >
                {NAV_SECTIONS.map(s => (
                  <option key={s.id} value={s.id}>
                    {s.title}
                  </option>
                ))}
              </select>
            </div>

            {/* Search Results */}
            {searchResults && (
              <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4 space-y-3 shadow-xs animate-fade-in">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-medium text-[var(--color-text-primary)]">
                    Search results for &ldquo;{globalSearch}&rdquo;
                  </h3>
                  <button
                    onClick={() => setGlobalSearch("")}
                    className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] cursor-pointer"
                  >
                    Clear
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  {searchResults.matchedSections.length > 0 && (
                    <div className="space-y-1">
                      <p className="text-[11px] font-medium text-[var(--color-text-muted)]">Matching sections ({searchResults.matchedSections.length})</p>
                      <div className="space-y-1">
                        {searchResults.matchedSections.map(s => (
                          <a
                            key={s.id}
                            href={`#section-${s.id}`}
                            onClick={() => {
                              setActiveSectionId(s.id);
                              setExpandedSections(prev => ({ ...prev, [s.id]: true }));
                            }}
                            className="block text-emerald-600 dark:text-emerald-400 hover:underline"
                          >
                            {s.title}
                          </a>
                        ))}
                      </div>
                    </div>
                  )}

                  {searchResults.matchedFaqs.length > 0 && (
                    <div className="space-y-1.5">
                      <p className="text-[11px] font-medium text-[var(--color-text-muted)]">Matching FAQs ({searchResults.matchedFaqs.length})</p>
                      <div className="space-y-1">
                        {searchResults.matchedFaqs.slice(0, 4).map(f => (
                          <p key={f.id} className="text-[var(--color-text-secondary)] text-xs leading-relaxed">
                            <span className="font-medium text-[var(--color-text-primary)]">Q:</span> {f.question}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ========================================================================= */}
            {/* 1. What is VeriField Nexus? */}
            {/* ========================================================================= */}
            <section id="section-introduction" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("introduction")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["introduction"])}
                aria-controls="content-introduction"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("introduction");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    1. What is VeriField Nexus?
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Platform architectural overview, carbon MRV framework, and data flow.
                  </p>
                </div>
                <div className="flex items-center gap-1.5 shrink-0 text-[var(--color-text-muted)]">
                  <button
                    onClick={e => {
                      e.stopPropagation();
                      copySectionLink("introduction");
                    }}
                    className="p-1 rounded hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-subtle)] transition-colors cursor-pointer"
                    title="Copy section link"
                    aria-label="Copy link to Section 1"
                  >
                    <Copy size={13} />
                  </button>
                  <ChevronDown size={16} className={`transition-transform duration-200 ${expandedSections["introduction"] ? "rotate-180" : ""}`} />
                </div>
              </header>

              {expandedSections["introduction"] && (
                <div id="content-introduction" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-4 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                  <p>
                    <strong className="text-[var(--color-text-primary)]">VeriField Nexus</strong> is an enterprise Climate MRV (Measurement, Reporting, and Verification) and Carbon Intelligence OS platform designed to manage the complete end-to-end lifecycle of carbon reduction and removal assets across high-impact climate sectors.
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div className="space-y-1">
                      <h4 className="font-medium text-[var(--color-text-primary)] text-xs">High-Integrity MRV</h4>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                        Replaces manual estimations with direct IoT telemetry, sensor verification, and automated AI trust scoring algorithms.
                      </p>
                    </div>

                    <div className="space-y-1">
                      <h4 className="font-medium text-[var(--color-text-primary)] text-xs">Enterprise Multi-Tenancy</h4>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                        Ensures absolute tenant isolation where organizations manage their projects, assets, and teams securely without cross-tenant leakage.
                      </p>
                    </div>

                    <div className="space-y-1">
                      <h4 className="font-medium text-[var(--color-text-primary)] text-xs">Registry Compliance</h4>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                        Binds approved climate methodologies (AMS-II.G, VM0038, EBC) to generate audited packages ready for Verra & Gold Standard issuance.
                      </p>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-[var(--color-border)] space-y-2">
                    <h4 className="text-xs font-medium text-[var(--color-text-primary)]">Core Architecture Data Flow</h4>
                    <div className="text-xs text-[var(--color-text-secondary)] flex flex-wrap items-center gap-1.5">
                      <span>Hardware Sensors & Mobile</span>
                      <span className="text-[var(--color-text-muted)]">→</span>
                      <span>Telemetry Ingestion</span>
                      <span className="text-[var(--color-text-muted)]">→</span>
                      <span>Methodology Calculator</span>
                      <span className="text-[var(--color-text-muted)]">→</span>
                      <span>Verification Audit</span>
                      <span className="text-[var(--color-text-muted)]">→</span>
                      <span className="text-emerald-700 dark:text-emerald-400 font-medium">Verified Credit Ledger</span>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 2. Platform End-to-End Operational Workflow */}
            {/* ========================================================================= */}
            <section id="section-workflow" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("workflow")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["workflow"])}
                aria-controls="content-workflow"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("workflow");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    2. Platform End-to-End Operational Workflow
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Sequential 10-step sequence from access request to carbon credit issuance.
                  </p>
                </div>
                <div className="flex items-center gap-1.5 shrink-0 text-[var(--color-text-muted)]">
                  <button
                    onClick={e => {
                      e.stopPropagation();
                      copySectionLink("workflow");
                    }}
                    className="p-1 rounded hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-subtle)] transition-colors cursor-pointer"
                    title="Copy section link"
                    aria-label="Copy link to Section 2"
                  >
                    <Copy size={13} />
                  </button>
                  <ChevronDown size={16} className={`transition-transform duration-200 ${expandedSections["workflow"] ? "rotate-180" : ""}`} />
                </div>
              </header>

              {expandedSections["workflow"] && (
                <div id="content-workflow" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-4 text-xs text-[var(--color-text-primary)] animate-fade-in">
                  <p className="text-[var(--color-text-secondary)]">Follow this 10-stage sequence to operationalize climate projects in VeriField Nexus:</p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                    {WORKFLOW_STEPS.map(ws => (
                      <div key={ws.step} className="p-3.5 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] flex flex-col justify-between space-y-2.5">
                        <div>
                          <div className="flex items-baseline justify-between gap-2">
                            <span className="text-xs font-semibold text-[var(--color-text-muted)] tabular-nums">
                              {String(ws.step).padStart(2, "0")}
                            </span>
                            <span className="text-[11px] text-[var(--color-text-muted)]">{ws.actor}</span>
                          </div>
                          <h4 className="text-xs font-semibold text-[var(--color-text-primary)] mt-1">{ws.title}</h4>
                          <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed mt-1">{ws.description}</p>
                        </div>
                        <div className="pt-2 border-t border-[var(--color-border)] text-[11px] text-[var(--color-text-muted)]">
                          <span className="font-medium text-[var(--color-text-secondary)]">Outputs: </span>
                          <span>{ws.keyOutputs.join(" · ")}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 3. Organizations Guide */}
            {/* ========================================================================= */}
            <section id="section-organizations" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("organizations")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["organizations"])}
                aria-controls="content-organizations"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("organizations");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    3. Organizations & Multi-Tenancy Guide
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Tenant scoping, administrator rights, and user onboarding.
                  </p>
                </div>
                <ChevronDown size={16} className={`transition-transform duration-200 text-[var(--color-text-muted)] ${expandedSections["organizations"] ? "rotate-180" : ""}`} />
              </header>

              {expandedSections["organizations"] && (
                <div id="content-organizations" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-3 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                  <p>
                    An <strong className="text-[var(--color-text-primary)]">Organization</strong> is the primary tenant boundary in VeriField Nexus. All climate projects, hardware assets, activity logs, and financial records belong strictly to an organization.
                  </p>
                  <div className="pt-2 space-y-1">
                    <h4 className="font-medium text-[var(--color-text-primary)] text-xs">Tenant Isolation Guarantee</h4>
                    <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                      Users provisioned within Organization A cannot query, view, or modify data belonging to Organization B. All API endpoints and database operations explicitly scope queries by <code className="font-mono text-[var(--color-text-primary)]">organization_id</code>.
                    </p>
                  </div>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 4. Projects Lifecycle Management */}
            {/* ========================================================================= */}
            <section id="section-projects" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("projects")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["projects"])}
                aria-controls="content-projects"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("projects");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    4. Projects Lifecycle Management
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Project statuses, methodology binding, and activity tracking.
                  </p>
                </div>
                <ChevronDown size={16} className={`transition-transform duration-200 text-[var(--color-text-muted)] ${expandedSections["projects"] ? "rotate-180" : ""}`} />
              </header>

              {expandedSections["projects"] && (
                <div id="content-projects" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-3 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                  <p>
                    Projects represent active climate initiatives (e.g. <i>Kano State Solar Mini-Grid Expansion</i> or <i>Rift Valley Biochar Facility</i>). Each project must bind to an approved methodology family.
                  </p>
                  <div className="pt-2">
                    <span className="font-medium text-[var(--color-text-primary)] text-xs block mb-1.5">Lifecycle Sequence:</span>
                    <div className="text-xs text-[var(--color-text-secondary)] flex flex-wrap items-center gap-2">
                      <span>Draft / Initialization</span>
                      <span className="text-[var(--color-text-muted)]">→</span>
                      <span className="text-emerald-700 dark:text-emerald-400 font-medium">Active Operational</span>
                      <span className="text-[var(--color-text-muted)]">→</span>
                      <span>Pending Audit</span>
                      <span className="text-[var(--color-text-muted)]">→</span>
                      <span>Verified & Issued</span>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 5. Assets & Hardware Devices */}
            {/* ========================================================================= */}
            <section id="section-assets" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("assets")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["assets"])}
                aria-controls="content-assets"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("assets");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    5. Assets & Hardware Devices
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Asset registration, IoT meters, chargers, pyrolyzers, and geofencing.
                  </p>
                </div>
                <ChevronDown size={16} className={`transition-transform duration-200 text-[var(--color-text-muted)] ${expandedSections["assets"] ? "rotate-180" : ""}`} />
              </header>

              {expandedSections["assets"] && (
                <div id="content-assets" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-3 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                  <p className="text-[var(--color-text-secondary)]">Assets are physical hardware items registered in the platform:</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="p-3 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-0.5">
                      <span className="font-semibold text-[var(--color-text-primary)] block">Clean Cookstoves</span>
                      <p className="text-xs text-[var(--color-text-secondary)]">Stove monitors, usage sensors, thermal loggers.</p>
                    </div>
                    <div className="p-3 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-0.5">
                      <span className="font-semibold text-[var(--color-text-primary)] block">Solar Arrays</span>
                      <p className="text-xs text-[var(--color-text-secondary)]">Smart kWh meters, inverter gateways, mini-grid hubs.</p>
                    </div>
                    <div className="p-3 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-0.5">
                      <span className="font-semibold text-[var(--color-text-primary)] block">Biochar Batches</span>
                      <p className="text-xs text-[var(--color-text-secondary)]">Pyrolysis kilns, temperature sensors, scale logs.</p>
                    </div>
                    <div className="p-3 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-0.5">
                      <span className="font-semibold text-[var(--color-text-primary)] block">EV Chargers</span>
                      <p className="text-xs text-[var(--color-text-secondary)]">Type 2 / CCS2 chargers, telemetry gateways, battery swappers.</p>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 6. Activities & MRV Telemetry Data */}
            {/* ========================================================================= */}
            <section id="section-activities" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("activities")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["activities"])}
                aria-controls="content-activities"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("activities");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    6. Activities & MRV Telemetry Data
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Recording operational data, ISO timestamps, calculations, and immutability.
                  </p>
                </div>
                <ChevronDown size={16} className={`transition-transform duration-200 text-[var(--color-text-muted)] ${expandedSections["activities"] ? "rotate-180" : ""}`} />
              </header>

              {expandedSections["activities"] && (
                <div id="content-activities" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-3 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                  <p>
                    Activities capture raw usage data from devices or mobile surveys. The methodology engine automatically converts operational activity data (hours cooked, kWh generated, dry tonnes pyrolyzed, charging sessions) into CO₂ equivalent reductions.
                  </p>
                  <p className="text-xs text-[var(--color-text-secondary)] border-l-2 border-amber-500 pl-3 py-0.5">
                    <strong className="text-[var(--color-text-primary)]">Immutability Rule:</strong> Approved or verified activities cannot be modified or deleted. Corrective activity records must be submitted to preserve an unbroken compliance audit log.
                  </p>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 7. Verification & Audit Architecture */}
            {/* ========================================================================= */}
            <section id="section-verification" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("verification")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["verification"])}
                aria-controls="content-verification"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("verification");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    7. Verification & Audit Architecture
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Three-tier verification: Field, Sensor Telemetry, and VVB Audit Workflows.
                  </p>
                </div>
                <ChevronDown size={16} className={`transition-transform duration-200 text-[var(--color-text-muted)] ${expandedSections["verification"] ? "rotate-180" : ""}`} />
              </header>

              {expandedSections["verification"] && (
                <div id="content-verification" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-3 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-1">
                      <h4 className="font-medium text-[var(--color-text-primary)] text-xs">1. Field Verification</h4>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                        Field supervisors inspect installations, upload calibration evidence, and verify beneficiary survey records.
                      </p>
                    </div>
                    <div className="space-y-1">
                      <h4 className="font-medium text-[var(--color-text-primary)] text-xs">2. Automated Telemetry Audit</h4>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                        Trust algorithms score data continuity (0–100). Records below 80 are flagged for operational review.
                      </p>
                    </div>
                    <div className="space-y-1">
                      <h4 className="font-medium text-[var(--color-text-primary)] text-xs">3. VVB Independent Verification</h4>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                        Independent auditors evaluate methodology adherence, evidence packages, and issue formal audit statements.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 8. Analytics & KPI Guide */}
            {/* ========================================================================= */}
            <section id="section-analytics" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("analytics")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["analytics"])}
                aria-controls="content-analytics"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("analytics");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    8. Analytics & KPI Metric Guide
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Dashboard KPIs, charts, and actual vs derived formulas.
                  </p>
                </div>
                <ChevronDown size={16} className={`transition-transform duration-200 text-[var(--color-text-muted)] ${expandedSections["analytics"] ? "rotate-180" : ""}`} />
              </header>

              {expandedSections["analytics"] && (
                <div id="content-analytics" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-3 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                  <p className="text-[var(--color-text-secondary)]">Primary Key Performance Indicators across sector workspaces:</p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="p-3.5 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-1">
                      <span className="font-semibold text-[var(--color-text-primary)] block">Total CO₂ Reduced (Cookstoves)</span>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">Metric tonnes of greenhouse gases avoided by displacing non-renewable wood and charcoal with clean cookstoves.</p>
                    </div>

                    <div className="p-3.5 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-1">
                      <span className="font-semibold text-[var(--color-text-primary)] block">Carbon Removed (Biochar)</span>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">Metric tonnes of stable elemental carbon sequestered through biomass pyrolysis and verified soil application.</p>
                    </div>

                    <div className="p-3.5 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-1">
                      <span className="font-semibold text-[var(--color-text-primary)] block">Energy Displaced (Hybrid Energy)</span>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">Total kWh generated by clean solar and mini-grid arrays minus baseline diesel emissions.</p>
                    </div>

                    <div className="p-3.5 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-1">
                      <span className="font-semibold text-[var(--color-text-primary)] block">Diesel Avoided (EV Mobility)</span>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">Liters of fuel displaced by commercial electric vehicle charging sessions, converted to tCO₂e.</p>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 9. Climate Sector Methodologies */}
            {/* ========================================================================= */}
            <section id="section-methodologies" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("methodologies")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["methodologies"])}
                aria-controls="content-methodologies"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("methodologies");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    9. Climate Sector Methodologies
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Methodology families, licensed sector enforcement, and registry mappings.
                  </p>
                </div>
                <ChevronDown size={16} className={`transition-transform duration-200 text-[var(--color-text-muted)] ${expandedSections["methodologies"] ? "rotate-180" : ""}`} />
              </header>

              {expandedSections["methodologies"] && (
                <div id="content-methodologies" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-3 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="p-3.5 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-1">
                      <h4 className="font-semibold text-[var(--color-text-primary)] text-xs">Clean Cookstoves</h4>
                      <p className="text-[11px] font-mono text-[var(--color-text-muted)]">AMS-I.E · AMS-II.G · VMR0006</p>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                        Quantifies biomass fuel savings and reduced deforestation from cookstove deployments.
                      </p>
                    </div>

                    <div className="p-3.5 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-1">
                      <h4 className="font-semibold text-[var(--color-text-primary)] text-xs">Hybrid Energy</h4>
                      <p className="text-[11px] font-mono text-[var(--color-text-muted)]">AMS-I.F · AMS-I.D · VM0038</p>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                        Quantifies solar generation and diesel generator displacement across mini-grid networks.
                      </p>
                    </div>

                    <div className="p-3.5 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-1">
                      <h4 className="font-semibold text-[var(--color-text-primary)] text-xs">Biochar Carbon Removal</h4>
                      <p className="text-[11px] font-mono text-[var(--color-text-muted)]">EBC Biochar · Verra VM0044</p>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                        Quantifies permanent carbon sequestration in soil and durable materials via biomass pyrolysis.
                      </p>
                    </div>

                    <div className="p-3.5 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-1">
                      <h4 className="font-semibold text-[var(--color-text-primary)] text-xs">EV Mobility</h4>
                      <p className="text-[11px] font-mono text-[var(--color-text-muted)]">Verra VM0038 · AMS-III.C</p>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                        Quantifies tailpipe emissions displaced by commercial electric vehicle charging fleets.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 10. User Roles & Scopes Directory */}
            {/* ========================================================================= */}
            <section id="section-roles" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("roles")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["roles"])}
                aria-controls="content-roles"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("roles");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    10. User Roles & Scopes Directory
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Breakdown of platform roles, permissions, and operational scopes.
                  </p>
                </div>
                <ChevronDown size={16} className={`transition-transform duration-200 text-[var(--color-text-muted)] ${expandedSections["roles"] ? "rotate-180" : ""}`} />
              </header>

              {expandedSections["roles"] && (
                <div id="content-roles" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-3 text-xs text-[var(--color-text-primary)] animate-fade-in">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {ROLE_GUIDES.map(r => (
                      <div key={r.code} className="p-3.5 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-2">
                        <div className="flex items-baseline justify-between gap-2">
                          <h4 className="font-semibold text-[var(--color-text-primary)] text-xs">{r.title}</h4>
                          <span className="text-[11px] text-[var(--color-text-muted)]">{r.scope}</span>
                        </div>
                        <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">{r.purpose}</p>

                        <div className="pt-1.5 border-t border-[var(--color-border)] space-y-1">
                          <div className="text-[11px]">
                            <span className="font-medium text-[var(--color-text-primary)]">Key permissions: </span>
                            <span className="text-[var(--color-text-secondary)] font-mono">{r.permissions.slice(0, 4).join(", ")}</span>
                          </div>
                          <div className="text-[11px]">
                            <span className="font-medium text-[var(--color-text-primary)]">Limitations: </span>
                            <span className="text-[var(--color-text-secondary)]">{r.limitations.join("; ")}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 11. Platform Super Admin Operations Manual */}
            {/* ========================================================================= */}
            <section id="section-super-admin" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("super-admin")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["super-admin"])}
                aria-controls="content-super-admin"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("super-admin");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    11. Platform Super Admin Operations Manual
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Tenant management, access approvals, security logs, and role governance.
                  </p>
                </div>
                <ChevronDown size={16} className={`transition-transform duration-200 text-[var(--color-text-muted)] ${expandedSections["super-admin"] ? "rotate-180" : ""}`} />
              </header>

              {expandedSections["super-admin"] && (
                <div id="content-super-admin" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-3 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                  <p>
                    The Super Admin Console (<code className="font-mono text-[var(--color-text-primary)]">/super-admin</code>) is the governance portal for platform owners. Super Admins manage multi-tenant access, review sector licensing, suspend/reactivate accounts, and audit platform logs.
                  </p>
                  <div className="pt-2 space-y-1">
                    <h4 className="font-medium text-[var(--color-text-primary)] text-xs">Governance Practices</h4>
                    <ul className="list-disc list-inside text-xs text-[var(--color-text-secondary)] space-y-1 leading-relaxed">
                      <li>Verify organization credentials before approving access requests.</li>
                      <li>Licensing an organization for a sector automatically provisions its default project template.</li>
                      <li>Use the Role Permission Console to perform impact analysis prior to modifying permissions.</li>
                    </ul>
                  </div>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 12. Atomic Permissions Matrix */}
            {/* ========================================================================= */}
            <section id="section-permissions" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("permissions")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["permissions"])}
                aria-controls="content-permissions"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("permissions");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    12. Atomic Permissions Matrix
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Granular action permissions, inheritance, and scoping.
                  </p>
                </div>
                <ChevronDown size={16} className={`transition-transform duration-200 text-[var(--color-text-muted)] ${expandedSections["permissions"] ? "rotate-180" : ""}`} />
              </header>

              {expandedSections["permissions"] && (
                <div id="content-permissions" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-3 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                  <p>
                    Permissions in VeriField Nexus are atomic codes in <code className="font-mono text-[var(--color-text-primary)]">category:action</code> format (e.g. <code className="font-mono text-[var(--color-text-primary)]">project:read</code>, <code className="font-mono text-[var(--color-text-primary)]">activity:create</code>, <code className="font-mono text-[var(--color-text-primary)]">activity:verify</code>, <code className="font-mono text-[var(--color-text-primary)]">report:all</code>). Wildcards like <code className="font-mono text-[var(--color-text-primary)]">project:all</code> automatically satisfy specific actions like <code className="font-mono text-[var(--color-text-primary)]">project:read</code>.
                  </p>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 13. Platform Search Engine Guide */}
            {/* ========================================================================= */}
            <section id="section-search" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("search")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["search"])}
                aria-controls="content-search"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("search");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    13. Platform Search Engine Guide
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Searching across projects, assets, users, IDs, and dates.
                  </p>
                </div>
                <ChevronDown size={16} className={`transition-transform duration-200 text-[var(--color-text-muted)] ${expandedSections["search"] ? "rotate-180" : ""}`} />
              </header>

              {expandedSections["search"] && (
                <div id="content-search" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-3 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                  <p className="text-[var(--color-text-secondary)]">
                    Global tables use debounced multi-field search. You can search by UUID, entity name, email address, asset serial number, status, methodology code, or date string. Results apply role priority and alphabetical ordering.
                  </p>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 14. Reports & Export Engine */}
            {/* ========================================================================= */}
            <section id="section-reports" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("reports")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["reports"])}
                aria-controls="content-reports"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("reports");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    14. Reports & Export Engine
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Generating PDF summaries, CSV raw telemetry, and Excel packages.
                  </p>
                </div>
                <ChevronDown size={16} className={`transition-transform duration-200 text-[var(--color-text-muted)] ${expandedSections["reports"] ? "rotate-180" : ""}`} />
              </header>

              {expandedSections["reports"] && (
                <div id="content-reports" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-3 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                  <p className="text-[var(--color-text-secondary)]">
                    Reports can be filtered by date preset, project scope, and verification status. Click &lsquo;Export Report&rsquo; in the Reports module to trigger compilation into PDF, CSV, or Excel formats.
                  </p>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 15. System Notifications & Alerts */}
            {/* ========================================================================= */}
            <section id="section-notifications" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("notifications")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["notifications"])}
                aria-controls="content-notifications"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("notifications");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    15. System Notifications & Alerts
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Approval notifications, verification flags, and security alerts.
                  </p>
                </div>
                <ChevronDown size={16} className={`transition-transform duration-200 text-[var(--color-text-muted)] ${expandedSections["notifications"] ? "rotate-180" : ""}`} />
              </header>

              {expandedSections["notifications"] && (
                <div id="content-notifications" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-3 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                  <p className="text-[var(--color-text-secondary)]">
                    System notifications trigger automatically when an access request is approved, an activity trust score falls below 80, or an account status is updated by an administrator.
                  </p>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 16. Troubleshooting Guide */}
            {/* ========================================================================= */}
            <section id="section-troubleshooting" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("troubleshooting")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["troubleshooting"])}
                aria-controls="content-troubleshooting"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("troubleshooting");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    16. Troubleshooting Guide
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Solutions for common operational and permission questions.
                  </p>
                </div>
                <ChevronDown size={16} className={`transition-transform duration-200 text-[var(--color-text-muted)] ${expandedSections["troubleshooting"] ? "rotate-180" : ""}`} />
              </header>

              {expandedSections["troubleshooting"] && (
                <div id="content-troubleshooting" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-3 text-xs text-[var(--color-text-primary)] animate-fade-in">
                  <div className="space-y-3">
                    <div className="space-y-0.5">
                      <h4 className="font-medium text-[var(--color-text-primary)]">Why can&apos;t I see my project?</h4>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">Ensure your user account is assigned to the project or holds an Organization Admin or Portfolio Manager role within the owning organization.</p>
                    </div>

                    <div className="space-y-0.5">
                      <h4 className="font-medium text-[var(--color-text-primary)]">Why is verification locked?</h4>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">Verification actions require the <code className="font-mono text-[var(--color-text-primary)]">activity:verify</code> permission held by QA Officers, Verifiers, and Auditors.</p>
                    </div>

                    <div className="space-y-0.5">
                      <h4 className="font-medium text-[var(--color-text-primary)]">Why am I seeing &lsquo;Permission Denied&rsquo;?</h4>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">You are attempting an action outside your role scope. Contact your Organization Admin to adjust role assignments.</p>
                    </div>

                    <div className="space-y-0.5">
                      <h4 className="font-medium text-[var(--color-text-primary)]">Why is my dashboard empty?</h4>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">Dashboards filter by licensed sectors and project selectors. Verify that your organization holds an active sector license.</p>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 17. Frequently Asked Questions */}
            {/* ========================================================================= */}
            <section id="section-faq" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("faq")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["faq"])}
                aria-controls="content-faq"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("faq");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    17. Frequently Asked Questions ({filteredFaqs.length})
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Answers grouped by operational category.
                  </p>
                </div>
                <ChevronDown size={16} className={`transition-transform duration-200 text-[var(--color-text-muted)] ${expandedSections["faq"] ? "rotate-180" : ""}`} />
              </header>

              {expandedSections["faq"] && (
                <div id="content-faq" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-4 text-xs text-[var(--color-text-primary)] animate-fade-in">
                  {/* Category Filter */}
                  <div className="flex flex-wrap gap-1.5 border-b border-[var(--color-border)] pb-3">
                    {["ALL", "General", "Access & Auth", "Security & Access", "Organizations & Projects", "Assets & Data", "Verification & Audits", "Methodologies & MRV", "Analytics & Metrics", "Super Admin"].map(cat => (
                      <button
                        key={cat}
                        onClick={() => setFaqCategoryFilter(cat)}
                        className={`px-2.5 py-1 rounded text-xs transition-colors cursor-pointer ${
                          faqCategoryFilter === cat
                            ? "bg-emerald-600 text-white font-medium"
                            : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-subtle)]"
                        }`}
                      >
                        {cat}
                      </button>
                    ))}
                  </div>

                  {/* FAQ Items */}
                  <div className="space-y-3">
                    {filteredFaqs.map(faq => (
                      <div key={faq.id} className="space-y-1 pb-3 border-b border-[var(--color-border)] last:border-b-0">
                        <div className="flex items-baseline justify-between gap-2">
                          <h4 className="font-medium text-[var(--color-text-primary)] text-xs">
                            {faq.question}
                          </h4>
                          <span className="text-[10px] text-[var(--color-text-muted)] shrink-0">
                            {faq.category}
                          </span>
                        </div>
                        <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                          {faq.answer}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 18. Keyboard Shortcuts Directory */}
            {/* ========================================================================= */}
            <section id="section-shortcuts" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("shortcuts")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["shortcuts"])}
                aria-controls="content-shortcuts"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("shortcuts");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    18. Keyboard Shortcuts
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Accelerate navigation with system hotkeys.
                  </p>
                </div>
                <ChevronDown size={16} className={`transition-transform duration-200 text-[var(--color-text-muted)] ${expandedSections["shortcuts"] ? "rotate-180" : ""}`} />
              </header>

              {expandedSections["shortcuts"] && (
                <div id="content-shortcuts" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-3 text-xs text-[var(--color-text-primary)] animate-fade-in">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                    {KEYBOARD_SHORTCUTS.map(sc => (
                      <div key={sc.keyCombo} className="p-2.5 rounded-md bg-[var(--color-surface-subtle)] border border-[var(--color-border)] flex items-center justify-between">
                        <span className="text-xs text-[var(--color-text-secondary)]">{sc.description}</span>
                        <kbd className="px-2 py-0.5 rounded bg-[var(--color-surface)] text-[var(--color-text-primary)] border border-[var(--color-border)] text-[11px] font-mono font-medium">
                          {sc.keyCombo}
                        </kbd>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>

            {/* ========================================================================= */}
            {/* 19. Climate & MRV Glossary */}
            {/* ========================================================================= */}
            <section id="section-glossary" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden transition-colors">
              <header
                onClick={() => toggleSection("glossary")}
                className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-subtle)] transition-colors select-none"
                role="button"
                tabIndex={0}
                aria-expanded={Boolean(expandedSections["glossary"])}
                aria-controls="content-glossary"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleSection("glossary");
                  }
                }}
              >
                <div className="min-w-0 pr-3">
                  <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    19. Climate & MRV Glossary
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Definitions of carbon accounting, IoT telemetry, and methodology terms.
                  </p>
                </div>
                <ChevronDown size={16} className={`transition-transform duration-200 text-[var(--color-text-muted)] ${expandedSections["glossary"] ? "rotate-180" : ""}`} />
              </header>

              {expandedSections["glossary"] && (
                <div id="content-glossary" className="px-5 pb-5 pt-3 border-t border-[var(--color-border)] space-y-3 text-xs text-[var(--color-text-primary)] animate-fade-in">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {GLOSSARY_TERMS.map(g => (
                      <div key={g.term} className="p-3 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-0.5">
                        <div className="flex items-baseline justify-between gap-2">
                          <span className="font-semibold text-[var(--color-text-primary)] text-xs">{g.term}</span>
                          <span className="text-[10px] text-[var(--color-text-muted)]">{g.category}</span>
                        </div>
                        <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">{g.definition}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>
          </div>
        </main>
      </div>

      {/* Floating Back-to-Top Button */}
      {showBackToTop && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-6 right-24 p-2.5 rounded-full bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] shadow-md hover:bg-[var(--color-surface-subtle)] transition-all z-40"
          title="Back to top"
          aria-label="Back to top"
        >
          <ArrowUp size={16} />
        </button>
      )}
    </div>
  );
}
