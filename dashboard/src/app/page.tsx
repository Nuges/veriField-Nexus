"use client";

import Link from "next/link";
import { 
  ShieldCheck, 
  ArrowUpRight, 
  CheckCircle, 
  Smartphone, 
  Cpu, 
  Database, 
  LineChart, 
  Zap, 
  Flame, 
  FileCheck2, 
  Globe, 
  Activity, 
  Leaf, 
  BarChart, 
  Server, 
  Car,
  Check,
  Building2,
  TreePine,
  Factory,
  Droplets,
  Wind,
  XCircle
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="bg-black text-white font-sans antialiased selection:bg-[#00B47A]/30 selection:text-white">

      {/* HEADER NAVBAR (Black Background) */}
      <header className="w-full bg-black border-b border-zinc-900 z-45 sticky top-0">
        <div className="max-w-[1400px] mx-auto px-6 md:px-12 h-20 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <img 
              src="/logo-green.png" 
              alt="VeriField" 
              className="h-10 w-auto object-contain"
            />
          </div>

          {/* Desktop Menu */}
          <nav className="hidden xl:flex items-center gap-6 text-[11px] font-bold uppercase tracking-wider text-zinc-400">
            <Link href="/" className="hover:text-white transition-colors">Home</Link>
            <a href="#platform" className="hover:text-white transition-colors">Platform</a>
            <a href="#solutions" className="hover:text-white transition-colors">Solutions</a>
            <a href="#methodologies" className="hover:text-white transition-colors">Methodologies</a>
            <a href="#industries" className="hover:text-white transition-colors">Industries</a>
            <a href="#resources" className="hover:text-white transition-colors">Resources</a>
            <a href="#about" className="hover:text-white transition-colors">About</a>
            <a href="#contact" className="hover:text-white transition-colors">Contact</a>
          </nav>

          {/* Header Action Buttons */}
          <div className="flex items-center gap-4">
            <Link 
              href="/login" 
              className="text-xs font-bold uppercase tracking-wider text-zinc-400 hover:text-white transition-colors"
            >
              Sign In
            </Link>
            <Link 
              href="/signup"
              className="text-xs font-bold uppercase tracking-wider py-2.5 px-5 rounded-full border border-zinc-800 hover:border-[#00B47A] text-white hover:text-[#00B47A] transition-all duration-300"
            >
              Sign Up
            </Link>
          </div>
        </div>
      </header>

      {/* 1. HERO SECTION */}
      <section className="bg-black py-16 lg:py-28 border-b border-zinc-900 overflow-hidden relative">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#00B47A15_0%,_transparent_40%)]" />
        <div className="max-w-[1400px] mx-auto px-6 md:px-12 flex flex-col lg:flex-row items-center gap-12 lg:gap-16 relative z-10">
          
          <div className="flex-1 space-y-8 text-left max-w-2xl">
            <div className="inline-block px-3 py-1 rounded-full border border-[#00B47A]/30 bg-[#00B47A]/10 text-[#00B47A] text-xs font-bold tracking-widest uppercase">
              VeriField
            </div>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight text-white leading-tight font-sans">
              Climate Infrastructure <span className="text-[#00B47A]">Operating System (CIOS)</span>
            </h1>

            <p className="text-zinc-400 text-sm md:text-lg leading-relaxed max-w-xl">
              Digitize the entire lifecycle of climate projects—from field deployment and monitoring to verification, compliance, reporting, and climate finance.
            </p>

            <div className="pt-4 flex flex-wrap gap-4">
              <Link 
                href="/signup"
                className="inline-flex items-center justify-center py-4 px-8 rounded-full bg-[#00B47A] text-black font-bold text-sm tracking-wider uppercase hover:bg-emerald-400 transition-all duration-300 shadow-lg shadow-[#00B47A]/10"
              >
                Sign Up
              </Link>
            </div>
          </div>

          <div className="flex-1 w-full flex items-center justify-center">
            <img 
              src="/dashboard-mock.png" 
              alt="VeriField CIOS Dashboard" 
              className="w-full max-w-[700px] h-auto object-contain select-none pointer-events-none drop-shadow-2xl"
            />
          </div>

        </div>
      </section>

      {/* 2. SUPPORTING COPY */}
      <section className="bg-zinc-950 py-12 border-b border-zinc-900">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <p className="text-sm md:text-lg font-medium text-zinc-300 leading-relaxed">
            VeriField is a modular operating system that enables governments, project developers, enterprises, investors, and carbon market participants to manage climate infrastructure across renewable energy, clean cooking, biochar, electric mobility, and future climate sectors through one unified platform.
          </p>
        </div>
      </section>

      {/* 3. THE CHALLENGE */}
      <section id="about" className="bg-white text-black py-20 lg:py-28 border-b border-zinc-100">
        <div className="max-w-[1400px] mx-auto px-6 md:px-12 flex flex-col lg:flex-row gap-16">
          
          <div className="flex-1 space-y-6">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight leading-tight">
              The Challenge
            </h2>
            <p className="text-zinc-600 text-base md:text-lg leading-relaxed">
              Climate projects are still managed with fragmented systems.<br /><br />
              Manual field reporting, spreadsheets, disconnected software, and costly verification processes make climate projects difficult to monitor, verify, finance, and scale.
            </p>
          </div>

          <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-6">
            {[
              "Fragmented project data",
              "Manual monitoring & reporting",
              "Delayed verification cycles",
              "Compliance complexity",
              "Limited operational visibility",
              "Slow access to carbon and climate finance"
            ].map((item, idx) => (
              <div key={idx} className="flex items-start gap-4 p-4 rounded-2xl bg-zinc-50 border border-zinc-100">
                <div className="w-8 h-8 rounded-full bg-red-500/10 flex items-center justify-center text-red-500 shrink-0 mt-0.5">
                  <XCircle size={16} strokeWidth={2} />
                </div>
                <p className="text-sm font-semibold text-zinc-800 leading-snug">{item}</p>
              </div>
            ))}
          </div>

        </div>
      </section>

      {/* 4. WHAT VERIFIELD DOES */}
      <section id="platform" className="bg-zinc-50 text-black py-20 lg:py-28 border-b border-zinc-200">
        <div className="max-w-[1400px] mx-auto px-6 md:px-12 space-y-16">
          <div className="text-center space-y-4 max-w-3xl mx-auto">
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight">What VeriField Does</h2>
            <p className="text-zinc-600 text-lg">One platform. Every stage of the climate project lifecycle.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6">
            {[
              { title: "Deploy", desc: "Digitally onboard climate projects, assets, teams, and methodologies.", icon: ArrowUpRight },
              { title: "Monitor", desc: "Collect trusted field data through mobile apps, IoT devices, SCADA, GIS, and remote sensing.", icon: Activity },
              { title: "Verify", desc: "Automated QA/QC, digital MRV, evidence validation, and trust scoring.", icon: ShieldCheck },
              { title: "Comply", desc: "Generate audit-ready reports aligned with Verra, Gold Standard, Article 6, and national regulations.", icon: FileCheck2 },
              { title: "Finance", desc: "Prepare projects for carbon markets, ESG reporting, climate finance, and investment.", icon: LineChart }
            ].map((feature, idx) => (
              <div key={idx} className="bg-white border border-zinc-200 p-6 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
                <div className="w-12 h-12 rounded-xl bg-emerald-500/10 text-[#00B47A] flex items-center justify-center mb-6">
                  <feature.icon size={24} />
                </div>
                <h3 className="text-xl font-bold mb-3">{feature.title}</h3>
                <p className="text-sm text-zinc-600 leading-relaxed">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 5. HOW IT WORKS */}
      <section id="how-it-works" className="bg-white text-black py-20 lg:py-28 border-b border-zinc-100">
        <div className="max-w-[1400px] mx-auto px-6 md:px-12 space-y-16">
          <div className="text-center">
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight">How It Works</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-12 relative">
            {[
              {
                step: 1,
                title: "Deploy Projects",
                desc: "Create organizations, projects, assets, methodologies, and field teams.",
                icon: Building2
              },
              {
                step: 2,
                title: "Capture Trusted Data",
                desc: "Offline-first mobile applications capture GPS, images, telemetry, documents, and evidence directly from the field.",
                icon: Smartphone
              },
              {
                step: 3,
                title: "Verify & Monitor",
                desc: "Automated validation engines detect anomalies, duplicates, missing evidence, and compliance issues.",
                icon: ShieldCheck
              },
              {
                step: 4,
                title: "Report & Finance",
                desc: "Generate monitoring reports, verification packages, registry exports, ESG reports, and investor dashboards.",
                icon: BarChart
              }
            ].map((step, idx) => (
              <div key={idx} className="flex gap-6 items-start bg-zinc-50 border border-zinc-200 rounded-3xl p-8 hover:bg-zinc-100 transition-colors">
                <div className="w-16 h-16 rounded-2xl bg-white border border-zinc-200 flex items-center justify-center shrink-0 shadow-sm relative">
                  <step.icon size={28} className="text-[#00B47A]" />
                  <span className="absolute -top-3 -right-3 w-8 h-8 bg-black text-white font-bold rounded-full flex items-center justify-center border-4 border-zinc-50">
                    {step.step}
                  </span>
                </div>
                <div className="space-y-2">
                  <h3 className="text-xl font-bold text-black">{step.title}</h3>
                  <p className="text-zinc-600 leading-relaxed">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 6. CLIMATE SECTORS */}
      <section id="industries" className="bg-black py-20 lg:py-28 border-b border-zinc-900">
        <div className="max-w-[1400px] mx-auto px-6 md:px-12 space-y-16">
          <div className="text-left space-y-4 max-w-3xl">
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-white">Climate Sectors</h2>
            <p className="text-zinc-400 text-lg">Built for today's climate economy.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { title: "Clean Cookstoves", desc: "Digital MRV for clean cooking programmes.", icon: Flame },
              { title: "Hybrid Energy & Solar", desc: "Solar farms, C&I solar, rooftop systems, mini-grids, batteries, diesel displacement, and distributed energy.", icon: Zap },
              { title: "Biochar", desc: "Feedstock tracking, production monitoring, carbon removals, and permanence.", icon: Leaf },
              { title: "Electric Mobility", desc: "Fleet monitoring, EV charging infrastructure, emissions reduction, and transportation decarbonisation.", icon: Car }
            ].map((sector, idx) => (
              <div key={idx} className="bg-zinc-950 border border-zinc-800 p-8 rounded-3xl hover:border-[#00B47A]/50 transition-colors group">
                <div className="w-14 h-14 rounded-2xl bg-zinc-900 flex items-center justify-center text-[#00B47A] mb-6 group-hover:bg-[#00B47A]/10 transition-colors">
                  <sector.icon size={28} />
                </div>
                <h3 className="text-xl font-bold text-white mb-3">{sector.title}</h3>
                <p className="text-sm text-zinc-400 leading-relaxed">{sector.desc}</p>
              </div>
            ))}
          </div>

          <div className="pt-12 border-t border-zinc-800">
            <h4 className="text-sm font-bold uppercase tracking-widest text-[#00B47A] mb-8">Future-ready architecture supporting:</h4>
            <div className="flex flex-wrap gap-4">
              {[
                { title: "Agriculture", icon: Leaf },
                { title: "Forestry", icon: TreePine },
                { title: "Blue Carbon", icon: Droplets },
                { title: "Waste", icon: Database },
                { title: "Industrial Decarbonisation", icon: Factory },
                { title: "Carbon Removal", icon: Wind },
                { title: "Nature-Based Solutions", icon: Globe }
              ].map((item, idx) => (
                <div key={idx} className="flex items-center gap-3 px-5 py-3 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-300">
                  <item.icon size={16} className="text-[#00B47A]" />
                  <span className="text-sm font-semibold">{item.title}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* 7. CORE PLATFORM & Built for Every Stakeholder */}
      <section className="bg-zinc-50 text-black py-20 lg:py-28 border-b border-zinc-200">
        <div className="max-w-[1400px] mx-auto px-6 md:px-12 flex flex-col lg:flex-row gap-16">
          
          <div className="flex-1 space-y-10">
            <div className="space-y-4">
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight">Core Platform</h2>
              <p className="text-zinc-600 text-lg">Built for production-scale climate infrastructure.</p>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {[
                "Offline-first Mobile Apps",
                "Dynamic Methodology Engine",
                "Digital MRV",
                "Compliance Engine",
                "Jurisdiction Framework",
                "Methodology Registry",
                "GIS & Spatial Intelligence",
                "IoT & SCADA Integration",
                "AI-powered Verification",
                "Digital Audit Trail",
                "Climate Reporting",
                "Carbon Registry Integration",
                "ESG Reporting",
                "Climate Finance Dashboard"
              ].map((feature, idx) => (
                <div key={idx} className="flex items-center gap-3 text-sm font-semibold text-zinc-800">
                  <CheckCircle size={18} className="text-[#00B47A]" />
                  {feature}
                </div>
              ))}
            </div>
          </div>

          <div className="flex-1 space-y-10 bg-white p-8 md:p-12 rounded-3xl border border-zinc-200 shadow-sm">
            <div className="space-y-4">
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight">Built for Every Stakeholder</h2>
            </div>
            
            <div className="flex flex-wrap gap-3">
              {[
                "Project Developers",
                "Governments",
                "Regulators",
                "Utilities",
                "Renewable Energy Developers",
                "Carbon Project Developers",
                "Investors",
                "Banks",
                "Verification Bodies",
                "Auditors",
                "NGOs",
                "Development Finance Institutions"
              ].map((stakeholder, idx) => (
                <span key={idx} className="px-4 py-2 rounded-lg bg-zinc-100 border border-zinc-200 text-sm font-semibold text-zinc-800">
                  {stakeholder}
                </span>
              ))}
            </div>
          </div>

        </div>
      </section>

      {/* 8. WHY VERIFIELD & CURRENT STATUS */}
      <section className="bg-white text-black py-20 lg:py-28 border-b border-zinc-100">
        <div className="max-w-[1400px] mx-auto px-6 md:px-12 flex flex-col lg:flex-row gap-16">
          
          <div className="flex-1 space-y-8">
            <div className="space-y-4">
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight">Why VeriField</h2>
              <p className="text-zinc-600 text-lg">One operating system instead of ten disconnected tools.</p>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              {[
                "Offline-first",
                "Modular",
                "Scalable",
                "AI-powered",
                "Registry-ready",
                "Methodology-driven",
                "Built for Africa",
                "Global standards compliant"
              ].map((item, idx) => (
                <div key={idx} className="flex items-center gap-3">
                  <span className="w-6 h-6 rounded-full bg-[#00B47A]/10 text-[#00B47A] flex items-center justify-center shrink-0">
                    <Check size={14} strokeWidth={3} />
                  </span>
                  <span className="font-semibold text-zinc-800">{item}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex-1 space-y-8 bg-zinc-950 p-8 md:p-12 rounded-3xl border border-zinc-900 text-white">
            <div className="space-y-4">
              <h2 className="text-2xl font-bold tracking-tight text-white">Current Status</h2>
              <div className="inline-block px-3 py-1 bg-yellow-500/20 text-yellow-400 text-xs font-bold uppercase tracking-wider rounded-full border border-yellow-500/30">
                Production Pilot
              </div>
            </div>
            
            <div className="space-y-4">
              {[
                "Climate Infrastructure Operating System completed",
                "Four production sectors (Clean Cookstoves, Hybrid Energy & Solar, Biochar, EV Mobility)",
                "Dynamic methodology engine",
                "Digital MRV",
                "Compliance framework",
                "600+ kWp renewable energy deployment pipeline",
                "Preparing for live commercial pilots"
              ].map((status, idx) => (
                <div key={idx} className="flex items-start gap-3">
                  <CheckCircle size={18} className="text-[#00B47A] shrink-0 mt-0.5" />
                  <span className="text-sm text-zinc-300 leading-snug">{status}</span>
                </div>
              ))}
            </div>
          </div>

        </div>
      </section>

      {/* 9. FINAL CTA */}
      <section className="bg-black py-24 border-b border-zinc-900 text-center relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_#00B47A15_0%,_transparent_60%)]" />
        <div className="max-w-3xl mx-auto px-6 relative z-10 space-y-8">
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-white leading-tight">
            Build trusted climate infrastructure.
          </h2>
          <p className="text-xl md:text-2xl text-[#00B47A] font-semibold">
            Monitor. Verify. Comply. Finance.
          </p>
          <div className="pt-8">
            <Link 
              href="/signup"
              className="inline-flex items-center justify-center gap-2 py-4 px-10 rounded-full bg-[#00B47A] text-black font-bold text-sm tracking-wider uppercase hover:bg-emerald-400 transition-all duration-300 shadow-[0_0_30px_rgba(0,180,122,0.3)]"
            >
              Sign Up
            </Link>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="bg-zinc-950 py-16 border-t border-zinc-900">
        <div className="max-w-[1400px] mx-auto px-6 md:px-12 flex flex-col md:flex-row justify-between gap-12">
          
          <div className="space-y-6 max-w-sm">
            <img 
              src="/logo-green.png" 
              alt="VeriField" 
              className="h-8 w-auto object-contain"
            />
            <div className="space-y-2">
              <p className="text-white font-bold tracking-tight text-lg">Climate Infrastructure Operating System</p>
              <p className="text-zinc-400 text-sm leading-relaxed">
                Building the digital infrastructure powering climate projects, carbon markets, and climate finance.
              </p>
            </div>
            <div className="flex items-center gap-2 text-zinc-500 text-sm font-semibold">
              <Globe size={16} />
              Lagos, Nigeria
            </div>
          </div>

          <div className="flex gap-16">
            <div className="space-y-4">
              <h4 className="text-white font-bold uppercase tracking-wider text-xs">Platform</h4>
              <div className="flex flex-col gap-3 text-sm text-zinc-400">
                <Link href="#platform" className="hover:text-[#00B47A] transition-colors">Core Platform</Link>
                <Link href="#how-it-works" className="hover:text-[#00B47A] transition-colors">How It Works</Link>
                <Link href="#industries" className="hover:text-[#00B47A] transition-colors">Climate Sectors</Link>
              </div>
            </div>
            <div className="space-y-4">
              <h4 className="text-white font-bold uppercase tracking-wider text-xs">Company</h4>
              <div className="flex flex-col gap-3 text-sm text-zinc-400">
                <Link href="#about" className="hover:text-[#00B47A] transition-colors">About</Link>
                <Link href="/login" className="hover:text-[#00B47A] transition-colors">Sign In</Link>
                <Link href="/signup" className="hover:text-[#00B47A] transition-colors">Sign Up</Link>
              </div>
            </div>
          </div>

        </div>
        <div className="max-w-[1400px] mx-auto px-6 md:px-12 pt-12 mt-12 border-t border-zinc-900 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-xs text-zinc-600 font-semibold uppercase tracking-wider">
            © {new Date().getFullYear()} VeriField. All rights reserved.
          </p>
        </div>
      </footer>

    </div>
  );
}
