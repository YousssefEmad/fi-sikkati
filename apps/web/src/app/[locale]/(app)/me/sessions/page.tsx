"use client";

import { useTranslations } from "next-intl";

import { SessionsPanel } from "@/features/account/sessions-panel";
import { RequireAccount } from "@/features/auth/require-account";
import { Link } from "@/i18n/navigation";

function SessionsBody() {
  const t = useTranslations("Account");
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("sessionsTitle")}</h1>
      <p className="text-muted-foreground mt-2">{t("sessionsBody")}</p>
      <p className="mt-4 text-sm">
        <Link href="/me" className="text-primary font-semibold underline-offset-4 hover:underline">
          {t("backToAccount")}
        </Link>
      </p>
      <div className="mt-8">
        <SessionsPanel />
      </div>
    </div>
  );
}

export default function SessionsPage() {
  return (
    <RequireAccount>
      <SessionsBody />
    </RequireAccount>
  );
}
