/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow large image uploads (base64 data URLs can be 5-10MB)
  experimental: {
    serverActions: {
      bodySizeLimit: '10mb',
    },
  },
}
module.exports = nextConfig

// Note: For App Router API routes, body size is handled by
// reading the request manually (req.json()) which has no
// built-in limit. If issues persist, it's likely CORS or network.
