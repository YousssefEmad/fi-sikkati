import { getTranslations } from "next-intl/server";

import { AuthShell } from "@/features/auth/auth-shell";
import { SignInForm } from "@/features/auth/sign-in-form";

export default async function SignInPage({
  searchParams,
}: {
  searchParams: Promise<{ registered?: string }>;
}) {
  const t = await getTranslations("Auth");
  const params = await searchParams;
  const registered = params.registered === "1";

  return (
    <AuthShell title={t("signInTitle")} description={t("signInBody")}>
      {registered ? (
        <p className="border-border bg-surface-muted mb-5 rounded-xl border px-4 py-3 text-sm font-semibold">
          {t("registeredReady")}
        </p>
      ) : null}
      <SignInForm />
    </AuthShell>
  );
}
