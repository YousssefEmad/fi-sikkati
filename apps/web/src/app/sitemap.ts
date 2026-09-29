import type { MetadataRoute } from "next";

import { routing } from "@/i18n/routing";
import { clientEnv } from "@/lib/env";

/** Public page paths (without locale prefix). Authenticated routes are never listed (MEP §54). */
const PUBLIC_PATHS: readonly string[] = [""];

export default function sitemap(): MetadataRoute.Sitemap {
  const base = clientEnv.NEXT_PUBLIC_SITE_URL;
  return PUBLIC_PATHS.flatMap((path) =>
    routing.locales.map((locale) => ({
      url: `${base}/${locale}${path}`,
      lastModified: new Date(),
      alternates: {
        languages: Object.fromEntries(routing.locales.map((alt) => [alt, `${base}/${alt}${path}`])),
      },
    })),
  );
}
