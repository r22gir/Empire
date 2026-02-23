/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/luxeforge/:path*',
        destination: `${backendUrl}/api/luxeforge/:path*`,
      },
    ];
  },
}
module.exports = nextConfig
