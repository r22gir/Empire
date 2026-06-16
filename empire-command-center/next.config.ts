import type { NextConfig } from "next";

// Capture build timestamp once at config load time (not per-call)
// This prevents the race condition where Date.now() returns different values
// between compilation and static page generation steps
const BUILD_TIMESTAMP = Date.now();

const BACKEND_UPSTREAM = process.env.NEXT_PUBLIC_BACKEND_UPSTREAM || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "Cache-Control", value: "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0" },
          { key: "Pragma", value: "no-cache" },
          { key: "Expires", value: "0" },
          { key: "Surrogate-Control", value: "no-store" },
          { key: "CDN-Cache-Control", value: "no-store" },
          { key: "Cloudflare-CDN-Cache-Control", value: "no-store" },
        ],
      },
    ];
  },
  // Same-origin /api/v1 proxy to the local FastAPI backend.
  // This is what allows studio.empirebox.store / LAN / forge pages to
  // call the backend without going cross-origin to api.empirebox.store
  // (which Cloudflare Access 302s to its login page, breaking fetch()).
  // The rewrite is server-side, so the browser never touches the
  // upstream backend directly; CF Access only sees the portal host.
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${BACKEND_UPSTREAM}/api/v1/:path*`,
      },
    ];
  },
  // Force unique chunk URLs on every build so phones never use stale JS
  generateBuildId: async () => `build-${BUILD_TIMESTAMP}`,
};

export default nextConfig;
