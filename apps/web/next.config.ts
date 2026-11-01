import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

import "./src/lib/env";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

/**
 * Baseline security headers for the web origin (security.md §6). A nonce-based
 * Content-Security-Policy is added in Phase 11 together with the map/tile origins it must allow.
 */
// React's development runtime reconstructs stacks with eval(). Production builds do not.
const scriptSrc =
  process.env.NODE_ENV === "development"
    ? "script-src 'self' 'unsafe-inline' 'unsafe-eval'"
    : "script-src 'self' 'unsafe-inline'";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Permissions-Policy", value: "geolocation=(self), camera=(), microphone=(), payment=()" },
  { key: "X-DNS-Prefetch-Control", value: "off" },
  {
    key: "Strict-Transport-Security",
    value: "max-age=31536000; includeSubDomains",
  },
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      scriptSrc,
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob: https:",
      "connect-src 'self' https://api.mapbox.com https://events.mapbox.com",
      "font-src 'self' data:",
      "worker-src 'self'",
      "frame-src https://www.google.com https://maps.google.com",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join("; "),
  },
];

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  poweredByHeader: false,
  typedRoutes: true,
  // The dev server treats localhost and 127.0.0.1 as different origins. Both are used locally.
  allowedDevOrigins: ["127.0.0.1"],
  images: {
    formats: ["image/avif", "image/webp"],
  },
  async rewrites() {
    // Browser calls stay on the web origin so ``__Host-`` session cookies attach here (ADR-0004).
    const api = (process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
    return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
  },
  async headers() {
    return [{ source: "/(.*)", headers: securityHeaders }];
  },
};

export default withNextIntl(nextConfig);
