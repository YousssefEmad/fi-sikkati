import { getTranslations } from "next-intl/server";

import { AuthShell } from "@/features/auth/auth-shell";
import { ResetPasswordForm } from "@/features/auth/reset-password-form";
import { fetchPublicConfig } from "@/features/platform/api";

export default async function ResetPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const t = await getTranslations("Auth");
  const { token } = await searchParams;
  const config = await fetchPublicConfig();

  return (
    <AuthShell title={t("resetTitle")} description={t("resetBody")}>
      <ResetPasswordForm token={token ?? ""} passwordMinLength={config?.passwordMinLength ?? 10} />
    </AuthShell>
  );
}
