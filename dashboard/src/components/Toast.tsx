// =============================================================================
// VeriField Nexus — Branded Toast Notification System
// =============================================================================
// Global toast provider and component for success/error/warning/info notifications.
// Styled to match the VeriField Nexus brand identity with smooth animations.
// =============================================================================

"use client";

import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface ToastContextValue {
  toast: {
    success: (title: string, message?: string) => void;
    error: (title: string, message?: string) => void;
    warning: (title: string, message?: string) => void;
    info: (title: string, message?: string) => void;
  };
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within <ToastProvider>");
  return ctx.toast;
}

// ---------------------------------------------------------------------------
// Icons
// ---------------------------------------------------------------------------

const icons: Record<ToastType, ReactNode> = {
  success: (
    <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" />
    </svg>
  ),
  error: (
    <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
    </svg>
  ),
  warning: (
    <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
    </svg>
  ),
  info: (
    <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
    </svg>
  ),
};

const colorMap: Record<ToastType, { bg: string; border: string; icon: string; bar: string }> = {
  success: {
    bg: "bg-[#0B1A14]",
    border: "border-[#00B47A]/30",
    icon: "text-[#00B47A]",
    bar: "bg-[#00B47A]",
  },
  error: {
    bg: "bg-[#1A0B0B]",
    border: "border-red-500/30",
    icon: "text-red-400",
    bar: "bg-red-500",
  },
  warning: {
    bg: "bg-[#1A150B]",
    border: "border-amber-500/30",
    icon: "text-amber-400",
    bar: "bg-amber-500",
  },
  info: {
    bg: "bg-[#0B111A]",
    border: "border-blue-500/30",
    icon: "text-blue-400",
    bar: "bg-blue-500",
  },
};

// ---------------------------------------------------------------------------
// Individual Toast Item
// ---------------------------------------------------------------------------

function ToastItem({ toast: t, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
  const [isExiting, setIsExiting] = useState(false);
  const [progress, setProgress] = useState(100);
  const duration = t.duration || 4000;
  const colors = colorMap[t.type];
  console.log("TOAST SYSTEM: ToastItem rendering:", { id: t.id, title: t.title, type: t.type });

  useEffect(() => {
    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, 100 - (elapsed / duration) * 100);
      setProgress(remaining);
      if (remaining <= 0) {
        clearInterval(interval);
      }
    }, 30);
    return () => clearInterval(interval);
  }, [duration]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsExiting(true);
      setTimeout(() => onDismiss(t.id), 300);
    }, duration);
    return () => clearTimeout(timer);
  }, [t.id, duration, onDismiss]);

  const handleDismiss = () => {
    setIsExiting(true);
    setTimeout(() => onDismiss(t.id), 300);
  };

  return (
    <div
      className={`
        relative overflow-hidden rounded-xl border shadow-2xl backdrop-blur-sm
        ${colors.bg} ${colors.border}
        ${isExiting ? "animate-toast-exit" : "animate-toast-enter"}
        min-w-[320px] max-w-[420px]
      `}
    >
      <div className="flex items-start gap-3 p-4">
        {/* Branded Icon */}
        <div className={`shrink-0 mt-0.5 ${colors.icon}`}>
          {icons[t.type]}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {/* VeriField brand mark */}
            <span className="text-[7px] font-black tracking-widest uppercase text-[var(--color-text-muted)] opacity-60">
              VeriField
            </span>
          </div>
          <p className="text-sm font-bold text-[var(--color-text-primary)] mt-0.5 leading-snug">
            {t.title}
          </p>
          {t.message && (
            <p className="text-[11px] text-[var(--color-text-secondary)] mt-1 leading-relaxed">
              {t.message}
            </p>
          )}
        </div>

        {/* Dismiss button */}
        <button
          onClick={handleDismiss}
          className="shrink-0 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors p-0.5 rounded-md hover:bg-white/5"
        >
          <svg className="w-3.5 h-3.5" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M1 1l12 12M13 1L1 13" />
          </svg>
        </button>
      </div>

      {/* Progress bar */}
      <div className="h-[2px] w-full bg-white/5">
        <div
          className={`h-full ${colors.bar} transition-all duration-100 ease-linear`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Toast Provider
// ---------------------------------------------------------------------------

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((type: ToastType, title: string, message?: string) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    console.log("TOAST SYSTEM: addToast called with", { id, type, title, message });
    setToasts((prev) => [...prev, { id, type, title, message, duration: type === "error" ? 6000 : 4000 }]);
  }, []);

  console.log("TOAST SYSTEM: ToastProvider rendering. Current toasts count:", toasts.length, toasts);

  const toast = {
    success: (title: string, message?: string) => addToast("success", title, message),
    error: (title: string, message?: string) => addToast("error", title, message),
    warning: (title: string, message?: string) => addToast("warning", title, message),
    info: (title: string, message?: string) => addToast("info", title, message),
  };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}

      {/* Toast container — fixed bottom-right */}
      <div className="fixed bottom-6 right-6 z-[9999] flex flex-col-reverse gap-3 pointer-events-none">
        {toasts.map((t) => (
          <div key={t.id} className="pointer-events-auto">
            <ToastItem toast={t} onDismiss={dismiss} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
