"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

export function HeroSection() {
  return (
    <section className="relative bg-[#050505] text-white pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden border-b border-zinc-900">
      {/* Extremely subtle background grid / technical texture */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(0,180,122,0.05)_0%,_transparent_50%)]" />
      <div 
        className="absolute inset-0 opacity-[0.03]" 
        style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)`,
          backgroundSize: '40px 40px'
        }} 
      />

      <div className="max-w-[1280px] mx-auto px-6 relative z-10 flex flex-col items-center text-center">
        
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-zinc-800 bg-zinc-900/50 mb-8"
        >
          <span className="w-2 h-2 rounded-full bg-[#00B47A] animate-pulse" />
          <span className="text-[11px] font-medium tracking-wide text-zinc-300">VeriField CIOS 2.0 is now available for deployment</span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="text-5xl sm:text-6xl md:text-7xl lg:text-[80px] font-semibold tracking-[-0.04em] leading-[1.05] max-w-5xl"
        >
          Climate Infrastructure <br className="hidden sm:block" />
          <span className="text-zinc-500">Operating System</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="mt-8 text-lg md:text-xl text-zinc-400 max-w-3xl leading-relaxed tracking-tight"
        >
          Deploy, monitor, verify, and manage climate projects from a single enterprise platform. Built for governments, developers, and investors to digitize field operations and access climate finance.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="mt-10 flex flex-col sm:flex-row items-center gap-4"
        >
          <Link 
            href="/signup"
            className="flex items-center gap-2 h-12 px-6 rounded-md bg-white text-black font-medium text-sm hover:bg-zinc-100 transition-colors"
          >
            Request Demo
            <ArrowRight size={16} />
          </Link>
          <Link 
            href="#platform"
            className="flex items-center gap-2 h-12 px-6 rounded-md bg-transparent border border-zinc-800 text-white font-medium text-sm hover:bg-zinc-900 transition-colors"
          >
            Explore Platform
          </Link>
        </motion.div>

        {/* Product Showcase */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="mt-20 w-full max-w-[1100px] mx-auto rounded-xl border border-zinc-800 bg-zinc-950 p-2 shadow-2xl overflow-hidden"
        >
          <img 
            src="/dashboard-mock.png" 
            alt="VeriField Dashboard UI" 
            className="w-full h-auto rounded-lg border border-zinc-900"
          />
        </motion.div>

      </div>
    </section>
  );
}
