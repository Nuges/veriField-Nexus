"use client";

import { motion } from "framer-motion";
import { Zap, Flame, Leaf, Car, Beaker, TreePine, Droplets, Factory } from "lucide-react";

export function ClimateSectorsSection() {
  return (
    <section id="industries" className="bg-white text-[#0A0A0A] py-24 lg:py-32 border-b border-zinc-200">
      <div className="max-w-[1280px] mx-auto px-6">
        
        <div className="mb-20 text-center max-w-2xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-6">Cross-Sector Architecture</h2>
          <p className="text-zinc-500 text-lg">
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
              className="group p-8 rounded-2xl bg-zinc-50 border border-zinc-200 hover:border-zinc-300 hover:bg-zinc-100/50 transition-colors"
            >
              <div className="flex items-center gap-4 mb-4">
                <div className="w-12 h-12 rounded-xl bg-white border border-zinc-200 flex items-center justify-center shadow-sm">
                  <sector.icon size={22} className="text-zinc-800" strokeWidth={1.5} />
                </div>
                <h3 className="text-xl font-semibold text-zinc-900 tracking-tight">{sector.title}</h3>
              </div>
              <p className="text-zinc-500 leading-relaxed text-sm">{sector.desc}</p>
            </motion.div>
          ))}
        </div>

        {/* Future Architecture */}
        <div className="pt-16 border-t border-zinc-200 text-center">
          <h4 className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-8">Architecture ready for future integrations</h4>
          <div className="flex flex-wrap justify-center gap-4">
            {[
              { icon: TreePine, label: "Forestry & ARR" },
              { icon: Droplets, label: "Blue Carbon" },
              { icon: Factory, label: "Industrial Decarbonisation" },
              { icon: Beaker, label: "Engineered Carbon Removal" }
            ].map((item, idx) => (
              <div key={idx} className="flex items-center gap-2 px-4 py-2 rounded-full border border-zinc-200 bg-white text-zinc-600 shadow-sm text-sm font-medium">
                <item.icon size={16} className="text-zinc-400" />
                {item.label}
              </div>
            ))}
          </div>
        </div>

      </div>
    </section>
  );
}
