import { getTranslations } from "next-intl/server";

import { AuthShell } from "@/features/auth/auth-shell";
import { SignInForm } from "@/features/auth/sign-in-form";

export default async function SignInPage() {
  const t = await getTranslations("Auth");
  return (
    <AuthShell title={t("signInTitle")} description={t("signInBody")}>
      <SignInForm />
    </AuthShell>
  );
}
