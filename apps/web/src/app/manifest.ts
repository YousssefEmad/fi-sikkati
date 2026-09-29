import type { MetadataRoute } from "next";

/** PWA manifest (MEP §64): installable shell; no offline claims for transactional features. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Fi Sikkati",
    short_name: "Fi Sikkati",
    description: "Find people already going your way.",
    start_url: "/ar",
    display: "standalone",
    background_color: "#faf8f4",
    theme_color: "#1f5f6b",
    dir: "rtl",
    lang: "ar",
    // Placeholder vector icon until branded PNG/maskable icons are produced (tracked in
    // docs/project-status.md, Phase 11 polish).
    icons: [{ src: "/icons/icon.svg", sizes: "any", type: "image/svg+xml" }],
  };
}
