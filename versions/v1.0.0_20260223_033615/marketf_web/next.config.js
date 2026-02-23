/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ['localhost', 'marketf.com'],
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || '',
  },
}

module.exports = nextConfig
