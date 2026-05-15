import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Bundle for the Docker runtime image.
  output: "standalone",
  // typedRoutes deliberately disabled: still experimental, refuses
  // `href={dynamicString}` props (e.g. the VerdictCard `link` prop that
  // we populate from API data at render time), and emits deprecation
  // warnings under `experimental`. The trade-off — static route
  // validation — is not worth the build friction.
  // Proxy /api requests to the FastAPI backend in dev so the frontend
  // can call relative paths and avoid CORS friction.
  async rewrites() {
    const backend = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
    ];
  },
};

export default nextConfig;
