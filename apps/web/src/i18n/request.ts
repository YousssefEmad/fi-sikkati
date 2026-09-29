import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";
import { locale as getLocaleRootParam } from "next/root-params";

import { routing } from "./routing";

const DEFAULT_TIMEZONE = "Africa/Cairo";

/**
 * Per-request i18n configuration. The locale comes from the `[locale]` root param
 * (`next/root-params`, Next.js 16) unless an explicit override is passed to an async API such as
 * `getTranslations({ locale })`. Unknown values fall back to the default locale because the
 * `[locale]` segment also catches unknown top-level paths.
 */
export default getRequestConfig(async ({ locale: override }) => {
  const candidate = override ?? (await getLocaleRootParam());
  const locale = hasLocale(routing.locales, candidate) ? candidate : routing.defaultLocale;
  const messages = (await import(`../../messages/${locale}.json`)) as { default: object };

  return {
    locale,
    messages: messages.default as Record<string, unknown>,
    timeZone: DEFAULT_TIMEZONE,
    formats: {
      dateTime: {
        short: { day: "numeric", month: "short" },
        time: { hour: "numeric", minute: "2-digit" },
      },
      number: {
        currency: { style: "currency", currency: "EGP", maximumFractionDigits: 0 },
      },
    },
  };
});
