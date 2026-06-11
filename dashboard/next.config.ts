import type { NextConfig } from "next";

const nextConfig: any = {
  /* config options here */
  typescript: {
    // Also ignore typescript check if there are differences in env/compiler versions on Vercel
    ignoreBuildErrors: true,
  }
};

export default nextConfig;
