// Mirrors next.config.ts so production builds do not depend on transpiling TS config.
const BUILD_TIMESTAMP = Date.now();

function empireUpstream() {
  const raw = process.env.EMPIRE_API_BASE || process.env.NEXT_PUBLIC_BACKEND_UPSTREAM || 'http://127.0.0.1:8000';
  return String(raw).replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
}

const BACKEND_UPSTREAM = empireUpstream();

// Mirrors next.config.ts. Default rewrite proxyTimeout is 30s and the
// cloned request body is capped at 10MB — both turn a phone Photo Analyzer
// measure into "Failed to proxy ... socket hang up" / Analysis failed (500).
//
// This is also the body-size ceiling for /api/v1/intake/projects/*/photos
// and /scans (LuxeForge intake uploads — PDFs, CAD, 3D scans, video, ...
// go through the same same-origin proxy below). Keep it in sync with
// backend/app/services/uploads/safe_file_serve.py:MAX_UPLOAD_BYTES
// (~200MB) — raising one without the other just moves the 413/timeout
// from the backend to this proxy or vice versa.
const VISION_PROXY_TIMEOUT_MS = 180_000;
const VISION_PROXY_BODY_LIMIT = '200mb';

// Keep Turbopack/NFT from copying local virtualenvs when a route's file
// trace reaches outside this app. docs/reports/pdf_venv/bin/python is a
// symlink that crashes `next build`. Do not delete those trees.
// Globs must not start with ".." — Turbopack rejects a prefix that leaves
// the project root. These still match docs/reports/pdf_venv when a trace
// reaches it, including the python symlink that crashes the build.
const VENV_TRACE_EXCLUDES = [
  '**/pdf_venv/**',
  '**/.venv/**',
  '**/venv/**',
  '**/*venv*/**',
];

// Family editions (AMP / Maxine) must not ship Empire's internal docs list.
// Swap app/lib/docs-registry.ts for the empty family registry in those builds.
const FAMILY_EDITION = ['amp', 'maxine'].includes(
  String(process.env.NEXT_PUBLIC_EMPIRE_EDITION || process.env.EMPIRE_EDITION || '').trim().toLowerCase(),
);

/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack(config, { webpack }) {
    if (FAMILY_EDITION) {
      const path = require('path');
      const familyRegistry = path.join(__dirname, 'app/lib/docs-registry.family.ts');
      config.plugins.push(
        new webpack.NormalModuleReplacementPlugin(/[\\/]lib[\\/]docs-registry(\.ts)?$/, (res) => {
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
  outputFileTracingExcludes: {
    '*': VENV_TRACE_EXCLUDES,
    '/api/docs/read': VENV_TRACE_EXCLUDES,
    '/api/docs/serve': VENV_TRACE_EXCLUDES,
  },
};

module.exports = nextConfig;
