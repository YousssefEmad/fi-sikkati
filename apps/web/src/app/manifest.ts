import type { MetadataRoute } from "next";

/** PWA manifest (MEP §64): installable shell; no offline claims for transactional features. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "في سكتي",
    short_name: "في سكتي",
    description: "لاقي ناس رايحين طريقك — مشاركة رحلات في العبور.",
    start_url: "/ar",
    scope: "/",
    id: "/",
    display: "standalone",
    orientation: "portrait-primary",
    background_color: "#CCF618",
    theme_color: "#1A1C16",
    dir: "rtl",
    lang: "ar",
    categories: ["travel", "social"],
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
