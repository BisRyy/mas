import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Bundle for the Docker runtime image.
  output: "standalone",
  // Proxy /api requests to the FastAPI backend in dev so the frontend can
  // call relative paths and avoid CORS friction.
  async rewrites() {
    const backend = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
    ];
  },
  experimental: {
    typedRoutes: true,
  },
};

export default nextConfig;
