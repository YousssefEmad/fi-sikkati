import { getTranslations } from "next-intl/server";

import { AuthShell } from "@/features/auth/auth-shell";
import { PhoneAuthForm } from "@/features/auth/phone-auth-form";

export default async function PhoneAuthPage() {
  const t = await getTranslations("Auth");

  return (
    <AuthShell title={t("phoneTitle")} description={t("phoneBody")}>
      <PhoneAuthForm />
    </AuthShell>
  );
}
