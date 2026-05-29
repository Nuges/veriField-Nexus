// =============================================================================
// VeriField Nexus — Developer Onboarding (Signup) Page
// =============================================================================
// Premium glassmorphic registration form for provisioning new organizations
// and their primary Org Admin accounts in one seamless flow.
// =============================================================================

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ShieldCheck, Mail, Lock, User, Building, Loader2, Sparkles } from "lucide-react";
import { onboardDeveloper, setAuthToken } from "@/lib/api";

export default function SignupPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [orgName, setOrgName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const result = await onboardDeveloper({
        email,
        password,
        full_name: fullName,
        organization_name: orgName,
      });

      // 1. Injected JWT token into client services
      setAuthToken(result.access_token);
      localStorage.setItem("vf_token", result.access_token);
      setSuccess(true);

      // 2. Redirect securely after showing quick success micro-animation
      setTimeout(() => {
        router.push("/dashboard");
      }, 1500);
    } catch (err: any) {
      setError(err.message || "Failed to complete onboarding. Please verify details.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--color-background)] flex items-center justify-center px-4 py-12">
      {/* Background dynamic light gradients */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md relative animate-fade-in-up">
        {/* Branding header */}
        <div className="text-center mb-6 flex flex-col items-center justify-center">
          <img
            src="/logo-black.png"
            alt="VeriField Nexus"
            className="h-12 w-auto block dark:hidden object-contain mb-1"
          />
          <img
            src="/logo-green.png"
            alt="VeriField Nexus"
            className="h-12 w-auto hidden dark:block object-contain mb-1"
          />
          <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[9px] font-extrabold tracking-wider uppercase flex items-center gap-1 mt-1">
            <Sparkles size={9} /> Self-Service Developer Onboarding
          </span>
        </div>

        {/* Signup Container Card */}
        <div className="bg-[var(--color-card)]/80 backdrop-blur-xl border border-[var(--color-border)] rounded-2xl p-8 shadow-2xl">
          <h2 className="text-lg font-bold text-[var(--color-text-primary)] mb-1">Create Organization</h2>
          <p className="text-[var(--color-text-secondary)] text-xs mb-6 font-medium">
            Register your company workspace to generate isolated carbon credit MRV ledgers.
          </p>

          {/* Success overlay */}
          {success ? (
            <div className="text-center py-8 space-y-4 animate-fade-in">
              <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">
                <ShieldCheck size={28} className="animate-pulse" />
              </div>
              <h3 className="text-sm font-bold text-emerald-400 uppercase tracking-wider">Onboarding Complete!</h3>
              <p className="text-xs text-[var(--color-text-secondary)] animate-pulse">
                Provisioning secure tenant databases... Redirecting to dashboard.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSignup} className="space-y-4">
              {/* Error Message banner */}
              {error && (
                <div className="px-4 py-3 rounded-xl text-xs bg-red-500/10 border border-red-500/20 text-red-400">
                  {error}
                </div>
              )}

              {/* Organization Name */}
              <div>
                <label className="text-xs font-bold text-[var(--color-text-secondary)] mb-1.5 block">Organization Name</label>
                <div className="relative">
                  <Building size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                  <input
                    type="text"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder="e.g. Clean Energy Africa"
                    required
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] 
                      text-[var(--color-text-primary)] placeholder:text-slate-600 text-xs
                      focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/50
                      transition-all duration-200"
                  />
                </div>
              </div>

              {/* Full Name */}
              <div>
                <label className="text-xs font-bold text-[var(--color-text-secondary)] mb-1.5 block">Full Name</label>
                <div className="relative">
                  <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Segun Oluwole"
                    required
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] 
                      text-[var(--color-text-primary)] placeholder:text-slate-600 text-xs
                      focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/50
                      transition-all duration-200"
                  />
                </div>
              </div>

              {/* Email Address */}
              <div>
                <label className="text-xs font-bold text-[var(--color-text-secondary)] mb-1.5 block">Email Address</label>
                <div className="relative">
                  <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@cleanenergy.org"
                    required
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] 
                      text-[var(--color-text-primary)] placeholder:text-slate-600 text-xs
                      focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/50
                      transition-all duration-200"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="text-xs font-bold text-[var(--color-text-secondary)] mb-1.5 block">Password</label>
                <div className="relative">
                  <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="•••••••• (Min 8 characters)"
                    required
                    minLength={8}
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] 
                      text-[var(--color-text-primary)] placeholder:text-slate-600 text-xs
                      focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/50
                      transition-all duration-200"
                  />
                </div>
              </div>

              {/* Register Action Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 
                  text-[var(--color-text-primary)] font-bold text-xs uppercase tracking-wide
                  hover:from-emerald-600 hover:to-emerald-700
                  disabled:opacity-50 disabled:cursor-not-allowed
                  transition-all duration-200 flex items-center justify-center gap-2
                  shadow-lg shadow-emerald-500/20 mt-2"
              >
                {isLoading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Onboarding Tenant...
                  </>
                ) : (
                  "Create Tenant Ledger"
                )}
              </button>
            </form>
          )}

          {/* Direct Link to Login */}
          {!success && (
            <div className="text-center mt-6 pt-4 border-t border-[var(--color-border)]">
              <span className="text-xs text-[var(--color-text-muted)] font-medium">Already have an organization workspace? </span>
              <Link href="/login" className="text-xs text-emerald-400 font-bold hover:underline">
                Sign In
              </Link>
            </div>
          )}
        </div>

        <p className="text-center text-slate-600 text-[10px] mt-6">
          VeriField Nexus v1.0 — Gold Standard TPDDTEC Certified MRV System
        </p>
      </div>
    </div>
  );
}
