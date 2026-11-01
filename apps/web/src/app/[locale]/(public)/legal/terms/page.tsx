import { getTranslations } from "next-intl/server";

import { fetchPublicConfig } from "@/features/platform/api";

export default async function TermsPage() {
  const t = await getTranslations("Legal");
  const config = await fetchPublicConfig();
  const version = config?.termsVersion ?? "2026-10-01";

  return (
    <article className="mx-auto w-full max-w-2xl px-4 py-14 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("termsTitle")}</h1>
      <p className="text-muted-foreground mt-2 text-sm">{t("version", { version })}</p>
      <div className="mt-8 flex flex-col gap-4 leading-relaxed">
        <p>{t("termsP1")}</p>
        <p>{t("termsP2")}</p>
        <p>{t("termsP3")}</p>
      </div>
    </article>
  );
}
