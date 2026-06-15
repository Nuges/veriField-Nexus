import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";
const BACKEND_URL = process.env.BACKEND_API_URL || (isProd ? 'https://verifield-nexus.onrender.com' : 'http://127.0.0.1:8000');

const nextConfig: any = {
  /* config options here */
  typescript: {
    // Also ignore typescript check if there are differences in env/compiler versions on Vercel
    ignoreBuildErrors: true,
  },
  // Keep-alive connections to reduce TCP handshake overhead with backend
  httpAgentOptions: {
    keepAlive: true,
  },
  allowedDevOrigins: [
    'http://192.168.8.199:3000',
    '192.168.8.199',
    'probasketball-overcrowdedly-ernestina.ngrok-free.dev',
    '*.ngrok-free.dev',
  ],
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${BACKEND_URL}/api/v1/:path*`,
      },
      {
        source: '/static/:path*',
        destination: `${BACKEND_URL}/static/:path*`,
      },
    ];
  },
};

export default nextConfig;

