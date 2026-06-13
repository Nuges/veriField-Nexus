import type { NextConfig } from "next";

const nextConfig: any = {
  /* config options here */
  typescript: {
    // Also ignore typescript check if there are differences in env/compiler versions on Vercel
    ignoreBuildErrors: true,
  },
  allowedDevOrigins: [
    'http://192.168.8.199:3000',
    '192.168.8.199',
  ],
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://127.0.0.1:8000/api/v1/:path*',
      },
    ];
  },
};

export default nextConfig;

