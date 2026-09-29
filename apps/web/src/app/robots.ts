import type { MetadataRoute } from "next";

import { clientEnv } from "@/lib/env";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/api/"] }],
    sitemap: `${clientEnv.NEXT_PUBLIC_SITE_URL}/sitemap.xml`,
  };
}
