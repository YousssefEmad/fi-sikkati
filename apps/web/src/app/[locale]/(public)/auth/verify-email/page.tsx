import { getTranslations } from "next-intl/server";

import { AuthShell } from "@/features/auth/auth-shell";
import { VerifyEmailPanel } from "@/features/auth/verify-email-panel";

export default async function VerifyEmailPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const t = await getTranslations("Auth");
  const { token } = await searchParams;

  return (
    <AuthShell title={t("verifyTitle")} description={t("verifyBody")}>
      <VerifyEmailPanel token={token ?? ""} />
    </AuthShell>
  );
}
