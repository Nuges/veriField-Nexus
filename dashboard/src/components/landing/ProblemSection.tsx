"use client";

import { motion } from "framer-motion";
import { AlertCircle, FileStack, LayoutDashboard, Globe } from "lucide-react";

export function ProblemSection() {
  return (
    <section id="platform" className="bg-white text-[#0A0A0A] py-24 lg:py-32 border-b border-zinc-200">
      <div className="max-w-[1280px] mx-auto px-6">
        
        {/* What VeriField Is */}
        <div className="max-w-3xl mb-24">
          <h2 className="text-sm font-semibold tracking-widest text-zinc-500 uppercase mb-4">The Infrastructure Layer</h2>
          <p className="text-3xl md:text-4xl font-medium tracking-tight leading-[1.3] text-zinc-900">
            VeriField is the <span className="font-semibold">Climate Infrastructure Operating System</span>. We provide the digital foundation to deploy, monitor, verify, and manage climate projects across multiple sectors globally.
          </p>
        </div>

        {/* The Problem */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-24">
          <div className="lg:col-span-5">
            <h3 className="text-2xl font-semibold tracking-tight mb-4">The Monitoring Gap</h3>
            <p className="text-zinc-600 leading-relaxed text-lg">
              Climate projects are currently managed with fragmented tools. Manual reporting, disconnected spreadsheets, and costly verification processes make it difficult to scale impact, maintain compliance, and unlock climate finance.
            </p>
          </div>

          <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-12">
            {[
              {
                icon: FileStack,
                title: "Fragmented Data",
                desc: "Critical field data is siloed across mobile forms, emails, and disconnected databases."
              },
              {
                icon: AlertCircle,
                title: "Delayed Verification",
                desc: "Manual audits take months, delaying carbon crediting and financial returns."
              },
              {
                icon: LayoutDashboard,
                title: "Limited Visibility",
                desc: "Investors and regulators lack real-time operational visibility into deployed assets."
              },
              {
                icon: Globe,
                title: "Compliance Complexity",
                desc: "Aligning with global standards (Verra, Gold Standard, Article 6) is a manual, error-prone process."
              }
            ].map((item, idx) => (
              <motion.div 
                key={idx}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: idx * 0.1 }}
                className="flex flex-col gap-3"
              >
                <div className="w-10 h-10 rounded-lg bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-800">
                  <item.icon size={18} strokeWidth={2} />
                </div>
                <h4 className="font-semibold text-zinc-900 tracking-tight">{item.title}</h4>
                <p className="text-zinc-500 text-sm leading-relaxed">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>

      </div>
    </section>
  );
}
