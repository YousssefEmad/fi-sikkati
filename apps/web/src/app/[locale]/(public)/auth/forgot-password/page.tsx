import { getTranslations } from "next-intl/server";

import { AuthShell } from "@/features/auth/auth-shell";
import { ForgotPasswordForm } from "@/features/auth/forgot-password-form";

export default async function ForgotPasswordPage() {
  const t = await getTranslations("Auth");
  return (
    <AuthShell title={t("forgotTitle")} description={t("forgotBody")}>
      <ForgotPasswordForm />
    </AuthShell>
  );
}
