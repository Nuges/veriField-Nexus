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
import { loginAdmin, setAuthToken, changePassword } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  // Forced password change states
  const [requiresReset, setRequiresReset] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [tempToken, setTempToken] = useState("");
  const [isResetting, setIsResetting] = useState(false);
  const [resetError, setResetError] = useState("");
  const [tempUserRole, setTempUserRole] = useState("");
  const [tempUserRedirect, setTempUserRedirect] = useState("");

  useEffect(() => {
    if (typeof window !== "undefined") {
      // Clear any stale auth state — user is on the login page, start fresh
      localStorage.removeItem("vf_token");
      setAuthToken(null);
      
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
      
      // Parse redirect parameter dynamically from the search query
      const params = new URLSearchParams(window.location.search);
      let targetRedirect = params.get("redirect") || "/dashboard";
      if (result.user.role === "SUPER_ADMIN") {
        targetRedirect = "/super-admin";
      }
      const isMobileCapture = targetRedirect.startsWith("/capture");
      
      if (!isMobileCapture && !["admin", "auditor", "SUPER_ADMIN", "ORG_ADMIN"].includes(result.user.role)) {
        throw new Error("Access denied. This system is restricted to verification personnel only.");
      }
      
      if (result.user.requires_password_change) {
        setTempToken(result.access_token);
        setTempUserRole(result.user.role);
        setTempUserRedirect(targetRedirect);
        setRequiresReset(true);
      } else {
        setAuthToken(result.access_token);
        localStorage.setItem("vf_token", result.access_token);
        window.location.href = targetRedirect;
      }
    } catch (err: any) {
      setError(err.message || "Invalid credentials");
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasswordReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setResetError("");
    
    if (newPassword.length < 8) {
      setResetError("New password must be at least 8 characters long.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setResetError("Passwords do not match.");
      return;
    }
    
    setIsResetting(true);
    try {
      setAuthToken(tempToken);
      await changePassword({ old_password: password, new_password: newPassword });
      
      // Save token and route securely
      localStorage.setItem("vf_token", tempToken);
      setRequiresReset(false);
      window.location.href = tempUserRedirect;
    } catch (err: any) {
      setResetError(err.message || "Failed to update password. Please try again.");
    } finally {
      setIsResetting(false);
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

      {/* Forced Password Reset Modal */}
      {requiresReset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="relative w-full max-w-md bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-8 shadow-2xl animate-fade-in-up">
            <div className="text-center mb-6">
              <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center mx-auto mb-3">
                <Lock size={24} />
              </div>
              <h3 className="text-lg font-bold text-[var(--color-text-primary)]">Password Change Required</h3>
              <p className="text-xs text-[var(--color-text-secondary)] mt-1.5 leading-relaxed">
                Your account was provisioned with temporary credentials. You must rotate your password before accessing the system.
              </p>
            </div>

            {resetError && (
              <div className="mb-4 px-4 py-2.5 rounded-xl text-xs bg-red-500/10 border border-red-500/20 text-red-400">
                {resetError}
              </div>
            )}

            <form onSubmit={handlePasswordReset} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-[var(--color-text-secondary)] mb-1.5 block">New Password</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="•••••••• (Min 8 characters)"
                  className="w-full px-4 py-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] placeholder:text-slate-600 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-[var(--color-text-secondary)] mb-1.5 block">Confirm New Password</label>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] placeholder:text-slate-600 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <button
                type="submit"
                disabled={isResetting}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 text-[var(--color-text-primary)] font-bold text-xs uppercase tracking-wide hover:from-emerald-600 hover:to-emerald-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isResetting ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Updating Password...
                  </>
                ) : (
                  "Change Password & Sign In"
                )}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
