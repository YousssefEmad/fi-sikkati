"use client";

import { useTranslations } from "next-intl";

import { SecurityPanel } from "@/features/account/security-panel";
import { RequireAccount } from "@/features/auth/require-account";
import { useSession } from "@/features/auth/session-provider";
import { Link } from "@/i18n/navigation";

function SecurityBody({
  passwordMinLength,
  deletionGraceDays,
}: {
  passwordMinLength: number;
  deletionGraceDays: number;
}) {
  const t = useTranslations("Account");
  const { account } = useSession();
  if (!account) return null;
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("securityTitle")}</h1>
      <p className="mt-4 text-sm">
        <Link href="/me" className="text-primary font-semibold underline-offset-4 hover:underline">
          {t("backToAccount")}
        </Link>
      </p>
      <div className="mt-8">
        <SecurityPanel
          account={account}
          passwordMinLength={passwordMinLength}
          deletionGraceDays={deletionGraceDays}
        />
      </div>
    </div>
  );
}

export function SecurityPageClient({
  passwordMinLength,
  deletionGraceDays,
}: {
  passwordMinLength: number;
  deletionGraceDays: number;
}) {
  return (
    <RequireAccount>
      <SecurityBody passwordMinLength={passwordMinLength} deletionGraceDays={deletionGraceDays} />
    </RequireAccount>
  );
}
