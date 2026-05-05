
// API Proxy for backend
const nextConfig = {
  ...(typeof module.exports === 'function' ? module.exports({}) : module.exports),
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://127.0.0.1:8010/api/v1/:path*',
      },
    ]
  },
}
module.exports = nextConfig
