// =============================================================================
// VeriField Nexus — Root Layout
// =============================================================================

import type { Metadata } from "next";
import { Providers } from "@/components/Providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "VeriField Nexus — Admin Dashboard",
  description: "Field data verification and analytics for climate projects",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "VeriField Capture",
  },
  icons: {
    icon: "/favicon.ico",
    apple: "/logo-white.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="font-sans antialiased" suppressHydrationWarning>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
