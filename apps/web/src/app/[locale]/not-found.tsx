import { getTranslations } from "next-intl/server";

import { Link } from "@/i18n/navigation";

export default async function NotFoundPage() {
  const [t, tCommon] = await Promise.all([getTranslations("NotFound"), getTranslations("Common")]);

  return (
    <main
      id="main"
      className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center px-4 py-24 text-center"
    >
      <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
      <p className="text-muted-foreground mt-4">{t("body")}</p>
      <Link href="/" className="text-primary mt-8 font-semibold underline-offset-4 hover:underline">
        {tCommon("backHome")}
      </Link>
    </main>
  );
}
