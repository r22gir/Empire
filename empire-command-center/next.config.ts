import type { NextConfig } from "next";

// Capture build timestamp once at config load time (not per-call)
// This prevents the race condition where Date.now() returns different values
// between compilation and static page generation steps
const BUILD_TIMESTAMP = Date.now();

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
  // Force unique chunk URLs on every build so phones never use stale JS
  generateBuildId: async () => `build-${BUILD_TIMESTAMP}`,
};

export default nextConfig;
