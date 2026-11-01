import { getTranslations } from "next-intl/server";

import { AuthShell } from "@/features/auth/auth-shell";
import { Link } from "@/i18n/navigation";

export default async function CheckEmailPage() {
  const t = await getTranslations("Auth");
  return (
    <AuthShell title={t("checkEmailTitle")} description={t("checkEmailBody")}>
      <p className="text-muted-foreground text-sm">{t("checkEmailDevHint")}</p>
      <p className="mt-6 text-sm">
        <Link
          href="/auth/sign-in"
          className="text-primary font-semibold underline-offset-4 hover:underline"
        >
          {t("backToSignIn")}
        </Link>
      </p>
    </AuthShell>
  );
}
