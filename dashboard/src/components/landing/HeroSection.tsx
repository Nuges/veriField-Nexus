"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

export function HeroSection() {
  return (
    <section className="relative bg-[#03060A] text-white pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden border-b border-zinc-900/50">
      {/* Animated Ambient Glow (Optimized for performance) */}
      <motion.div 
        animate={{ 
          scale: [1, 1.1, 1],
          opacity: [0.1, 0.2, 0.1],
        }}
        transition={{ 
          duration: 8, 
          repeat: Infinity,
          ease: "easeInOut" 
        }}
        className="absolute top-[-20%] left-[50%] -translate-x-1/2 w-[800px] h-[600px] bg-[radial-gradient(circle_at_center,_rgba(0,180,122,0.8)_0%,_transparent_70%)] rounded-full pointer-events-none"
      />
      
      {/* Extremely subtle background grid / technical texture */}
      <div 
        className="absolute inset-0 opacity-[0.02]" 
        style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,1) 1px, transparent 1px)`,
          backgroundSize: '40px 40px'
        }} 
      />

      <div className="max-w-[1280px] mx-auto px-6 relative z-10 flex flex-col items-center text-center">

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
            Request Access
            <ArrowRight size={16} />
          </Link>
        </motion.div>

      </div>
    </section>
  );
}
