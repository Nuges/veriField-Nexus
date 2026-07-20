"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion, useScroll, useTransform } from "framer-motion";
import { cn } from "@/lib/utils/cn";

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
    };
    window.addEventListener("scroll", handleScroll);
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <motion.header
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "fixed top-0 inset-x-0 z-50 transition-all duration-300 border-b",
        scrolled 
          ? "bg-white/80 backdrop-blur-md border-zinc-200 shadow-sm" 
          : "bg-transparent border-transparent"
      )}
    >
      <div className="max-w-[1280px] mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <img 
            src={scrolled ? "/logo-black.png" : "/logo-white.png"} 
            alt="VeriField" 
            className="h-5 w-auto object-contain transition-opacity"
          />
        </Link>

        <nav className="hidden lg:flex items-center gap-8">
          {[
            { label: "Platform", href: "#platform" },
            { label: "Solutions", href: "#solutions" },
            { label: "Technology", href: "#technology" },
            { label: "Industries", href: "#industries" },
            { label: "Resources", href: "#resources" },
            { label: "Company", href: "#company" },
          ].map((item) => (
            <Link 
              key={item.label} 
              href={item.href}
              className={cn(
                "text-[13px] font-medium tracking-tight transition-colors",
                scrolled ? "text-zinc-500 hover:text-zinc-900" : "text-zinc-400 hover:text-white"
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-4">
          <Link 
            href="/login" 
            className={cn(
              "text-[13px] font-medium tracking-tight transition-colors",
              scrolled ? "text-zinc-600 hover:text-zinc-900" : "text-zinc-300 hover:text-white"
            )}
          >
            Sign In
          </Link>
          <Link 
            href="/signup"
            className="text-[13px] font-semibold bg-[#00B47A] text-white px-4 py-2 rounded-md hover:bg-emerald-500 transition-colors shadow-sm"
          >
            Request Access
          </Link>
        </div>
      </div>
    </motion.header>
  );
}
