import type { NextConfig } from "next";

// Capture build timestamp once at config load time (not per-call)
// This prevents the race condition where Date.now() returns different values
// between compilation and static page generation steps
const BUILD_TIMESTAMP = Date.now();

const BACKEND_UPSTREAM = process.env.NEXT_PUBLIC_BACKEND_UPSTREAM || "http://127.0.0.1:8000";

// Photo Analyzer POSTs go through this rewrite. Next's http-proxy default
// proxyTimeout is 30s; MiniMax measure is ~20s and often longer once the
// body is in flight, and the proxy then logs
// "Failed to proxy ... Error: socket hang up" (UI: Analysis failed (500)).
// Every request body is also cloned with a size cap (body-streams.js). A
// phone JPEG base64 blows past a small cap, the clone ends early, and the
// upstream socket resets. Self-hosted CC is not on Vercel's proxy cap.
//
// This is also the body-size ceiling for /api/v1/intake/projects/*/photos
// and /scans (LuxeForge intake uploads — PDFs, CAD, 3D scans, video, ...
// go through the same same-origin proxy below). Keep it in sync with
// backend/app/services/uploads/safe_file_serve.py:MAX_UPLOAD_BYTES
// (~200MB) — raising one without the other just moves the 413/timeout
// from the backend to this proxy or vice versa.
const VISION_PROXY_TIMEOUT_MS = 180_000;
const VISION_PROXY_BODY_LIMIT = "200mb";

const nextConfig: NextConfig = {
  experimental: {
    proxyTimeout: VISION_PROXY_TIMEOUT_MS,
    proxyClientMaxBodySize: VISION_PROXY_BODY_LIMIT,
  },
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
  // /intake_uploads/:path* is proxied too so client-uploaded photos
  // (mounted by the FastAPI StaticFiles at /intake_uploads) render
  // inside the same host. Without this proxy, the front-end would 404
  // photos served from the backend (iX-day R1X-INT-FIX).
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${BACKEND_UPSTREAM}/api/v1/:path*`,
      },
      {
        source: "/intake_uploads/:path*",
        destination: `${BACKEND_UPSTREAM}/intake_uploads/:path*`,
      },
    ];
  },
  // Force unique chunk URLs on every build so phones never use stale JS
  generateBuildId: async () => `build-${BUILD_TIMESTAMP}`,
};

export default nextConfig;
