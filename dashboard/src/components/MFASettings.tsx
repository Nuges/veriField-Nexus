// =============================================================================

// VeriField Nexus — MFA Settings Component

// =============================================================================

// Allows users to setup, verify, and disable TOTP two-factor authentication

// from their account security settings. Shows QR code for authenticator app

// enrollment and manages recovery codes.

// =============================================================================



"use client";



import React, { useState, useEffect, useCallback } from "react";

import { Shield, ShieldCheck, ShieldOff, KeyRound, Copy, Check, Loader2, AlertTriangle } from "lucide-react";

import { getMFAStatus, setupMFA, verifyMFASetup, disableMFA } from "@/lib/api";



type MFAStep = "idle" | "loading" | "setup" | "verify" | "recovery-display" | "disable-confirm";



export default function MFASettings() {

  const [step, setStep] = useState<MFAStep>("loading");

  const [mfaEnabled, setMfaEnabled] = useState(false);

  const [recoveryRemaining, setRecoveryRemaining] = useState(0);



  // Setup state

  const [secret, setSecret] = useState("");

  const [qrCode, setQrCode] = useState<string | null>(null);

  const [verifyCode, setVerifyCode] = useState("");

  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);

  const [copied, setCopied] = useState(false);



  // Disable state

  const [disableCode, setDisableCode] = useState("");



  const [error, setError] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);



  const loadStatus = useCallback(async () => {

    try {

      const status = await getMFAStatus();

      setMfaEnabled(status.mfa_enabled);

      setRecoveryRemaining(status.recovery_codes_remaining);

      setStep("idle");

    } catch {

      setStep("idle");

    }

  }, []);



  useEffect(() => {

    loadStatus();

  }, [loadStatus]);



  const handleSetup = async () => {

    setError("");

    setIsSubmitting(true);

    try {

      const result = await setupMFA();

      setSecret(result.secret);

      setQrCode(result.qr_code_base64);

      setStep("setup");

    } catch (err: any) {

      setError(err.message || "Failed to start MFA setup");

    } finally {

      setIsSubmitting(false);

    }

  };



  const handleVerify = async (e: React.FormEvent) => {

    e.preventDefault();

    setError("");

    setIsSubmitting(true);

    try {

      const result = await verifyMFASetup(verifyCode, secret);

      setRecoveryCodes(result.recovery_codes);

      setMfaEnabled(true);

      setStep("recovery-display");

    } catch (err: any) {

      setError(err.message || "Invalid code");

    } finally {

      setIsSubmitting(false);

    }

  };



  const handleDisable = async (e: React.FormEvent) => {

    e.preventDefault();

    setError("");

    setIsSubmitting(true);

    try {

      await disableMFA(disableCode);

      setMfaEnabled(false);

      setStep("idle");

      setDisableCode("");

    } catch (err: any) {

      setError(err.message || "Invalid code");

    } finally {

      setIsSubmitting(false);

    }

  };



  const copyRecoveryCodes = () => {

    navigator.clipboard.writeText(recoveryCodes.join("\n"));

    setCopied(true);

    setTimeout(() => setCopied(false), 2000);

  };



  if (step === "loading") {

    return (

      <div className="p-6 rounded-xl border border-[var(--color-border)] bg-[var(--color-card)]">

        <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">

          <Loader2 size={16} className="animate-spin" /> Loading security settings...

        </div>

      </div>

    );

  }



  return (

    <div className="p-6 rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] space-y-4">

      <div className="flex items-center justify-between">

        <div className="flex items-center gap-3">

          {mfaEnabled ? (

            <ShieldCheck size={20} className="text-emerald-400" />

          ) : (

            <Shield size={20} className="text-yellow-400" />

          )}

          <div>

            <h3 className="text-sm font-bold text-[var(--color-text-primary)]">Two-Factor Authentication</h3>

            <p className="text-xs text-[var(--color-text-secondary)]">

              {mfaEnabled

                ? `MFA is active. ${recoveryRemaining} recovery codes remaining.`

                : "Add an extra layer of security to your account."}

            </p>

          </div>

        </div>



        {step === "idle" && (

          <button

            onClick={mfaEnabled ? () => setStep("disable-confirm") : handleSetup}

            disabled={isSubmitting}

            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${

              mfaEnabled

                ? "bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20"

                : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20"

            }`}

          >

            {isSubmitting ? <Loader2 size={14} className="animate-spin" /> : mfaEnabled ? "Disable MFA" : "Enable MFA"}

          </button>

        )}

      </div>



      {error && (

        <div className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs">

          {error}

        </div>

      )}



      {/* Setup Step: Show QR Code */}

      {step === "setup" && (

        <div className="space-y-4 pt-4 border-t border-[var(--color-border)]">

          <p className="text-xs text-[var(--color-text-secondary)]">

            Scan this QR code with your authenticator app (Google Authenticator, Authy, 1Password, etc.)

          </p>

          {qrCode && (

            <div className="flex justify-center p-4 bg-white rounded-xl w-fit mx-auto">

              <img src={`data:image/png;base64,${qrCode}`} alt="MFA QR Code" className="w-48 h-48" />

            </div>

          )}

          <div className="text-center">

            <p className="text-[10px] text-[var(--color-text-secondary)] mb-1">Or enter this key manually:</p>

            <code className="text-xs font-mono bg-[var(--color-surface)] px-3 py-1.5 rounded-lg border border-[var(--color-border)] text-[var(--color-text-primary)] select-all">

              {secret}

            </code>

          </div>



          <form onSubmit={handleVerify} className="space-y-3 pt-2">

            <label className="text-xs font-bold text-[var(--color-text-primary)]">Enter the 6-digit code from your app</label>

            <input

              type="text"

              inputMode="numeric"

              maxLength={6}

              value={verifyCode}

              onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, "").slice(0, 6))}

              placeholder="000000"

              autoFocus

              className="w-full px-4 py-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-xl font-mono tracking-[0.4em] text-center focus:outline-none focus:border-emerald-500"

            />

            <div className="flex gap-2">

              <button

                type="button"

                onClick={() => { setStep("idle"); setSecret(""); setQrCode(null); }}

                className="flex-1 py-2 rounded-lg border border-[var(--color-border)] text-xs font-bold text-[var(--color-text-secondary)] hover:bg-[var(--color-surface)] cursor-pointer"

              >

                Cancel

              </button>

              <button

                type="submit"

                disabled={isSubmitting || verifyCode.length < 6}

                className="flex-1 py-2 rounded-lg bg-emerald-500 text-slate-950 text-xs font-bold hover:bg-emerald-600 disabled:opacity-50 cursor-pointer"

              >

                {isSubmitting ? "Verifying..." : "Activate MFA"}

              </button>

            </div>

          </form>

        </div>

      )}



      {/* Recovery Codes Display */}

      {step === "recovery-display" && (

        <div className="space-y-4 pt-4 border-t border-[var(--color-border)]">

          <div className="flex items-start gap-2 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/30">

            <AlertTriangle size={16} className="text-yellow-400 shrink-0 mt-0.5" />

            <p className="text-xs text-yellow-200">

              <strong>Save these recovery codes now.</strong> They will not be shown again. Each code can only be used once.

            </p>

          </div>



          <div className="grid grid-cols-2 gap-2 p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)]">

            {recoveryCodes.map((code, i) => (

              <code key={i} className="text-xs font-mono text-[var(--color-text-primary)] py-1">{code}</code>

            ))}

          </div>



          <div className="flex gap-2">

            <button

              onClick={copyRecoveryCodes}

              className="flex-1 py-2 rounded-lg border border-[var(--color-border)] text-xs font-bold text-[var(--color-text-primary)] hover:bg-[var(--color-surface)] cursor-pointer flex items-center justify-center gap-1.5"

            >

              {copied ? <><Check size={12} /> Copied!</> : <><Copy size={12} /> Copy All</>}

            </button>

            <button

              onClick={() => { setStep("idle"); loadStatus(); }}

              className="flex-1 py-2 rounded-lg bg-emerald-500 text-slate-950 text-xs font-bold hover:bg-emerald-600 cursor-pointer"

            >

              Done — I&apos;ve Saved Them

            </button>

          </div>

        </div>

      )}



      {/* Disable Confirmation */}

      {step === "disable-confirm" && (

        <form onSubmit={handleDisable} className="space-y-3 pt-4 border-t border-[var(--color-border)]">

          <p className="text-xs text-[var(--color-text-secondary)]">

            Enter a current TOTP code to confirm disabling MFA.

          </p>

          <input

            type="text"

            inputMode="numeric"

            maxLength={6}

            value={disableCode}

            onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, "").slice(0, 6))}

            placeholder="000000"

            autoFocus

            className="w-full px-4 py-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-xl font-mono tracking-[0.4em] text-center focus:outline-none focus:border-red-500"

          />

          <div className="flex gap-2">

            <button

              type="button"

              onClick={() => { setStep("idle"); setDisableCode(""); }}

              className="flex-1 py-2 rounded-lg border border-[var(--color-border)] text-xs font-bold text-[var(--color-text-secondary)] hover:bg-[var(--color-surface)] cursor-pointer"

            >

              Cancel

            </button>

            <button

              type="submit"

              disabled={isSubmitting || disableCode.length < 6}

              className="flex-1 py-2 rounded-lg bg-red-500 text-white text-xs font-bold hover:bg-red-600 disabled:opacity-50 cursor-pointer"

            >

              {isSubmitting ? "Disabling..." : "Confirm Disable"}

            </button>

          </div>

        </form>

      )}

    </div>

  );

}
