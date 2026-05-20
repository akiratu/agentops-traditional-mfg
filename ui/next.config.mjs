/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const backend = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
    return [{ source: '/api/:path*', destination: `${backend}/:path*` }]
  },
  experimental: {
    typedRoutes: false, // App Router stable; types come from query factories instead
  },
}
export default nextConfig
