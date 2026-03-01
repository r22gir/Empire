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
