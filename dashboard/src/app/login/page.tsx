// =============================================================================
// VeriField Nexus — Admin Login Page
// =============================================================================
// Premium glassmorphic login form for admin dashboard access.
// =============================================================================

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck, Mail, Lock, Loader2 } from "lucide-react";
import { loginAdmin, setAuthToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const result = await loginAdmin(email, password);
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
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-600 mx-auto flex items-center justify-center mb-4 shadow-lg shadow-emerald-500/20">
            <ShieldCheck size={28} className="text-[var(--color-text-primary)]" />
          </div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">
            VeriField Nexus
          </h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">Admin Dashboard</p>
        </div>

        {/* Login Card */}
        <div className="bg-[var(--color-card)]/80 backdrop-blur-xl border border-[var(--color-border)] rounded-2xl p-8">
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-6">Sign in</h2>

          {/* Error Message */}
          {error && (
            <div className="mb-4 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
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
        </div>

        <p className="text-center text-slate-600 text-xs mt-6">
          VeriField Nexus v1.0 — Climate Data Verification Platform
        </p>
      </div>
    </div>
  );
}
