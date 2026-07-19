"use client";

export function IntegrationsSection() {
  return (
    <section id="technology" className="bg-[#0A0A0A] text-white py-24 lg:py-32 border-b border-zinc-900">
      <div className="max-w-[1280px] mx-auto px-6">
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center mb-24">
          <div>
            <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-6">Methodology & Compliance Engine</h2>
            <p className="text-zinc-400 text-lg leading-relaxed mb-8">
              VeriField acts as a protocol-agnostic translation layer. We take complex, PDF-based climate methodologies and convert them into strict digital logic, automated data validation rules, and mandatory field capture workflows.
            </p>
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-4 border border-zinc-800 bg-zinc-900/50 p-4 rounded-xl">
                <div className="w-2 h-2 rounded-full bg-[#00B47A]" />
                <span className="text-sm font-medium text-zinc-300">Automated Emissions Factor Calculations</span>
              </div>
              <div className="flex items-center gap-4 border border-zinc-800 bg-zinc-900/50 p-4 rounded-xl">
                <div className="w-2 h-2 rounded-full bg-[#00B47A]" />
                <span className="text-sm font-medium text-zinc-300">Double-Counting Prevention (Geospatial)</span>
              </div>
              <div className="flex items-center gap-4 border border-zinc-800 bg-zinc-900/50 p-4 rounded-xl">
                <div className="w-2 h-2 rounded-full bg-[#00B47A]" />
                <span className="text-sm font-medium text-zinc-300">Cryptographic Evidence Hashing</span>
              </div>
            </div>
          </div>
          
          {/* Conceptual Tech Diagram */}
          <div className="relative border border-zinc-800 bg-zinc-950 rounded-2xl p-8 aspect-square flex flex-col justify-between">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(0,180,122,0.1)_0%,_transparent_60%)]" />
            
            <div className="relative z-10 grid grid-cols-2 gap-4 flex-1">
              <div className="border border-zinc-800 bg-[#050505] rounded-xl flex items-center justify-center text-zinc-500 font-mono text-sm shadow-xl">Data Input</div>
              <div className="border border-[#00B47A]/30 bg-[#00B47A]/5 rounded-xl flex items-center justify-center text-[#00B47A] font-mono text-sm shadow-xl relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[#00B47A] to-transparent animate-pulse" />
                Validation Engine
              </div>
              <div className="border border-zinc-800 bg-[#050505] rounded-xl flex items-center justify-center text-zinc-500 font-mono text-sm shadow-xl">Compliance DB</div>
              <div className="border border-zinc-800 bg-[#050505] rounded-xl flex items-center justify-center text-zinc-500 font-mono text-sm shadow-xl">Registry API</div>
            </div>
          </div>
        </div>

        {/* Framework Integrations */}
        <div className="text-center pt-20 border-t border-zinc-900">
          <h3 className="text-sm font-semibold tracking-widest text-zinc-500 uppercase mb-12">Supported Frameworks & Integrations</h3>
          <div className="flex flex-wrap justify-center gap-x-12 gap-y-8 items-center opacity-60 grayscale hover:grayscale-0 transition-all duration-500">
            {/* We use text representations in place of logos to maintain a clean enterprise look */}
            <span className="text-xl font-bold font-serif tracking-tight">Verra</span>
            <span className="text-xl font-bold tracking-tighter">Gold Standard</span>
            <span className="text-xl font-bold font-mono">CDM</span>
            <span className="text-xl font-medium tracking-tight border border-current px-3 py-1 rounded-sm">Article 6</span>
            <span className="text-xl font-bold tracking-widest">ISO 14064</span>
            <span className="text-sm font-medium border-l-2 pl-4 py-1 border-current">Nigeria Climate<br/>Change Act</span>
          </div>
        </div>

      </div>
    </section>
  );
}
