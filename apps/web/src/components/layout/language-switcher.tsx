"use client";

import { Languages } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useParams } from "next/navigation";
import { useId, type ChangeEvent } from "react";

import { usePathname, useRouter } from "@/i18n/navigation";
import { LOCALE_LABEL, routing, type Locale } from "@/i18n/routing";
import { cn } from "@/lib/utils";

interface LanguageSwitcherProps {
  tone?: "default" | "inverse";
}

/** Accessible language switch (NFR-01): a labelled native select, keyboard-operable by default. */
export function LanguageSwitcher({ tone = "default" }: LanguageSwitcherProps) {
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
    <div
      className={cn(
        "inline-flex h-11 items-center gap-1.5 rounded-full border px-2.5 sm:gap-2 sm:px-3",
        tone === "inverse"
          ? "text-inverse-foreground border-white/20 bg-white/5"
          : "border-border-strong text-foreground bg-surface hover:bg-surface-muted",
      )}
    >
      <Languages aria-hidden="true" className="size-4 shrink-0 opacity-80" />
      <label htmlFor={id} className="sr-only">
        {t("language")}
      </label>
      <select
        id={id}
        data-testid="language-switcher"
        value={locale}
        onChange={onChange}
        className="cursor-pointer appearance-none bg-transparent pe-1 text-sm font-bold outline-none"
      >
        {routing.locales.map((code) => (
          <option key={code} value={code} lang={code} className="text-foreground">
            {LOCALE_LABEL[code]}
          </option>
        ))}
      </select>
    </div>
  );
}
