import type { MetadataRoute } from "next";

/** PWA manifest (MEP §64): installable shell; no offline claims for transactional features. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Fi Sikkati",
    short_name: "Fi Sikkati",
    description: "Find people already going your way.",
    start_url: "/ar",
    display: "standalone",
    background_color: "#CCF618",
    theme_color: "#1A1C16",
    dir: "rtl",
    lang: "ar",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
