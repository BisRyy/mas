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
  // Server-side proxy for /api/* — handled by the Next.js Node process,
  // never reaches the browser. We deliberately use INTERNAL_API_URL (NOT
  // NEXT_PUBLIC_API_URL) so the proxy hops over the Docker network to
  // `http://backend:8000` instead of hairpinning out to the public URL
  // (which would (a) waste a TLS round-trip and (b) fail with
  // DEPTH_ZERO_SELF_SIGNED_CERT when Let's Encrypt hasn't fully issued).
  //
  // Fallback order:
  //   1. INTERNAL_API_URL — set in docker-compose to http://backend:8000
  //   2. NEXT_PUBLIC_API_URL — useful in local dev where there is no
  //      internal network and you just point at the dev backend on :8000
  //   3. http://localhost:8000 — last-resort dev default
  async rewrites() {
    const backend =
      process.env.INTERNAL_API_URL ??
      process.env.NEXT_PUBLIC_API_URL ??
      "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
    ];
  },
};

export default nextConfig;
