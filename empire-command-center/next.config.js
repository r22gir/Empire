// Mirrors next.config.ts so production builds do not depend on transpiling TS config.
const BUILD_TIMESTAMP = Date.now();

const BACKEND_UPSTREAM = process.env.NEXT_PUBLIC_BACKEND_UPSTREAM || 'http://127.0.0.1:8000';

/** @type {import('next').NextConfig} */
const nextConfig = {
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'Cache-Control', value: 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0' },
          { key: 'Pragma', value: 'no-cache' },
          { key: 'Expires', value: '0' },
          { key: 'Surrogate-Control', value: 'no-store' },
          { key: 'CDN-Cache-Control', value: 'no-store' },
          { key: 'Cloudflare-CDN-Cache-Control', value: 'no-store' },
        ],
      },
    ];
  },
  // Same-origin /api/v1 proxy to the local FastAPI backend. Mirrors
  // next.config.ts; see the TS file for the full rationale.
  // /intake_uploads/:path* is proxied too so client-uploaded photos
  // (mounted by the FastAPI StaticFiles at /intake_uploads) render
  // inside the same host. Without this proxy, the front-end would 404
  // photos served from the backend (iX-day R1X-INT-FIX).
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${BACKEND_UPSTREAM}/api/v1/:path*`,
      },
      {
        source: '/intake_uploads/:path*',
        destination: `${BACKEND_UPSTREAM}/intake_uploads/:path*`,
      },
    ];
  },
  generateBuildId: async () => `build-${BUILD_TIMESTAMP}`,
};

module.exports = nextConfig;
