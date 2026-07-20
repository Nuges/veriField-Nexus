"use client";

import { motion } from "framer-motion";
import { Zap, Flame, Leaf, Car, Beaker, TreePine, Droplets, Factory } from "lucide-react";

export function ClimateSectorsSection() {
  return (
    <section id="industries" className="bg-[#050505] text-white py-24 lg:py-32 border-b border-zinc-900">
      <div className="max-w-[1280px] mx-auto px-6">
        
        <div className="mb-20 text-center max-w-2xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-6">Supported Sectors</h2>
          <p className="text-zinc-400 text-lg">
            VeriField is not limited to a single asset class. Our methodology engine is built to support the entire spectrum of global climate infrastructure.
          </p>
        </div>

        {/* Primary Production Sectors */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-20">
          {[
            {
              icon: Flame,
              title: "Clean Cookstoves",
              desc: "Digital MRV for clean cooking programmes. Track distribution, usage, and carbon displacement."
            },
            {
              icon: Zap,
              title: "Hybrid Energy & Solar",
              desc: "Monitoring for solar farms, C&I solar, rooftop systems, mini-grids, and diesel displacement."
            },
            {
              icon: Leaf,
              title: "Biochar",
              desc: "Feedstock tracking, production monitoring, and verification for durable carbon removals."
            },
            {
              icon: Car,
              title: "EV Mobility",
              desc: "Fleet monitoring, EV charging infrastructure utilization, and transportation decarbonisation."
            }
          ].map((sector, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: idx * 0.1 }}
              className="group p-8 rounded-2xl bg-zinc-900/40 border border-zinc-800 hover:border-zinc-700 hover:bg-zinc-800/40 transition-colors"
            >
              <div className="flex items-center gap-4 mb-4">
                <div className="w-12 h-12 rounded-xl bg-[#0A0A0A] border border-zinc-800 flex items-center justify-center shadow-sm">
                  <sector.icon size={22} className="text-zinc-300" strokeWidth={1.5} />
                </div>
                <h3 className="text-xl font-semibold text-white tracking-tight">{sector.title}</h3>
              </div>
              <p className="text-zinc-400 leading-relaxed text-sm">{sector.desc}</p>
            </motion.div>
          ))}
        </div>

        {/* Framework Integrations (Moved here from IntegrationsSection) */}
        <div className="text-center pt-20 border-t border-zinc-900 mt-20">
          <h3 className="text-sm font-semibold tracking-widest text-zinc-500 uppercase mb-12">Supported Frameworks & Integrations</h3>
          <div className="flex flex-wrap justify-center gap-x-12 gap-y-8 items-center opacity-60 grayscale hover:grayscale-0 transition-all duration-500">
            <span className="text-xl font-bold font-serif tracking-tight text-white">Verra</span>
            <span className="text-xl font-bold tracking-tighter text-white">Gold Standard</span>
            <span className="text-xl font-bold font-mono text-white">CDM</span>
            <span className="text-xl font-medium tracking-tight border border-current px-3 py-1 rounded-sm text-white">Article 6</span>
            <span className="text-xl font-bold tracking-widest text-white">ISO 14064</span>
            <span className="text-sm font-medium border-l-2 pl-4 py-1 border-current text-white">Nigeria Climate<br/>Change Act</span>
          </div>
        </div>

      </div>
    </section>
  );
}
