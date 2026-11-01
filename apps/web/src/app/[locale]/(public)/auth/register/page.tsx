import { getTranslations } from "next-intl/server";

import { AuthShell } from "@/features/auth/auth-shell";
import { RegisterForm } from "@/features/auth/register-form";
import { fetchPublicConfig } from "@/features/platform/api";

export default async function RegisterPage() {
  const t = await getTranslations("Auth");
  const config = await fetchPublicConfig();

  return (
    <AuthShell title={t("registerTitle")} description={t("registerBody")}>
      <RegisterForm
        passwordMinLength={config?.passwordMinLength ?? 10}
        minimumAgeYears={config?.minimumAgeYears ?? 18}
        termsVersion={config?.termsVersion ?? "2026-10-01"}
        privacyVersion={config?.privacyVersion ?? "2026-10-01"}
      />
    </AuthShell>
  );
}
