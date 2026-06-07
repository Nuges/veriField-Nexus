// =============================================================================
// VeriField Nexus — Admin Login Page
// =============================================================================
// Premium glassmorphic login form for admin dashboard access.
// =============================================================================

"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ShieldCheck, Mail, Lock, Loader2 } from "lucide-react";
import { loginAdmin, setAuthToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("error") === "unauthorized") {
        setError("Access denied. This system is restricted to verification personnel only.");
      }
    }
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const result = await loginAdmin(email, password);
      if (result.user.role !== "admin" && result.user.role !== "auditor") {
        throw new Error("Access denied. This system is restricted to verification personnel only.");
      }
      setAuthToken(result.access_token);
      localStorage.setItem("vf_token", result.access_token);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Invalid credentials");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--color-background)] flex items-center justify-center px-4">
      {/* Background gradient decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md relative animate-fade-in-up">
        {/* Logo */}
        <div className="text-center mb-8 flex flex-col items-center justify-center">
          <img
            src="/logo-black.png"
            alt="VeriField Nexus"
            className="h-14 w-auto block dark:hidden object-contain mb-2"
          />
          <img
            src="/logo-green.png"
            alt="VeriField Nexus"
            className="h-14 w-auto hidden dark:block object-contain mb-2"
          />
          <p className="text-[var(--color-text-secondary)] text-xs mt-1 font-semibold uppercase tracking-widest opacity-80">
            Admin Dashboard
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-[var(--color-card)]/80 backdrop-blur-xl border border-[var(--color-border)] rounded-2xl p-8">
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-6">Sign in</h2>

          {/* Error Message */}
          {error && (
            <div className={`mb-4 px-4 py-3 rounded-xl text-sm ${
              error.includes("unavailable") || error.includes("Network")
                ? "bg-amber-500/10 border border-amber-500/20 text-amber-400"
                : "bg-red-500/10 border border-red-500/20 text-red-400"
            }`}>
              {error}
              {(error.includes("unavailable") || error.includes("Network")) && (
                <p className="text-xs mt-1 opacity-70">This is a temporary network issue. Please try again.</p>
              )}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            {/* Email */}
            <div>
              <label className="text-sm text-[var(--color-text-secondary)] mb-1.5 block">Email</label>
              <div className="relative">
                <Mail size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@verifield.io"
                  required
                  className="w-full pl-10 pr-4 py-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] 
                    text-[var(--color-text-primary)] placeholder:text-slate-600 text-sm
                    focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/50
                    transition-all duration-200"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="text-sm text-[var(--color-text-secondary)] mb-1.5 block">Password</label>
              <div className="relative">
                <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full pl-10 pr-4 py-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] 
                    text-[var(--color-text-primary)] placeholder:text-slate-600 text-sm
                    focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/50
                    transition-all duration-200"
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 
                text-[var(--color-text-primary)] font-semibold text-sm
                hover:from-emerald-600 hover:to-emerald-700
                disabled:opacity-50 disabled:cursor-not-allowed
                transition-all duration-200 flex items-center justify-center gap-2
                shadow-lg shadow-emerald-500/20"
            >
              {isLoading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign In"
              )}
            </button>
          </form>

          {/* New public onboarding/signup link */}
          <div className="text-center mt-6 pt-4 border-t border-[var(--color-border)]">
            <span className="text-xs text-[var(--color-text-muted)] font-medium">New Carbon Developer or NGO? </span>
            <Link href="/signup" className="text-xs text-emerald-400 font-bold hover:underline">
              Create Organization Account
            </Link>
          </div>
        </div>

        <p className="text-center text-slate-600 text-xs mt-6">
          VeriField Nexus v1.0 — Climate Data Verification Platform
        </p>
      </div>
    </div>
  );
}
