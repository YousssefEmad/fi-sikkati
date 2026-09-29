"use client";

import { useLocale, useTranslations } from "next-intl";
import { useParams } from "next/navigation";
import { useId, type ChangeEvent } from "react";

import { usePathname, useRouter } from "@/i18n/navigation";
import { LOCALE_LABEL, routing, type Locale } from "@/i18n/routing";

/** Accessible language switch (NFR-01): a labelled native select, keyboard-operable by default. */
export function LanguageSwitcher() {
  const t = useTranslations("Common");
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const params = useParams();
  const id = useId();

  function onChange(event: ChangeEvent<HTMLSelectElement>) {
    const next = event.target.value as Locale;
    router.replace(
      // @ts-expect-error -- params are only known for dynamic routes at runtime
      { pathname, params },
      { locale: next },
    );
  }

  return (
    <label htmlFor={id} className="inline-flex items-center gap-2 text-sm">
      <span className="text-muted-foreground">{t("language")}</span>
      <select
        id={id}
        data-testid="language-switcher"
        value={locale}
        onChange={onChange}
        className="border-border bg-surface min-h-11 rounded-md border px-3 text-sm"
      >
        {routing.locales.map((code) => (
          <option key={code} value={code} lang={code}>
            {LOCALE_LABEL[code]}
          </option>
        ))}
      </select>
    </label>
  );
}
