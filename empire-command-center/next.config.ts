import type { NextConfig } from "next";

// Capture build timestamp once at config load time (not per-call)
// This prevents the race condition where Date.now() returns different values
// between compilation and static page generation steps
const BUILD_TIMESTAMP = Date.now();

function empireUpstream(): string {
  const raw = process.env.EMPIRE_API_BASE || process.env.NEXT_PUBLIC_BACKEND_UPSTREAM || "http://127.0.0.1:8000";
  return String(raw).replace(/\/api\/v1\/?$/, "").replace(/\/$/, "");
}

const BACKEND_UPSTREAM = empireUpstream();

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

// Mirrors next.config.js. Skips local virtualenvs (pdf_venv and others)
// so file tracing does not walk symlink trees under docs/.
// Globs must not start with "..". Turbopack rejects a prefix that leaves
// the project root. These still match a local pdf_venv (and other venvs).
const VENV_TRACE_EXCLUDES = [
  "**/pdf_venv/**",
  "**/.venv/**",
  "**/venv/**",
  "**/*venv*/**",
];

// Mirrors next.config.js: family editions get the empty docs registry.
const FAMILY_EDITION = ["amp", "maxine"].includes(
  String(process.env.NEXT_PUBLIC_EMPIRE_EDITION || process.env.EMPIRE_EDITION || "").trim().toLowerCase(),
);

const nextConfig: NextConfig = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  webpack(config: any, { webpack }: any) {
    if (FAMILY_EDITION) {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const path = require("path");
      const familyRegistry = path.join(__dirname, "app/lib/docs-registry.family.ts");
      config.plugins.push(
        new webpack.NormalModuleReplacementPlugin(/[\\/]lib[\\/]docs-registry(\.ts)?$/, (res: { request: string }) => {
          res.request = familyRegistry;
        }),
      );
    }
    return config;
  },
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
  outputFileTracingExcludes: {
    "*": VENV_TRACE_EXCLUDES,
    "/api/docs/read": VENV_TRACE_EXCLUDES,
    "/api/docs/serve": VENV_TRACE_EXCLUDES,
  },
};

export default nextConfig;
