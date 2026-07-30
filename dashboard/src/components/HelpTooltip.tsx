// =============================================================================

// VeriField Nexus — Help Tooltip Component

// =============================================================================

// Simple hover tooltip for inline help text across the dashboard.

// =============================================================================



"use client";



import React, { useState, useRef } from "react";

import { HelpCircle } from "lucide-react";



interface HelpTooltipProps {

  text: string;

  position?: "top" | "bottom" | "left" | "right";

  size?: number;

  children?: React.ReactNode;

}



export default function HelpTooltip({ text, position = "top", size = 14, children }: HelpTooltipProps) {

  const [visible, setVisible] = useState(false);

  const timeoutRef = useRef<NodeJS.Timeout | null>(null);



  const show = () => {

    if (timeoutRef.current) clearTimeout(timeoutRef.current);

    setVisible(true);

  };



  const hide = () => {

    timeoutRef.current = setTimeout(() => setVisible(false), 150);

  };



  const positionClasses: Record<string, string> = {

    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",

    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",

    left: "right-full top-1/2 -translate-y-1/2 mr-2",

    right: "left-full top-1/2 -translate-y-1/2 ml-2",

  };



  return (

    <span

      className="relative inline-flex items-center"

      onMouseEnter={show}

      onMouseLeave={hide}

      onFocus={show}

      onBlur={hide}

    >

      {children || <HelpCircle size={size} className="text-[var(--color-text-secondary)] hover:text-[#00B47A] transition-colors cursor-help" />}

      {visible && (

        <span

          className={`absolute z-50 ${positionClasses[position]} px-3 py-2 rounded-lg bg-[#1a1a2e] border border-[var(--color-border)] text-[11px] text-[var(--color-text-primary)] font-medium shadow-lg whitespace-nowrap max-w-[280px]`}

          style={{ whiteSpace: "normal" }}

        >

          {text}

        </span>

      )}

    </span>

  );

}
