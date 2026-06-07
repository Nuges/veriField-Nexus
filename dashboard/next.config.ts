import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  eslint: {
    // Warning: This allows production builds to successfully complete even if
    // the project has ESLint errors.
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Also ignore typescript check if there are differences in env/compiler versions on Vercel
    ignoreBuildErrors: true,
  }
};

export default nextConfig;
