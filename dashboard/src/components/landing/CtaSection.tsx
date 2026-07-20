"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";

export function CtaSection() {
  return (
    <section className="bg-[#00B47A] text-white py-32 border-b border-[#009E6A]">
      <div className="max-w-[1000px] mx-auto px-6 text-center">
        <h2 className="text-4xl md:text-5xl font-semibold tracking-tight mb-8">Ready to digitize your climate infrastructure?</h2>
        <p className="text-[#E6F8F2] text-xl max-w-2xl mx-auto mb-12 leading-relaxed">
          Join governments, developers, and investors using VeriField to deploy, monitor, and verify climate projects at scale.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link 
            href="/signup"
            className="flex items-center justify-center gap-2 h-14 px-8 rounded-md bg-white text-black font-semibold text-base hover:bg-zinc-100 transition-colors w-full sm:w-auto shadow-lg"
          >
            Request Access
            <ArrowRight size={18} />
          </Link>
          <Link 
            href="/login"
            className="flex items-center justify-center gap-2 h-14 px-8 rounded-md bg-transparent border-2 border-white/30 text-white font-semibold text-base hover:bg-white/10 transition-colors w-full sm:w-auto"
          >
            Sign In
          </Link>
        </div>
      </div>
    </section>
  );
}
