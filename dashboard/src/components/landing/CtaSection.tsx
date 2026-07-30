"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";

export function CtaSection() {
  return (
    <section className="bg-[#050505] text-white py-24 lg:py-32 border-b border-zinc-900">
      <div className="max-w-[1000px] mx-auto px-6 text-center">
        <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-6">Ready to digitize your climate infrastructure?</h2>
        <p className="text-zinc-400 text-lg max-w-2xl mx-auto mb-10 leading-relaxed">
          Join governments, developers, and investors using VeriField to deploy, monitor, and verify climate projects at scale.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/signup"
            className="flex items-center justify-center h-12 px-8 rounded-md bg-white text-zinc-900 font-medium text-sm hover:bg-zinc-100 transition-colors w-full sm:w-auto shadow-sm"
          >
            Request Access
          </Link>
          <Link
            href="/login"
            className="flex items-center justify-center h-12 px-8 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-300 font-medium text-sm hover:text-white hover:bg-zinc-800 transition-colors w-full sm:w-auto"
          >
            Sign In
          </Link>
        </div>
      </div>
    </section>
  );
}
