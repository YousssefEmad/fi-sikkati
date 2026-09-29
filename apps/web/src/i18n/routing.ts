import { defineRouting } from "next-intl/routing";

/** Arabic is the default and first-class locale (NFR-01). */
export const routing = defineRouting({
  locales: ["ar", "en"],
  defaultLocale: "ar",
  localePrefix: "always",
});

export type Locale = (typeof routing.locales)[number];

export const LOCALE_DIRECTION: Record<Locale, "rtl" | "ltr"> = {
  ar: "rtl",
  en: "ltr",
};

export const LOCALE_LABEL: Record<Locale, string> = {
  ar: "العربية",
  en: "English",
};
