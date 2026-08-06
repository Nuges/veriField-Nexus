"use client";

import React, { useEffect, useState } from "react";

export interface ThemeLogoProps {
  className?: string;
  alt?: string;
}

export function ThemeLogo({
  className = "h-8 w-auto object-contain",
  alt = "VeriField Nexus"
}: ThemeLogoProps) {
  const [isDark, setIsDark] = useState<boolean>(false);

  useEffect(() => {
    const updateTheme = () => {
      setIsDark(document.documentElement.classList.contains("dark"));
    };

    updateTheme();

    const observer = new MutationObserver(updateTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });

    return () => observer.disconnect();
  }, []);

  return (
    <img
      src={isDark ? "/logo-white.png" : "/logo-black.png"}
      alt={alt}
      className={className}
    />
  );
}
