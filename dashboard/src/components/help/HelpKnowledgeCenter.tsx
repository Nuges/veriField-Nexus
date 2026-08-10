"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  BookOpen,
  GitMerge,
  Building2,
  Briefcase,
  Radio,
  Activity,
  ShieldCheck,
  BarChart3,
  Layers,
  Users,
  ShieldAlert,
  Key,
  Search,
  FileText,
  Bell,
  AlertTriangle,
  HelpCircle,
  Command,
  FileCode,
  ChevronDown,
  ChevronRight,
  Copy,
  Printer,
  ExternalLink,
  CheckCircle2,
  Info,
  Lock,
  Zap,
  Flame,
  TreeDeciduous,
  Car,
  ArrowUp,
  Sliders,
  Filter,
  Sparkles,
  RefreshCw,
  Mail,
  LifeBuoy
} from "lucide-react";
import { useToast } from "@/components/Toast";
import {
  NAV_SECTIONS,
  WORKFLOW_STEPS,
  ROLE_GUIDES,
  GLOSSARY_TERMS,
  FAQS_LIST,
  KEYBOARD_SHORTCUTS,
  NavSection,
  FAQItem
} from "./HelpData";

const ICON_MAP: Record<string, any> = {
  BookOpen,
  GitMerge,
  Building2,
  Briefcase,
  Radio,
  Activity,
  ShieldCheck,
  BarChart3,
  Layers,
  Users,
  ShieldAlert,
  Key,
  Search,
  FileText,
  Bell,
  AlertTriangle,
  HelpCircle,
  Command,
  FileCode
};

export default function HelpKnowledgeCenter() {
  const toast = useToast();
  const searchParams = useSearchParams();
  const router = useRouter();

  // Search & Navigation States
  const [globalSearch, setGlobalSearch] = useState("");
  const [activeSectionId, setActiveSectionId] = useState<string>("introduction");
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    introduction: true,
    workflow: true
  });
  const [faqCategoryFilter, setFaqCategoryFilter] = useState<string>("ALL");
  const [showBackToTop, setShowBackToTop] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);

  const mainContainerRef = useRef<HTMLDivElement>(null);

  // Initialize deep linking & state memory from URL query or localStorage
  useEffect(() => {
    const sectionParam = searchParams?.get("section");
    if (sectionParam) {
      setActiveSectionId(sectionParam);
      setExpandedSections(prev => ({ ...prev, [sectionParam]: true }));
      setTimeout(() => {
        const el = document.getElementById(`section-${sectionParam}`);
        if (el) el.scrollIntoView({ behavior: "smooth" });
      }, 300);
    } else {
      try {
        const saved = localStorage.getItem("verifield_help_expanded");
        if (saved) {
          setExpandedSections(JSON.parse(saved));
        }
      } catch (e) {}
    }
  }, [searchParams]);

  // Persist expanded accordion states
  const toggleSection = (id: string) => {
    setExpandedSections(prev => {
      const next = { ...prev, [id]: !prev[id] };
      try {
        localStorage.setItem("verifield_help_expanded", JSON.stringify(next));
      } catch (e) {}
      return next;
    });
  };

  const expandAll = () => {
    const allExpanded: Record<string, boolean> = {};
    NAV_SECTIONS.forEach(s => (allExpanded[s.id] = true));
    setExpandedSections(allExpanded);
    toast.info("Expanded All", "All 19 documentation sections expanded.");
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
      const progress = (scrollTop / (scrollHeight - clientHeight)) * 100;
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
      {/* Scroll Reading Progress Bar */}
      <div className="w-full bg-[var(--color-border)] h-1 shrink-0">
        <div
          className="bg-emerald-500 h-full transition-all duration-150"
          style={{ width: `${Math.min(100, Math.max(0, scrollProgress))}%` }}
        />
      </div>

      {/* Header & Global Search Bar */}
      <header className="px-6 py-4 border-b border-[var(--color-border)] bg-[var(--color-surface)] flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 shrink-0 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <BookOpen size={20} />
          </div>
          <div>
            <h1 className="text-lg font-black tracking-wide text-[var(--color-text-primary)]">
              Help & Knowledge Centre
            </h1>
            <p className="text-xs text-[var(--color-text-secondary)]">
              Enterprise documentation, operational workflows, methodology guides, and troubleshooting directory.
            </p>
          </div>
        </div>

        {/* Global Instant Search Input */}
        <div className="relative flex-1 max-w-xl">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400" />
          <input
            type="text"
            value={globalSearch}
            onChange={e => setGlobalSearch(e.target.value)}
            placeholder="Instant search documentation (e.g., Cookstoves, Trust Score, Roles, Assets, Verification)..."
            className="w-full pl-10 pr-10 py-2 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-secondary)] focus:outline-none focus:border-emerald-500 shadow-inner"
          />
          {globalSearch && (
            <button
              onClick={() => setGlobalSearch("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-zinc-400 hover:text-white"
            >
              ✕
            </button>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={expandAll}
            className="px-3 py-1.5 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-emerald-500/40 transition-colors"
          >
            Expand All
          </button>
          <button
            onClick={collapseAll}
            className="px-3 py-1.5 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-emerald-500/40 transition-colors"
          >
            Collapse All
          </button>
          <button
            onClick={handlePrint}
            className="p-2 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
            title="Print Documentation"
          >
            <Printer size={16} />
          </button>
        </div>
      </header>

      {/* Main Workspace Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar Navigation */}
        <aside className="w-72 border-r border-[var(--color-border)] bg-[var(--color-surface)] overflow-y-auto p-4 shrink-0 hidden lg:block space-y-6">
          <div className="space-y-1">
            <p className="text-[10px] font-mono font-bold uppercase text-[var(--color-text-secondary)] tracking-wider px-2 mb-2">
              DOCUMENTATION INDEX ({NAV_SECTIONS.length} SECTIONS)
            </p>
            {NAV_SECTIONS.map(s => {
              const IconComp = ICON_MAP[s.icon] || BookOpen;
              const isActive = activeSectionId === s.id;
              const isExpanded = expandedSections[s.id];

              return (
                <button
                  key={s.id}
                  onClick={() => {
                    setActiveSectionId(s.id);
                    setExpandedSections(prev => ({ ...prev, [s.id]: true }));
                    const el = document.getElementById(`section-${s.id}`);
                    if (el) el.scrollIntoView({ behavior: "smooth" });
                  }}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all text-left group ${
                    isActive
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold"
                      : "text-[var(--color-text-secondary)] hover:bg-[var(--color-background)] hover:text-[var(--color-text-primary)]"
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <IconComp size={15} className={isActive ? "text-emerald-400" : "text-zinc-400 group-hover:text-white"} />
                    <span className="truncate">{s.title}</span>
                  </div>
                  <span className="text-[9px] font-mono text-zinc-500 shrink-0 ml-1">
                    {s.readingTimeMinutes}m
                  </span>
                </button>
              );
            })}
          </div>

          <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20 space-y-2">
            <div className="flex items-center gap-2 text-emerald-400 text-xs font-bold">
              <LifeBuoy size={16} /> Need Human Assistance?
            </div>
            <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
              Our enterprise support team is available 24/7 for operational and deployment guidance.
            </p>
            <a
              href="mailto:support@verifield.io"
              className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-400 hover:underline pt-1"
            >
              <Mail size={12} /> Contact Enterprise Support
            </a>
          </div>
        </aside>

        {/* Right Main Content Scrollable Area */}
        <main ref={mainContainerRef} className="flex-1 overflow-y-auto p-6 md:p-8 space-y-8 relative">
          {/* Search Overlay Results if Searching */}
          {searchResults && (
            <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-2xl p-6 space-y-4 animate-fade-in">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-2">
                  <Sparkles size={16} /> Instant Search Results for "{globalSearch}"
                </h3>
                <button
                  onClick={() => setGlobalSearch("")}
                  className="text-xs text-zinc-400 hover:text-white underline"
                >
                  Clear Search
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                {searchResults.matchedSections.length > 0 && (
                  <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl space-y-2">
                    <p className="font-bold text-white">Matching Documentation Sections:</p>
                    <div className="space-y-1">
                      {searchResults.matchedSections.map(s => (
                        <a
                          key={s.id}
                          href={`#section-${s.id}`}
                          onClick={() => {
                            setActiveSectionId(s.id);
                            setExpandedSections(prev => ({ ...prev, [s.id]: true }));
                          }}
                          className="block text-emerald-400 hover:underline"
                        >
                          • {s.title}
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {searchResults.matchedFaqs.length > 0 && (
                  <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl space-y-2">
                    <p className="font-bold text-white">Matching FAQs ({searchResults.matchedFaqs.length}):</p>
                    <div className="space-y-1">
                      {searchResults.matchedFaqs.slice(0, 5).map(f => (
                        <p key={f.id} className="text-zinc-300">
                          <strong className="text-white">Q:</strong> {f.question}
                        </p>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Breadcrumb Header */}
          <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)] border-b border-[var(--color-border)] pb-3 font-mono">
            <div className="flex items-center gap-2">
              <span>VeriField Nexus</span>
              <span>/</span>
              <span>Documentation</span>
              <span>/</span>
              <span className="text-emerald-400 font-bold">Knowledge Base</span>
            </div>
            <span>Last Updated: August 2026 • Production Edition</span>
          </div>

          {/* 1. What is VeriField Nexus */}
          <section id="section-introduction" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("introduction")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <BookOpen size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">1. What is VeriField Nexus?</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Platform architectural overview, carbon MRV framework, and data flow.</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={e => {
                    e.stopPropagation();
                    copySectionLink("introduction");
                  }}
                  className="p-1.5 rounded-lg bg-[var(--color-background)] text-zinc-400 hover:text-white"
                  title="Copy direct section link"
                >
                  <Copy size={14} />
                </button>
                {expandedSections["introduction"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
              </div>
            </header>

            {expandedSections["introduction"] && (
              <div className="p-6 space-y-6 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                <p>
                  <strong>VeriField Nexus</strong> is an enterprise Climate MRV (Measurement, Reporting, and Verification) and Carbon Intelligence OS platform designed to manage the complete end-to-end lifecycle of carbon reduction and removal assets across high-impact climate sectors.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2">
                    <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs">
                      <Zap size={14} /> High-Integrity MRV
                    </div>
                    <p className="text-[11px] text-[var(--color-text-secondary)]">
                      Replaces manual estimations with direct IoT telemetry, sensor verification, and automated AI trust scoring algorithms.
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2">
                    <div className="flex items-center gap-2 text-blue-400 font-bold text-xs">
                      <Building2 size={14} /> Enterprise Multi-Tenancy
                    </div>
                    <p className="text-[11px] text-[var(--color-text-secondary)]">
                      Ensures absolute tenant isolation where organizations manage their projects, assets, and teams securely without cross-tenant leakage.
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2">
                    <div className="flex items-center gap-2 text-purple-400 font-bold text-xs">
                      <ShieldCheck size={14} /> Registry Compliance
                    </div>
                    <p className="text-[11px] text-[var(--color-text-secondary)]">
                      Binds approved climate methodologies (AMS-II.G, VM0038, EBC) to generate audited packages ready for Verra & Gold Standard issuance.
                    </p>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-3">
                  <h4 className="font-bold text-white uppercase tracking-wider text-[11px]">Core Architecture Data Flow</h4>
                  <div className="flex flex-col md:flex-row items-center justify-between gap-2 font-mono text-[11px] text-zinc-300">
                    <span className="p-2.5 rounded bg-[#141F20] border border-[#213233] text-center w-full">Hardware Sensors & Mobile</span>
                    <span>→</span>
                    <span className="p-2.5 rounded bg-[#141F20] border border-[#213233] text-center w-full">Telemetry Ingestion Engine</span>
                    <span>→</span>
                    <span className="p-2.5 rounded bg-[#141F20] border border-[#213233] text-center w-full">Methodology Calculator</span>
                    <span>→</span>
                    <span className="p-2.5 rounded bg-[#141F20] border border-[#213233] text-center w-full">Verification Audit</span>
                    <span>→</span>
                    <span className="p-2.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-center w-full font-bold">Verified Credit Ledger</span>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* 2. Platform End-to-End Workflow */}
          <section id="section-workflow" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("workflow")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <GitMerge size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">2. Platform End-to-End Operational Workflow</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Visual 10-step sequence from onboarding to credit issuance.</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={e => {
                    e.stopPropagation();
                    copySectionLink("workflow");
                  }}
                  className="p-1.5 rounded-lg bg-[var(--color-background)] text-zinc-400 hover:text-white"
                >
                  <Copy size={14} />
                </button>
                {expandedSections["workflow"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
              </div>
            </header>

            {expandedSections["workflow"] && (
              <div className="p-6 space-y-6 text-xs text-[var(--color-text-primary)] animate-fade-in">
                <p>Follow this 10-stage sequential workflow to operate climate projects in VeriField Nexus:</p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {WORKFLOW_STEPS.map(ws => (
                    <div key={ws.step} className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          STAGE {ws.step} OF 10
                        </span>
                        <span className="text-[10px] font-mono text-zinc-400">{ws.actor}</span>
                      </div>
                      <h4 className="text-xs font-bold text-white">{ws.title}</h4>
                      <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">{ws.description}</p>
                      <div className="pt-2 border-t border-[var(--color-border)] flex flex-wrap gap-1">
                        {ws.keyOutputs.map(out => (
                          <span key={out} className="px-2 py-0.5 rounded text-[9px] font-mono bg-blue-500/10 text-blue-400 border border-blue-500/20">
                            ✓ {out}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* 3. Organizations Guide */}
          <section id="section-organizations" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("organizations")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <Building2 size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">3. Organizations & Multi-Tenancy Guide</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Tenant scoping, administrator rights, and user onboarding.</p>
                </div>
              </div>
              {expandedSections["organizations"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </header>

            {expandedSections["organizations"] && (
              <div className="p-6 space-y-4 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                <p>
                  An <strong>Organization</strong> is the primary tenant boundary in VeriField Nexus. All climate projects, hardware assets, activity logs, and financial records belong strictly to an organization.
                </p>
                <div className="bg-[var(--color-background)] p-4 rounded-xl border border-[var(--color-border)] space-y-2">
                  <h4 className="font-bold text-white text-xs">Tenant Isolation Guarantee:</h4>
                  <p className="text-[11px] text-[var(--color-text-secondary)]">
                    Users provisioned within Organization A can never query, view, or modify data belonging to Organization B. All API endpoints and SQL repositories explicitly scope queries by `organization_id`.
                  </p>
                </div>
              </div>
            )}
          </section>

          {/* 4. Projects Management */}
          <section id="section-projects" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("projects")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <Briefcase size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">4. Projects Lifecycle Management</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Project statuses, methodology binding, and activity tracking.</p>
                </div>
              </div>
              {expandedSections["projects"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </header>

            {expandedSections["projects"] && (
              <div className="p-6 space-y-4 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                <p>
                  Projects represent active climate initiatives (e.g. <i>Kano State Solar Mini-Grid Expansion</i> or <i>Rift Valley Biochar Facility</i>). Each project must bind to an approved methodology family.
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-[10px]">
                  <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 text-center">DRAFT / INITIALIZATION</div>
                  <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-center">ACTIVE OPERATIONAL</div>
                  <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-center">PENDING AUDIT</div>
                  <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400 text-center">VERIFIED & ISSUED</div>
                </div>
              </div>
            )}
          </section>

          {/* 5. Assets & Devices */}
          <section id="section-assets" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("assets")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <Radio size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">5. Assets & Hardware Devices</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Asset registration, IoT meters, chargers, pyrolyzers, and geofencing.</p>
                </div>
              </div>
              {expandedSections["assets"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </header>

            {expandedSections["assets"] && (
              <div className="p-6 space-y-4 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                <p>Assets are physical hardware items registered in the platform:</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-[11px]">
                  <div className="p-3 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)]">
                    <span className="font-bold text-amber-400 block">Clean Cookstoves</span> Stove monitors, usage sensors, thermal loggers.
                  </div>
                  <div className="p-3 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)]">
                    <span className="font-bold text-yellow-400 block">Solar Arrays</span> Smart kWh meters, inverter gateways, mini-grid hubs.
                  </div>
                  <div className="p-3 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)]">
                    <span className="font-bold text-emerald-400 block">Biochar Batches</span> Pyrolysis kilns, temperature sensors, scale logs.
                  </div>
                  <div className="p-3 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)]">
                    <span className="font-bold text-blue-400 block">EV Chargers</span> Type 2 / CCS2 chargers, telemetry gateways, battery swappers.
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* 6. Activities & MRV Data */}
          <section id="section-activities" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("activities")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <Activity size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">6. Activities & MRV Telemetry Data</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Recording operational data, ISO timestamps, calculations, and immutability.</p>
                </div>
              </div>
              {expandedSections["activities"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </header>

            {expandedSections["activities"] && (
              <div className="p-6 space-y-4 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                <p>
                  Activities capture raw usage data from devices or mobile surveys. The methodology engine automatically converts operational activity data (hours cooked, kWh generated, dry tonnes pyrolyzed, charging sessions) into CO₂ equivalent reductions.
                </p>
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300">
                  ⚠️ <strong>Immutability Rule:</strong> Approved or Verified activities cannot be edited or deleted. Corrective activity records must be submitted to preserve an immutable compliance audit log.
                </div>
              </div>
            )}
          </section>

          {/* 7. Verification & Audits */}
          <section id="section-verification" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("verification")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <ShieldCheck size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">7. Verification & Audit Architecture</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">3-tier verification: Field, Sensor Telemetry, and VVB Audit Workflows.</p>
                </div>
              </div>
              {expandedSections["verification"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </header>

            {expandedSections["verification"] && (
              <div className="p-6 space-y-4 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)]">
                    <h4 className="font-bold text-white text-xs mb-1">1. Field Verification</h4>
                    <p className="text-[11px] text-[var(--color-text-secondary)]">Field Supervisors inspect physical installations, upload photo calibration proof, and verify beneficiary surveys.</p>
                  </div>
                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)]">
                    <h4 className="font-bold text-emerald-400 text-xs mb-1">2. AI Telemetry Audit</h4>
                    <p className="text-[11px] text-[var(--color-text-secondary)]">Automated trust algorithms score data continuity (0-100). Scores below 80 are flagged for QA review.</p>
                  </div>
                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)]">
                    <h4 className="font-bold text-purple-400 text-xs mb-1">3. VVB Third-Party Verification</h4>
                    <p className="text-[11px] text-[var(--color-text-secondary)]">Independent auditors review methodology compliance, evidence files, and issue audit certificates.</p>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* 8. Analytics & KPI Guide */}
          <section id="section-analytics" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("analytics")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <BarChart3 size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">8. Analytics & KPI Metric Guide</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Explaining every dashboard KPI, chart, and actual vs derived formula.</p>
                </div>
              </div>
              {expandedSections["analytics"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </header>

            {expandedSections["analytics"] && (
              <div className="p-6 space-y-4 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                <p>Understanding platform Key Performance Indicators across sector dashboards:</p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[11px]">
                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-1">
                    <span className="font-bold text-emerald-400 block">TOTAL CO₂ REDUCED (Cookstoves)</span>
                    <p className="text-zinc-300">Metric tonnes of greenhouse gases avoided by displacing non-renewable wood/charcoal with clean cookstoves.</p>
                  </div>

                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-1">
                    <span className="font-bold text-purple-400 block">CARBON REMOVED (Biochar)</span>
                    <p className="text-zinc-300">Metric tonnes of stable elemental carbon sequestered long-term through biomass pyrolysis and soil application.</p>
                  </div>

                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-1">
                    <span className="font-bold text-yellow-400 block">ENERGY DISPLACED (Hybrid Energy)</span>
                    <p className="text-zinc-300">Total kWh generated by solar/mini-grid arrays minus baseline diesel generator equivalent emissions.</p>
                  </div>

                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-1">
                    <span className="font-bold text-blue-400 block">DIESEL AVOIDED (EV Mobility)</span>
                    <p className="text-zinc-300">Liters of diesel/gasoline fuel avoided by electric vehicle charging sessions, converted to tCO₂e.</p>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* 9. Climate Sector Methodologies */}
          <section id="section-methodologies" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("methodologies")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <Layers size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">9. Climate Sector Methodologies</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Methodology families, licensed sector enforcement, and cross-sector blocks.</p>
                </div>
              </div>
              {expandedSections["methodologies"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </header>

            {expandedSections["methodologies"] && (
              <div className="p-6 space-y-4 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2">
                    <h4 className="font-bold text-amber-400 flex items-center gap-1.5"><Flame size={14} /> Clean Cookstoves (COOKSTOVES)</h4>
                    <p className="text-[11px] text-zinc-300">Bound to AMS-I.E, AMS-II.G, and VMR0006. Quantifies biomass fuel savings and reduced deforestation.</p>
                  </div>

                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2">
                    <h4 className="font-bold text-yellow-400 flex items-center gap-1.5"><Zap size={14} /> Hybrid Energy (HYBRID_ENERGY)</h4>
                    <p className="text-[11px] text-zinc-300">Bound to AMS-I.F, AMS-I.D, and VM0038. Quantifies solar mini-grid generation and diesel generator replacement.</p>
                  </div>

                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2">
                    <h4 className="font-bold text-emerald-400 flex items-center gap-1.5"><TreeDeciduous size={14} /> Biochar Carbon Removal (BIOCHAR)</h4>
                    <p className="text-[11px] text-zinc-300">Bound to EBC Biochar, Verra VM0044. Quantifies permanent carbon sequestration in soil and materials.</p>
                  </div>

                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2">
                    <h4 className="font-bold text-blue-400 flex items-center gap-1.5"><Car size={14} /> EV Mobility (EV_MOBILITY)</h4>
                    <p className="text-[11px] text-zinc-300">Bound to Verra VM0038, AMS-III.C. Quantifies tailpipe emissions avoided by EV charging fleets.</p>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* 10. User Roles & Scopes */}
          <section id="section-roles" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("roles")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <Users size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">10. User Roles & Scopes Directory</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Complete breakdown of all 9 platform roles, permissions, and limitations.</p>
                </div>
              </div>
              {expandedSections["roles"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </header>

            {expandedSections["roles"] && (
              <div className="p-6 space-y-4 text-xs text-[var(--color-text-primary)] animate-fade-in">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {ROLE_GUIDES.map(r => (
                    <div key={r.code} className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-3">
                      <div className="flex items-center justify-between">
                        <h4 className="font-bold text-white text-xs">{r.title}</h4>
                        <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          {r.scope}
                        </span>
                      </div>
                      <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">{r.purpose}</p>

                      <div>
                        <span className="text-[10px] font-bold text-zinc-400 block mb-1">Key Permissions:</span>
                        <div className="flex flex-wrap gap-1">
                          {r.permissions.slice(0, 4).map(p => (
                            <span key={p} className="px-2 py-0.5 rounded text-[9px] font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20">
                              {p}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div>
                        <span className="text-[10px] font-bold text-zinc-400 block mb-1">Limitations:</span>
                        <p className="text-[10px] text-amber-300">{r.limitations.join("; ")}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* 11. Super Admin Manual */}
          <section id="section-super-admin" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("super-admin")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <ShieldAlert size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">11. Platform Super Admin Operations Manual</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Tenant management, access approvals, security logs, and role catalogue governance.</p>
                </div>
              </div>
              {expandedSections["super-admin"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </header>

            {expandedSections["super-admin"] && (
              <div className="p-6 space-y-4 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                <p>
                  The Super Admin Console (`/super-admin`) is the central governance portal for platform owners. Super Admins manage multi-tenant access, review sector licensing, suspend/reactivate accounts, and audit platform activity logs.
                </p>
                <div className="p-4 rounded-xl bg-[#141F20] border border-[#213233] space-y-2">
                  <h4 className="font-bold text-white text-xs">Governance Best Practices:</h4>
                  <ul className="list-disc list-inside text-[11px] text-zinc-300 space-y-1">
                    <li>Always verify organization registration credentials before approving access requests.</li>
                    <li>Licensing an organization for a sector automatically provisions its corresponding default project template.</li>
                    <li>Use the Role Permission Console to perform impact analysis before modifying any custom role permissions.</li>
                  </ul>
                </div>
              </div>
            )}
          </section>

          {/* 12. Permissions Matrix */}
          <section id="section-permissions" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("permissions")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <Key size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">12. Atomic Permissions Matrix</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Granular action permissions, inheritance, and scoping.</p>
                </div>
              </div>
              {expandedSections["permissions"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </header>

            {expandedSections["permissions"] && (
              <div className="p-6 space-y-4 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                <p>
                  Permissions in VeriField Nexus are atomic codes in `category:action` format (e.g. `project:read`, `activity:create`, `activity:verify`, `report:all`). Wildcards like `project:all` automatically satisfy specific actions like `project:read` or `project:update`.
                </p>
              </div>
            )}
          </section>

          {/* 13. Search Engine Guide */}
          <section id="section-search" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("search")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <Search size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">13. Platform Search Engine Guide</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Searching across projects, assets, users, IDs, and dates.</p>
                </div>
              </div>
              {expandedSections["search"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </header>

            {expandedSections["search"] && (
              <div className="p-6 space-y-4 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                <p>
                  Global tables use debounced multi-field search. You can search by UUID, entity name, email address, asset serial number, status, methodology code, or date string. Results apply global role priority and A-Z ordering.
                </p>
              </div>
            )}
          </section>

          {/* 14. Reports & Exports */}
          <section id="section-reports" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("reports")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <FileText size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">14. Reports & Export Engine</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Generating PDF summaries, CSV raw telemetry, and Excel packages.</p>
                </div>
              </div>
              {expandedSections["reports"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </header>

            {expandedSections["reports"] && (
              <div className="p-6 space-y-4 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                <p>
                  Reports can be filtered by date preset, project scope, and verification status. Click 'Export Report' in the Reports module to trigger asynchronous compilation into PDF, CSV, or Excel formats.
                </p>
              </div>
            )}
          </section>

          {/* 15. System Notifications */}
          <section id="section-notifications" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("notifications")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <Bell size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">15. System Notifications & Alerts</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Approval notifications, verification flags, and security alerts.</p>
                </div>
              </div>
              {expandedSections["notifications"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </header>

            {expandedSections["notifications"] && (
              <div className="p-6 space-y-4 text-xs text-[var(--color-text-primary)] leading-relaxed animate-fade-in">
                <p>
                  System notifications trigger automatically when an access request is approved, an activity trust score falls below 80, or an account status is updated by an administrator.
                </p>
              </div>
            )}
          </section>

          {/* 16. Troubleshooting Guide */}
          <section id="section-troubleshooting" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("troubleshooting")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <AlertTriangle size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">16. Troubleshooting Guide</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Solutions for common operational and permission issues.</p>
                </div>
              </div>
              {expandedSections["troubleshooting"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </header>

            {expandedSections["troubleshooting"] && (
              <div className="p-6 space-y-4 text-xs text-[var(--color-text-primary)] animate-fade-in">
                <div className="space-y-3">
                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-1">
                    <h4 className="font-bold text-white">Why can't I see my project?</h4>
                    <p className="text-[11px] text-[var(--color-text-secondary)]">Ensure your user account is assigned to the project or holds an Organization Admin / Portfolio Manager role within the project's owning organization.</p>
                  </div>

                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-1">
                    <h4 className="font-bold text-white">Why is verification locked?</h4>
                    <p className="text-[11px] text-[var(--color-text-secondary)]">Verification options require the `activity:verify` permission held by QA Officers, Verifiers, and Auditors.</p>
                  </div>

                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-1">
                    <h4 className="font-bold text-white">Why am I seeing 'Permission Denied'?</h4>
                    <p className="text-[11px] text-[var(--color-text-secondary)]">You are attempting an action outside your role scope. Contact your Organization Admin to adjust your role assignments.</p>
                  </div>

                  <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-1">
                    <h4 className="font-bold text-white">Why is my dashboard empty?</h4>
                    <p className="text-[11px] text-[var(--color-text-secondary)]">Dashboards automatically filter by licensed sectors and date presets. Click 'Reset Filters' in the dashboard header to restore default views.</p>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* 17. Frequently Asked Questions (50+ FAQs) */}
          <section id="section-faq" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("faq")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <HelpCircle size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">17. Frequently Asked Questions ({filteredFaqs.length} FAQs)</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Comprehensive repository of 50+ hand-written answers grouped by category.</p>
                </div>
              </div>
              {expandedSections["faq"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </header>

            {expandedSections["faq"] && (
              <div className="p-6 space-y-6 text-xs text-[var(--color-text-primary)] animate-fade-in">
                {/* Category Filter Pills */}
                <div className="flex flex-wrap gap-2 border-b border-[var(--color-border)] pb-4">
                  {["ALL", "General", "Access & Auth", "Security & Access", "Organizations & Projects", "Assets & Data", "Verification & Audits", "Methodologies & MRV", "Analytics & Metrics", "Super Admin"].map(cat => (
                    <button
                      key={cat}
                      onClick={() => setFaqCategoryFilter(cat)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        faqCategoryFilter === cat
                          ? "bg-emerald-500 text-black font-bold"
                          : "bg-[var(--color-background)] border border-[var(--color-border)] text-zinc-400 hover:text-white"
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>

                {/* FAQ Accordion Items */}
                <div className="space-y-3">
                  {filteredFaqs.map(faq => (
                    <div key={faq.id} className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2 hover:border-emerald-500/40 transition-colors">
                      <div className="flex items-center justify-between">
                        <h4 className="font-bold text-white text-xs flex items-center gap-2">
                          <HelpCircle size={14} className="text-emerald-400" /> {faq.question}
                        </h4>
                        <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                          {faq.category}
                        </span>
                      </div>
                      <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed pl-5">
                        {faq.answer}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* 18. Keyboard Shortcuts */}
          <section id="section-shortcuts" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("shortcuts")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <Command size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">18. Keyboard Shortcuts Directory</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Accelerate your workflow with system hotkeys.</p>
                </div>
              </div>
              {expandedSections["shortcuts"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </header>

            {expandedSections["shortcuts"] && (
              <div className="p-6 space-y-4 text-xs text-[var(--color-text-primary)] animate-fade-in">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono">
                  {KEYBOARD_SHORTCUTS.map(sc => (
                    <div key={sc.keyCombo} className="p-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] flex items-center justify-between">
                      <span className="text-[11px] text-zinc-300">{sc.description}</span>
                      <kbd className="px-2 py-1 rounded bg-[#141F20] text-emerald-400 border border-[#213233] text-[10px] font-bold">
                        {sc.keyCombo}
                      </kbd>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* 19. Climate & MRV Glossary */}
          <section id="section-glossary" className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-xs">
            <header
              onClick={() => toggleSection("glossary")}
              className="p-5 bg-[var(--color-surface)] border-b border-[var(--color-border)] flex items-center justify-between cursor-pointer hover:bg-[var(--color-background)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <FileCode size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">19. Climate & MRV Glossary</h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Definitions of major carbon, IoT, and methodology terms.</p>
                </div>
              </div>
              {expandedSections["glossary"] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </header>

            {expandedSections["glossary"] && (
              <div className="p-6 space-y-4 text-xs text-[var(--color-text-primary)] animate-fade-in">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {GLOSSARY_TERMS.map(g => (
                    <div key={g.term} className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white text-xs">{g.term}</span>
                        <span className="text-[9px] font-mono text-zinc-500">{g.category}</span>
                      </div>
                      <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">{g.definition}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        </main>
      </div>

      {/* Floating Back-to-Top Button */}
      {showBackToTop && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-6 right-6 p-3 rounded-full bg-emerald-500 text-black shadow-lg hover:bg-emerald-400 transition-all z-50 animate-bounce"
          title="Back to top"
        >
          <ArrowUp size={18} />
        </button>
      )}
    </div>
  );
}
