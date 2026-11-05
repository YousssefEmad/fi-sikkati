"use client";

import { useTranslations } from "next-intl";

import { buttonVariants } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";

/**
 * Phone-first auth is prepared in the UI. Full OTP login still needs a production SMS provider
 * and dedicated login endpoints; until then we guide users to the normal register flow with phone.
 */
export function PhoneAuthForm() {
  const t = useTranslations("Auth");

  return (
    <div className="space-y-5">
      <p className="bg-brand-soft rounded-xl px-4 py-3 text-sm font-semibold leading-relaxed">
        {t("phoneStagingNote")}
      </p>
      <Link href="/auth/register" className={buttonVariants({ size: "lg", block: true })}>
        {t("phoneGoRegister")}
      </Link>
      <Link
        href="/auth/sign-in"
        className={buttonVariants({ size: "lg", variant: "outline", block: true })}
      >
        {t("phoneGoSignIn")}
      </Link>
    </div>
  );
}
