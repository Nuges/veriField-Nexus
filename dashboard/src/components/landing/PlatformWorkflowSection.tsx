"use client";

import { motion } from "framer-motion";
import { Layers, Zap, Search, Shield, BarChart3, Cloud, CheckCircle2 } from "lucide-react";

const WORKFLOW_STEPS = [
  {
    id: "01",
    title: "Deploy Projects",
    desc: "Digitally onboard organizations, projects, physical assets, methodology requirements, and field teams into a unified hierarchy."
  },
  {
    id: "02",
    title: "Monitor Operations",
    desc: "Collect trusted data via offline-first mobile applications capturing GPS, images, telemetry, and documents directly from the field."
  },
  {
    id: "03",
    title: "Verify Impact",
    desc: "Run automated validation engines to detect anomalies, duplicates, missing evidence, and methodology compliance issues."
  },
  {
    id: "04",
    title: "Generate Reports",
    desc: "Export audit-ready monitoring reports, verification packages, registry integrations, and ESG compliance dashboards."
  }
];

export function PlatformWorkflowSection() {
  return (
    <section className="bg-[#FAFAFA] text-[#0A0A0A] py-24 lg:py-32 border-b border-zinc-200 overflow-hidden">
      <div className="max-w-[1280px] mx-auto px-6">
        
        <div className="mb-20 text-center max-w-2xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-6">How the OS Works</h2>
          <p className="text-zinc-500 text-lg">A structured, methodology-driven pipeline connecting physical field deployment to global climate finance.</p>
        </div>

        {/* Workflow Progression */}
        <div className="relative">
          {/* Subtle connecting line */}
          <div className="hidden lg:block absolute top-[28px] left-[10%] right-[10%] h-[1px] bg-zinc-200" />
          
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-12 relative z-10">
            {WORKFLOW_STEPS.map((step, idx) => (
              <motion.div 
                key={step.id}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.5, delay: idx * 0.1 }}
                className="flex flex-col items-center lg:items-start text-center lg:text-left relative"
              >
                <div className="w-14 h-14 rounded-full bg-white border border-zinc-200 flex items-center justify-center font-semibold text-zinc-900 shadow-sm mb-6 z-10">
                  {step.id}
                </div>
                <h3 className="text-xl font-semibold tracking-tight mb-3">{step.title}</h3>
                <p className="text-zinc-500 text-sm leading-relaxed">{step.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Core Modules List */}
        <div className="mt-32 pt-20 border-t border-zinc-200 grid grid-cols-1 lg:grid-cols-12 gap-16">
          <div className="lg:col-span-5">
            <h2 className="text-3xl font-semibold tracking-tight mb-6">Core Infrastructure Modules</h2>
            <p className="text-zinc-500 mb-8 leading-relaxed">
              VeriField provides enterprise-grade infrastructure components built specifically for climate protocols.
            </p>
            <div className="p-1 rounded-2xl bg-white border border-zinc-200 shadow-sm">
              <img 
                src="/dashboard-mock.png" 
                alt="Platform Modules" 
                className="w-full h-auto rounded-xl grayscale-[0.2] contrast-[1.05]" 
              />
            </div>
          </div>

          <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-6">
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
              "Carbon Registry Integration"
            ].map((module, idx) => (
              <div key={idx} className="flex items-center gap-3 border-b border-zinc-100 pb-4">
                <CheckCircle2 size={16} className="text-[#00B47A]" strokeWidth={2.5} />
                <span className="text-sm font-medium text-zinc-800">{module}</span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </section>
  );
}
