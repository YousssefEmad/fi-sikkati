import { Cairo, Plus_Jakarta_Sans } from "next/font/google";

/**
 * Arabic is the default locale, so Cairo (full Arabic + Latin coverage) carries the UI and
 * Plus Jakarta Sans gives the English pages a geometric, transport-app feel. Both are variable
 * fonts exposed as CSS variables and consumed by the `font-arabic` / `font-latin` utilities.
 */
export const cairo = Cairo({
  subsets: ["arabic", "latin"],
  display: "swap",
  variable: "--font-cairo",
});

export const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-jakarta",
});
