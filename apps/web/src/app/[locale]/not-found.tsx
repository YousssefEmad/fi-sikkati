import { ArrowLeft } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { Logo } from "@/components/brand/logo";
import { Badge } from "@/components/ui/badge";
import { Link } from "@/i18n/navigation";

export default async function NotFoundPage() {
  const [t, tCommon] = await Promise.all([getTranslations("NotFound"), getTranslations("Common")]);

  return (
    <main
      id="main"
      className="hero-glow flex w-full flex-1 flex-col items-center justify-center px-4 py-24 text-center"
    >
      <Logo />
      <Badge variant="soft" size="sm" className="mt-10 font-mono">
        404
      </Badge>
      <h1 className="mt-5 text-3xl font-extrabold tracking-tight sm:text-4xl">{t("title")}</h1>
      <p className="text-muted-foreground mt-4 max-w-md leading-relaxed">{t("body")}</p>
      <Link
        href="/"
        className="bg-primary text-primary-foreground hover:bg-primary-hover shadow-card mt-9 inline-flex min-h-11 items-center gap-2 rounded-full px-6 text-sm font-semibold"
      >
        <ArrowLeft aria-hidden="true" className="size-4 rtl:rotate-180" />
        {tCommon("backHome")}
      </Link>
    </main>
  );
}
