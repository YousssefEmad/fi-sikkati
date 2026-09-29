"use client";

import { useTranslations } from "next-intl";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";

/**
 * Route-level error boundary (MEP §80): never shows raw errors; offers retry and a reference id
 * that support can correlate with server logs.
 */
export default function LocaleError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("Error");

  useEffect(() => {
    // Error tracking SDK is wired in Phase 11; until then the digest is enough to correlate.
    console.error("route_error", { digest: error.digest });
  }, [error]);

  return (
    <main
      id="main"
      className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center px-4 py-24 text-center"
    >
      <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
      <p className="text-muted-foreground mt-4">{t("body")}</p>
      {error.digest ? (
        <p className="text-muted-foreground mt-2 font-mono text-xs">
          {t("reference", { id: error.digest })}
        </p>
      ) : null}
      <div className="mt-8">
        <Button onClick={reset}>{t("retry")}</Button>
      </div>
    </main>
  );
}
