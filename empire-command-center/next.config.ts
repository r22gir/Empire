import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* Disable Turbopack in dev to avoid persistent cache corruption */
  experimental: {
    turbo: undefined,
  },
};

export default nextConfig;
