// =============================================================================

// VeriField Nexus — Admin Login Page

// =============================================================================

// Premium glassmorphic login form for admin dashboard access.

// =============================================================================



"use client";



import { useState, useEffect } from "react";

import { useRouter } from "next/navigation";

import Link from "next/link";

import { ShieldCheck, Mail, Lock, Loader2, KeyRound, ArrowLeft } from "lucide-react";

import { loginAdmin, setAuthToken, changePassword, verifyMFALogin, useMFARecovery, getSSOProviders, initiateSSOLogin } from "@/lib/api";

import { safeStorage } from "@/lib/storage";
import { isDashboardRoleAllowed } from "@/lib/roles";
import { ThemeLogo } from "@/components/common/ThemeLogo";



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



  // MFA states

  const [mfaRequired, setMfaRequired] = useState(false);

  const [mfaToken, setMfaToken] = useState("");

  const [mfaCode, setMfaCode] = useState("");

  const [mfaError, setMfaError] = useState("");

  const [isMfaVerifying, setIsMfaVerifying] = useState(false);

  const [showRecovery, setShowRecovery] = useState(false);

  const [recoveryCode, setRecoveryCode] = useState("");



  // SSO states

  const [ssoProviders, setSsoProviders] = useState<Array<{name: string; display_name: string}>>([]);



  useEffect(() => {

    getSSOProviders().then(r => setSsoProviders(r?.providers || [])).catch(() => {});

  }, []);



  useEffect(() => {

    if (typeof window !== "undefined") {

      const params = new URLSearchParams(window.location.search);



      // If a valid token exists AND there is a redirect target, the user may

      // have been bounced back by a transient network error.  In that case,

      // try to honour the existing token instead of wiping it.

      const existingToken = safeStorage.getItem("vf_token");

      const redirectTarget = params.get("redirect");



      if (existingToken && redirectTarget) {

        // Attempt to resume — redirect back to the target without clearing creds

        window.location.href = redirectTarget;

        return;

      }



      // Otherwise — genuine fresh login.  Clear any stale auth state.

      safeStorage.removeItem("vf_token");

      safeStorage.removeItem("vf_user");

      setAuthToken(null);



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



      // Check if MFA is required

      if (result.mfa_required) {

        setMfaRequired(true);

        setMfaToken(result.mfa_token || "");

        setIsLoading(false);

        return;

      }



      // Parse redirect parameter dynamically from the search query

      const params = new URLSearchParams(window.location.search);

      let targetRedirect = params.get("redirect") || "/dashboard";



      const userRoleUpper = (result.user?.role || "").toUpperCase().replace(" ", "_");

      if (userRoleUpper === "SUPER_ADMIN") {

        targetRedirect = "/super-admin";

      }



      const isMobileCapture = targetRedirect.startsWith("/capture");



      if (!isMobileCapture && !isDashboardRoleAllowed(result.user?.role)) {
        throw new Error("Access denied. This system is restricted to verification personnel only.");
      }



      if (result.user?.requires_password_change) {

        setTempToken(result.access_token);

        setTempUserRole(result.user.role);

        setTempUserRedirect(targetRedirect);

        setRequiresReset(true);

      } else {

        setAuthToken(result.access_token);
        safeStorage.setItem("vf_token", result.access_token);
        if (result.user) {
          safeStorage.setItem("vf_user", JSON.stringify(result.user));
          if (result.user.id) {
            safeStorage.removeItem(`vf_workspace_${result.user.id}`);
          }
        }
        window.location.href = targetRedirect;

      }

    } catch (err: any) {

      setError(err.message || "Invalid credentials");

    } finally {

      setIsLoading(false);

    }

  };



  const handleMfaVerify = async (e: React.FormEvent) => {

    e.preventDefault();

    setMfaError("");

    setIsMfaVerifying(true);

    try {

      let result;

      if (showRecovery) {

        result = await useMFARecovery(mfaToken, recoveryCode);

      } else {

        result = await verifyMFALogin(mfaToken, mfaCode);

      }

      setAuthToken(result.access_token);

      safeStorage.setItem("vf_token", result.access_token);

      const params = new URLSearchParams(window.location.search);

      window.location.href = params.get("redirect") || "/dashboard";

    } catch (err: any) {

      setMfaError(err.message || "Invalid verification code");

    } finally {

      setIsMfaVerifying(false);

    }

  };



  const handleSSOLogin = async (provider: string) => {

    try {

      const redirectUri = window.location.origin + "/login";

      const result = await initiateSSOLogin(provider, redirectUri);

      window.location.href = result.authorization_url;

    } catch (err: any) {

      setError(err.message || `SSO login with ${provider} failed`);

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
      await changePassword({ new_password: newPassword });

      // Save token and route securely
      safeStorage.setItem("vf_token", tempToken);
      const userStr = safeStorage.getItem("vf_user");
      if (userStr) {
        try {
          const userObj = JSON.parse(userStr);
          userObj.requires_password_change = false;
          safeStorage.setItem("vf_user", JSON.stringify(userObj));
        } catch (_) {}
      }
      setRequiresReset(false);
      window.location.href = tempUserRedirect || "/dashboard";
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

          <ThemeLogo className="h-8 w-auto object-contain mb-2" />

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
                  placeholder="segunoluwole22@gmail.com"
                  required
                  className="w-full pl-10 pr-4 py-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)]
                    text-[var(--color-text-primary)] placeholder:text-slate-500 text-sm
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
                    text-[var(--color-text-primary)] placeholder:text-slate-500 text-sm
                    focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/50
                    transition-all duration-200"
                />
              </div>
            </div>

            {/* Quick Demo Fill Credentials */}
            <div className="pt-1 pb-1">
              <p className="text-[11px] font-semibold text-[var(--color-text-secondary)] mb-1.5 uppercase tracking-wider">Quick Sign-In Presets</p>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setEmail("segunoluwole22@gmail.com");
                    setPassword("VeriField_Dev_2026!");
                  }}
                  className="px-2.5 py-1.5 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] hover:border-emerald-500/40 text-[11px] font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] text-left transition-colors flex items-center gap-1.5 cursor-pointer"
                >
                  <ShieldCheck size={13} className="text-[#008A5E] shrink-0" />
                  <span className="truncate">Super Admin</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEmail("shalom@gmail.com");
                    setPassword("Password123!");
                  }}
                  className="px-2.5 py-1.5 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] hover:border-blue-500/40 text-[11px] font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] text-left transition-colors flex items-center gap-1.5 cursor-pointer"
                >
                  <ShieldCheck size={13} className="text-blue-400 shrink-0" />
                  <span className="truncate">Org Admin</span>
                </button>
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



          {/* SSO Provider Buttons */}

          {ssoProviders.length > 0 && (

            <div className="mt-4 pt-4 border-t border-[var(--color-border)]">

              <p className="text-xs text-[var(--color-text-secondary)] text-center mb-3 font-medium">Or sign in with Enterprise SSO</p>

              <div className="space-y-2">

                {ssoProviders.map((p) => (

                  <button

                    key={p.name}

                    onClick={() => handleSSOLogin(p.name)}

                    className="w-full py-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-sm font-semibold text-[var(--color-text-primary)] hover:bg-[var(--color-background)] transition-all flex items-center justify-center gap-2 cursor-pointer"

                  >

                    <ShieldCheck size={16} className="text-blue-400" />

                    {p.display_name}

                  </button>

                ))}

              </div>

            </div>

          )}

        </div>



        <p className="text-center text-slate-600 text-xs mt-6">

          VeriField Nexus v1.0 — Climate Data Verification Platform

        </p>

      </div>



      {/* MFA Verification Modal */}

      {mfaRequired && (

        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">

          <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-8 max-w-md w-full animate-fade-in-up">

            <div className="flex items-center gap-3 mb-6">

              <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">

                <KeyRound size={20} className="text-emerald-400" />

              </div>

              <div>

                <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">

                  Two-Factor Authentication

                </h3>

                <p className="text-xs text-[var(--color-text-secondary)]">

                  {showRecovery ? "Enter a recovery code" : "Enter the 6-digit code from your authenticator app"}

                </p>

              </div>

            </div>



            {mfaError && (

              <div className="mb-4 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">

                {mfaError}

              </div>

            )}



            <form onSubmit={handleMfaVerify} className="space-y-4">

              {showRecovery ? (

                <div>

                  <label className="text-sm text-[var(--color-text-secondary)] mb-1.5 block">Recovery Code</label>

                  <input

                    type="text"

                    value={recoveryCode}

                    onChange={(e) => setRecoveryCode(e.target.value)}

                    placeholder="XXXX-XXXX-XXXX"

                    autoFocus

                    required

                    className="w-full px-4 py-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm focus:outline-none focus:border-emerald-500 transition-all font-mono tracking-wider text-center"

                  />

                </div>

              ) : (

                <div>

                  <label className="text-sm text-[var(--color-text-secondary)] mb-1.5 block">Verification Code</label>

                  <input

                    type="text"

                    inputMode="numeric"

                    maxLength={6}

                    value={mfaCode}

                    onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, "").slice(0, 6))}

                    placeholder="000000"

                    autoFocus

                    required

                    className="w-full px-4 py-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-2xl font-mono tracking-[0.5em] text-center focus:outline-none focus:border-emerald-500 transition-all"

                  />

                </div>

              )}



              <button

                type="submit"

                disabled={isMfaVerifying}

                className="w-full py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 text-white font-semibold text-sm hover:from-emerald-600 hover:to-emerald-700 disabled:opacity-50 transition-all flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20"

              >

                {isMfaVerifying ? (

                  <><Loader2 size={18} className="animate-spin" /> Verifying...</>

                ) : (

                  "Verify"

                )}

              </button>

            </form>



            <div className="mt-4 flex items-center justify-between">

              <button

                onClick={() => setShowRecovery(!showRecovery)}

                className="text-xs text-emerald-400 hover:underline cursor-pointer"

              >

                {showRecovery ? "Use authenticator code" : "Lost your device? Use recovery code"}

              </button>

              <button

                onClick={() => { setMfaRequired(false); setMfaToken(""); setMfaCode(""); }}

                className="text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] cursor-pointer flex items-center gap-1"

              >

                <ArrowLeft size={12} /> Back to login

              </button>

            </div>

          </div>

        </div>

      )}





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
