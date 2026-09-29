import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

import "./src/lib/env";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

/**
 * Baseline security headers for the web origin (security.md §6). A nonce-based
 * Content-Security-Policy is added in Phase 11 together with the map/tile origins it must allow.
 */
const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Permissions-Policy", value: "geolocation=(self), camera=(), microphone=(), payment=()" },
];

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  poweredByHeader: false,
  typedRoutes: true,
  images: {
    formats: ["image/avif", "image/webp"],
  },
  async headers() {
    return [{ source: "/(.*)", headers: securityHeaders }];
  },
};

export default withNextIntl(nextConfig);
