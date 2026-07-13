// =============================================================================
// VeriField Nexus — Premium Landing Page (Exact Replica)
// =============================================================================
// Formatted precisely to match the layout, typography, and contrast flow
// of the uploaded design screenshot. Alternates between premium black
// and crisp white sections with VeriField brand green (#00B47A) accents.
// =============================================================================

"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { 
  ShieldCheck, 
  ArrowUpRight, 
  CheckCircle, 
  XCircle, 
  Smartphone, 
  Cpu, 
  Database, 
  Globe, 
  LineChart, 
  Zap, 
  Flame, 
  Coins, 
  FileCheck2, 
  Server, 
  Wifi, 
  Check, 
  ExternalLink, 
  Clock, 
  MapPin, 
  Activity, 
  Sparkles,
  Loader2,
  Lock,
  Cloud,
  Link as LinkIcon,
  X
} from "lucide-react";
import { createAccessRequest } from "@/lib/api";

interface LogEntry {
  timestamp: string;
  location: string;
  capacity: string;
  type: string;
  status: "success" | "warning";
  trustScore: number;
  auditHash: string;
}

export default function LandingPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    org: "",
    projectType: "",
    region: "Global Operations",
    notes: ""
  });
  
  const [submittingState, setSubmittingState] = useState<"idle" | "submitting" | "success">("idle");
  const [generatedTx, setGeneratedTx] = useState("");

  // Live MRV Log Stream for Purpose-Built Section Map simulation
  const [logs, setLogs] = useState<LogEntry[]>([
    {
      timestamp: "00:44:02",
      location: "Lagos, NG",
      capacity: "120kWp",
      type: "Hybrid Solar",
      status: "success",
      trustScore: 98,
      auditHash: "4xQe9v...Z1"
    },
    {
      timestamp: "00:41:15",
      location: "Abuja, NG",
      capacity: "85kWp",
      type: "Solar Mini-Grid",
      status: "success",
      trustScore: 95,
      auditHash: "7yRp8m...K5"
    }
  ]);

  useEffect(() => {
    const locations = ["Lagos, NG", "Kano, NG", "Ibadan, NG", "Abuja, NG", "Enugu, NG"];
    const capacities = ["45kWp", "80kWp", "150kWp", "60kWp", "200kWp"];
    
    const interval = setInterval(() => {
      const date = new Date();
      const timeStr = date.toTimeString().split(" ")[0];
      const randomLoc = locations[Math.floor(Math.random() * locations.length)];
      const randomCap = capacities[Math.floor(Math.random() * capacities.length)];
      const trustScore = Math.floor(Math.random() * 15) + 85;
      const randHash = Math.random().toString(36).substring(2, 6) + "..." + Math.random().toString(36).substring(2, 5);
      
      const newEntry: LogEntry = {
        timestamp: timeStr,
        location: randomLoc,
        capacity: randomCap,
        type: "Solar Installation",
        status: "success",
        trustScore,
        auditHash: randHash
      };

      setLogs(prev => [newEntry, ...prev.slice(0, 1)]);
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const handleRequestAccess = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.email || !formData.org) return;

    setSubmittingState("submitting");
    try {
      const payload = {
        full_name: formData.name,
        email: formData.email,
        phone: formData.phone || undefined,
        organization_name: formData.org,
        country: formData.region || undefined,
        use_case: `${formData.projectType.toUpperCase()} - ${formData.notes}`,
        sector: formData.projectType
      };
      await createAccessRequest(payload);
      setSubmittingState("success");
    } catch (err: any) {
      console.error(err);
      alert(err.message || "Failed to submit onboarding request. Please verify connection and try again.");
      setSubmittingState("idle");
    }
  };

  const resetForm = () => {
    setFormData({
      name: "",
      email: "",
      phone: "",
      org: "",
      projectType: "",
      region: "Global Operations",
      notes: ""
    });
    setSubmittingState("idle");
    setIsModalOpen(false);
  };

  return (
    <div className="bg-black text-white font-sans antialiased selection:bg-[#00B47A]/30 selection:text-white">

      {/* HEADER NAVBAR (Black Background) */}
      <header className="w-full bg-black border-b border-zinc-900 z-45">
        <div className="max-w-7xl mx-auto px-6 md:px-12 h-20 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <img 
              src="/logo-green.png" 
              alt="VeriField Nexus" 
              className="h-10 w-auto object-contain"
            />
          </div>

          {/* Desktop Menu */}
          <nav className="hidden md:flex items-center gap-8 text-xs font-semibold uppercase tracking-wider text-zinc-400">
            <a href="#about" className="hover:text-white transition-colors">About Us</a>
            <a href="#product" className="hover:text-white transition-colors">Product</a>
            <a href="#how-it-works" className="hover:text-white transition-colors">How It Works</a>
            <a href="#use-cases" className="hover:text-white transition-colors">Use Cases</a>
            <a href="#deployments" className="hover:text-white transition-colors">Deployments</a>
          </nav>

          {/* Header Action Buttons */}
          <div className="flex items-center gap-6">
            <Link 
              href="/login" 
              className="text-xs font-bold uppercase tracking-wider text-zinc-400 hover:text-white transition-colors"
            >
              Sign In
            </Link>
            <button 
              onClick={() => setIsModalOpen(true)}
              className="text-xs font-bold uppercase tracking-wider py-2.5 px-5 rounded-full border border-zinc-800 hover:border-[#00B47A] text-white hover:text-[#00B47A] transition-all duration-300"
            >
              Request Access
            </button>
          </div>
        </div>
      </header>

      {/* 1. HERO SECTION (Black Background) */}
      <section className="bg-black py-12 lg:py-24 border-b border-zinc-900 overflow-hidden">
        <div className="max-w-7xl mx-auto px-6 md:px-12 flex flex-col lg:flex-row items-center gap-12 lg:gap-16">
          
          <div className="flex-1 space-y-8 text-left max-w-xl">
            <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight text-white leading-tight font-sans">
              A digital infrastructure for <span className="text-[#00B47A]">distributed energy systems</span>
            </h1>

            <p className="text-zinc-400 text-sm md:text-base leading-relaxed max-w-lg">
              A modular platform for monitoring, verifying, and managing energy assets across off-grid and grid-connected environments.
            </p>

            <div className="pt-2">
              <button 
                onClick={() => setIsModalOpen(true)}
                className="inline-flex items-center justify-center py-4 px-8 rounded-full bg-[#00B47A] text-black font-bold text-sm tracking-wider uppercase hover:bg-emerald-400 transition-all duration-300 shadow-lg shadow-[#00B47A]/10"
              >
                Request Access
              </button>
            </div>
          </div>

          {/* High-Resolution Mockup Image */}
          <div className="flex-1 w-full flex items-center justify-center">
            <img 
              src="/dashboard-mock.png" 
              alt="VeriField Nexus Dashboard on Laptop and Capture app on iPhone" 
              className="w-full max-w-[620px] h-auto object-contain select-none pointer-events-none"
            />
          </div>

        </div>
      </section>

      {/* GRANT-ALIGNED PLATFORM STATEMENT */}
      <section className="bg-zinc-950 py-8 border-b border-zinc-900">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <p className="text-xs md:text-sm font-semibold tracking-wide text-[#00B47A]/95 leading-relaxed font-mono">
            This platform is designed to support distributed energy ecosystem operators in improving planning, monitoring, and operational efficiency of decentralized energy assets across emerging markets.
          </p>
        </div>
      </section>

      {/* 2. THE VERIFICATION GAP SECTION (White Background) */}
      <section id="about" className="bg-white text-black py-20 lg:py-28 border-b border-zinc-100">
        <div className="max-w-7xl mx-auto px-6 md:px-12 flex flex-col lg:flex-row items-stretch gap-12 lg:gap-16">
          
          {/* Left Side: The Gap */}
          <div className="flex-1 space-y-6 flex flex-col justify-between">
            <div className="space-y-6">
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-black leading-tight">
                The monitoring & verification gap<br />in distributed energy
              </h2>
              <p className="text-zinc-600 text-sm md:text-base max-w-md leading-relaxed">
                Manual reporting, delayed audits, and inconsistent field data create visibility gaps in decentralized energy systems.
              </p>
            </div>

            <ul className="space-y-4 pt-6">
              {[
                "Unverifiable operational claims",
                "Duplicate or ghost installations",
                "Fragmented asset visibility",
                "High cost and slow verification cycles"
              ].map((item, idx) => (
                <li key={idx} className="flex items-center gap-3 text-sm font-semibold text-zinc-800">
                  <span className="w-5 h-5 rounded-full border border-emerald-500/35 flex items-center justify-center text-[#00B47A] shrink-0 select-none">
                    <X size={10} strokeWidth={2.5} />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Middle Line Separator (only desktop) */}
          <div className="hidden lg:flex flex-col items-center justify-center py-4 relative">
            <div className="w-[1px] h-full bg-zinc-200" />
            <div className="w-2.5 h-2.5 rounded-full border-2 border-[#00B47A] bg-white absolute top-1/2 -translate-y-1/2" />
          </div>

          {/* Right Side: A New Standard for Trust (Solution Section) */}
          <div className="flex-1 space-y-8 flex flex-col justify-between">
            <div className="space-y-6">
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-black leading-tight">
                Operations & Verification
              </h2>
              <p className="text-zinc-600 text-sm md:text-base max-w-md leading-relaxed">
                We replace manual processes with an offline-first digital verification layer that delivers operational visibility, structural integrity checks, and high-fidelity reporting.
              </p>
            </div>

            {/* 4 Pillars Grid */}
            <div className="grid grid-cols-2 gap-x-8 gap-y-6 pt-6">
              {[
                { title: "Capture", desc: "Collect field data at the source", icon: Smartphone },
                { title: "Verify", desc: "Automated integrity checks & trust scoring", icon: ShieldCheck },
                { title: "Record", desc: "Cryptographic audit trail in private registry", icon: Database },
                { title: "Visualize", desc: "Real-time dashboard & analytics", icon: LineChart }
              ].map((pillar, idx) => (
                <div key={idx} className="space-y-2.5 text-left group">
                  <div className="w-11 h-11 rounded-xl bg-emerald-500/5 border border-emerald-500/10 flex items-center justify-center text-[#00B47A] shrink-0 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)] group-hover:bg-[#00B47A] group-hover:text-black group-hover:border-transparent transition-all duration-300">
                    <pillar.icon size={18} strokeWidth={1.5} />
                  </div>
                  <h4 className="font-bold text-zinc-900 text-sm">{pillar.title}</h4>
                  <p className="text-zinc-500 text-xs leading-normal">{pillar.desc}</p>
                </div>
              ))}
            </div>
          </div>

        </div>
      </section>

      {/* 3. HOW IT WORKS SECTION (White Background, Light Grey Box) */}
      <section id="how-it-works" className="bg-white text-black py-16 lg:py-24 border-b border-zinc-100">
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          
          <div className="bg-zinc-50 rounded-[28px] p-8 md:p-12 lg:p-16 border border-zinc-100 shadow-sm space-y-12">
            
            <div className="text-center">
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-black">
                How VeriField Nexus Works
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
              {[
                {
                  step: 1,
                  label: "Field Capture",
                  desc: "Field agents capture GPS, photos, timestamps and installation details.",
                  icon: Smartphone
                },
                {
                  step: 2,
                  label: "Verification Engine",
                  desc: "Our system runs automated checks for duplicates, anomalies and completeness.",
                  icon: ShieldCheck
                },
                {
                  step: 3,
                  label: "Audit Trail Security",
                  desc: "Verified records are stored with a private cryptographic signature as a secure audit trail.",
                  icon: Database
                },
                {
                  step: 4,
                  label: "Registry & Analytics",
                  desc: "Live dashboard provides visibility, insights and audit ready reports.",
                  icon: LineChart
                }
              ].map((stepItem, idx) => (
                <div key={idx} className="flex flex-row items-center gap-4 sm:gap-6 bg-[#FAFAFA] border border-zinc-200/90 rounded-[20px] sm:rounded-[24px] p-4 sm:p-6 hover:shadow-md hover:border-zinc-300/60 transition-all duration-300 w-full">
                  <div className="w-20 h-20 sm:w-28 sm:h-28 bg-white border border-zinc-200 rounded-xl sm:rounded-2xl flex flex-col items-center justify-center shrink-0 p-2 sm:p-3 relative shadow-[0_2px_6px_rgba(0,0,0,0.02)]">
                    <stepItem.icon className="text-zinc-800 shrink-0" size={24} strokeWidth={1.5} />
                    <span className="text-[9px] sm:text-xs font-bold text-center mt-1.5 sm:mt-2.5 text-zinc-900 leading-tight">
                      {stepItem.label}
                    </span>
                    <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-[#00B47A] text-black font-mono font-bold text-[10px] flex items-center justify-center shadow-sm">
                      {stepItem.step}
                    </span>
                  </div>
                  <div className="flex-1 text-left">
                    <p className="text-zinc-600 text-xs sm:text-sm leading-relaxed">{stepItem.desc}</p>
                  </div>
                </div>
              ))}
            </div>

          </div>

        </div>
      </section>

      {/* 4. SYSTEM MODULES & APPLICATIONS (White Background) */}
      <section id="product" className="bg-white text-black py-16 lg:py-24 border-b border-zinc-100">
        <div className="max-w-7xl mx-auto px-6 md:px-12 space-y-16">
          
          {/* Modules Row */}
          <div className="space-y-8">
            <div className="text-left border-b border-zinc-100 pb-4">
              <span className="text-xs uppercase tracking-widest text-[#00B47A] font-bold">04 / Core Modules</span>
              <h3 className="text-2xl md:text-3xl font-bold tracking-tight text-black mt-1">
                Core System Components
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[
                { title: "Offline Field Capture", shortLabel: "Field Capture", desc: "Flutter client optimized for remote environments, biometric location lock, and local-first data caching.", icon: Smartphone },
                { title: "DER Operations Engine", shortLabel: "DER Engine", desc: "Algorithmic validation checking duplicate tags, grid coordinate ranges, and trust indexes.", icon: Cpu },
                { title: "Microgrid Operations Dashboard", shortLabel: "Dashboard", desc: "Microgrid visibility, active asset maps, validation timelines, and operational analytics.", icon: LineChart },
                { title: "Cryptographic Audit Trail", shortLabel: "Audit Trail", desc: "Proprietary verification service recording data validation hashes.", icon: Database },
                { title: "Distributed Asset Registry", shortLabel: "Asset Registry", desc: "Secure PostgreSQL registry database indexing coordinates, asset profiles, and telemetry lineages.", icon: Server }
              ].map((module, idx) => (
                <div key={idx} className={`flex flex-row items-center gap-4 sm:gap-6 bg-[#FAFAFA] border border-zinc-200/90 rounded-[20px] sm:rounded-[24px] p-4 sm:p-6 hover:shadow-md hover:border-zinc-300 transition-all duration-300 w-full ${idx === 4 ? "md:col-span-2" : ""}`}>
                  <div className="w-20 h-20 sm:w-28 sm:h-28 bg-white border border-zinc-200 rounded-xl sm:rounded-2xl flex flex-col items-center justify-center shrink-0 p-2 sm:p-3 relative shadow-[0_2px_6px_rgba(0,0,0,0.02)]">
                    <module.icon className="text-zinc-800 shrink-0" size={24} strokeWidth={1.5} />
                    <span className="text-[9px] sm:text-xs font-bold text-center mt-1.5 sm:mt-2.5 text-zinc-900 leading-tight">
                      {module.shortLabel}
                    </span>
                  </div>
                  <div className="flex-1 text-left">
                    <h4 className="font-bold text-zinc-900 text-sm sm:text-base leading-snug mb-1">{module.title}</h4>
                    <p className="text-zinc-500 text-xs sm:text-sm leading-relaxed">{module.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Use Cases Row */}
          <div id="use-cases" className="space-y-8 pt-8">
            <div className="text-left border-b border-zinc-100 pb-4">
              <span className="text-xs uppercase tracking-widest text-[#00B47A] font-bold">05 / Use Cases</span>
              <h3 className="text-2xl md:text-3xl font-bold tracking-tight text-black mt-1">
                Built for Distributed Energy Infrastructure
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[
                { title: "Universal Asset Monitoring", shortLabel: "Assets", desc: "Verify generic asset coordinate distributions and usage profiles to validate performance and emissions reporting readiness.", icon: Flame },
                { title: "Solar & hybrid mini-grids", shortLabel: "Mini-Grids", desc: "Validate asset installation, location coordinates, and operational parameters across off-grid networks.", icon: Zap },
                { title: "Emissions Reporting Readiness", shortLabel: "Readiness", desc: "Ingest cryptographically verified operational data directly to ESG compliance registry adapters.", icon: Coins },
                { title: "Grid Operations Visibility", shortLabel: "Grid Ops", desc: "Streamline field data collection to satisfy utility compliance and planning requirements.", icon: FileCheck2 },
                { title: "Asset Performance Visibility", shortLabel: "Asset Perf", desc: "Give capital providers and operators direct operational visibility into physical asset installation rates.", icon: Globe }
              ].map((uc, idx) => (
                <div key={idx} className={`flex flex-row items-center gap-4 sm:gap-6 bg-[#FAFAFA] border border-zinc-200/90 rounded-[20px] sm:rounded-[24px] p-4 sm:p-6 hover:shadow-md hover:border-zinc-300 transition-all duration-300 w-full ${idx === 4 ? "md:col-span-2" : ""}`}>
                  <div className="w-20 h-20 sm:w-28 sm:h-28 bg-white border border-zinc-200 rounded-xl sm:rounded-2xl flex flex-col items-center justify-center shrink-0 p-2 sm:p-3 relative shadow-[0_2px_6px_rgba(0,0,0,0.02)]">
                    <uc.icon className="text-zinc-800 shrink-0" size={24} strokeWidth={1.5} />
                    <span className="text-[9px] sm:text-xs font-bold text-center mt-1.5 sm:mt-2.5 text-zinc-900 leading-tight">
                      {uc.shortLabel}
                    </span>
                  </div>
                  <div className="flex-1 text-left">
                    <h4 className="font-bold text-zinc-900 text-sm sm:text-base leading-snug mb-1">{uc.title}</h4>
                    <p className="text-zinc-500 text-xs sm:text-sm leading-relaxed">{uc.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>
      </section>

      {/* 5. PURPOSE-BUILT SECTION & TECH STACK (Black Background) */}
      <section id="deployments" className="bg-black py-20 lg:py-28 border-b border-zinc-900">
        <div className="max-w-7xl mx-auto px-6 md:px-12 space-y-16">
          
          <div className="flex flex-col lg:flex-row items-center gap-12 lg:gap-16">
            
            {/* Left Column: Grid */}
            <div className="flex-1 space-y-8 max-w-xl text-left">
              <div className="space-y-4">
                <span className="text-xs uppercase tracking-widest text-[#00B47A] font-bold">06 / DEPLOYMENT ROBUSTNESS</span>
                <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white leading-tight">
                  Purpose-built for<br />real-world deployment
                </h2>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
                {[
                  { title: "Offline First", desc: "Capture in low connectivity environments.", icon: Wifi },
                  { title: "Secure by Design", desc: "End-to-end encryption and hashed data.", icon: Lock },
                  { title: "Real-Time Sync", desc: "Instant submissions when back online.", icon: Zap },
                  { title: "Scalable Infrastructure", desc: "Built to support thousands of installations.", icon: Database }
                ].map((item, idx) => (
                  <div key={idx} className="flex gap-4 items-start group">
                    <div className="w-11 h-11 rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center text-[#00B47A] shrink-0 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)] group-hover:border-[#00B47A]/40 transition-all duration-300">
                      <item.icon size={20} strokeWidth={1.5} />
                    </div>
                    <div className="space-y-1">
                      <h4 className="font-bold text-white text-sm">{item.title}</h4>
                      <p className="text-zinc-400 text-xs leading-relaxed">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right Column: World Map / Simulation Mockup */}
            <div className="flex-1 w-full bg-zinc-950 rounded-2xl border border-zinc-900 p-6 space-y-4 shadow-xl">
              <div className="flex items-center justify-between border-b border-zinc-900 pb-3">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#00B47A] animate-pulse" />
                  <span className="text-[10px] font-mono font-bold text-zinc-400 uppercase">PILOT PREPARATION MAP</span>
                </div>
                <span className="text-[9px] bg-zinc-900 text-[#00B47A] border border-zinc-800 px-2 py-0.5 rounded font-mono font-bold">
                  GLOBAL PIPELINE
                </span>
              </div>

              {/* Map grid mockup */}
              <div className="aspect-[16/9] w-full rounded bg-zinc-900/60 border border-zinc-800/40 relative flex items-center justify-center overflow-hidden">
                {/* Simulated Grid Dots */}
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_#1c2d2f_1px,_transparent_1px)] bg-[size:1rem_1rem] opacity-30" />
                
                {/* Region indicator */}
                <div className="absolute w-24 h-24 rounded-full border border-[#00B47A]/20 bg-[#00B47A]/5 flex items-center justify-center animate-pulse">
                  <MapPin size={24} className="text-[#00B47A]" />
                </div>

                <div className="absolute bottom-4 left-4 right-4 bg-black/80 px-3 py-2 rounded border border-zinc-800/80 font-mono text-[9px] flex justify-between items-center text-zinc-400">
                  <span>LAT: 6.5244° N | LON: 3.3792° E</span>
                  <span className="text-[#00B47A]">Validated Asset</span>
                </div>
              </div>

              {/* Real-time simulation info */}
              {logs.map((log, index) => (
                <div key={index} className="bg-black border border-zinc-900 p-3 rounded font-mono text-[10px] flex justify-between items-center">
                  <div className="space-y-0.5">
                    <span className="text-zinc-500">INGESTION STATUS: VALIDATED</span>
                    <p className="text-white font-bold">{log.location} Mini-Grid Submission</p>
                  </div>
                  <span className="text-[#00B47A] font-bold">Score: {log.trustScore}/100</span>
                </div>
              ))}
            </div>

          </div>

          {/* Infrastructure Tech Stack & System Status Info */}
          <div className="pt-12 border-t border-zinc-900 space-y-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <span className="text-xs uppercase tracking-widest text-[#00B47A] font-bold">07 / Infrastructure Stack</span>
                <p className="text-zinc-400 text-xs mt-1">
                  Mobile Field Ingestion (Flutter) • FastAPI Validation Engine • Real-time Operations Dashboard (Next.js / Web) • Cryptographic Audit Trail • Local-first data capture with offline support
                </p>
              </div>
              
              <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-900 font-mono text-[10px] flex items-center gap-3 shrink-0">
                <span className="w-2 h-2 rounded-full bg-[#00B47A] animate-ping" />
                <span className="text-zinc-400">System Status: <span className="text-white font-bold">Operational</span></span>
              </div>
            </div>

            <p className="text-zinc-500 text-xs leading-relaxed max-w-2xl text-left">
              VeriField Nexus is currently in the pilot preparation stage. Early validation has been completed in controlled environments, and the platform is preparing for field integration with distributed solar mini-grid operators.
            </p>
          </div>

        </div>
      </section>

      {/* 6. STATS BAR SECTION (White Background) */}
      <section className="bg-white text-black py-12 border-b border-zinc-100">
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 md:gap-8">
            
            <div className="flex items-center gap-4 px-4 py-4 rounded-2xl bg-zinc-50 border border-zinc-100/65 shadow-sm hover:border-[#00B47A]/30 transition-all duration-300">
              <div className="w-12 h-12 rounded-xl bg-emerald-500/5 border border-emerald-500/10 flex items-center justify-center text-[#00B47A] shrink-0 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
                <ShieldCheck size={20} strokeWidth={1.5} />
              </div>
              <div className="text-left">
                <div className="text-lg font-bold text-black tracking-tight leading-snug">Pilot-Ready System</div>
                <div className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider mt-1 leading-normal">Validated in controlled environments</div>
              </div>
            </div>

            <div className="flex items-center gap-4 px-4 py-4 rounded-2xl bg-zinc-50 border border-zinc-100/65 shadow-sm hover:border-[#00B47A]/30 transition-all duration-300">
              <div className="w-12 h-12 rounded-xl bg-emerald-500/5 border border-emerald-500/10 flex items-center justify-center text-[#00B47A] shrink-0 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
                <Zap size={20} strokeWidth={1.5} />
              </div>
              <div className="text-left">
                <div className="text-lg font-bold text-black tracking-tight leading-snug">~600 kWp pipeline</div>
                <div className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider mt-1 leading-normal">Distributed solar projects</div>
              </div>
            </div>

            <div className="flex items-center gap-4 px-4 py-4 rounded-2xl bg-zinc-50 border border-zinc-100/65 shadow-sm hover:border-[#00B47A]/30 transition-all duration-300">
              <div className="w-12 h-12 rounded-xl bg-emerald-500/5 border border-emerald-500/10 flex items-center justify-center text-[#00B47A] shrink-0 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
                <Cloud size={20} strokeWidth={1.5} />
              </div>
              <div className="text-left">
                <div className="text-lg font-bold text-black tracking-tight leading-snug">Simulated Estimates</div>
                <div className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider mt-1 leading-normal">Carbon impact model pending validation</div>
              </div>
            </div>

            <div className="flex items-center gap-4 px-4 py-4 rounded-2xl bg-zinc-50 border border-zinc-100/65 shadow-sm hover:border-[#00B47A]/30 transition-all duration-300">
              <div className="w-12 h-12 rounded-xl bg-emerald-500/5 border border-emerald-500/10 flex items-center justify-center text-[#00B47A] shrink-0 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
                <LinkIcon size={20} strokeWidth={1.5} />
              </div>
              <div className="text-left">
                <div className="text-lg font-bold text-black tracking-tight leading-snug">Cryptographic Trail</div>
                <div className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider mt-1 leading-normal">100% private secure audit logging</div>
              </div>
            </div>

          </div>

        </div>
      </section>

      {/* 7. READY TO BUILD / CTA SECTION (Black Background) */}
      <section className="bg-black py-20 lg:py-28 border-b border-zinc-900">
        <div className="max-w-7xl mx-auto px-6 md:px-12 flex flex-col md:flex-row items-center justify-between gap-12">
          
          <div className="space-y-4 max-w-xl text-left">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white leading-tight">
              Ready to build climate<br />infrastructure you can trust?
            </h2>
            <p className="text-zinc-400 text-sm md:text-base">
              Join organizations verifying real impact with VeriField Nexus.
            </p>
          </div>

          <div className="flex flex-col items-center md:items-end gap-3 shrink-0">
            <button 
              onClick={() => setIsModalOpen(true)}
              className="inline-flex items-center justify-center gap-2 py-4 px-8 rounded-full bg-[#00B47A] text-black font-bold text-sm tracking-wider uppercase hover:bg-emerald-400 transition-all duration-300 shadow-lg shadow-[#00B47A]/10"
            >
              Request Access
              <ArrowUpRight size={16} strokeWidth={2.5} />
            </button>
            <span className="text-[11px] text-zinc-500 font-medium">Get early access to the live system.</span>
          </div>

        </div>
      </section>

      {/* FOOTER (Black Background) */}
      <footer className="bg-black py-16 border-t border-zinc-900">
        <div className="max-w-7xl mx-auto px-6 md:px-12 flex flex-col md:flex-row items-center justify-between gap-8">
          
          <div className="flex flex-col items-center md:items-start gap-2">
            <img 
              src="/logo-green.png" 
              alt="VeriField Nexus" 
              className="h-10 w-auto object-contain"
            />
            <span className="text-[10px] text-zinc-500 font-semibold uppercase tracking-widest mt-1">Global Deployments</span>
          </div>

          <div className="text-center">
            <p className="text-xs text-zinc-400 font-medium">Infrastructure for verifiable climate impact.</p>
          </div>

          <div>
            <p className="text-xs text-zinc-500 font-semibold uppercase tracking-wider">
              © 2024 VeriField Nexus. All rights reserved.
            </p>
          </div>

        </div>
      </footer>

      {/* CRYPTOGRAPHIC PARTNER ACCESS MODAL */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
          <div className="relative w-full max-w-lg bg-[#0E1617] border border-[#213233] rounded-2xl shadow-2xl overflow-hidden animate-fade-in-up">
            
            {/* Modal Title bar */}
            <div className="bg-[#141F20] px-6 py-4 border-b border-[#213233] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="text-[#00B47A]" size={18} />
                <span className="font-bold text-sm text-white">Request Partner Credentials</span>
              </div>
              <button 
                onClick={resetForm}
                className="text-[#5F6F6C] hover:text-white p-1.5 hover:bg-[#213233] rounded-lg transition-colors duration-200"
              >
                <X size={14} />
              </button>
            </div>

            {/* Modal Form body */}
            <div className="p-6">
              {submittingState === "idle" && (
                <form onSubmit={handleRequestAccess} className="space-y-4">
                  <div>
                    <label className="text-xs text-[#8E9E9B] font-semibold mb-1 block">Full Name</label>
                    <input 
                      type="text" 
                      required
                      value={formData.name}
                      onChange={e => setFormData(prev => ({...prev, name: e.target.value}))}
                      placeholder="e.g. Segun Adewale"
                      className="w-full px-4 py-2.5 rounded-xl bg-[#090F10] border border-[#213233] text-white placeholder:text-zinc-700 text-xs focus:outline-none focus:border-[#00B47A] transition-colors"
                    />
                  </div>

                  <div>
                    <label className="text-xs text-[#8E9E9B] font-semibold mb-1 block">Business Email</label>
                    <input 
                      type="email" 
                      required
                      value={formData.email}
                      onChange={e => setFormData(prev => ({...prev, email: e.target.value}))}
                      placeholder="e.g. s.adewale@energyco.ng"
                      className="w-full px-4 py-2.5 rounded-xl bg-[#090F10] border border-[#213233] text-white placeholder:text-zinc-700 text-xs focus:outline-none focus:border-[#00B47A] transition-colors"
                    />
                  </div>

                  <div>
                    <label className="text-xs text-[#8E9E9B] font-semibold mb-1 block">Phone Number (Optional)</label>
                    <input 
                      type="text" 
                      value={formData.phone}
                      onChange={e => setFormData(prev => ({...prev, phone: e.target.value}))}
                      placeholder="e.g. +234 803 123 4567"
                      className="w-full px-4 py-2.5 rounded-xl bg-[#090F10] border border-[#213233] text-white placeholder:text-zinc-700 text-xs focus:outline-none focus:border-[#00B47A] transition-colors"
                    />
                  </div>

                  <div>
                    <label className="text-xs text-[#8E9E9B] font-semibold mb-1 block">Organization Name</label>
                    <input 
                      type="text" 
                      required
                      value={formData.org}
                      onChange={e => setFormData(prev => ({...prev, org: e.target.value}))}
                      placeholder="e.g. Clean Energy Africa"
                      className="w-full px-4 py-2.5 rounded-xl bg-[#090F10] border border-[#213233] text-white placeholder:text-zinc-700 text-xs focus:outline-none focus:border-[#00B47A] transition-colors"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs text-[#8E9E9B] font-semibold mb-1 block">Project Sector</label>
                      <input 
                        type="text" 
                        value={formData.projectType}
                        onChange={e => setFormData(prev => ({...prev, projectType: e.target.value}))}
                        placeholder="e.g. Distributed Energy, Carbon Removal"
                        className="w-full px-4 py-2.5 rounded-xl bg-[#090F10] border border-[#213233] text-white placeholder:text-zinc-700 text-xs focus:outline-none focus:border-[#00B47A] transition-colors"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-[#8E9E9B] font-semibold mb-1 block">Operational Region</label>
                      <input 
                        type="text" 
                        value={formData.region}
                        onChange={e => setFormData(prev => ({...prev, region: e.target.value}))}
                        placeholder="e.g. Lagos, Global"
                        className="w-full px-4 py-2.5 rounded-xl bg-[#090F10] border border-[#213233] text-white placeholder:text-zinc-700 text-xs focus:outline-none focus:border-[#00B47A] transition-colors"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-xs text-[#8E9E9B] font-semibold mb-1 block">Additional Notes (Optional)</label>
                    <textarea 
                      rows={3}
                      value={formData.notes}
                      onChange={e => setFormData(prev => ({...prev, notes: e.target.value}))}
                      placeholder="e.g. Integration with 600kWp solar grid project..."
                      className="w-full px-4 py-2.5 rounded-xl bg-[#090F10] border border-[#213233] text-white placeholder:text-zinc-700 text-xs focus:outline-none focus:border-[#00B47A] transition-colors resize-none"
                    />
                  </div>

                  <button 
                    type="submit"
                    className="w-full py-3 rounded-xl bg-[#00B47A] text-black font-bold text-xs uppercase hover:bg-emerald-400 transition-all duration-300"
                  >
                    Submit Access Request
                  </button>
                </form>
              )}

              {/* Progress Flow Animations */}
              {submittingState === "submitting" && (
                <div className="py-12 flex flex-col items-center justify-center space-y-6 text-center">
                  <Loader2 className="animate-spin text-[#00B47A]" size={36} />
                  
                  <div className="space-y-1 font-mono">
                    <p className="text-sm font-bold text-white">Submitting Access Request...</p>
                    <p className="text-[10px] text-[#5F6F6C]">Awaiting gateway confirmation</p>
                  </div>
                </div>
              )}

              {/* Success Screen */}
              {submittingState === "success" && (
                <div className="py-8 text-center space-y-6">
                  <div className="w-16 h-16 rounded-full bg-[#00B47A]/10 border border-[#00B47A] flex items-center justify-center mx-auto animate-pulse">
                    <CheckCircle className="text-[#00B47A]" size={32} />
                  </div>
                  
                  <div className="space-y-2">
                    <h3 className="text-lg font-bold text-white">Onboarding Request Sent</h3>
                    <p className="text-xs text-[#8E9E9B] max-w-sm mx-auto leading-relaxed">
                      Thank you. Your request for partner credentials has been successfully submitted and is now in the review queue.
                    </p>
                  </div>

                  <div className="bg-[#141F20] p-4 rounded-xl border border-[#213233] max-w-sm mx-auto space-y-2 text-left font-mono">
                    <div className="flex justify-between items-center text-[10px]">
                      <span className="text-[#5F6F6C]">EMAIL:</span>
                      <span className="text-white font-bold">{formData.email}</span>
                    </div>
                    <div className="flex justify-between items-center text-[10px]">
                      <span className="text-[#5F6F6C]">ORGANIZATION:</span>
                      <span className="text-white font-bold">{formData.org}</span>
                    </div>
                    <div className="flex justify-between items-center text-[10px]">
                      <span className="text-[#5F6F6C]">REGISTRATION STATUS:</span>
                      <span className="text-yellow-500 font-bold">PENDING_REVIEW</span>
                    </div>
                    <div className="flex justify-between items-center text-[10px]">
                      <span className="text-[#5F6F6C]">REVIEW QUEUE:</span>
                      <span className="text-[#00B47A] font-bold">SUPER_ADMIN</span>
                    </div>
                  </div>

                  <p className="text-[10px] text-[#5F6F6C] max-w-xs mx-auto leading-relaxed">
                    Our compliance team will review your project credentials and issue login credentials via email once approved.
                  </p>

                  <button 
                    onClick={resetForm}
                    className="py-2.5 px-6 rounded-lg bg-[#141F20] hover:bg-[#213233] text-xs text-white border border-[#213233] transition-colors"
                  >
                    Close Window
                  </button>
                </div>
              )}

            </div>
          </div>
        </div>
      )}

    </div>
  );
}
